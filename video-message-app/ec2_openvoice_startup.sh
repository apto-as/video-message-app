#!/bin/bash

# ==================================================
# OpenVoice EC2 緊急起動スクリプト
# Artemis Technical Perfectionist - 即座解決策
# ==================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== OpenVoice EC2 Service 緊急起動 ===${NC}"

# 作業ディレクトリ
BASE_DIR="$HOME/video-message-app/video-message-app"
EC2_SETUP_DIR="$BASE_DIR/ec2_setup"
SERVICE_SCRIPT="$EC2_SETUP_DIR/openvoice_ec2_service.py"

echo -e "${BLUE}作業ディレクトリ: $BASE_DIR${NC}"

# 1. 現在のプロセスをチェック
echo -e "${YELLOW}[1/8] 既存プロセスチェック...${NC}"
if pgrep -f "openvoice_ec2_service.py" > /dev/null; then
    echo -e "${RED}既存プロセス発見。終了します...${NC}"
    pkill -f "openvoice_ec2_service.py"
    sleep 2
fi

# 2. Port 8001 使用状況チェック
echo -e "${YELLOW}[2/8] Port 8001 チェック...${NC}"
if netstat -tuln | grep :8001 > /dev/null; then
    echo -e "${RED}Port 8001 使用中。プロセスを終了...${NC}"
    sudo lsof -ti:8001 | xargs sudo kill -9 2>/dev/null || true
    sleep 2
fi

# 3. 必要なディレクトリ確認・作成
echo -e "${YELLOW}[3/8] ディレクトリ構造確認...${NC}"
mkdir -p "$HOME/video-message-app/video-message-app/data/openvoice/checkpoints_v2"
mkdir -p "$HOME/video-message-app/video-message-app/data/backend/storage/openvoice"
mkdir -p "$HOME/video-message-app/video-message-app/openvoice_ec2/temp"

# 4. Python環境とライブラリの確認
echo -e "${YELLOW}[4/8] Python環境確認...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3が見つかりません${NC}"
    exit 1
fi

# UV環境でOpenVoice必須ライブラリをインストール
echo -e "${YELLOW}[5/8] OpenVoice必須依存関係インストール...${NC}"
pip install --no-cache-dir --upgrade \
    torch==2.0.1+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# CUDA環境向けライブラリ
pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1 \
    numpy==1.24.3 \
    soundfile==0.12.1 \
    librosa==0.10.1 \
    pydantic==2.5.0

echo -e "${GREEN}✓ 基本依存関係インストール完了${NC}"

# 6. OpenVoiceライブラリのクローンとインストール
echo -e "${YELLOW}[6/8] OpenVoice ライブラリセットアップ...${NC}"
cd "$HOME/video-message-app"

if [ ! -d "OpenVoice" ]; then
    echo -e "${BLUE}OpenVoice リポジトリをクローン...${NC}"
    git clone https://github.com/myshell-ai/OpenVoice.git
fi

cd OpenVoice
pip install -e .

# MeloTTS もインストール（必要に応じて）
if [ ! -d "../MeloTTS" ]; then
    echo -e "${BLUE}MeloTTS リポジトリをクローン...${NC}"
    cd ..
    git clone https://github.com/myshell-ai/MeloTTS.git
    cd MeloTTS
    pip install -e .
    cd ..
fi

# 7. モデルファイルのダウンロード
echo -e "${YELLOW}[7/8] OpenVoice モデルファイルダウンロード...${NC}"
cd "$HOME/video-message-app/video-message-app"
python3 << 'EOF'
import os
import subprocess
from pathlib import Path

# モデルダウンロードディレクトリ
models_dir = Path.home() / "video-message-app" / "video-message-app" / "data" / "openvoice" / "checkpoints_v2"
models_dir.mkdir(parents=True, exist_ok=True)

converter_dir = models_dir / "converter"
converter_dir.mkdir(exist_ok=True)

speakers_dir = models_dir / "base_speakers" / "ses"
speakers_dir.mkdir(parents=True, exist_ok=True)

# 必要なファイルリスト
files_to_download = [
    ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/converter/checkpoint.pth", converter_dir / "checkpoint.pth"),
    ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/converter/config.json", converter_dir / "config.json"),
    ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/base_speakers/ses/en-default.pth", speakers_dir / "en-default.pth"),
    ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/base_speakers/ses/jp.pth", speakers_dir / "jp.pth")
]

# ダウンロード実行
for url, path in files_to_download:
    if not path.exists():
        print(f"Downloading {path.name}...")
        subprocess.run(["wget", "-O", str(path), url], check=True)
    else:
        print(f"✓ {path.name} already exists")

print("モデルファイルダウンロード完了")
EOF

# 8. OpenVoice サービス起動
echo -e "${YELLOW}[8/8] OpenVoice EC2 Service 起動...${NC}"

if [ ! -f "$SERVICE_SCRIPT" ]; then
    echo -e "${RED}サービススクリプトが見つかりません: $SERVICE_SCRIPT${NC}"
    exit 1
fi

cd "$EC2_SETUP_DIR"

# 環境変数設定
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export CUDA_VISIBLE_DEVICES=0  # Tesla T4 GPU使用

# バックグラウンドで起動
echo -e "${BLUE}Starting OpenVoice Service...${NC}"
nohup python3 openvoice_ec2_service.py > ../logs/openvoice_service.log 2>&1 &
SERVICE_PID=$!

# PIDを保存
echo $SERVICE_PID > ../.openvoice_ec2_pid

# 起動確認
sleep 10
if ps -p $SERVICE_PID > /dev/null; then
    echo -e "${GREEN}✓ OpenVoice Service 起動成功 (PID: $SERVICE_PID)${NC}"
    
    # Health check
    max_retries=30
    for i in $(seq 1 $max_retries); do
        if curl -f http://localhost:8001/health 2>/dev/null; then
            echo -e "${GREEN}✓ Health check 成功${NC}"
            echo -e "${GREEN}=== OpenVoice Service 起動完了 ===${NC}"
            echo -e "${BLUE}Service URL: http://localhost:8001${NC}"
            echo -e "${BLUE}Health check: curl http://localhost:8001/health${NC}"
            exit 0
        fi
        echo -e "${YELLOW}Health check 試行 $i/$max_retries...${NC}"
        sleep 2
    done
    
    echo -e "${RED}Health check 失敗${NC}"
    exit 1
else
    echo -e "${RED}✗ OpenVoice Service 起動失敗${NC}"
    echo -e "${YELLOW}ログを確認: tail -f ../logs/openvoice_service.log${NC}"
    exit 1
fi