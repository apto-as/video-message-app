#!/bin/bash

# クイック同期スクリプト（特定ファイルのみ更新）
# 使い方: ./aws-quick-sync.sh backend/main.py

set -e

# 設定
EC2_IP="${EC2_IP:-YOUR_EC2_IP_HERE}"
KEY_FILE="${SSH_KEY:-~/.ssh/your-key.pem}"
REPO_DIR="video-message-app"

# 引数チェック
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file_path> [service_name]"
    echo "Example: $0 backend/main.py backend"
    exit 1
fi

FILE_PATH=$1
SERVICE_NAME=${2:-""}

# EC2_IPチェック
if [ "$EC2_IP" = "YOUR_EC2_IP_HERE" ]; then
    echo "Error: Please set EC2_IP environment variable"
    exit 1
fi

echo "📤 Syncing $FILE_PATH to EC2..."

# ファイル転送
scp -i "$KEY_FILE" "$FILE_PATH" "ubuntu@$EC2_IP:~/$REPO_DIR/$FILE_PATH"

echo "✅ File transferred"

# サービス再起動（指定された場合）
if [ -n "$SERVICE_NAME" ]; then
    echo "🔄 Restarting $SERVICE_NAME..."
    ssh -i "$KEY_FILE" "ubuntu@$EC2_IP" "cd $REPO_DIR && docker compose restart $SERVICE_NAME"
    echo "✅ Service restarted"
fi

echo "🎉 Quick sync complete!"