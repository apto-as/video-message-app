#!/bin/bash

# HTTPSセットアップスクリプト

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== HTTPSセットアップ ===${NC}"
echo -e "${YELLOW}どの方法を使用しますか？${NC}"
echo "1) Let's Encrypt (ドメイン必要)"
echo "2) 自己署名証明書 (テスト用)"
echo "3) ngrok (一時的)"
read -p "選択 (1-3): " choice

case $choice in
  1)
    echo -e "${YELLOW}ドメイン名を入力してください:${NC}"
    read domain
    
    # Nginxインストール
    sudo apt update
    sudo apt install -y nginx certbot python3-certbot-nginx
    
    # Nginx設定
    sudo tee /etc/nginx/sites-available/video-app > /dev/null <<EOF
server {
    listen 80;
    server_name $domain;

    location / {
        proxy_pass http://localhost:55434;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:55433/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/video-app /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    
    # SSL証明書取得
    sudo certbot --nginx -d $domain
    
    echo -e "${GREEN}HTTPS設定完了！${NC}"
    echo -e "URL: https://$domain"
    ;;
    
  2)
    echo -e "${YELLOW}自己署名証明書を作成...${NC}"
    
    sudo apt update
    sudo apt install -y nginx
    
    # 証明書作成
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/ssl/private/selfsigned.key \
      -out /etc/ssl/certs/selfsigned.crt \
      -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Dev/CN=localhost"
    
    # Nginx設定
    sudo tee /etc/nginx/sites-available/video-app-ssl > /dev/null <<'EOF'
server {
    listen 443 ssl;
    server_name _;
    
    ssl_certificate /etc/ssl/certs/selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/selfsigned.key;
    
    location / {
        proxy_pass http://localhost:55434;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        proxy_pass http://localhost:55433/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/video-app-ssl /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    
    echo -e "${GREEN}自己署名証明書でHTTPS設定完了！${NC}"
    echo -e "${YELLOW}警告: ブラウザで警告が表示されますが、「詳細設定」から進めばアクセス可能です${NC}"
    echo -e "URL: https://3.115.141.166"
    ;;
    
  3)
    echo -e "${YELLOW}ngrokをセットアップ...${NC}"
    
    # ngrokダウンロード
    if [ ! -f "ngrok" ]; then
        wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
        tar xvzf ngrok-v3-stable-linux-amd64.tgz
    fi
    
    echo -e "${GREEN}ngrokを起動します...${NC}"
    echo -e "${YELLOW}注意: このターミナルを閉じるとHTTPSが停止します${NC}"
    ./ngrok http 55434
    ;;
    
  *)
    echo -e "${RED}無効な選択です${NC}"
    exit 1
    ;;
esac