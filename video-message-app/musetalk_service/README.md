# MuseTalk Lip-Sync Service

D-ID API compatible lip-sync video generation service using [MuseTalk v1.5](https://github.com/TMElyralab/MuseTalk).

## Overview

This service provides real-time lip-sync video generation from a single face image and audio input. It's designed as a drop-in replacement for D-ID API with compatible endpoints.

### Key Features

- **D-ID API Compatible**: Same endpoint structure for easy migration
- **MuseTalk v1.5**: State-of-the-art lip-sync generation
- **CUDA Optimized**: Efficient GPU inference with VRAM management
- **Async Job Processing**: Background processing with status polling
- **File Upload Support**: Direct file uploads or URL references

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  /generate   │ /talk-status │   /upload-*  │    /health    │
│    -video    │   /{id}      │              │               │
└──────┬───────┴──────┬───────┴──────────────┴───────────────┘
       │              │
       ▼              ▼
┌──────────────┐ ┌──────────────┐
│  Job Queue   │ │  Job Store   │
│  (asyncio)   │ │   (dict)     │
└──────┬───────┘ └──────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│         MuseTalk Inference           │
│  ┌──────────┬──────────┬──────────┐  │
│  │   VAE    │   UNet   │  Whisper │  │
│  │ Encoder  │ Lip-Sync │  Audio   │  │
│  └──────────┴──────────┴──────────┘  │
└──────────────────────────────────────┘
```

## API Endpoints

### Video Generation

#### POST /generate-video

Create a new lip-sync video generation job.

**Request (Form Data):**
```
audio_url: str (optional) - URL to audio file
source_url: str (optional) - URL to source image
audio_data: File (optional) - Audio file upload
source_image: File (optional) - Image file upload
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "result_url": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### GET /talk-status/{talk_id}

Get status of a video generation job.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "result_url": "/storage/videos/550e8400-e29b-41d4-a716-446655440000.mp4",
  "progress": 1.0,
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:05Z",
  "completed_at": "2025-01-15T10:31:00Z",
  "error": null
}
```

### File Uploads

#### POST /upload-source-image

Upload a source face image.

#### POST /upload-audio

Upload an audio file.

### Health Check

#### GET /health

```json
{
  "status": "healthy",
  "service": "MuseTalk Lip-Sync Service",
  "version": "1.0.0",
  "model_loaded": true,
  "device": "cuda",
  "vram_used_gb": 4.2,
  "vram_total_gb": 16.0,
  "jobs_queued": 0,
  "jobs_processing": 1
}
```

## Docker Deployment

### Build Image

```bash
cd musetalk_service
docker build -t musetalk-service:latest .
```

### Run Container

```bash
docker run -d \
  --name musetalk-service \
  --gpus all \
  -p 8003:8003 \
  -v /path/to/storage:/app/storage \
  -v /path/to/models:/app/models \
  musetalk-service:latest
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  musetalk:
    build: ./musetalk_service
    container_name: musetalk_service
    ports:
      - "8003:8003"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./data/musetalk/models:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - LAZY_LOAD=true
      - MAX_CONCURRENT_JOBS=2
      - CLEAR_CACHE_AFTER_GENERATION=true
    restart: unless-stopped
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8003` | Server port |
| `STORAGE_DIR` | `/app/storage` | Storage directory |
| `MODELS_DIR` | `/app/models` | Models directory |
| `MUSETALK_DIR` | `/app/MuseTalk` | MuseTalk installation |
| `LAZY_LOAD` | `true` | Lazy load models on first request |
| `UNLOAD_IDLE_SECONDS` | `300` | Unload models after idle time |
| `MAX_VRAM_GB` | `14.0` | Maximum VRAM usage |
| `CLEAR_CACHE_AFTER_GENERATION` | `true` | Clear VRAM cache after each job |
| `OUTPUT_RESOLUTION` | `256` | Output video resolution |
| `OUTPUT_FPS` | `25` | Output video frame rate |
| `MAX_CONCURRENT_JOBS` | `2` | Maximum parallel jobs |
| `JOB_TIMEOUT_SECONDS` | `600` | Job timeout in seconds |
| `MAX_QUEUE_SIZE` | `10` | Maximum queued jobs |

## Model Downloads

MuseTalk models are automatically downloaded from HuggingFace on first use.
For faster startup, pre-download models:

```bash
# Download models to local directory
git lfs install
git clone https://huggingface.co/TMElyralab/MuseTalk /path/to/models/musetalk

# Mount in Docker
docker run -v /path/to/models/musetalk:/app/models ...
```

## VRAM Management

This service is optimized for NVIDIA Tesla T4 (16GB VRAM):

1. **Lazy Loading**: Models loaded on first request
2. **Cache Clearing**: VRAM cleared after each generation
3. **Idle Unloading**: Models unloaded after 5 minutes of inactivity
4. **FP16 Precision**: Half-precision inference on CUDA

### Estimated VRAM Usage

| Component | VRAM |
|-----------|------|
| VAE | ~1.5 GB |
| UNet | ~2.0 GB |
| Audio Processor | ~0.5 GB |
| **Total Base** | **~4.0 GB** |
| Per-batch inference | ~2-4 GB |
| **Peak Usage** | **~8-10 GB** |

## Supported Formats

### Input Images
- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)

### Input Audio
- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- OGG (.ogg)
- FLAC (.flac)

### Output Video
- MP4 (H.264 + AAC)

## Performance

| Metric | Value |
|--------|-------|
| Resolution | 256x256 |
| FPS | 25 |
| Processing Speed | ~2x real-time on T4 |
| Typical Generation | 30s audio -> 15-20s processing |

## Troubleshooting

### CUDA Out of Memory

```bash
# Reduce concurrent jobs
export MAX_CONCURRENT_JOBS=1

# Enable aggressive cache clearing
export CLEAR_CACHE_AFTER_GENERATION=true

# Reduce max VRAM
export MAX_VRAM_GB=12.0
```

### Model Loading Fails

```bash
# Check MuseTalk installation
docker exec musetalk-service python -c "import musetalk; print('OK')"

# Verify model files
docker exec musetalk-service ls -la /app/models/
```

### No Face Detected

- Ensure source image has a clear, front-facing face
- Image should be well-lit with minimal occlusion
- Minimum resolution: 256x256

## Migration from D-ID

Replace D-ID API URL with this service:

```python
# Before (D-ID)
DID_API_URL = "https://api.d-id.com/talks"

# After (MuseTalk)
DID_API_URL = "http://localhost:8003"

# API calls remain the same
response = requests.post(f"{DID_API_URL}/generate-video", ...)
status = requests.get(f"{DID_API_URL}/talk-status/{talk_id}")
```

## License

This service uses MuseTalk which is released under a research license.
Please check the [MuseTalk license](https://github.com/TMElyralab/MuseTalk/blob/main/LICENSE) for commercial use restrictions.

## References

- [MuseTalk Paper](https://arxiv.org/abs/2401.10761)
- [MuseTalk GitHub](https://github.com/TMElyralab/MuseTalk)
- [D-ID API Documentation](https://docs.d-id.com/)
