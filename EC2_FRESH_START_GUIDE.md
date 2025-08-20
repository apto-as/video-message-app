# EC2 新規インスタンス構築ガイド
作成日: 2025-08-19

## 🚀 新規EC2インスタンス立ち上げ手順

### 理由: 環境のクリーンスタート
現在のEC2インスタンスには以下の問題が存在する可能性があります：
- Python環境の汚染（複数バージョンの混在）
- パッケージの競合
- 設定ファイルの不整合
- CUDAドライバーの残骸

### 新規インスタンスの仕様

```yaml
# EC2 Instance Configuration
Instance Type: t3.large
vCPU: 2
Memory: 8 GB
Storage: 30 GB (gp3)
Network Performance: Up to 5 Gbps

# Operating System
AMI: Ubuntu 22.04 LTS (ami-0d3a2960f98f3e2a3)
Region: ap-northeast-1 (Tokyo)

# Security Group
Inbound Rules:
  - SSH (22): Your IP
  - HTTP (80): 0.0.0.0/0
  - HTTPS (443): 0.0.0.0/0
  - Backend API (55433): 0.0.0.0/0
  - Frontend (55434): 0.0.0.0/0
  - OpenVoice (8001): VPC内部のみ
  - VoiceVox (50021): VPC内部のみ
```

## 📦 セットアップスクリプト

### 1. 基本環境構築スクリプト（uv使用版）

```bash
#!/bin/bash
# filename: setup_fresh_ubuntu_with_uv.sh

set -e

echo "=== Ubuntu 22.04 Fresh Setup with uv for OpenVoice ==="

# 1. System Update
echo "1. Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. Essential packages
echo "2. Installing essential packages..."
sudo apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    unzip \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release

# 3. uv installation (Pythonバージョン管理含む)
echo "3. Installing uv (Python package manager)..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# uvがPythonバージョンを管理するため、システムPythonは最小限に
echo "4. Installing minimal system Python..."
sudo apt-get install -y python3-minimal

# 5. Locale setup for Japanese
echo "5. Setting up locales..."
sudo apt-get install -y locales
sudo locale-gen en_US.UTF-8 ja_JP.UTF-8
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# 6. Audio processing dependencies
echo "6. Installing audio dependencies..."
sudo apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev

# 7. Docker installation
echo "7. Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
rm get-docker.sh

# 8. Docker Compose installation
echo "8. Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 9. Node.js setup (for frontend)
echo "9. Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 10. Create project directories
echo "10. Creating project structure..."
mkdir -p ~/video-message-app/video-message-app
mkdir -p ~/video-message-app/checkpoints_v2
mkdir -p ~/video-message-app/data/backend/storage/openvoice

echo "=== Basic setup complete! ==="
echo "Next: Run setup_openvoice_with_uv.sh"
echo "Please log out and log back in for Docker permissions to take effect."
```

### 2. OpenVoice専用環境構築（uv版）

```bash
#!/bin/bash
# filename: setup_openvoice_with_uv.sh

set -e

echo "=== OpenVoice Environment Setup with uv ==="

# 0. uvが利用可能か確認
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# 1. Project directory and uv environment
echo "1. Creating uv Python environment..."
cd ~/video-message-app/video-message-app

# uvでPython 3.11環境を作成（プロジェクトごとに分離）
uv venv --python 3.11
source .venv/bin/activate

# 2. Upgrade pip in uv environment
echo "2. Upgrading pip..."
uv pip install --upgrade pip setuptools wheel

# 3. Install PyTorch CPU version with uv
echo "3. Installing PyTorch (CPU version)..."
uv pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

# 4. Clone and install OpenVoice
echo "4. Installing OpenVoice..."
cd ~/video-message-app
if [ ! -d "OpenVoice" ]; then
    git clone https://github.com/myshell-ai/OpenVoice
fi
cd OpenVoice
uv pip install -e .

# 5. Additional dependencies with uv
echo "5. Installing additional packages with uv..."
uv pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    numpy==1.24.4 \
    scipy \
    librosa \
    soundfile \
    openai-whisper \
    httpx \
    aiofiles \
    python-dotenv \
    pydantic==2.5.0 \
    pydantic-settings \
    mutagen==1.47.0

# 6. Download OpenVoice V2 checkpoints
echo "6. Downloading OpenVoice V2 models..."
cd ~/video-message-app
mkdir -p checkpoints_v2/converter
mkdir -p checkpoints_v2/base_speakers/ses

cd checkpoints_v2

# Download from HuggingFace
if [ ! -f "converter/checkpoint.pth" ]; then
    wget https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/converter/checkpoint.pth -P converter/
fi
if [ ! -f "converter/config.json" ]; then
    wget https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/converter/config.json -P converter/
fi

# Base speakers
if [ ! -f "base_speakers/ses/en-us.pth" ]; then
    wget https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/base_speakers/ses/en-us.pth -P base_speakers/ses/
fi
if [ ! -f "base_speakers/ses/zh.pth" ]; then
    wget https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/base_speakers/ses/zh.pth -P base_speakers/ses/
fi

# 7. Create activation script
echo "7. Creating activation script..."
cat > ~/video-message-app/activate_openvoice.sh << 'EOF'
#!/bin/bash
cd ~/video-message-app/video-message-app
source .venv/bin/activate
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
echo "OpenVoice uv environment activated"
echo "Python: $(which python)"
echo "Python version: $(python --version)"
EOF
chmod +x ~/video-message-app/activate_openvoice.sh

echo "=== OpenVoice uv environment setup complete! ==="
echo "To activate: source ~/video-message-app/activate_openvoice.sh"
```

### 3. アプリケーションデプロイ

```bash
#!/bin/bash
# filename: deploy_application.sh

set -e

echo "=== Deploying Video Message App ==="

# 1. Clone repository
cd ~/video-message-app
git clone https://github.com/your-repo/video-message-app.git
cd video-message-app

# 2. Setup backend
echo "Setting up backend..."
cd backend
cp .env.example .env
# Edit .env file with necessary API keys

# 3. Setup frontend
echo "Setting up frontend..."
cd ../frontend
npm install
npm run build

# 4. Start services with Docker
echo "Starting Docker services..."
cd ..
docker-compose up -d voicevox_engine
docker-compose up -d frontend
docker-compose up -d backend

# 5. Start OpenVoice service
echo "Starting OpenVoice service..."
cd ~/video-message-app
source openvoice_env/bin/activate
nohup python3 openvoice_service.py > openvoice.log 2>&1 &

echo "=== Deployment complete! ==="
```

## 🧹 データ移行計画

### 既存インスタンスからのデータ移行

```bash
# 既存インスタンスで実行
cd ~/video-message-app
tar -czf backup_data.tar.gz \
    video-message-app/data/backend/storage/ \
    video-message-app/backend/.env \
    video-message-app/frontend/.env

# SCPで新インスタンスへ転送
scp -i ~/.ssh/video-app-key.pem \
    backup_data.tar.gz \
    ubuntu@NEW_INSTANCE_IP:~/

# 新インスタンスで展開
tar -xzf backup_data.tar.gz
```

## 🔍 環境検証チェックリスト

### システムレベル
- [ ] Ubuntu 22.04 LTS
- [ ] Python 3.11.x
- [ ] ロケール設定（UTF-8）
- [ ] FFmpeg インストール

### Python環境
- [ ] venv環境分離
- [ ] PyTorch CPU版
- [ ] OpenVoice インストール
- [ ] Whisper モデル

### Docker環境
- [ ] Docker Engine 24.x
- [ ] Docker Compose v2
- [ ] ネットワーク設定
- [ ] ボリュームマウント

### アプリケーション
- [ ] Backend API起動
- [ ] Frontend起動
- [ ] VoiceVox起動
- [ ] OpenVoice起動

## 📊 パフォーマンス比較

### 既存インスタンス
- Python混在: 3.10, 3.11, 3.12
- パッケージ競合あり
- CUDA残骸あり
- メモリ使用量: 6GB+

### 新規インスタンス（期待値）
- Python統一: 3.11のみ
- クリーンな依存関係
- CPU専用最適化
- メモリ使用量: 4GB以下

## 🚨 切り替え手順

### 1. DNSレコード更新準備
```bash
# Elastic IP割り当て
aws ec2 allocate-address --domain vpc

# 新インスタンスに関連付け
aws ec2 associate-address \
    --instance-id i-xxxxx \
    --allocation-id eipalloc-xxxxx
```

### 2. ヘルスチェック
```bash
# 全サービス確認
curl http://NEW_IP:55433/health  # Backend
curl http://NEW_IP:55434/        # Frontend
curl http://NEW_IP:8001/health   # OpenVoice
curl http://NEW_IP:50021/version # VoiceVox
```

### 3. 切り替え実行
- Route53/Nginxの設定更新
- 旧インスタンスの停止
- モニタリング開始

## 💰 コスト見積もり

### 移行コスト
- 新規インスタンス起動: $0.0416/hour (t3.large)
- データ転送: 約$0.10
- 並行稼働時間: 2-4時間
- **合計**: 約$0.30

### 月間コスト（移行後）
- t3.large: $60.48/月
- EBS 30GB: $3.00/月
- データ転送: $5.00/月
- **合計**: 約$68.48/月

## 📝 最終確認事項

### 移行前
- [ ] 完全バックアップ作成
- [ ] 設定ファイルの確認
- [ ] API キーの準備
- [ ] DNSレコードTTL短縮

### 移行後
- [ ] 全機能テスト
- [ ] ログ監視
- [ ] パフォーマンス測定
- [ ] 旧インスタンス削除

---

## 推奨事項

**Trinitas-Core推奨**: 
現在の環境汚染を考慮すると、新規インスタンスでのクリーンスタートを強く推奨します。
- 時間効率: デバッグ時間 < 新規構築時間
- 確実性: 100%クリーンな環境
- 将来性: 明確なドキュメントで再現可能

作成者: Trinitas-Core System
更新日: 2025-08-19