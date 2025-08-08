# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video Message App - AI-powered video generation application using D-ID API with voice synthesis capabilities. The system combines VOICEVOX, OpenVoice V2, and D-ID to create talking avatar videos from photos and text.

## Architecture

### Core Services

1. **Backend (FastAPI)** - Port 55433
   - Main API server handling video generation, voice synthesis, and file management
   - Runs in Docker container with environment-specific path management
   - Key routers: `voice`, `voicevox`, `unified_voice`, `voice_clone`, `background`, `d_id`

2. **Frontend (React 19)** - Port 55434
   - Modern React application with voice selection and video generation UI
   - Supports drag-and-drop image upload and real-time preview

3. **OpenVoice Native Service** - Port 8001
   - Separate Python service for voice cloning (Mac-native, not Dockerized)
   - Requires Conda environment `openvoice_v2`
   - Handles voice feature extraction and synthesis

4. **VOICEVOX Engine** - Port 50021
   - Docker container for Japanese text-to-speech
   - CPU version for Mac compatibility

### Data Flow

1. User uploads image + enters text ’ Frontend
2. Frontend sends to Backend API
3. Backend orchestrates:
   - Voice synthesis (VOICEVOX or OpenVoice)
   - D-ID API call for video generation
   - File storage and profile management
4. Generated video returned to user

## Commands

### Development Setup

```bash
# Initial setup (once)
./setup_new_env.sh prototype-app  # Creates Conda environment

# Start services
# Terminal 1 - OpenVoice Native Service
cd openvoice_native
conda activate openvoice_v2
python main.py

# Terminal 2 - Docker services
docker-compose up -d

# Access
open http://localhost:55434
```

### Common Tasks

```bash
# Check service health
curl http://localhost:55433/health
curl http://localhost:8001/health

# View voice profiles
curl http://localhost:55433/api/voice-clone/profiles | jq

# Restart backend only
docker-compose restart backend

# View logs
docker logs voice_backend --tail 50
docker logs voice_frontend --tail 50

# Stop all services
docker-compose down
```

### Testing Voice Clone

```bash
# Test synthesis with existing profile
python backend/scripts/test_voice_synthesis.py

# Delete a profile
curl -X DELETE http://localhost:55433/api/voice-clone/profiles/{profile_id}
```

## Environment Configuration

The system uses environment-aware path management:

- **Docker**: Uses `/app/storage/` paths internally
- **Local**: Uses absolute paths like `/Users/.../data/backend/storage/`
- **Auto-detection**: `EnvironmentConfig` class handles path translation

Key environment files:
- `backend/.env` - Local development
- `backend/.env.docker` - Docker environment
- Both need `D_ID_API_KEY` for video generation

## Critical Implementation Details

### Path Management (VoiceStorageService)
- Automatically detects Docker vs local environment
- Handles path translation for file operations
- Metadata stored in `data/backend/storage/voices/voices_metadata.json`

### Voice Profile ID Synchronization
- Backend generates profile IDs like `openvoice_9f913e90`
- OpenVoice Native Service must use the same ID (not generate its own)
- Embedding files (.pkl) stored in `data/backend/storage/openvoice/`

### Error Handling Patterns
- Profile deletion is tolerant - removes from metadata even if files missing
- Voice synthesis has fallback: Native Service ’ Reference audio ’ Error
- Docker/local path mismatches handled via environment detection

### OpenVoice Native Service Integration
- Runs outside Docker due to Mac MPS (Metal) support requirements
- Communicates via `host.docker.internal:8001` from Docker
- Whisper model patched to force CPU mode on Mac to avoid CUDA errors

## Known Issues & Solutions

1. **"CTranslate2 package was not compiled with CUDA support"**
   - Solution: OpenVoice service monkey-patches WhisperModel to use CPU

2. **Profiles not showing in list**
   - Check metadata file exists and is properly formatted
   - Verify Docker volumes are mounted correctly

3. **Profile deletion 404 errors**
   - Normal if directory already deleted - metadata cleanup continues

4. **Docker connection reset**
   - Ensure Docker Desktop is running: `open -a Docker`
   - Wait 30 seconds before starting services

## Dependencies Management

- Backend uses standard pip requirements
- OpenVoice Native requires specific Conda environment (Python 3.11.12)
- NumPy version must be <2.0 to avoid compatibility issues
- FFmpeg required system-wide for audio processing