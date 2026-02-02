# Local Inference Architecture Design

## Overview

This document describes the architectural design for migrating Video Message App from cloud-dependent services to fully local inference on AWS EC2.

**Project**: Video Message App - Local Inference Migration
**Branch**: `feature/local-inference`
**Target Environment**: AWS EC2 g4dn.xlarge (Tesla T4 16GB VRAM)

## Migration Summary

| Component | Current | New | Status |
|-----------|---------|-----|--------|
| TTS | OpenVoice V2 | Qwen3-TTS-12Hz-1.7B-Base | Planned |
| Voice Cloning | OpenVoice V2 | Qwen3-TTS (Zero-shot) | Planned |
| Lip-Sync | D-ID API (Cloud) | MuseTalk v1.5 | Planned |
| Inpainting | N/A | LaMa | Planned |
| Japanese TTS Fallback | VOICEVOX | VOICEVOX (Keep) | No Change |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NEW ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    NGINX (443/80)                            │   │
│  │                  SSL Termination                             │   │
│  └──────────┬──────────────────────┬────────────────────────────┘   │
│             │                      │                                │
│    ┌────────▼────────┐    ┌───────▼───────┐                        │
│    │    Frontend     │    │    Backend    │                        │
│    │      :80        │    │    :55433     │                        │
│    └─────────────────┘    └───────┬───────┘                        │
│                                   │                                │
│      ┌────────────────────────────┼────────────────────────────┐   │
│      │                            │                            │   │
│ ┌────▼────┐  ┌────────────┐  ┌────▼────┐  ┌──────────────┐    │   │
│ │Qwen3-TTS│  │  VOICEVOX  │  │MuseTalk │  │    LaMa      │    │   │
│ │  :8002  │  │   :50021   │  │  :8003  │  │ (embedded)   │    │   │
│ │GPU:6-8GB│  │   (CPU)    │  │GPU:8-12G│  │ GPU: 2-4GB   │    │   │
│ └─────────┘  └────────────┘  └─────────┘  └──────────────┘    │   │
│                                                                │   │
│  ══════════════════════════════════════════════════════════   │   │
│                   Tesla T4 16GB VRAM                          │   │
│            Sequential Processing (VRAM Sharing)               │   │
│  ══════════════════════════════════════════════════════════   │   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Processing Pipeline

```
[User Request]
       │
       ▼
┌──────────────────┐
│  1. Image Upload │
│  (Source Photo)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ 2. Background    │────▶│ 3. LaMa Repair   │ (if clothing damaged)
│    Removal       │     │ (Inpainting)     │
│    (rembg)       │     │ VRAM: 2-4GB      │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └───────────┬────────────┘
                     ▼
         ┌──────────────────┐
         │ 4. Qwen3-TTS     │
         │ Voice Synthesis  │
         │ VRAM: 6-8GB      │
         │ (Zero-shot Clone)│
         └────────┬─────────┘
                  │ torch.cuda.empty_cache()
                  ▼
         ┌──────────────────┐
         │ 5. MuseTalk      │
         │ Lip-Sync Video   │
         │ VRAM: 8-12GB     │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ 6. Output Video  │
         │ (MP4)            │
         └──────────────────┘
```

## VRAM Management Strategy

Since T4 has only 16GB VRAM and combined peak usage exceeds this:
- Qwen3-TTS: 6-8GB
- MuseTalk: 8-12GB
- Total: 14-20GB (EXCEEDS 16GB)

**Solution**: Sequential processing with explicit VRAM release

```python
# Step 1: LaMa Inpainting (if needed)
lama_model = load_lama()
repaired_image = lama_model(image, mask)
del lama_model
torch.cuda.empty_cache()  # Release ~2-4GB

# Step 2: TTS Synthesis
tts_model = load_qwen3_tts()
audio = tts_model.synthesize(text, reference_audio)
del tts_model
torch.cuda.empty_cache()  # Release ~6-8GB

# Step 3: Lip-Sync Generation
musetalk_model = load_musetalk()
video = musetalk_model.generate(image, audio)
del musetalk_model
torch.cuda.empty_cache()  # Release ~8-12GB
```

## Service Specifications

### 1. Qwen3-TTS Service (Port 8002)

**Technology**: Qwen3-TTS-12Hz-1.7B-Base
**VRAM**: 6-8GB
**Features**:
- Zero-shot voice cloning (3s reference audio)
- 10 languages including Japanese
- Streaming support
- Apache 2.0 License

**API Endpoints** (Compatible with current OpenVoice):
```
POST /voice-clone/create
  - name: str
  - audio_samples: List[UploadFile]
  - language: str = "ja"
  - voice_profile_id: str (optional)
  Response: { success: bool, profile_id: str, message: str }

POST /voice-clone/synthesize
  - text: str
  - voice_profile_id: str
  - language: str = "ja"
  - speed: float = 1.0
  - pitch: float = 0.0
  - volume: float = 1.0
  - pause_duration: float = 0.0
  Response: { success: bool, audio_data: str (base64) }

GET /voice-clone/profiles
  Response: List[VoiceProfile]

DELETE /voice-clone/profiles/{profile_id}
  Response: { success: bool, message: str }

GET /health
  Response: { status: str, service: str, model_loaded: bool }
```

### 2. MuseTalk Service (Port 8003)

**Technology**: MuseTalk v1.5
**VRAM**: 8-12GB
**Features**:
- Real-time lip-sync (30+ fps on V100-equivalent)
- 256x256 resolution
- MIT License

**API Endpoints** (Compatible with current D-ID):
```
POST /generate-video
  - audio_url: str (or audio_data: bytes)
  - source_url: str (or source_data: bytes)
  Response: { id: str, status: str, result_url: str, created_at: str }

GET /talk-status/{talk_id}
  Response: { id: str, status: str, result_url: str, ... }

POST /upload-source-image
  - file: UploadFile
  Response: { url: str }

POST /upload-audio
  - file: UploadFile
  Response: { url: str }

GET /health
  Response: { status: str, service: str, model_loaded: bool }
```

### 3. LaMa Inpainting (Embedded in Backend)

**Technology**: LaMa (simple-lama-inpainting)
**VRAM**: 2-4GB
**License**: Apache 2.0

**Integration**: Called from `backend/services/inpainting_service.py`
```python
from simple_lama_inpainting import SimpleLama

class InpaintingService:
    def repair_clothing(self, image: bytes, mask: bytes) -> bytes:
        """Repair damaged clothing from background removal"""
        lama = SimpleLama()
        result = lama(image, mask)
        del lama
        torch.cuda.empty_cache()
        return result
```

## Docker Configuration

### docker-compose.yml (New Services)

```yaml
version: '3.8'

services:
  # NEW: Qwen3-TTS Service (replaces OpenVoice)
  qwen-tts:
    build:
      context: ./qwen_tts_service
      dockerfile: Dockerfile
    container_name: qwen_tts
    runtime: nvidia
    ports:
      - "8002:8002"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./data/models/qwen-tts:/app/models
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
      - MODEL_NAME=Qwen/Qwen3-TTS-12Hz-1.7B-Base
    networks:
      - voice_network
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # NEW: MuseTalk Lip-Sync Service (replaces D-ID API)
  musetalk:
    build:
      context: ./musetalk_service
      dockerfile: Dockerfile
    container_name: musetalk
    runtime: nvidia
    ports:
      - "8003:8003"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./data/models/musetalk:/app/models
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
    networks:
      - voice_network
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # KEEP: VOICEVOX (Japanese TTS fallback)
  voicevox:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    container_name: voicevox_engine
    ports:
      - "50021:50021"
    networks:
      - voice_network
    restart: unless-stopped

  # UPDATED: Backend with new service URLs
  backend:
    build: ./backend
    container_name: voice_backend
    runtime: nvidia
    expose:
      - "55433"
    volumes:
      - ./data/backend/storage:/app/storage
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - QWEN_TTS_URL=http://qwen-tts:8002
      - MUSETALK_URL=http://musetalk:8003
      - VOICEVOX_URL=http://voicevox:50021
      # Keep D-ID for emergency fallback
      - D_ID_API_KEY=${D_ID_API_KEY:-}
      - USE_LOCAL_LIPSYNC=true
      - USE_LOCAL_TTS=true
    networks:
      - voice_network
    depends_on:
      - qwen-tts
      - musetalk
      - voicevox
    restart: unless-stopped

  # KEEP: Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.production
    container_name: voice_frontend
    expose:
      - "80"
    networks:
      - voice_network
    depends_on:
      - backend
    restart: unless-stopped

  # KEEP: Nginx
  nginx:
    image: nginx:alpine
    container_name: voice_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    networks:
      - voice_network
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

networks:
  voice_network:
    driver: bridge
```

## Directory Structure

```
video-message-app/
├── docker-compose.yml              # Updated with new services
├── backend/
│   ├── services/
│   │   ├── qwen_tts_client.py     # NEW: Qwen3-TTS client
│   │   ├── musetalk_client.py     # NEW: MuseTalk client
│   │   ├── inpainting_service.py  # NEW: LaMa integration
│   │   ├── openvoice_native_client.py  # DEPRECATED
│   │   ├── d_id_client.py         # DEPRECATED (keep for fallback)
│   │   └── ...
│   └── ...
├── qwen_tts_service/               # NEW: Qwen3-TTS container
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── tts_service.py
│   └── models/
├── musetalk_service/               # NEW: MuseTalk container
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── lipsync_service.py
│   └── models/
├── data/
│   ├── models/
│   │   ├── qwen-tts/              # ~4GB
│   │   └── musetalk/              # ~2GB
│   └── backend/storage/
│       └── voices/                # Voice profiles
└── docs/
    └── architecture/
        └── LOCAL_INFERENCE_DESIGN.md  # This file
```

## Voice Profile Migration

Existing OpenVoice profiles will be migrated to Qwen3-TTS format:

### Current Profiles
| ID | Name | Created |
|----|------|---------|
| openvoice_c403f011 | 女性1 | 2025-09-13 |
| openvoice_78450a3c | 男性1 | 2025-09-14 |
| openvoice_d4be3324 | 男性2 | 2025-10-06 |

### Migration Strategy
1. Keep reference audio files (sample_01.wav, etc.)
2. Qwen3-TTS uses reference audio directly for zero-shot cloning
3. No embedding file conversion needed (Qwen3 generates on-the-fly)
4. Profile metadata format remains compatible

## Feature Flags

Backend environment variables for gradual migration:

```bash
# TTS Engine Selection
USE_LOCAL_TTS=true          # true: Qwen3-TTS, false: OpenVoice
TTS_FALLBACK_ENABLED=true   # Enable VOICEVOX fallback

# Lip-Sync Engine Selection
USE_LOCAL_LIPSYNC=true      # true: MuseTalk, false: D-ID API

# Inpainting
INPAINTING_ENABLED=true     # Enable LaMa clothing repair
INPAINTING_THRESHOLD=0.01   # Damage detection threshold (1%)
```

## Rollback Procedure

If issues occur, rollback by:

1. **Environment Variables**:
   ```bash
   USE_LOCAL_TTS=false
   USE_LOCAL_LIPSYNC=false
   ```

2. **Docker Compose**:
   ```bash
   docker-compose stop qwen-tts musetalk
   docker-compose up -d openvoice  # Restart old service
   ```

3. **Code**:
   ```bash
   git checkout main -- backend/services/
   ```

## Testing Strategy

### Phase 1: TTS Testing
- [ ] Qwen3-TTS model loading
- [ ] Voice cloning with existing profiles
- [ ] Japanese text synthesis quality
- [ ] A/B comparison with OpenVoice

### Phase 1.5: Inpainting Testing
- [ ] LaMa model loading
- [ ] Clothing damage detection
- [ ] Repair quality assessment

### Phase 2: Lip-Sync Testing
- [ ] MuseTalk model loading
- [ ] Video generation quality
- [ ] Comparison with D-ID output
- [ ] Processing time benchmarks

### Phase 3: Integration Testing
- [ ] End-to-end pipeline
- [ ] VRAM sequential processing
- [ ] Error recovery
- [ ] Progress tracking

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| TTS Quality (MOS) | >= 4.0 | User survey |
| Lip-Sync Accuracy | >= 90% | Manual review |
| E2E Processing Time | < 45s | Automated test |
| VRAM Peak Usage | < 14GB | nvidia-smi |
| D-ID API Cost | $0/month | AWS billing |

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 0: Preparation | 1 week | Branch, docs, API contracts |
| 1: Qwen3-TTS | 2 weeks | TTS service, voice cloning |
| 1.5: LaMa | 1 week | Inpainting integration |
| 2: MuseTalk | 3 weeks | Lip-sync service |
| 3: Integration | 2 weeks | Pipeline, testing |
| 4: Optimization | 2 weeks | TensorRT, cleanup |
| **Total** | **11 weeks** | |

---

**Document Version**: 1.0
**Created**: 2026-02-02
**Author**: Trinitas Orchestration Team (Clotho + Lachesis)
**Status**: Phase 0 - In Progress
