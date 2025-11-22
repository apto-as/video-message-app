#!/bin/bash

# Let's Encrypt証明書更新後の処理スクリプト
# Certbotの自動更新後に実行される

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}SSL証明書を更新中...${NC}"

# ドメイン名を取得（最初のLet's Encryptディレクトリから）
DOMAIN=$(ls -1 /etc/letsencrypt/live/ | head -n 1)

if [ -z "$DOMAIN" ]; then
    echo "Error: No Let's Encrypt certificate found"
    exit 1
fi

# 新しい証明書をDockerボリュームにコピー
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt/
sudo chown -R ec2-user:ec2-user /home/ec2-user/video-message-app/video-message-app/ssl/letsencrypt

# Nginxコンテナをリロード
cd /home/ec2-user/video-message-app/video-message-app
docker-compose exec nginx nginx -s reload

echo -e "${GREEN}SSL証明書が正常に更新されました${NC}"