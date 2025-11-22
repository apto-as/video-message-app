#!/bin/bash

# Let's Encrypt SSL証明書のセットアップスクリプト
# 現在の構成への影響を最小限にしつつ、正規のSSL証明書を設定

set -e

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Let's Encrypt SSL証明書セットアップ ===${NC}"

# ドメイン名の入力を求める
read -p "使用するドメイン名を入力してください (例: app.example.com): " DOMAIN_NAME
if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}エラー: ドメイン名が入力されていません${NC}"
    exit 1
fi

read -p "メールアドレスを入力してください (Let's Encrypt通知用): " EMAIL
if [ -z "$EMAIL" ]; then
    echo -e "${RED}エラー: メールアドレスが入力されていません${NC}"
    exit 1
fi

# EC2インスタンスに接続してセットアップ
echo -e "${YELLOW}EC2インスタンスでLet's Encryptをセットアップ中...${NC}"

# EC2での作業をリモート実行
cat << 'REMOTE_SCRIPT' > /tmp/setup_letsencrypt_remote.sh
#!/bin/bash

DOMAIN_NAME="$1"
EMAIL="$2"

# Certbotのインストール
echo "Installing Certbot..."
sudo dnf install -y certbot python3-certbot-nginx

# 一時的にNginxの設定を変更してHTTP検証を有効にする
echo "Creating temporary Nginx configuration for verification..."
sudo tee /tmp/nginx_letsencrypt.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}
EOF

# ドメイン名を置換
sudo sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN_NAME/" /tmp/nginx_letsencrypt.conf

# Certbot用のディレクトリを作成
sudo mkdir -p /var/www/certbot

# 既存のDockerコンテナを停止（ポート80を解放）
cd /home/ec2-user/video-message-app/video-message-app
sudo docker-compose stop nginx

# スタンドアロンモードでCertbotを実行
echo "Obtaining SSL certificate..."
sudo certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --domains $DOMAIN_NAME \
    --non-interactive

# 証明書が正常に取得されたか確認
if [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    echo "SSL certificate obtained successfully!"
    
    # 証明書をDockerで使用できる場所にコピー
    sudo mkdir -p /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt
    sudo cp /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt/
    sudo cp /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt/
    sudo chown -R ec2-user:ec2-user /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt
    
    echo "Certificates copied to Docker volume directory"
else
    echo "Failed to obtain SSL certificate"
    exit 1
fi

# 自動更新用のcronジョブを設定
echo "Setting up auto-renewal..."
(sudo crontab -l 2>/dev/null; echo "0 0,12 * * * /usr/bin/certbot renew --quiet --post-hook '/home/ec2-user/video-message-app/video-message-app/update_ssl_cert.sh'") | sudo crontab -

echo "Setup complete!"
REMOTE_SCRIPT

# リモートスクリプトを実行
echo "$DOMAIN_NAME" > /tmp/domain.txt
echo "$EMAIL" > /tmp/email.txt
./ec2_control.sh upload /tmp/setup_letsencrypt_remote.sh /tmp/setup_letsencrypt_remote.sh
echo "chmod +x /tmp/setup_letsencrypt_remote.sh && /tmp/setup_letsencrypt_remote.sh '$DOMAIN_NAME' '$EMAIL'" | ./ec2_control.sh ssh

# Nginx設定の更新
echo -e "${YELLOW}Nginx設定を更新中...${NC}"

# 新しいNginx設定を作成（Let's Encrypt証明書を使用）
cat << EOF > nginx/default_letsencrypt.conf
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN_NAME;
    
    # Let's Encrypt証明書を使用
    ssl_certificate /etc/nginx/ssl/letsencrypt/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/letsencrypt/privkey.pem;
    
    # 強力なSSL設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    client_max_body_size 100M;
    
    # フロントエンド
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # バックエンドAPI
    location /api/ {
        proxy_pass http://backend:55433/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

echo -e "${GREEN}Let's Encrypt設定用のファイルが作成されました${NC}"
echo ""
echo -e "${YELLOW}次のステップ:${NC}"
echo "1. ドメイン($DOMAIN_NAME)のDNS設定でEC2インスタンスのIPアドレスを指定してください"
echo "2. docker-compose.ymlを更新して新しい設定を使用するようにしてください:"
echo "   - nginx/default.conf -> nginx/default_letsencrypt.conf"
echo "   - ssl/letsencrypt/をマウント"
echo "3. docker-compose up -d で再起動してください"