#!/bin/bash

# このスクリプトはローカルマシンから実行してください
# EC2_KEY_PATH と EC2_IP を設定してから実行

EC2_KEY_PATH="~/.ssh/your-key.pem"  # SSH鍵のパスを設定
EC2_IP="3.115.141.166"
EC2_USER="ubuntu"

echo "EC2インスタンスに接続して502エラーを修正します..."
echo "使用する鍵: $EC2_KEY_PATH"
echo "接続先: $EC2_USER@$EC2_IP"

# リモートで修正コマンドを実行
ssh -i "$EC2_KEY_PATH" "$EC2_USER@$EC2_IP" << 'REMOTE_SCRIPT'

set -e

echo "===  EC2での修正を開始 ==="

cd ~/video-message-app/video-message-app

# Dockerコンテナを確認・起動
echo "Dockerコンテナの状態を確認..."
sudo docker-compose ps

# 必要に応じてコンテナを起動
sudo docker-compose up -d

# Nginx設定を修正
echo "Nginx設定を更新..."
sudo tee /etc/nginx/sites-available/video-app-ssl > /dev/null << 'NGINX'
server {
    listen 443 ssl;
    server_name 3.115.141.166;
    
    ssl_certificate /home/ubuntu/video-message-app/video-message-app/ssl/server.crt;
    ssl_certificate_key /home/ubuntu/video-message-app/video-message-app/ssl/server.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    root /home/ubuntu/video-message-app/video-message-app/frontend/build;
    index index.html;
    
    location /api/ {
        proxy_pass http://127.0.0.1:55433/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:55434/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}

server {
    listen 80;
    server_name 3.115.141.166;
    return 301 https://$server_name$request_uri;
}
NGINX

# Nginx設定を有効化して再起動
sudo ln -sf /etc/nginx/sites-available/video-app-ssl /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# ヘルスチェック
echo "ヘルスチェック..."
curl -s http://localhost:55433/health || echo "バックエンドエラー"
curl -k -s https://localhost/api/health || echo "HTTPS APIエラー"

echo "=== 修正完了 ==="

REMOTE_SCRIPT

echo "修正が完了しました。"
echo "ブラウザで https://3.115.141.166 にアクセスしてください。"