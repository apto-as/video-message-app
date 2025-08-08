#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== EC2 502エラー修正スクリプト ===${NC}"
echo -e "${YELLOW}このスクリプトをEC2インスタンスで実行してください${NC}"

# プロジェクトディレクトリに移動
cd ~/video-message-app/video-message-app

# 1. Docker サービスが起動しているか確認
echo -e "${YELLOW}Dockerサービスの状態を確認...${NC}"
if ! sudo docker ps > /dev/null 2>&1; then
    echo -e "${YELLOW}Docker Desktop を起動します...${NC}"
    open -a Docker || true
    echo "Dockerの起動を待機中..."
    sleep 30
fi

# 2. コンテナの状態を確認
echo -e "${YELLOW}コンテナの状態を確認...${NC}"
sudo docker-compose ps

# 3. コンテナが停止している場合は起動
if ! sudo docker ps | grep -q voice_backend; then
    echo -e "${YELLOW}バックエンドコンテナを起動...${NC}"
    sudo docker-compose up -d backend
    sleep 15
fi

if ! sudo docker ps | grep -q voicevox_engine; then
    echo -e "${YELLOW}VoiceVoxエンジンを起動...${NC}"
    sudo docker-compose up -d voicevox
    sleep 15
fi

# 4. Nginx設定ファイルを作成/更新
echo -e "${YELLOW}Nginx設定を更新...${NC}"

sudo tee /etc/nginx/sites-available/video-app-ssl > /dev/null << 'NGINX_CONFIG'
server {
    listen 443 ssl;
    server_name 3.115.141.166;
    
    ssl_certificate /home/ubuntu/video-message-app/video-message-app/ssl/server.crt;
    ssl_certificate_key /home/ubuntu/video-message-app/video-message-app/ssl/server.key;
    
    # SSL設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ログファイル
    access_log /var/log/nginx/video-app-access.log;
    error_log /var/log/nginx/video-app-error.log;
    
    # フロントエンドの静的ファイル
    root /home/ubuntu/video-message-app/video-message-app/frontend/build;
    index index.html;
    
    # APIプロキシ設定
    location /api/ {
        proxy_pass http://localhost:55433/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # バッファサイズ設定
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # WebSocket設定
    location /ws {
        proxy_pass http://localhost:55434/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # React Router対応
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# HTTPからHTTPSへリダイレクト
server {
    listen 80;
    server_name 3.115.141.166;
    return 301 https://$server_name$request_uri;
}
NGINX_CONFIG

# 5. Nginx設定を有効化
echo -e "${YELLOW}Nginx設定を有効化...${NC}"
sudo ln -sf /etc/nginx/sites-available/video-app-ssl /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 6. Nginx設定をテスト
echo -e "${YELLOW}Nginx設定をテスト...${NC}"
sudo nginx -t

# 7. Nginxを再起動
echo -e "${YELLOW}Nginxを再起動...${NC}"
sudo systemctl restart nginx

# 8. サービスの状態を確認
echo -e "${YELLOW}サービスの状態を確認...${NC}"
sleep 5

# バックエンドのヘルスチェック
echo -e "${YELLOW}バックエンドのヘルスチェック...${NC}"
if curl -s http://localhost:55433/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ バックエンド: 正常${NC}"
else
    echo -e "${RED}✗ バックエンド: エラー${NC}"
    sudo docker logs voice_backend --tail 20
fi

# VoiceVoxのヘルスチェック
echo -e "${YELLOW}VoiceVoxのヘルスチェック...${NC}"
if curl -s http://localhost:50021/speakers | head -c 10 > /dev/null; then
    echo -e "${GREEN}✓ VoiceVox: 正常${NC}"
else
    echo -e "${RED}✗ VoiceVox: エラー${NC}"
    sudo docker logs voicevox_engine --tail 20
fi

# API経由でのテスト
echo -e "${YELLOW}API経由でのテスト...${NC}"
if curl -k -s https://localhost/api/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ HTTPS API: 正常${NC}"
else
    echo -e "${RED}✗ HTTPS API: エラー${NC}"
fi

echo -e "${GREEN}=== 修正完了 ===${NC}"
echo -e "${BLUE}URL: https://3.115.141.166${NC}"
echo -e "${YELLOW}ブラウザをリロードしてください${NC}"