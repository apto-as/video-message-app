#!/bin/bash

# GPU対応AWS環境管理スクリプト
# 使い方: ./gpu-manage.sh [command]

set -e

# 設定
REGION="${AWS_REGION:-ap-northeast-1}"
APP_INSTANCE_ID="${APP_INSTANCE_ID:-}"
GPU_INSTANCE_ID="${GPU_INSTANCE_ID:-}"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 使い方
usage() {
    echo -e "${YELLOW}GPU-Enabled AWS Management Script${NC}"
    echo ""
    echo "Commands:"
    echo "  start-all      - Start both app and GPU instances"
    echo "  start-app      - Start application server only"
    echo "  start-gpu      - Start GPU server only"
    echo "  stop-all       - Stop both instances"
    echo "  stop-app       - Stop application server"
    echo "  stop-gpu       - Stop GPU server (save money!)"
    echo "  status         - Show instance status"
    echo "  cost           - Show current cost estimate"
    echo "  gpu-info       - Show GPU utilization"
    echo "  connect-app    - SSH to app server"
    echo "  connect-gpu    - SSH to GPU server"
    echo ""
    exit 0
}

# インスタンスID取得（タグベース）
get_instance_ids() {
    if [ -z "$APP_INSTANCE_ID" ]; then
        APP_INSTANCE_ID=$(aws ec2 describe-instances \
            --filters "Name=tag:Type,Values=Application" "Name=tag:Environment,Values=dev" \
            --query 'Reservations[0].Instances[0].InstanceId' \
            --output text --region $REGION)
    fi
    
    if [ -z "$GPU_INSTANCE_ID" ]; then
        GPU_INSTANCE_ID=$(aws ec2 describe-instances \
            --filters "Name=tag:Type,Values=GPU" "Name=tag:Environment,Values=dev" \
            --query 'Reservations[0].Instances[0].InstanceId' \
            --output text --region $REGION)
    fi
}

# ステータス確認
check_status() {
    get_instance_ids
    
    echo -e "${YELLOW}Instance Status:${NC}"
    echo ""
    
    # アプリサーバー
    if [ "$APP_INSTANCE_ID" != "None" ] && [ -n "$APP_INSTANCE_ID" ]; then
        APP_STATE=$(aws ec2 describe-instances \
            --instance-ids $APP_INSTANCE_ID \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text --region $REGION 2>/dev/null || echo "not-found")
        
        APP_IP=$(aws ec2 describe-instances \
            --instance-ids $APP_INSTANCE_ID \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text --region $REGION 2>/dev/null || echo "N/A")
        
        if [ "$APP_STATE" = "running" ]; then
            echo -e "App Server:  ${GREEN}● $APP_STATE${NC} ($APP_IP)"
        else
            echo -e "App Server:  ${RED}● $APP_STATE${NC}"
        fi
    else
        echo -e "App Server:  ${RED}Not found${NC}"
    fi
    
    # GPUサーバー
    if [ "$GPU_INSTANCE_ID" != "None" ] && [ -n "$GPU_INSTANCE_ID" ]; then
        GPU_STATE=$(aws ec2 describe-instances \
            --instance-ids $GPU_INSTANCE_ID \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text --region $REGION 2>/dev/null || echo "not-found")
        
        GPU_IP=$(aws ec2 describe-instances \
            --instance-ids $GPU_INSTANCE_ID \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text --region $REGION 2>/dev/null || echo "N/A")
        
        if [ "$GPU_STATE" = "running" ]; then
            echo -e "GPU Server:  ${GREEN}● $GPU_STATE${NC} ($GPU_IP)"
        else
            echo -e "GPU Server:  ${RED}● $GPU_STATE${NC}"
        fi
    else
        echo -e "GPU Server:  ${RED}Not found${NC}"
    fi
}

# コスト計算
calculate_cost() {
    echo -e "${YELLOW}Cost Estimate:${NC}"
    echo ""
    
    # 現在の時刻（時間）
    CURRENT_HOUR=$(date +%H)
    
    # 今月の経過日数
    DAYS_PASSED=$(date +%d)
    
    # アプリサーバーコスト（t3.large = $0.10/hour）
    APP_HOURLY=0.10
    APP_HOURS=$((DAYS_PASSED * 8))  # 1日8時間想定
    APP_COST=$(echo "$APP_HOURS * $APP_HOURLY" | bc)
    
    # GPUサーバーコスト（g4dn.xlarge = $0.71/hour）
    GPU_HOURLY=0.71
    GPU_HOURS=$((DAYS_PASSED * 2))  # 1日2時間想定
    GPU_COST=$(echo "$GPU_HOURS * $GPU_HOURLY" | bc)
    
    # その他のコスト
    STORAGE_COST=10
    
    # 合計
    TOTAL=$(echo "$APP_COST + $GPU_COST + $STORAGE_COST" | bc)
    
    echo -e "App Server:   ${DAYS_PASSED}日 × 8時間 = ${APP_HOURS}時間 = ${GREEN}\$${APP_COST}${NC}"
    echo -e "GPU Server:   ${DAYS_PASSED}日 × 2時間 = ${GPU_HOURS}時間 = ${GREEN}\$${GPU_COST}${NC}"
    echo -e "Storage/EFS:  ${GREEN}\$${STORAGE_COST}${NC}"
    echo -e "─────────────────────────"
    echo -e "Month Total:  ${YELLOW}\$${TOTAL}${NC}"
    echo ""
    echo -e "${MAGENTA}💡 Tip: GPUサーバーは使用後すぐ停止して節約！${NC}"
}

# 起動
start_instances() {
    get_instance_ids
    
    case "$1" in
        all)
            echo -e "${YELLOW}Starting all instances...${NC}"
            aws ec2 start-instances --instance-ids $APP_INSTANCE_ID $GPU_INSTANCE_ID --region $REGION
            ;;
        app)
            echo -e "${YELLOW}Starting application server...${NC}"
            aws ec2 start-instances --instance-ids $APP_INSTANCE_ID --region $REGION
            ;;
        gpu)
            echo -e "${YELLOW}Starting GPU server...${NC}"
            echo -e "${MAGENTA}💰 Remember: g4dn.xlarge costs \$0.71/hour${NC}"
            aws ec2 start-instances --instance-ids $GPU_INSTANCE_ID --region $REGION
            ;;
    esac
    
    echo -e "${GREEN}✅ Start command sent${NC}"
    echo "Waiting for instances to be ready..."
    sleep 10
    check_status
}

# 停止
stop_instances() {
    get_instance_ids
    
    case "$1" in
        all)
            echo -e "${YELLOW}Stopping all instances...${NC}"
            aws ec2 stop-instances --instance-ids $APP_INSTANCE_ID $GPU_INSTANCE_ID --region $REGION
            ;;
        app)
            echo -e "${YELLOW}Stopping application server...${NC}"
            aws ec2 stop-instances --instance-ids $APP_INSTANCE_ID --region $REGION
            ;;
        gpu)
            echo -e "${YELLOW}Stopping GPU server...${NC}"
            echo -e "${GREEN}💰 Good! Saving \$0.71/hour${NC}"
            aws ec2 stop-instances --instance-ids $GPU_INSTANCE_ID --region $REGION
            ;;
    esac
    
    echo -e "${GREEN}✅ Stop command sent${NC}"
}

# GPU情報取得
gpu_info() {
    get_instance_ids
    
    GPU_STATE=$(aws ec2 describe-instances \
        --instance-ids $GPU_INSTANCE_ID \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text --region $REGION)
    
    if [ "$GPU_STATE" != "running" ]; then
        echo -e "${RED}GPU server is not running${NC}"
        exit 1
    fi
    
    GPU_IP=$(aws ec2 describe-instances \
        --instance-ids $GPU_INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text --region $REGION)
    
    echo -e "${YELLOW}GPU Server Information:${NC}"
    echo ""
    
    # SSH経由でnvidia-smi実行
    ssh -o StrictHostKeyChecking=no ubuntu@$GPU_IP "nvidia-smi" 2>/dev/null || \
        echo -e "${RED}Cannot connect to GPU server${NC}"
}

# SSH接続
connect_ssh() {
    get_instance_ids
    
    case "$1" in
        app)
            INSTANCE_ID=$APP_INSTANCE_ID
            SERVER_TYPE="Application"
            ;;
        gpu)
            INSTANCE_ID=$GPU_INSTANCE_ID
            SERVER_TYPE="GPU"
            ;;
    esac
    
    # IPアドレス取得
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text --region $REGION)
    
    if [ "$PUBLIC_IP" = "None" ] || [ -z "$PUBLIC_IP" ]; then
        echo -e "${RED}$SERVER_TYPE server is not running${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Connecting to $SERVER_TYPE server ($PUBLIC_IP)...${NC}"
    ssh ubuntu@$PUBLIC_IP
}

# メイン処理
case "$1" in
    start-all)
        start_instances all
        ;;
    start-app)
        start_instances app
        ;;
    start-gpu)
        start_instances gpu
        ;;
    stop-all)
        stop_instances all
        ;;
    stop-app)
        stop_instances app
        ;;
    stop-gpu)
        stop_instances gpu
        ;;
    status)
        check_status
        ;;
    cost)
        calculate_cost
        ;;
    gpu-info)
        gpu_info
        ;;
    connect-app)
        connect_ssh app
        ;;
    connect-gpu)
        connect_ssh gpu
        ;;
    *)
        usage
        ;;
esac