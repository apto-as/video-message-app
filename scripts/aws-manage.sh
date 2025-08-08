#!/bin/bash

# AWS EC2 管理スクリプト
# 使い方: ./aws-manage.sh [start|stop|status|logs|ssh]

set -e

# 設定
EC2_IP="${EC2_IP:-YOUR_EC2_IP_HERE}"
INSTANCE_ID="${INSTANCE_ID:-YOUR_INSTANCE_ID_HERE}"
KEY_FILE="${SSH_KEY:-~/.ssh/your-key.pem}"
REPO_DIR="video-message-app"
REGION="${AWS_REGION:-ap-northeast-1}"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 使い方表示
usage() {
    echo -e "${YELLOW}AWS EC2 Management Script${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start EC2 instance"
    echo "  stop     - Stop EC2 instance"
    echo "  status   - Check instance status"
    echo "  logs     - View application logs"
    echo "  ssh      - SSH into EC2"
    echo "  deploy   - Deploy latest code"
    echo "  backup   - Backup data to S3"
    echo "  info     - Show instance information"
    echo ""
    echo "Environment variables:"
    echo "  EC2_IP       - EC2 public IP address"
    echo "  INSTANCE_ID  - EC2 instance ID"
    echo "  SSH_KEY      - Path to SSH key file"
    echo ""
    exit 0
}

# インスタンス開始
start_instance() {
    echo -e "${YELLOW}Starting EC2 instance...${NC}"
    aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    echo "Waiting for instance to start..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    # 新しいIPアドレスを取得
    NEW_IP=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo -e "${GREEN}✅ Instance started!${NC}"
    echo -e "Public IP: ${GREEN}$NEW_IP${NC}"
    echo ""
    echo "Update your EC2_IP:"
    echo "  export EC2_IP=$NEW_IP"
}

# インスタンス停止
stop_instance() {
    echo -e "${YELLOW}Stopping EC2 instance...${NC}"
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    echo "Waiting for instance to stop..."
    aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    echo -e "${GREEN}✅ Instance stopped!${NC}"
}

# ステータス確認
check_status() {
    echo -e "${YELLOW}Checking instance status...${NC}"
    
    STATE=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)
    
    if [ "$STATE" = "running" ]; then
        echo -e "Status: ${GREEN}$STATE${NC}"
        
        # アプリケーションステータス確認
        if [ "$EC2_IP" != "YOUR_EC2_IP_HERE" ]; then
            echo ""
            echo "Checking application status..."
            ssh -o ConnectTimeout=5 -i "$KEY_FILE" "ubuntu@$EC2_IP" \
                "cd $REPO_DIR && docker compose ps" 2>/dev/null || \
                echo -e "${RED}Cannot connect to EC2${NC}"
        fi
    else
        echo -e "Status: ${RED}$STATE${NC}"
    fi
}

# ログ表示
show_logs() {
    if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
        echo -e "${RED}Error: EC2_IP not set${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Showing application logs...${NC}"
    ssh -i "$KEY_FILE" "ubuntu@$EC2_IP" \
        "cd $REPO_DIR && docker compose logs -f --tail=100"
}

# SSH接続
ssh_connect() {
    if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
        echo -e "${RED}Error: EC2_IP not set${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Connecting to EC2...${NC}"
    ssh -i "$KEY_FILE" "ubuntu@$EC2_IP"
}

# デプロイ
deploy() {
    if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
        echo -e "${RED}Error: EC2_IP not set${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Deploying to EC2...${NC}"
    ssh -i "$KEY_FILE" "ubuntu@$EC2_IP" << 'ENDSSH'
        cd video-message-app
        git pull
        docker compose down
        docker compose up -d
        docker compose ps
ENDSSH
    echo -e "${GREEN}✅ Deployment complete!${NC}"
}

# バックアップ
backup() {
    if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
        echo -e "${RED}Error: EC2_IP not set${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Creating backup...${NC}"
    DATE=$(date +%Y%m%d_%H%M%S)
    
    ssh -i "$KEY_FILE" "ubuntu@$EC2_IP" << ENDSSH
        cd video-message-app
        tar -czf /tmp/backup_$DATE.tar.gz data/
        aws s3 cp /tmp/backup_$DATE.tar.gz s3://your-backup-bucket/backups/
        rm /tmp/backup_$DATE.tar.gz
        echo "Backup created: backup_$DATE.tar.gz"
ENDSSH
    echo -e "${GREEN}✅ Backup complete!${NC}"
}

# インスタンス情報
show_info() {
    echo -e "${YELLOW}Instance Information:${NC}"
    echo "Instance ID: $INSTANCE_ID"
    echo "Region: $REGION"
    echo "EC2 IP: $EC2_IP"
    echo "SSH Key: $KEY_FILE"
    echo ""
    
    if [ "$INSTANCE_ID" != "YOUR_INSTANCE_ID_HERE" ]; then
        aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --region "$REGION" \
            --query 'Reservations[0].Instances[0].{ID:InstanceId,Type:InstanceType,State:State.Name,IP:PublicIpAddress,LaunchTime:LaunchTime}' \
            --output table
    fi
}

# メイン処理
case "$1" in
    start)
        start_instance
        ;;
    stop)
        stop_instance
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    ssh)
        ssh_connect
        ;;
    deploy)
        deploy
        ;;
    backup)
        backup
        ;;
    info)
        show_info
        ;;
    *)
        usage
        ;;
esac