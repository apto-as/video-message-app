"""
Qwen3-TTS Service FastAPI Application
Compatible with OpenVoice API for drop-in replacement
"""

import logging
import asyncio
import aiofiles
import json
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional

from config import config
from models import (
    VoiceCloneRequest,
    VoiceSynthesisRequest,
    VoiceProfile,
    VoiceCloneResponse,
    VoiceSynthesisResponse,
    HealthCheckResponse,
    ErrorResponse,
)
from tts_service import Qwen3TTSService

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service instance
tts_service = Qwen3TTSService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Qwen3-TTS Service starting...")

    # Initialize service
    success = await tts_service.initialize()
    if not success:
        logger.error("Qwen3-TTS service initialization failed")
        # Continue anyway - health check will show degraded status

    logger.info(f"Qwen3-TTS Service started (Port: {config.port}, Device: {config.device})")

    yield

    # Shutdown
    logger.info("Qwen3-TTS Service shutting down...")


# FastAPI application
app = FastAPI(
    title="Qwen3-TTS Service",
    description="Zero-shot voice cloning and TTS using Qwen3-TTS model. Compatible with OpenVoice API.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
        ).model_dump()
    )


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint"""
    return await health_check()


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check - compatible with OpenVoice API"""
    status_data = await tts_service.get_health_status()
    return HealthCheckResponse(**status_data)


@app.post("/voice-clone/create", response_model=VoiceCloneResponse)
async def create_voice_clone(
    name: str = Form(..., description="Voice profile name"),
    language: str = Form(default="ja", description="Language code"),
    description: Optional[str] = Form(None, description="Description"),
    voice_profile_id: Optional[str] = Form(None, description="Profile ID (optional, from backend)"),
    audio_samples: List[UploadFile] = File(..., description="Audio samples (minimum 1, recommended 3+)")
):
    """Create voice clone - compatible with OpenVoice API

    Creates a voice profile from reference audio samples.
    Qwen3-TTS can work with a single audio sample (minimum 3 seconds),
    but quality improves with more samples.
    """

    # Validate audio samples
    if len(audio_samples) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least 1 audio sample is required"
        )

    try:
        # Read audio data
        audio_files = []
        for sample in audio_samples:
            content = await sample.read()
            if len(content) > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio file {sample.filename} is too large (max 50MB)"
                )
            if len(content) < 1024:  # Minimum 1KB
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio file {sample.filename} is too small"
                )
            audio_files.append(content)

        # Create voice clone
        result = await tts_service.create_voice_clone(
            name=name,
            audio_files=audio_files,
            language=language,
            profile_id=voice_profile_id,
        )

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error or "Voice clone creation failed"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice clone creation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice clone creation failed: {str(e)}"
        )


@app.post("/voice-clone/synthesize", response_model=VoiceSynthesisResponse)
async def synthesize_voice(
    text: str = Form(..., description="Text to synthesize"),
    voice_profile_id: str = Form(..., description="Voice profile ID"),
    language: str = Form(default="ja", description="Language code"),
    speed: float = Form(default=1.0, description="Speech speed (0.5-2.0)"),
    pitch: float = Form(default=0.0, description="Pitch shift (-0.15 to 0.15)"),
    volume: float = Form(default=1.0, description="Volume (0.0-2.0)"),
    pause_duration: float = Form(default=0.0, description="End pause duration in seconds (0.0-3.0)")
):
    """Synthesize voice - compatible with OpenVoice API

    Generates speech using the specified voice profile.

    Args:
        text: Text to synthesize
        voice_profile_id: Voice profile ID
        language: Language code (ja/en/zh/ko/etc.)
        speed: Speech speed (0.5-2.0)
        pitch: Pitch shift (-0.15 to 0.15)
        volume: Volume (0.0-2.0)
        pause_duration: End pause duration in seconds (0.0-3.0)
    """

    # Parameter validation
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    if not (0.5 <= speed <= 2.0):
        raise HTTPException(
            status_code=400,
            detail="Speed must be between 0.5 and 2.0"
        )

    if not (-0.15 <= pitch <= 0.15):
        raise HTTPException(
            status_code=400,
            detail="Pitch shift must be between -0.15 and 0.15"
        )

    if not (0.0 <= volume <= 2.0):
        raise HTTPException(
            status_code=400,
            detail="Volume must be between 0.0 and 2.0"
        )

    if not (0.0 <= pause_duration <= 3.0):
        raise HTTPException(
            status_code=400,
            detail="Pause duration must be between 0.0 and 3.0"
        )

    try:
        # Perform synthesis
        result = await tts_service.synthesize_voice(
            text=text,
            voice_profile_id=voice_profile_id,
            language=language,
            speed=speed,
            pitch=pitch,
            volume=volume,
            pause_duration=pause_duration,
        )

        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error or "Synthesis failed"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {str(e)}"
        )


@app.get("/voice-clone/profiles")
async def list_voice_profiles():
    """List voice profiles - compatible with OpenVoice API"""
    try:
        profiles = await tts_service.list_profiles()
        return [profile.model_dump() for profile in profiles]

    except Exception as e:
        logger.error(f"Profile list error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list profiles: {str(e)}"
        )


@app.delete("/voice-clone/profiles/{profile_id}")
async def delete_voice_profile(profile_id: str):
    """Delete voice profile - compatible with OpenVoice API"""
    try:
        success = await tts_service.delete_profile(profile_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Profile not found"
            )

        return {
            "success": True,
            "message": f"Profile {profile_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile deletion error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Profile deletion failed: {str(e)}"
        )


# Additional endpoints for Qwen3-TTS specific features

@app.get("/model/status")
async def get_model_status():
    """Get model loading status"""
    status = await tts_service.get_health_status()
    return {
        "model_loaded": status.get("model_loaded", False),
        "model_name": status.get("model_name", config.model_name),
        "device": status.get("pytorch_device", config.device),
        "vram_usage_mb": status.get("vram_usage_mb"),
    }


@app.post("/model/load")
async def load_model():
    """Manually trigger model loading"""
    success = await tts_service._load_model()
    return {
        "success": success,
        "message": "Model loaded" if success else "Model loading failed"
    }


@app.post("/model/unload")
async def unload_model():
    """Manually unload model to free VRAM"""
    await tts_service._unload_model()
    return {
        "success": True,
        "message": "Model unloaded"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info"
    )
