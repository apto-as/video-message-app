# NVIDIA CUDA base image with cuDNN for YOLOv8 GPU acceleration
# Using runtime image (smaller) with manually installed nvrtc
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set CUDA library paths for cuDNN and nvrtc
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:${LD_LIBRARY_PATH}
ENV PATH=/usr/local/cuda/bin:${PATH}

# Install NVRTC (NVIDIA Runtime Compiler) library required by cuDNN
# This is the missing component in the runtime image
RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-nvrtc-11-8 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
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

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Upgrade pip
RUN python -m pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# PyTorch with CUDA support for YOLOv8 Person Detection
# EC2 (g4dn.xlarge) uses NVIDIA Tesla T4 GPU with CUDA 11.8
# Note: torchvision 0.15.1 requires torch 2.0.0 (not 2.0.1)
RUN pip install --no-cache-dir torch==2.0.0+cu118 torchvision==0.15.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/voices

# Set environment variables
ENV PYTHONPATH=/app
ENV VOICEVOX_BASE_URL=http://voicevox:50021
ENV OPENVOICE_API_URL=http://localhost:8001

# Expose port
EXPOSE 55433

# Health check
HEALTHCHECK --interval=120s --timeout=30s --start-period=180s --retries=2 \
  CMD curl -s -f http://localhost:55433/health > /dev/null || exit 1

# Start application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "55433", "--reload", "--timeout-keep-alive", "300", "--timeout-graceful-shutdown", "30"]
