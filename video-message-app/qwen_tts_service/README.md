# Qwen3-TTS Service

Zero-shot voice cloning and text-to-speech service using Qwen3-TTS model.
Compatible with OpenVoice API for drop-in replacement.

## Features

- **Zero-shot Voice Cloning**: Clone any voice with just 3 seconds of reference audio
- **Multi-language Support**: Japanese, English, Chinese, Korean, and more
- **VRAM Management**: Lazy model loading and automatic unloading
- **OpenVoice API Compatible**: Drop-in replacement for existing integrations

## Quick Start

### Docker (Recommended)

```bash
# Build with CUDA support (EC2)
docker build --build-arg USE_CUDA=true --build-arg DEVICE=cuda -t qwen3-tts .

# Build CPU-only (Mac/Dev)
docker build --build-arg USE_CUDA=false --build-arg DEVICE=cpu -t qwen3-tts .

# Run
docker run -d \
  --name qwen3-tts \
  --gpus all \
  -p 8002:8002 \
  -v ./storage:/app/storage \
  -v ./models:/app/models \
  qwen3-tts
```

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Run
python main.py
```

## API Endpoints

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "service": "Qwen3-TTS Service",
  "version": "1.0.0",
  "model_loaded": true,
  "pytorch_device": "cuda",
  "model_name": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
}
```

### Create Voice Clone

```bash
POST /voice-clone/create
Content-Type: multipart/form-data

Parameters:
- name: string (required) - Profile name
- audio_samples: file[] (required) - Reference audio files
- language: string (default: "ja") - Language code
- voice_profile_id: string (optional) - Custom profile ID

Response:
{
  "success": true,
  "voice_profile_id": "qwen3tts_abc12345",
  "message": "Voice clone profile created successfully"
}
```

### Synthesize Voice

```bash
POST /voice-clone/synthesize
Content-Type: multipart/form-data

Parameters:
- text: string (required) - Text to synthesize
- voice_profile_id: string (required) - Profile ID
- language: string (default: "ja") - Language code
- speed: float (default: 1.0) - Speech speed (0.5-2.0)
- pitch: float (default: 0.0) - Pitch shift (-0.15 to 0.15)
- volume: float (default: 1.0) - Volume (0.0-2.0)
- pause_duration: float (default: 0.0) - End pause (0.0-3.0 seconds)

Response:
{
  "success": true,
  "audio_data": "<base64-encoded-wav>",
  "duration": 3.5,
  "message": "Synthesis completed successfully"
}
```

### List Profiles

```bash
GET /voice-clone/profiles

Response:
[
  {
    "id": "qwen3tts_abc12345",
    "name": "Sample Voice",
    "language": "ja",
    "status": "ready",
    "created_at": "2025-01-15T10:00:00Z"
  }
]
```

### Delete Profile

```bash
DELETE /voice-clone/profiles/{profile_id}

Response:
{
  "success": true,
  "message": "Profile deleted successfully"
}
```

## Model Management

### Manual Model Loading/Unloading

```bash
# Load model manually
POST /model/load

# Unload model to free VRAM
POST /model/unload

# Check model status
GET /model/status
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE` | auto | Device: cuda, cpu, mps |
| `STORAGE_PATH` | /app/storage | Voice profiles storage |
| `MODELS_PATH` | /app/models | HuggingFace cache |
| `TEMP_PATH` | /tmp/qwen_tts | Temporary files |

## VRAM Requirements

- **Model Size**: ~3.5GB VRAM
- **Inference**: ~1GB additional
- **Recommended**: 6GB+ VRAM (RTX 3060 or better)

## Differences from OpenVoice

| Feature | OpenVoice V2 | Qwen3-TTS |
|---------|-------------|-----------|
| Min Reference Audio | 5 seconds | 3 seconds |
| Sample Rate | 24000 Hz | 22050 Hz |
| Voice Embedding | Speaker embedding file | Reference audio only |
| Inference Speed | Fast | Medium |
| Quality | Good | Better |

## Troubleshooting

### Model Download Slow

The model (~3.5GB) downloads on first use. Set `HF_HOME` to a fast storage location.

### CUDA Out of Memory

1. Use model unloading: `POST /model/unload`
2. Reduce batch size (not applicable for single inference)
3. Use a GPU with more VRAM

### Japanese Text Issues

Ensure proper UTF-8 encoding in your requests.

## License

This service uses the Qwen3-TTS model which is subject to Alibaba's model license.
Check the [model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) for details.
