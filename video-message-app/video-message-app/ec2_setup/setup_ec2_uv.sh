#!/bin/bash
# EC2 OpenVoice Setup with uv
# Based on working Mac implementation

set -e

echo "=== EC2 OpenVoice Setup with uv ==="
echo "Starting at: $(date)"

# 1. Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# 2. Check uv installation
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "uv version: $(uv --version)"

# 3. Setup directories
cd ~/video-message-app/video-message-app
mkdir -p openvoice_ec2/temp
mkdir -p data/openvoice/checkpoints_v2/converter
mkdir -p data/openvoice/checkpoints_v2/base_speakers/ses
mkdir -p data/backend/storage/openvoice

# 4. Create uv environment with Python 3.11
echo "Creating uv environment..."
cd openvoice_ec2
uv venv --python 3.11
source .venv/bin/activate

# 5. Upgrade pip
echo "Upgrading pip..."
uv pip install --upgrade pip setuptools wheel

# 6. Install PyTorch CPU version
echo "Installing PyTorch (CPU)..."
uv pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

# 7. Clone OpenVoice if not exists
echo "Setting up OpenVoice..."
cd ~/video-message-app
if [ ! -d "OpenVoice" ]; then
    git clone https://github.com/myshell-ai/OpenVoice
fi

# 8. Install OpenVoice
cd OpenVoice
uv pip install -e .

# 9. Install additional dependencies
echo "Installing dependencies..."
uv pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    numpy==1.24.4 \
    scipy \
    librosa==0.10.0 \
    soundfile \
    openai-whisper \
    faster-whisper \
    httpx \
    aiofiles \
    python-dotenv \
    pydantic==2.5.0 \
    pydantic-settings \
    mutagen==1.47.0 \
    inflect \
    unidecode \
    eng_to_ipa \
    pypinyin

# 10. Install MeloTTS (optional but recommended)
echo "Installing MeloTTS..."
cd ~/video-message-app
if [ ! -d "MeloTTS" ]; then
    git clone https://github.com/myshell-ai/MeloTTS.git
fi
cd MeloTTS
uv pip install -e .

# 11. Download model files if not exists
echo "Checking model files..."
cd ~/video-message-app/video-message-app/data/openvoice/checkpoints_v2

# Download converter model
if [ ! -f "converter/checkpoint.pth" ]; then
    echo "Downloading converter checkpoint..."
    wget -q https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/converter/checkpoint.pth -P converter/
fi

if [ ! -f "converter/config.json" ]; then
    echo "Downloading converter config..."
    wget -q https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/converter/config.json -P converter/
fi

# Download base speakers
echo "Downloading base speakers..."
cd base_speakers/ses
speakers=("en-au" "en-br" "en-default" "en-india" "en-newest" "en-us" "es" "fr" "jp" "kr" "zh")
for speaker in "${speakers[@]}"; do
    if [ ! -f "${speaker}.pth" ]; then
        echo "Downloading ${speaker}.pth..."
        wget -q "https://huggingface.co/myshell-ai/OpenVoice/resolve/main/checkpoints_v2/base_speakers/ses/${speaker}.pth"
    fi
done

# 12. Create activation script
echo "Creating activation script..."
cat > ~/video-message-app/activate_openvoice.sh << 'EOF'
#!/bin/bash
cd ~/video-message-app/video-message-app/openvoice_ec2
source .venv/bin/activate
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export CUDA_VISIBLE_DEVICES=""
echo "OpenVoice uv environment activated"
echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo "To start service: python openvoice_ec2_service.py"
EOF
chmod +x ~/video-message-app/activate_openvoice.sh

# 13. Create test script
echo "Creating test script..."
cat > ~/video-message-app/video-message-app/openvoice_ec2/test_service.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("Testing OpenVoice Service...")

# 1. Health check
resp = requests.get(f"{BASE_URL}/health")
print(f"Health: {resp.json()}")

# 2. List profiles
resp = requests.get(f"{BASE_URL}/api/profiles")
print(f"Profiles: {len(resp.json())} found")

print("\nService is running!")
EOF
chmod +x ~/video-message-app/video-message-app/openvoice_ec2/test_service.py

echo "=== Setup Complete ==="
echo "To activate environment: source ~/video-message-app/activate_openvoice.sh"
echo "To start service: python openvoice_ec2_service.py"
echo "Completed at: $(date)"