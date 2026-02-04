"""
MuseTalk Lip-Sync Service - FastAPI Application

A D-ID API compatible service for lip-sync video generation using MuseTalk v1.5
"""
# CRITICAL: Initialize CUDA and load models BEFORE uvicorn starts
# PyTorch CUDA + MuseTalk models must be loaded before uvicorn's event loop
# to avoid segfault caused by CUDA/asyncio interaction
import torch
import sys
import os

# Add MuseTalk to path early
musetalk_dir = os.getenv("MUSETALK_DIR", "/app/MuseTalk")
if musetalk_dir not in sys.path:
    sys.path.insert(0, musetalk_dir)

# Pre-load ALL models synchronously BEFORE any async imports
# This includes vae, unet, pe, AND AudioProcessor to avoid CUDA/asyncio segfault
_preloaded_models = None
_preloaded_audio_processor = None
if torch.cuda.is_available():
    print("Pre-loading MuseTalk models to avoid CUDA/asyncio segfault...")
    torch.cuda.init()
    try:
        from musetalk.utils.utils import load_all_model
        from musetalk.utils.audio_processor import AudioProcessor
        # CRITICAL: Pre-import ALL modules that _generate_video_sync uses
        # These imports trigger dlib/mmpose/CUDA library loading - must happen
        # in the main thread BEFORE uvicorn starts, not in thread pool
        from musetalk.utils.utils import get_file_type, datagen  # noqa: F401
        from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs, coord_placeholder  # noqa: F401
        from musetalk.utils.blending import get_image_prepare_material, get_image_blending  # noqa: F401
        print("Pre-imported all MuseTalk inference modules (preprocessing, blending)")

        # Load main models
        _preloaded_models = load_all_model(device="cuda")
        print(f"Pre-loaded models: {type(_preloaded_models)}, count: {len(_preloaded_models)}")

        # Load audio processor
        models_dir = os.getenv("MODELS_DIR", "/app/models")
        whisper_model_dir = os.path.join(models_dir, "whisper")
        _preloaded_audio_processor = AudioProcessor(feature_extractor_path=whisper_model_dir)
        print(f"Pre-loaded AudioProcessor from {whisper_model_dir}")
    except Exception as e:
        print(f"FATAL: Failed to pre-load models on CUDA: {e}")
        import traceback
        traceback.print_exc()
        print("Exiting: CUDA model pre-loading is required to avoid segfault during async operations")
        sys.exit(1)

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import aiofiles
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import Config
from models import (
    HealthResponse,
    JobStatus,
    JobStatusResponse,
    UploadResponse,
    VideoGenerationResponse,
    JobData
)
from lipsync_service import init_globals

# Initialize global instances with pre-loaded models to avoid CUDA/asyncio segfault
inference_engine, job_queue = init_globals(
    preloaded_models=_preloaded_models,
    preloaded_audio_processor=_preloaded_audio_processor
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(f"Starting {Config.SERVICE_NAME} v{Config.VERSION}")
    logger.info(f"Device: {Config.get_device()}")
    logger.info(f"Storage: {Config.STORAGE_DIR}")

    # Initialize directories
    Config.init_directories()

    # Start job workers
    await job_queue.start_workers(inference_engine)

    # Pre-load models if not lazy loading
    if not Config.LAZY_LOAD:
        logger.info("Pre-loading MuseTalk models...")
        inference_engine.load_models()

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    inference_engine.unload_models()


# Create FastAPI app
app = FastAPI(
    title=Config.SERVICE_NAME,
    description="D-ID API compatible lip-sync video generation service using MuseTalk",
    version=Config.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage directory for serving files
app.mount("/storage", StaticFiles(directory=str(Config.STORAGE_DIR)), name="storage")


# ============================================================================
# Helper Functions
# ============================================================================

def generate_job_id() -> str:
    """Generate unique job ID"""
    return str(uuid.uuid4())


def get_file_hash(content: bytes) -> str:
    """Generate hash for file content"""
    return hashlib.sha256(content).hexdigest()[:16]


async def download_file(url: str, target_path: Path) -> Path:
    """Download file from URL"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        async with aiofiles.open(target_path, 'wb') as f:
            await f.write(response.content)

    return target_path


def validate_image_format(filename: str) -> bool:
    """Validate image file format"""
    ext = filename.lower().split('.')[-1]
    return ext in Config.SUPPORTED_IMAGE_FORMATS


def validate_audio_format(filename: str) -> bool:
    """Validate audio file format"""
    ext = filename.lower().split('.')[-1]
    return ext in Config.SUPPORTED_AUDIO_FORMATS


async def save_upload_file(
    upload_file: UploadFile,
    target_dir: Path,
    max_size_mb: int = 10
) -> Path:
    """Save uploaded file with validation"""
    # Check file size
    content = await upload_file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > max_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size_mb}MB"
        )

    # Generate unique filename
    ext = upload_file.filename.split('.')[-1].lower()
    file_hash = get_file_hash(content)
    filename = f"{file_hash}.{ext}"
    target_path = target_dir / filename

    # Save file
    async with aiofiles.open(target_path, 'wb') as f:
        await f.write(content)

    return target_path


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": Config.SERVICE_NAME,
        "version": Config.VERSION,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    vram_used, vram_total = inference_engine.get_vram_info()
    queued, processing = job_queue.get_stats()

    return HealthResponse(
        status="healthy",
        service=Config.SERVICE_NAME,
        version=Config.VERSION,
        model_loaded=inference_engine.model_loaded,
        device=inference_engine.device,
        vram_used_gb=vram_used,
        vram_total_gb=vram_total,
        jobs_queued=queued,
        jobs_processing=processing
    )


@app.post("/generate-video", response_model=VideoGenerationResponse, tags=["Video Generation"])
async def generate_video(
    audio_url: Optional[str] = Form(None, description="URL to audio file"),
    source_url: Optional[str] = Form(None, description="URL to source image"),
    audio_data: Optional[UploadFile] = File(None, description="Audio file upload"),
    source_image: Optional[UploadFile] = File(None, description="Image file upload"),
):
    """
    Generate lip-sync video from audio and source image.

    Compatible with D-ID API format. Accepts either URLs or file uploads.

    Returns job ID for status polling.
    """
    # Validate inputs
    has_audio = audio_url or audio_data
    has_image = source_url or source_image

    if not has_audio:
        raise HTTPException(status_code=400, detail="Audio is required (audio_url or audio_data)")
    if not has_image:
        raise HTTPException(status_code=400, detail="Source image is required (source_url or source_image)")

    # Check queue capacity
    queued, processing = job_queue.get_stats()
    if queued >= Config.MAX_QUEUE_SIZE:
        raise HTTPException(status_code=503, detail="Queue is full. Please try again later.")

    # Create job
    job_id = generate_job_id()
    job = JobData(job_id)

    try:
        # Process audio input
        if audio_data:
            if not validate_audio_format(audio_data.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format. Supported: {Config.SUPPORTED_AUDIO_FORMATS}"
                )
            audio_path = await save_upload_file(
                audio_data,
                Config.UPLOADS_DIR,
                Config.MAX_AUDIO_SIZE_MB
            )
        else:
            ext = audio_url.split('.')[-1].split('?')[0].lower()
            if ext not in Config.SUPPORTED_AUDIO_FORMATS:
                ext = 'wav'  # Default fallback
            audio_path = Config.UPLOADS_DIR / f"{job_id}_audio.{ext}"
            await download_file(audio_url, audio_path)

        # Process image input
        if source_image:
            if not validate_image_format(source_image.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image format. Supported: {Config.SUPPORTED_IMAGE_FORMATS}"
                )
            image_path = await save_upload_file(
                source_image,
                Config.UPLOADS_DIR,
                Config.MAX_IMAGE_SIZE_MB
            )
        else:
            ext = source_url.split('.')[-1].split('?')[0].lower()
            if ext not in Config.SUPPORTED_IMAGE_FORMATS:
                ext = 'jpg'  # Default fallback
            image_path = Config.UPLOADS_DIR / f"{job_id}_image.{ext}"
            await download_file(source_url, image_path)

        # Set job input paths
        job.audio_path = str(audio_path)
        job.image_path = str(image_path)

        # Add to queue
        if not await job_queue.add_job(job):
            raise HTTPException(status_code=503, detail="Failed to queue job")

        logger.info(f"Created job {job_id}: audio={job.audio_path}, image={job.image_path}")

        return VideoGenerationResponse(
            id=job_id,
            status=JobStatus.QUEUED,
            result_url=None,
            created_at=job.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/talk-status/{talk_id}", response_model=JobStatusResponse, tags=["Video Generation"])
async def get_talk_status(talk_id: str):
    """
    Get status of a video generation job.

    Compatible with D-ID API polling endpoint.
    """
    job = job_queue.get_job(talk_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {talk_id}")

    return job.to_response()


@app.delete("/talk/{talk_id}", tags=["Video Generation"])
async def delete_talk(talk_id: str):
    """
    Delete a video generation job and its output.
    """
    job = job_queue.get_job(talk_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {talk_id}")

    # Delete output video if exists
    video_path = Config.VIDEOS_DIR / f"{talk_id}.mp4"
    if video_path.exists():
        video_path.unlink()

    # Remove from queue
    job_queue.remove_job(talk_id)

    return {"message": f"Job {talk_id} deleted"}


@app.post("/upload-source-image", response_model=UploadResponse, tags=["Uploads"])
async def upload_source_image(file: UploadFile = File(..., description="Source face image")):
    """
    Upload a source image for video generation.

    Returns URL that can be used in generate-video endpoint.
    """
    if not validate_image_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format. Supported: {Config.SUPPORTED_IMAGE_FORMATS}"
        )

    try:
        saved_path = await save_upload_file(file, Config.UPLOADS_DIR, Config.MAX_IMAGE_SIZE_MB)
        filename = saved_path.name
        size = saved_path.stat().st_size

        return UploadResponse(
            url=f"/storage/uploads/{filename}",
            filename=filename,
            size=size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-audio", response_model=UploadResponse, tags=["Uploads"])
async def upload_audio(file: UploadFile = File(..., description="Audio file")):
    """
    Upload an audio file for video generation.

    Returns URL that can be used in generate-video endpoint.
    """
    if not validate_audio_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {Config.SUPPORTED_AUDIO_FORMATS}"
        )

    try:
        saved_path = await save_upload_file(file, Config.UPLOADS_DIR, Config.MAX_AUDIO_SIZE_MB)
        filename = saved_path.name
        size = saved_path.stat().st_size

        return UploadResponse(
            url=f"/storage/uploads/{filename}",
            filename=filename,
            size=size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}", tags=["Videos"])
async def get_video(video_id: str):
    """
    Download a generated video by ID.
    """
    video_path = Config.VIDEOS_DIR / f"{video_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )


@app.post("/models/load", tags=["Models"])
async def load_models():
    """
    Manually trigger model loading.

    Useful for pre-warming the service before first request.
    """
    if inference_engine.model_loaded:
        return {"message": "Models already loaded"}

    success = inference_engine.load_models()
    if success:
        return {"message": "Models loaded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to load models")


@app.post("/models/unload", tags=["Models"])
async def unload_models():
    """
    Manually unload models to free VRAM.
    """
    if not inference_engine.model_loaded:
        return {"message": "Models not loaded"}

    inference_engine.unload_models()
    return {"message": "Models unloaded"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        workers=1  # Single worker for GPU inference
    )
