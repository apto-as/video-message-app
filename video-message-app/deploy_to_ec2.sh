#!/bin/bash

# EC2 自動デプロイスクリプト
# OpenVoice V2サービスの起動を含む完全自動化

set -e

EC2_HOST="3.115.141.166"
EC2_USER="ec2-user"
EC2_PORT="22"

echo "🚀 EC2 Auto Deployment Script"
echo "================================"

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# SSHキーファイルを探す
find_ssh_key() {
    local key_paths=(
        "$HOME/.ssh/video-app-key.pem"
        "$HOME/.ssh/id_rsa"
        "$HOME/.ssh/id_ed25519"
        "$HOME/.ssh/ec2-terraform.pem"
        "$HOME/.ssh/aws-ec2.pem"
    )
    
    for key in "${key_paths[@]}"; do
        if [ -f "$key" ]; then
            echo "$key"
            return 0
        fi
    done
    
    return 1
}

SSH_KEY=$(find_ssh_key)
if [ -z "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found${NC}"
    echo "Please specify your SSH key path:"
    echo "  export SSH_KEY_PATH=/path/to/your/key"
    echo "  ./deploy_to_ec2.sh"
    exit 1
fi

echo -e "${GREEN}Using SSH key: $SSH_KEY${NC}"

# Step 1: ローカルでコミット&プッシュ
echo -e "\n${YELLOW}Step 1: Checking local changes...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes detected. Committing..."
    git add -A
    git commit -m "Auto-commit before EC2 deployment" || true
fi

echo "Pushing to GitHub..."
git push origin master || {
    echo -e "${YELLOW}Warning: Push failed, continuing anyway...${NC}"
}

# Step 2: EC2でのデプロイスクリプト
echo -e "\n${YELLOW}Step 2: Deploying to EC2...${NC}"

ssh -i "$SSH_KEY" -p $EC2_PORT $EC2_USER@$EC2_HOST << 'ENDSSH'
set -e

echo "📦 Updating code from GitHub..."
cd /home/ec2-user/video-message-app/video-message-app
git pull origin master

echo "🔧 Setting up OpenVoice Native Service..."
cd openvoice_native

# 既存プロセスを停止
echo "Stopping existing OpenVoice processes..."
pkill -f "python main.py" || true
sleep 2

# Python仮想環境の確認と作成
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    # 仮想環境を有効化して依存関係をインストール
    source venv/bin/activate
    pip install --upgrade pip
    
    # NumPy 1.22.0を最初にインストール
    echo "Installing NumPy 1.22.0..."
    pip install numpy==1.22.0
    
    # PyTorch CUDA版
    echo "Installing PyTorch with CUDA support..."
    pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
    
    # その他の依存関係
    echo "Installing other dependencies..."
    pip install librosa==0.10.0 soundfile==0.12.1 unidecode==1.3.6
    pip install eng_to_ipa==0.0.2 inflect==7.0.0 scipy==1.10.1
    pip install mecab-python3==1.0.8 unidic-lite==1.0.8
    pip install fastapi==0.104.1 uvicorn[standard]==0.24.0
    pip install python-multipart==0.0.6 aiofiles==23.2.1
    pip install httpx==0.25.2 pydantic==2.5.0 python-dotenv==1.0.0
    pip install mutagen==1.47.0 pydub==0.25.1 ffmpeg-python==0.2.0
    
    # MeCab辞書
    echo "Downloading MeCab dictionary..."
    python -m unidic download
else
    echo "Virtual environment exists, activating..."
    source venv/bin/activate
fi

# OpenVoice V2リポジトリの確認
if [ ! -d "OpenVoiceV2" ]; then
    echo "Cloning OpenVoice V2..."
    git clone https://github.com/myshell-ai/OpenVoice.git OpenVoiceV2
    # v2ブランチは存在しないので、mainブランチを使用
    cd ..
fi

# MeCabディレクトリシンボリックリンクを作成（必要な場合）
if [ ! -L "/home/ec2-user/.local/lib/python3.11/site-packages/unidic/dicdir" ]; then
    echo "Setting up MeCab dictionary symlink..."
    sudo mkdir -p /home/ec2-user/.local/lib/python3.11/site-packages/unidic/
    DICT_PATH=$(find venv -name "dicdir" -type d | grep unidic | head -1)
    if [ -n "$DICT_PATH" ]; then
        sudo ln -sf "$(pwd)/$DICT_PATH" /home/ec2-user/.local/lib/python3.11/site-packages/unidic/dicdir
    fi
fi

# サービスを起動
echo "🚀 Starting OpenVoice Native Service..."
nohup uvicorn main:app --host 0.0.0.0 --port 8001 > openvoice.log 2>&1 &
OPENVOICE_PID=$!

# 起動確認（最大60秒待機 - モデル読み込みに時間がかかる）
echo "Waiting for service to initialize (this may take 30-60 seconds)..."
for i in {1..60}; do
    if curl -s http://localhost:8001/health 2>/dev/null | grep -q '"status":"healthy"'; then
        echo ""
        echo "✅ OpenVoice Native Service is running and healthy! (PID: $OPENVOICE_PID)"
        break
    fi
    if [ $((i % 10)) -eq 0 ]; then
        echo -n " ${i}s"
    else
        echo -n "."
    fi
    sleep 1
done

# Dockerサービスの再起動
echo ""
echo "🐳 Restarting Docker services..."
cd /home/ec2-user/video-message-app/video-message-app
docker-compose restart backend

echo "✨ Deployment completed successfully!"
echo ""
echo "Service Status:"
echo "- OpenVoice: http://localhost:8001/health"
curl -s http://localhost:8001/health | python3 -m json.tool || echo "OpenVoice health check failed"
echo ""
echo "- Backend: http://localhost:55433/health"
curl -s http://localhost:55433/health | python3 -m json.tool || echo "Backend health check failed"

ENDSSH

# Step 3: 最終確認
echo -e "\n${YELLOW}Step 3: Final verification...${NC}"
echo "Testing from local machine..."

# OpenVoiceサービスの確認（EC2経由）
if curl -s https://$EC2_HOST/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend API is accessible${NC}"
else
    echo -e "${RED}❌ Backend API is not accessible${NC}"
fi

echo -e "\n${GREEN}🎉 Deployment completed!${NC}"
echo "Access your application at: https://$EC2_HOST"
echo ""
echo "To check logs on EC2:"
echo "  ssh -i $SSH_KEY -p $EC2_PORT $EC2_USER@$EC2_HOST"
echo "  cd /home/ec2-user/video-message-app/video-message-app/openvoice_native"
echo "  tail -f openvoice.log"