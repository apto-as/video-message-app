#!/bin/bash

# OpenVoice Native Service Setup for EC2 with NVIDIA GPU
# This script sets up OpenVoice V2 on EC2 with proper dependencies

echo "=== OpenVoice Native Service EC2 Setup ==="

# Python環境の確認
echo "Checking Python version..."
python3 --version

# 既存の仮想環境を削除（クリーンインストール）
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# 新しい仮想環境を作成
echo "Creating virtual environment..."
python3 -m venv venv

# 仮想環境をアクティベート
source venv/bin/activate

# pipをアップグレード
echo "Upgrading pip..."
pip install --upgrade pip

# NumPyを正しいバージョンでインストール（OpenVoice V2要件）
echo "Installing NumPy 1.22.0 for OpenVoice compatibility..."
pip install numpy==1.22.0

# PyTorchをCUDA対応版でインストール（EC2 GPUインスタンス用）
echo "Installing PyTorch with CUDA support..."
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# OpenVoice V2の依存関係をインストール
echo "Installing OpenVoice V2 dependencies..."
pip install librosa==0.10.0
pip install soundfile==0.12.1
pip install unidecode==1.3.6
pip install eng_to_ipa==0.0.2
pip install inflect==7.0.0
pip install scipy==1.10.1

# MeCab関連の依存関係をインストール
echo "Installing MeCab and unidic..."
pip install mecab-python3==1.0.8
pip install unidic-lite==1.0.8

# unidicの辞書データをダウンロード
echo "Downloading unidic dictionary..."
python -m unidic download

# FastAPIと関連ライブラリをインストール
echo "Installing FastAPI and related libraries..."
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install python-multipart==0.0.6
pip install aiofiles==23.2.1
pip install httpx==0.25.2
pip install pydantic==2.5.0
pip install python-dotenv==1.0.0
pip install mutagen==1.47.0

# 音声処理ライブラリ
echo "Installing audio processing libraries..."
pip install pydub==0.25.1
pip install ffmpeg-python==0.2.0

# OpenVoice V2をクローン（もしまだない場合）
if [ ! -d "OpenVoiceV2" ]; then
    echo "Cloning OpenVoice V2 repository..."
    git clone https://github.com/myshell-ai/OpenVoice.git OpenVoiceV2
    cd OpenVoiceV2
    git checkout v2
    cd ..
fi

# 環境変数の設定
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
CUDA_VISIBLE_DEVICES=0
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
EOF
fi

# テストスクリプト
echo "Creating test script..."
cat > test_openvoice.py << 'EOF'
#!/usr/bin/env python3
"""OpenVoice V2 Test Script"""

import sys
import numpy as np

print("Python version:", sys.version)
print("NumPy version:", np.__version__)

try:
    import torch
    print("PyTorch version:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("CUDA device:", torch.cuda.get_device_name(0))
except ImportError as e:
    print(f"PyTorch import error: {e}")

try:
    import MeCab
    m = MeCab.Tagger()
    print("MeCab is working")
except Exception as e:
    print(f"MeCab error: {e}")

try:
    from openvoice import se_extractor
    print("OpenVoice se_extractor imported successfully")
except ImportError as e:
    print(f"OpenVoice import error: {e}")

print("\nSetup completed successfully!")
EOF

# テストを実行
echo "Running test..."
python test_openvoice.py

echo "=== Setup Complete ==="
echo "To start the service, run:"
echo "  source venv/bin/activate"
echo "  python main.py"