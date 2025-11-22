# OpenVoice Native Service - Python 3.11 Docker Image
# Supports both CUDA (EC2) and CPU (Mac) environments

FROM python:3.11-slim as base

# Build argument for CUDA support
ARG USE_CUDA=false
ARG DEVICE=cpu

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
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
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install PyTorch based on CUDA availability
RUN if [ "$USE_CUDA" = "true" ]; then \
        pip install --no-cache-dir torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install MeloTTS from GitHub (pip package is broken)
RUN pip install --no-cache-dir git+https://github.com/myshell-ai/MeloTTS.git

# Download UniDic dictionary for Japanese text processing
RUN python -m unidic download

# Copy OpenVoiceV2 source code
COPY OpenVoiceV2/ /app/OpenVoiceV2/

# Install OpenVoiceV2 in editable mode
WORKDIR /app/OpenVoiceV2
RUN pip install --no-deps -e .

# Return to main working directory
WORKDIR /app

# Copy application code
COPY main.py .
COPY config.py .
COPY models.py .
COPY openvoice_service.py .

# Create necessary directories
RUN mkdir -p /app/storage/openvoice /app/storage/voices /app/data/openvoice

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEVICE=${DEVICE}
ENV STORAGE_PATH=/app/storage
ENV OPENVOICE_BASE_DIR=/app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["python", "-u", "main.py"]
