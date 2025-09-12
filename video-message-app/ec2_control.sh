#!/bin/bash

# EC2インスタンス制御スクリプト
# 夜に停止、朝に起動するための便利スクリプト

EC2_INSTANCE_IP="3.115.141.166"
SSH_KEY="$HOME/.ssh/video-app-key.pem"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 {start|stop|restart|status|ssh|logs}"
    echo ""
    echo "Commands:"
    echo "  start   - EC2インスタンスを起動"
    echo "  stop    - EC2インスタンスを停止（コスト削減）"
    echo "  restart - EC2インスタンスを再起動"
    echo "  status  - インスタンスとサービスの状態確認"
    echo "  ssh     - EC2にSSH接続"
    echo "  logs    - サービスログを表示"
    exit 1
}

# AWS CLIがインストールされているか確認
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI is not installed${NC}"
        echo "Install with: brew install awscli"
        exit 1
    fi
}

# インスタンスIDを取得
get_instance_id() {
    aws ec2 describe-instances \
        --filters "Name=ip-address,Values=$EC2_INSTANCE_IP" \
        --query "Reservations[0].Instances[0].InstanceId" \
        --output text 2>/dev/null
}

# インスタンスを起動
start_instance() {
    check_aws_cli
    local instance_id=$(get_instance_id)
    
    if [ -z "$instance_id" ] || [ "$instance_id" = "None" ]; then
        echo -e "${RED}Error: Instance not found for IP $EC2_INSTANCE_IP${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Starting EC2 instance: $instance_id${NC}"
    aws ec2 start-instances --instance-ids "$instance_id"
    
    echo "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids "$instance_id"
    
    # 新しいパブリックIPを取得
    local new_ip=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query "Reservations[0].Instances[0].PublicIpAddress" \
        --output text)
    
    echo -e "${GREEN}✅ Instance started successfully!${NC}"
    echo -e "New Public IP: ${YELLOW}$new_ip${NC}"
    
    # IPが変わった場合の警告
    if [ "$new_ip" != "$EC2_INSTANCE_IP" ]; then
        echo -e "${YELLOW}⚠️  Warning: Public IP has changed!${NC}"
        echo "Old IP: $EC2_INSTANCE_IP"
        echo "New IP: $new_ip"
        echo "You may need to update DNS records or configurations."
    fi
    
    echo ""
    echo "Waiting for services to start (30 seconds)..."
    sleep 30
    
    # サービス状態確認
    check_services "$new_ip"
}

# インスタンスを停止
stop_instance() {
    check_aws_cli
    local instance_id=$(get_instance_id)
    
    if [ -z "$instance_id" ] || [ "$instance_id" = "None" ]; then
        echo -e "${RED}Error: Instance not found for IP $EC2_INSTANCE_IP${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Stopping EC2 instance: $instance_id${NC}"
    echo "This will save costs while the instance is stopped."
    
    # 確認プロンプト
    read -p "Are you sure you want to stop the instance? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    aws ec2 stop-instances --instance-ids "$instance_id"
    
    echo "Waiting for instance to stop..."
    aws ec2 wait instance-stopped --instance-ids "$instance_id"
    
    echo -e "${GREEN}✅ Instance stopped successfully!${NC}"
    echo "💰 You are now saving money on compute costs!"
}

# インスタンスを再起動
restart_instance() {
    check_aws_cli
    local instance_id=$(get_instance_id)
    
    if [ -z "$instance_id" ] || [ "$instance_id" = "None" ]; then
        echo -e "${RED}Error: Instance not found for IP $EC2_INSTANCE_IP${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Restarting EC2 instance: $instance_id${NC}"
    aws ec2 reboot-instances --instance-ids "$instance_id"
    
    echo "Waiting for instance to be available..."
    sleep 60
    
    check_services "$EC2_INSTANCE_IP"
}

# サービス状態確認
check_services() {
    local ip=${1:-$EC2_INSTANCE_IP}
    
    echo -e "\n${YELLOW}Checking services on $ip...${NC}"
    
    # Backend
    if curl -s --max-time 5 "https://$ip/api/health" > /dev/null 2>&1; then
        echo -e "✅ Backend API: ${GREEN}Running${NC}"
    else
        echo -e "❌ Backend API: ${RED}Not responding${NC}"
    fi
    
    # OpenVoice (via SSH)
    if ssh -o ConnectTimeout=5 -i "$SSH_KEY" -p 22 "ec2-user@$ip" "curl -s http://localhost:8001/health" > /dev/null 2>&1; then
        echo -e "✅ OpenVoice: ${GREEN}Running${NC}"
    else
        echo -e "❌ OpenVoice: ${RED}Not responding${NC}"
    fi
    
    # Frontend
    if curl -s --max-time 5 "https://$ip" > /dev/null 2>&1; then
        echo -e "✅ Frontend: ${GREEN}Accessible${NC}"
    else
        echo -e "❌ Frontend: ${RED}Not accessible${NC}"
    fi
    
    echo ""
    echo -e "Access your application at: ${GREEN}https://$ip${NC}"
}

# インスタンス状態確認
check_status() {
    check_aws_cli
    local instance_id=$(get_instance_id)
    
    if [ -z "$instance_id" ] || [ "$instance_id" = "None" ]; then
        echo -e "${RED}Error: Instance not found for IP $EC2_INSTANCE_IP${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Instance Status for $instance_id:${NC}"
    
    local state=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query "Reservations[0].Instances[0].State.Name" \
        --output text)
    
    local public_ip=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query "Reservations[0].Instances[0].PublicIpAddress" \
        --output text)
    
    case $state in
        "running")
            echo -e "State: ${GREEN}$state${NC}"
            echo "Public IP: $public_ip"
            check_services "$public_ip"
            ;;
        "stopped")
            echo -e "State: ${YELLOW}$state${NC}"
            echo "💰 Instance is stopped (saving costs)"
            ;;
        "stopping"|"pending"|"shutting-down"|"terminated")
            echo -e "State: ${RED}$state${NC}"
            ;;
        *)
            echo -e "State: $state"
            ;;
    esac
}

# SSH接続
ssh_connect() {
    echo -e "${GREEN}Connecting to EC2 instance...${NC}"
    ssh -i "$SSH_KEY" -p 22 "ec2-user@$EC2_INSTANCE_IP"
}

# ログ表示
show_logs() {
    echo -e "${YELLOW}Showing service logs...${NC}"
    ssh -i "$SSH_KEY" -p 22 "ec2-user@$EC2_INSTANCE_IP" << 'ENDSSH'
echo "=== OpenVoice Logs ==="
sudo journalctl -u openvoice -n 20 --no-pager
echo ""
echo "=== Docker Compose Logs ==="
cd /home/ec2-user/video-message-app/video-message-app
docker-compose logs --tail=20
ENDSSH
}

# メインロジック
case "$1" in
    start)
        start_instance
        ;;
    stop)
        stop_instance
        ;;
    restart)
        restart_instance
        ;;
    status)
        check_status
        ;;
    ssh)
        ssh_connect
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        ;;
esac