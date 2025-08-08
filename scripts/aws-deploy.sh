#!/bin/bash

# AWS EC2 デプロイスクリプト
# 使い方: ./aws-deploy.sh

set -e

# 設定（環境変数または直接設定）
EC2_IP="${EC2_IP:-YOUR_EC2_IP_HERE}"
KEY_FILE="${SSH_KEY:-~/.ssh/your-key.pem}"
REPO_DIR="video-message-app"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Starting deployment to AWS EC2...${NC}"

# EC2_IPチェック
if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
    echo -e "${RED}Error: Please set EC2_IP environment variable or edit this script${NC}"
    echo "Example: export EC2_IP=54.123.45.67"
    exit 1
fi

# キーファイルチェック
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}Error: SSH key file not found: $KEY_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}📡 Connecting to EC2: $EC2_IP${NC}"

# デプロイ実行
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" ubuntu@"$EC2_IP" << ENDSSH
    set -e
    echo "📂 Navigating to application directory..."
    cd $REPO_DIR

    echo "📥 Pulling latest changes from Git..."
    git pull

    echo "🛑 Stopping current containers..."
    docker compose down

    echo "🔨 Building containers (if needed)..."
    docker compose build

    echo "🚀 Starting containers..."
    docker compose up -d

    echo "⏳ Waiting for services to start..."
    sleep 5

    echo "✅ Checking container status..."
    docker compose ps

    echo "📊 Recent logs:"
    docker compose logs --tail=20
ENDSSH

echo -e "${GREEN}✨ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}📱 Application URLs:${NC}"
echo -e "  Frontend: ${GREEN}http://$EC2_IP:55434${NC}"
echo -e "  Backend:  ${GREEN}http://$EC2_IP:55433${NC}"
echo -e "  VoiceVox: ${GREEN}http://$EC2_IP:50021${NC}"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "  Check logs:  ssh -i $KEY_FILE ubuntu@$EC2_IP 'cd $REPO_DIR && docker compose logs -f'"
echo "  SSH login:   ssh -i $KEY_FILE ubuntu@$EC2_IP"
echo "  Stop EC2:    aws ec2 stop-instances --instance-ids <INSTANCE_ID>"