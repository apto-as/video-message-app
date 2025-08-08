#!/bin/bash

# AWS Simple Setup Script for Video Message App
# 開発環境用の簡単セットアップスクリプト

set -e

echo "========================================="
echo "Video Message App - AWS Setup Script"
echo "========================================="

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 関数定義
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    fi
}

# 1. 前提条件チェック
echo -e "\n${YELLOW}1. Checking prerequisites...${NC}"
check_command terraform
check_command aws

# AWS認証情報チェック
echo -e "\n${YELLOW}Checking AWS credentials...${NC}"
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}✅ AWS credentials configured${NC}"
    aws sts get-caller-identity --output table
else
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

# 2. Terraform初期化
echo -e "\n${YELLOW}2. Initializing Terraform...${NC}"
terraform init

# 3. 変数設定
echo -e "\n${YELLOW}3. Setting up variables...${NC}"
if [ ! -f terraform.tfvars ]; then
    cp terraform.tfvars.example terraform.tfvars
    echo -e "${YELLOW}Please edit terraform.tfvars with your settings${NC}"
    echo "Especially set your key_name for EC2 access"
    read -p "Press enter when ready..."
fi

# 4. Plan確認
echo -e "\n${YELLOW}4. Creating Terraform plan...${NC}"
terraform plan -out=tfplan

# 5. 実行確認
echo -e "\n${YELLOW}5. Ready to create resources${NC}"
echo "This will create:"
echo "  - 1 EC2 instance (t3.large)"
echo "  - 1 Elastic IP"
echo "  - 1 Security Group"
echo "  - 1 S3 bucket for backups"
echo ""
echo -e "${YELLOW}Estimated monthly cost: \$44-85${NC}"
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

# 6. Terraform実行
echo -e "\n${YELLOW}6. Creating AWS resources...${NC}"
terraform apply tfplan

# 7. 出力情報取得
echo -e "\n${YELLOW}7. Getting connection information...${NC}"
PUBLIC_IP=$(terraform output -raw instance_public_ip)
INSTANCE_ID=$(terraform output -raw instance_id)
S3_BUCKET=$(terraform output -raw s3_bucket_name)

# 8. 接続情報表示
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "S3 Bucket: $S3_BUCKET"
echo ""
echo "SSH Command:"
echo "  ssh -i your-key.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Application URLs (after deployment):"
echo "  Frontend: http://$PUBLIC_IP:55434"
echo "  Backend:  http://$PUBLIC_IP:55433"
echo "  VoiceVox: http://$PUBLIC_IP:50021"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. SSH into the instance"
echo "2. Clone your repository"
echo "3. Run docker-compose up -d"
echo ""
echo -e "${GREEN}Enjoy your development environment!${NC}"

# 9. デプロイスクリプト生成
cat > deploy.sh << EOF
#!/bin/bash
# Auto-generated deployment script

PUBLIC_IP=$PUBLIC_IP
KEY_FILE=\${1:-your-key.pem}

echo "Deploying to \$PUBLIC_IP..."

# リポジトリクローンとセットアップ
ssh -i \$KEY_FILE ubuntu@\$PUBLIC_IP << 'ENDSSH'
    # アプリケーションディレクトリ作成
    mkdir -p /home/ubuntu/apps
    cd /home/ubuntu/apps
    
    # Gitクローン（または更新）
    if [ ! -d video-message-app ]; then
        git clone https://github.com/your-repo/video-message-app.git
    else
        cd video-message-app
        git pull
    fi
    
    cd video-message-app
    
    # 環境変数設定
    if [ ! -f backend/.env ]; then
        echo "Please set up backend/.env with your API keys"
    fi
    
    # Docker Compose起動
    docker compose down
    docker compose up -d
    
    # ステータス確認
    docker compose ps
ENDSSH

echo "Deployment complete!"
echo "Frontend: http://\$PUBLIC_IP:55434"
echo "Backend:  http://\$PUBLIC_IP:55433"
EOF

chmod +x deploy.sh

echo -e "\n${GREEN}Generated deploy.sh for easy deployment${NC}"