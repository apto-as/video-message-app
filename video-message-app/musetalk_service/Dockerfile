# MuseTalk Lip-Sync Service Dockerfile
# Base: NVIDIA CUDA 11.8 with cuDNN 8 for deep learning inference

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

# Python environment settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# CUDA settings
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# Service settings
ENV HOST=0.0.0.0
ENV PORT=8003
ENV STORAGE_DIR=/app/storage
ENV MODELS_DIR=/app/models
ENV MUSETALK_DIR=/app/MuseTalk

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    cmake \
    git \
    git-lfs \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Upgrade pip and ensure setuptools has pkg_resources
RUN python -m pip install --upgrade pip wheel && \
    python -m pip install --upgrade "setuptools>=70.0.0"

# Create working directory
WORKDIR /app

# Clone MuseTalk repository
RUN git clone https://github.com/TMElyralab/MuseTalk.git ${MUSETALK_DIR}

# Install PyTorch with CUDA support (explicitly use python -m pip for consistency)
RUN python -m pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install dlib with CUDA support (build from source for GPU acceleration)
RUN python -m pip install cmake && \
    git clone https://github.com/davisking/dlib.git /tmp/dlib && \
    cd /tmp/dlib && \
    mkdir build && cd build && \
    cmake .. -DDLIB_USE_CUDA=1 -DUSE_AVX_INSTRUCTIONS=1 && \
    cmake --build . --config Release && \
    cd /tmp/dlib && python setup.py install && \
    rm -rf /tmp/dlib

# Copy requirements and install Python dependencies
# Note: openai-whisper requires --no-build-isolation because its setup.py
# uses pkg_resources which isn't available in pip's isolated build environment
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir openai-whisper==20231117 --no-build-isolation && \
    python -m pip install --no-cache-dir -r requirements.txt

# Verify PyTorch is available before MMLab installation
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed, CUDA: {torch.cuda.is_available()}')"

# Install MMLab packages required by MuseTalk (mmpose, mmcv, mmdet)
# Note: mim requires torch to detect CUDA version for correct wheel selection
# Note: chumpy is skipped as it has broken build and MuseTalk doesn't need SMPL body model
RUN python -m pip install --no-cache-dir -U openmim && \
    python -m mim install mmengine && \
    python -m mim install "mmcv==2.0.1" && \
    python -m mim install "mmdet==3.1.0" && \
    python -m pip install --no-cache-dir "mmpose==1.1.0" --no-deps && \
    python -m pip install --no-cache-dir xtcocotools json_tricks munkres

# Install MuseTalk dependencies (MuseTalk is not a pip package, just scripts)
WORKDIR ${MUSETALK_DIR}
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt; fi

# Return to app directory and set PYTHONPATH for MuseTalk imports
WORKDIR /app
ENV PYTHONPATH="${MUSETALK_DIR}:${PYTHONPATH}"

# Create symlink from MuseTalk models to app models (volume mount point)
# MuseTalk's load_all_model() uses relative paths like "models/sd-vae"
RUN rm -rf ${MUSETALK_DIR}/models && ln -s ${MODELS_DIR} ${MUSETALK_DIR}/models

# Copy application code
COPY config.py /app/config.py
COPY models.py /app/models.py
COPY face_utils.py /app/face_utils.py
COPY lipsync_service.py /app/lipsync_service.py
COPY main.py /app/main.py

# Create storage directories (these will be overridden by volume mounts)
RUN mkdir -p ${STORAGE_DIR}/videos ${STORAGE_DIR}/uploads ${STORAGE_DIR}/temp ${MODELS_DIR}

# Note: Running as root to handle mounted volume permissions
# TODO: Add proper user mapping for production security

# Expose port
EXPOSE 8003

# Health check (start-period=180s: GPU model loading takes time on cold start)
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Start command
CMD ["python", "-u", "main.py"]
