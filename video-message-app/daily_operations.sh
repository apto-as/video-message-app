#!/bin/bash

# 日次運用スクリプト
# 朝と夜の定型作業を自動化

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EC2_CONTROL="$SCRIPT_DIR/ec2_control.sh"

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 現在時刻を取得
HOUR=$(date +%H)

morning_routine() {
    echo -e "${YELLOW}☀️  Good Morning! Starting your development environment...${NC}"
    echo "=================================================="
    
    # EC2インスタンスを起動
    echo -e "\n${BLUE}1. Starting EC2 instance...${NC}"
    $EC2_CONTROL start
    
    # ステータス確認
    echo -e "\n${BLUE}2. Checking service status...${NC}"
    $EC2_CONTROL status
    
    echo -e "\n${GREEN}✨ Morning routine completed!${NC}"
    echo "Your development environment is ready."
    echo ""
    echo "Quick commands:"
    echo "  Deploy code:  ./deploy_to_ec2.sh"
    echo "  SSH access:   ./ec2_control.sh ssh"
    echo "  View logs:    ./ec2_control.sh logs"
}

evening_routine() {
    echo -e "${YELLOW}🌙 Good Evening! Shutting down to save costs...${NC}"
    echo "=================================================="
    
    # ステータス確認
    echo -e "\n${BLUE}1. Current status check...${NC}"
    $EC2_CONTROL status
    
    # EC2インスタンスを停止
    echo -e "\n${BLUE}2. Stopping EC2 instance...${NC}"
    $EC2_CONTROL stop
    
    echo -e "\n${GREEN}✨ Evening routine completed!${NC}"
    echo "💰 Your EC2 instance is stopped. You're saving money!"
    echo ""
    echo "To start again tomorrow:"
    echo "  ./daily_operations.sh morning"
}

status_check() {
    echo -e "${BLUE}📊 Checking current status...${NC}"
    echo "================================"
    $EC2_CONTROL status
}

# メインロジック
case "$1" in
    morning|start)
        morning_routine
        ;;
    evening|night|stop)
        evening_routine
        ;;
    status)
        status_check
        ;;
    *)
        # 引数がない場合は時間帯で判断
        if [ -z "$1" ]; then
            if [ $HOUR -ge 6 ] && [ $HOUR -lt 12 ]; then
                echo "It's morning. Starting services..."
                morning_routine
            elif [ $HOUR -ge 18 ] || [ $HOUR -lt 6 ]; then
                echo "It's evening/night. Ready to stop services?"
                evening_routine
            else
                echo "Checking current status..."
                status_check
            fi
        else
            echo "Usage: $0 [morning|evening|status]"
            echo ""
            echo "Commands:"
            echo "  morning  - Start EC2 instance and all services"
            echo "  evening  - Stop EC2 instance to save costs"
            echo "  status   - Check current status"
            echo ""
            echo "Without arguments, the script will suggest action based on time of day."
        fi
        ;;
esac