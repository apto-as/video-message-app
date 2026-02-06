# LivePortrait + JoyVASA Service Dockerfile
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
ENV PORT=8004
ENV STORAGE_DIR=/app/storage
ENV MODELS_DIR=/app/models

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Create working directory
WORKDIR /app

# Install PyTorch with CUDA support
RUN python -m pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

# Install ONNX Runtime with CUDA support (override CPU version from requirements)
RUN python -m pip install --no-cache-dir onnxruntime-gpu==1.17.0

# Verify installations
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed, CUDA: {torch.cuda.is_available()}')" && \
    python -c "import onnxruntime as ort; print(f'ONNX Runtime {ort.__version__}, providers: {ort.get_available_providers()}')"

# Copy application code
COPY config.py /app/config.py
COPY models.py /app/models.py
COPY utils.py /app/utils.py
COPY motion_generator.py /app/motion_generator.py
COPY joyvasa_pipeline.py /app/joyvasa_pipeline.py
COPY liveportrait_engine.py /app/liveportrait_engine.py
COPY main.py /app/main.py

# Create storage directories (these will be overridden by volume mounts)
RUN mkdir -p ${STORAGE_DIR}/videos ${STORAGE_DIR}/uploads ${STORAGE_DIR}/temp ${MODELS_DIR}

# Expose port
EXPOSE 8004

# Health check (start-period=300s: Model loading takes time on cold start)
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Start command
CMD ["python", "-u", "main.py"]
