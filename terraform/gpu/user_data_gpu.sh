#!/bin/bash
# GPU Server Setup Script for OpenVoice

# ログ出力
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting GPU server setup..."

# システム更新
apt-get update
apt-get upgrade -y

# 必要なパッケージインストール
apt-get install -y \
    git \
    htop \
    ncdu \
    nfs-common \
    ffmpeg

# EFSマウント
mkdir -p /mnt/shared
echo "${efs_id}.efs.${region}.amazonaws.com:/ /mnt/shared nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0" >> /etc/fstab
mount -a

# ディレクトリ権限設定
chown -R ubuntu:ubuntu /mnt/shared

# NVIDIA Docker設定（Deep Learning AMIには通常プリインストール）
if ! command -v nvidia-docker &> /dev/null; then
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt-get update
    apt-get install -y nvidia-docker2
    systemctl restart docker
fi

# GPU確認スクリプト
cat > /home/ubuntu/check_gpu.sh << 'EOF'
#!/bin/bash
echo "Checking GPU availability..."
nvidia-smi
echo ""
echo "Testing Docker GPU support..."
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
EOF

chmod +x /home/ubuntu/check_gpu.sh
chown ubuntu:ubuntu /home/ubuntu/check_gpu.sh

# OpenVoice Dockerfile作成
cat > /home/ubuntu/Dockerfile.openvoice << 'EOF'
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# 環境変数
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# システムパッケージ
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Python パッケージ
RUN pip3 install --no-cache-dir \
    torch==2.0.1 \
    torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu118

# OpenVoice V2
RUN git clone https://github.com/myshell-ai/OpenVoice.git /app/OpenVoice
WORKDIR /app/OpenVoice
RUN pip3 install --no-cache-dir -e .

# FastAPI サーバー
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    aiofiles

# アプリケーションコード
COPY openvoice_service.py /app/openvoice_service.py

# データディレクトリ
VOLUME ["/mnt/shared"]

WORKDIR /app
EXPOSE 8001

CMD ["uvicorn", "openvoice_service:app", "--host", "0.0.0.0", "--port", "8001"]
EOF

chown ubuntu:ubuntu /home/ubuntu/Dockerfile.openvoice

# OpenVoice サービスコード
cat > /home/ubuntu/openvoice_service.py << 'EOF'
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
import torch
import os
import tempfile
import shutil
from pathlib import Path

app = FastAPI(title="OpenVoice GPU Service")

# GPU確認
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 共有ストレージパス
SHARED_DATA = Path("/mnt/shared/data")
VOICES_DIR = SHARED_DATA / "voices"
MODELS_DIR = SHARED_DATA / "models"
GENERATED_DIR = SHARED_DATA / "generated"

# ディレクトリ作成
for dir in [VOICES_DIR, MODELS_DIR, GENERATED_DIR]:
    dir.mkdir(parents=True, exist_ok=True)

@app.get("/")
async def root():
    return {
        "service": "OpenVoice GPU Service",
        "status": "running",
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "gpu": device}

@app.post("/clone_voice")
async def clone_voice(
    audio_file: UploadFile = File(...),
    profile_name: str = Form(...)
):
    """音声クローニング処理（GPU使用）"""
    try:
        # 一時ファイル保存
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        shutil.copyfileobj(audio_file.file, temp_audio)
        temp_audio.close()
        
        # GPU処理（実際のOpenVoice処理をここに実装）
        # ... OpenVoice処理 ...
        
        # 結果を共有ストレージに保存
        profile_dir = VOICES_DIR / profile_name
        profile_dir.mkdir(exist_ok=True)
        
        # プロファイル保存
        # ... 保存処理 ...
        
        return {
            "status": "success",
            "profile_name": profile_name,
            "device_used": device,
            "profile_path": str(profile_dir)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if temp_audio:
            os.unlink(temp_audio.name)

@app.post("/synthesize")
async def synthesize(
    text: str = Form(...),
    profile_name: str = Form(...)
):
    """音声合成処理（GPU使用）"""
    try:
        profile_dir = VOICES_DIR / profile_name
        if not profile_dir.exists():
            return {"status": "error", "message": "Profile not found"}
        
        # GPU処理
        # ... 音声合成処理 ...
        
        output_file = GENERATED_DIR / f"{profile_name}_{os.urandom(4).hex()}.wav"
        
        return FileResponse(
            path=str(output_file),
            media_type="audio/wav",
            filename="synthesized.wav"
        )
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF

chown ubuntu:ubuntu /home/ubuntu/openvoice_service.py

# 起動スクリプト
cat > /home/ubuntu/start_openvoice.sh << 'EOF'
#!/bin/bash

# Dockerイメージビルド
echo "Building OpenVoice Docker image..."
docker build -f Dockerfile.openvoice -t openvoice-gpu .

# コンテナ起動
echo "Starting OpenVoice GPU service..."
docker run -d \
  --name openvoice-gpu \
  --gpus all \
  -p 8001:8001 \
  -v /mnt/shared:/mnt/shared \
  -v $(pwd)/openvoice_service.py:/app/openvoice_service.py \
  --restart unless-stopped \
  openvoice-gpu

# ステータス確認
sleep 5
docker logs openvoice-gpu
echo ""
echo "OpenVoice GPU service started on port 8001"
echo "Check status: curl http://localhost:8001/health"
EOF

chmod +x /home/ubuntu/start_openvoice.sh
chown ubuntu:ubuntu /home/ubuntu/start_openvoice.sh

# 停止スクリプト
cat > /home/ubuntu/stop_openvoice.sh << 'EOF'
#!/bin/bash
docker stop openvoice-gpu
docker rm openvoice-gpu
echo "OpenVoice GPU service stopped"
EOF

chmod +x /home/ubuntu/stop_openvoice.sh
chown ubuntu:ubuntu /home/ubuntu/stop_openvoice.sh

echo "GPU server setup completed at $(date)" > /home/ubuntu/setup_complete.txt
chown ubuntu:ubuntu /home/ubuntu/setup_complete.txt

echo "GPU Setup complete!"