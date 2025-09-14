#!/bin/bash

# OpenVoice Service Wrapper Script for systemd
# This script ensures all environment variables are properly set before starting the Python service

# エラー時に即座に終了
set -e

# ログディレクトリの設定
LOG_DIR="/home/ec2-user/video-message-app/video-message-app/openvoice_native"
LOG_FILE="${LOG_DIR}/openvoice.log"

# 起動時刻を記録
echo "========================================" >> ${LOG_FILE}
echo "[$(date '+%Y-%m-%d %H:%M:%S')] OpenVoice Wrapper Script Starting..." >> ${LOG_FILE}
echo "========================================" >> ${LOG_FILE}

# 環境変数の設定
export LD_LIBRARY_PATH="/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/torch/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cuda_nvrtc/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cudnn/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cuda_runtime/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/ctranslate2.libs:/usr/local/cuda/lib64:/usr/lib64"
export CUDA_HOME="/usr/local/cuda"
export CUDA_VISIBLE_DEVICES="0"
export PYTHONUNBUFFERED="1"
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# 環境変数をログに記録
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Environment Variables Set:" >> ${LOG_FILE}
echo "  LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" >> ${LOG_FILE}
echo "  CUDA_HOME=${CUDA_HOME}" >> ${LOG_FILE}
echo "  CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}" >> ${LOG_FILE}
echo "  PYTHONUNBUFFERED=${PYTHONUNBUFFERED}" >> ${LOG_FILE}
echo "  PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF}" >> ${LOG_FILE}

# GPUの状態を確認
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking GPU Status:" >> ${LOG_FILE}
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader >> ${LOG_FILE} 2>&1 || echo "  WARNING: nvidia-smi failed" >> ${LOG_FILE}

# ライブラリの存在確認
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking Required Libraries:" >> ${LOG_FILE}

# CUDNN library check
if [ -f "/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/torch/lib/libcudnn_cnn_infer.so.8" ]; then
    echo "  ✓ CUDNN library found" >> ${LOG_FILE}
else
    echo "  ✗ CUDNN library NOT found" >> ${LOG_FILE}
fi

# NVRTC library check
if [ -f "/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cuda_nvrtc/lib/libnvrtc.so.12" ]; then
    echo "  ✓ NVRTC library found" >> ${LOG_FILE}
else
    echo "  ✗ NVRTC library NOT found" >> ${LOG_FILE}
fi

# ワーキングディレクトリに移動
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native

# Pythonバージョンの確認
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Python Version:" >> ${LOG_FILE}
/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/bin/python --version >> ${LOG_FILE} 2>&1

# CUDAライブラリの動的リンク確認
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking CUDA Library Loading:" >> ${LOG_FILE}
ldd /home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/torch/lib/libtorch_cuda.so 2>&1 | head -5 >> ${LOG_FILE} || echo "  WARNING: ldd check failed" >> ${LOG_FILE}

# サービスの起動
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting OpenVoice Python Service..." >> ${LOG_FILE}
echo "========================================" >> ${LOG_FILE}

# exec を使用してPIDを引き継ぐ（systemdが正しくプロセスを管理できるように）
exec /home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/bin/python -u main.py >> ${LOG_FILE} 2>&1