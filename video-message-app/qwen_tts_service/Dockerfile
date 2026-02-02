# Qwen3-TTS Service Dockerfile
# Supports CUDA (EC2 GPU) and CPU environments

# ============================================
# Base Stage
# ============================================
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS cuda-base

# Build arguments
ARG USE_CUDA=true
ARG DEVICE=cuda
ARG PYTHON_VERSION=3.11

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    git \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    libsndfile1 \
    libsndfile1-dev \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-distutils \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

# Install pip
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

# ============================================
# CPU-only Stage (for non-GPU environments)
# ============================================
FROM python:3.11-slim AS cpu-base

# Build arguments
ARG USE_CUDA=false
ARG DEVICE=cpu

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Final Stage (select based on USE_CUDA)
# ============================================
FROM cuda-base AS final

# Re-declare ARGs after FROM
ARG USE_CUDA=true
ARG DEVICE=cuda

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install PyTorch with CUDA support
RUN if [ "$USE_CUDA" = "true" ]; then \
        pip install --no-cache-dir torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install flash-attention for faster inference (CUDA only)
RUN if [ "$USE_CUDA" = "true" ]; then \
        pip install --no-cache-dir ninja packaging && \
        pip install --no-cache-dir flash-attn --no-build-isolation || echo "Flash attention install failed, continuing without it"; \
    fi

# Copy application code
COPY main.py .
COPY config.py .
COPY models.py .
COPY tts_service.py .

# Create directories
RUN mkdir -p /app/storage/voices/profiles \
    /app/models/huggingface \
    /tmp/qwen_tts

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEVICE=${DEVICE} \
    STORAGE_PATH=/app/storage \
    MODELS_PATH=/app/models \
    TEMP_PATH=/tmp/qwen_tts \
    QWEN_BASE_DIR=/app \
    HF_HOME=/app/models/huggingface \
    TRANSFORMERS_CACHE=/app/models/huggingface

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application
CMD ["python", "-u", "main.py"]
