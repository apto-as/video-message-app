#!/bin/bash

# ==================================================
# Docker内でOpenVoice Serviceを実行するセットアップ
# Artemis Technical Perfectionist - Docker統合版
# ==================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Docker内OpenVoice Service セットアップ ===${NC}"

# 1. Docker Composeにopenvoice serviceを追加
echo -e "${YELLOW}[1/4] docker-compose.yml 更新...${NC}"

cat >> docker-compose.yml << 'EOF'

  # OpenVoice Native Service (Docker内実行)
  openvoice:
    build:
      context: .
      dockerfile: Dockerfile.openvoice
    ports:
      - "8001:8001"
    volumes:
      - "./data:/app/data"
      - "./video-message-app/ec2_setup:/app/service"
    environment:
      - PYTHONIOENCODING=utf-8
      - LC_ALL=C.UTF-8
      - LANG=C.UTF-8
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - app-network
    depends_on:
      - redis
EOF

# 2. OpenVoice専用Dockerfileを作成
echo -e "${YELLOW}[2/4] OpenVoice Dockerfile作成...${NC}"

cat > Dockerfile.openvoice << 'EOF'
FROM nvidia/cuda:11.8-runtime-ubuntu22.04

# 基本パッケージインストール
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Python環境セットアップ
RUN pip3 install --upgrade pip

# PyTorch (CUDA 11.8対応)
RUN pip3 install torch==2.0.1+cu118 torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# OpenVoice依存関係
RUN pip3 install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1 \
    numpy==1.24.3 \
    soundfile==0.12.1 \
    librosa==0.10.1 \
    pydantic==2.5.0

# 作業ディレクトリ
WORKDIR /app

# OpenVoiceライブラリクローン
RUN git clone https://github.com/myshell-ai/OpenVoice.git /app/OpenVoice
WORKDIR /app/OpenVoice
RUN pip3 install -e .

# MeloTTSライブラリクローン
RUN git clone https://github.com/myshell-ai/MeloTTS.git /app/MeloTTS
WORKDIR /app/MeloTTS
RUN pip3 install -e .

# 作業ディレクトリ戻し
WORKDIR /app

# モデルファイルダウンロード用スクリプト
COPY docker-download-models.py /app/download_models.py

# ポート開放
EXPOSE 8001

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# エントリポイント
CMD ["python3", "/app/service/openvoice_ec2_service.py"]
EOF

# 3. モデルダウンロードスクリプト作成
echo -e "${YELLOW}[3/4] モデルダウンロードスクリプト作成...${NC}"

cat > docker-download-models.py << 'EOF'
#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

def download_models():
    """OpenVoiceモデルファイルをダウンロード"""
    models_dir = Path("/app/data/openvoice/checkpoints_v2")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    converter_dir = models_dir / "converter"
    converter_dir.mkdir(exist_ok=True)
    
    speakers_dir = models_dir / "base_speakers" / "ses"  
    speakers_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_download = [
        ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/converter/checkpoint.pth", 
         converter_dir / "checkpoint.pth"),
        ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/converter/config.json", 
         converter_dir / "config.json"),
        ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/base_speakers/ses/en-default.pth", 
         speakers_dir / "en-default.pth"),
        ("https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/base_speakers/ses/jp.pth", 
         speakers_dir / "jp.pth")
    ]
    
    for url, path in files_to_download:
        if not path.exists():
            print(f"Downloading {path.name}...")
            subprocess.run(["wget", "-O", str(path), url], check=True)
            print(f"✓ {path.name} downloaded")
        else:
            print(f"✓ {path.name} already exists")
    
    print("All model files ready!")

if __name__ == "__main__":
    download_models()
EOF

# 4. Docker Composeサービス起動
echo -e "${YELLOW}[4/4] OpenVoice Service起動...${NC}"

# モデルダウンロードを先に実行
python3 docker-download-models.py

# Dockerサービス起動
docker-compose up -d openvoice

echo -e "${GREEN}✓ Docker OpenVoice Service 起動完了${NC}"
echo -e "${BLUE}Service URL: http://localhost:8001${NC}"
echo -e "${BLUE}Health check: curl http://localhost:8001/health${NC}"
echo -e "${BLUE}ログ確認: docker-compose logs -f openvoice${NC}"