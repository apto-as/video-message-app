FROM python:3.11-slim

# Mac環境対応のシステム依存関係インストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    portaudio19-dev \
    build-essential \
    curl \
    git \
    pkg-config \
    libffi-dev \
    libblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# OpenVoiceはネイティブサービスに分離済み（PyTorch不要）

# Pythonの依存関係をインストール（Mac環境対応、キャッシュ最適化）
COPY requirements.txt .

# PyTorch with CUDA support for YOLOv8 Person Detection
# EC2 (g4dn.xlarge) uses NVIDIA Tesla T4 GPU with CUDA 11.8
# Note: Large download (~2.3GB), using retry and timeout settings
RUN pip install --upgrade pip && \
    pip config set global.timeout 300 && \
    pip config set global.retries 5 && \
    pip install --no-cache-dir torch==2.0.1+cu118 torchvision==0.15.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ストレージディレクトリを作成（OpenVoice関連は除外）
RUN mkdir -p /app/storage/voices

# 環境変数設定
ENV PYTHONPATH=/app
ENV VOICEVOX_BASE_URL=http://voicevox:50021
ENV OPENVOICE_API_URL=http://localhost:8001

# ポート公開
EXPOSE 55433

# ヘルスチェック（Mac環境対応、ログ負荷軽減）
HEALTHCHECK --interval=120s --timeout=30s --start-period=180s --retries=2 \
  CMD curl -s -f http://localhost:55433/health > /dev/null || exit 1

# アプリケーション起動（タイムアウト延長とワーカー最適化）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "55433", "--reload", "--timeout-keep-alive", "300", "--timeout-graceful-shutdown", "30"]