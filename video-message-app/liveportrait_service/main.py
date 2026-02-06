"""
LivePortrait + JoyVASA Service - FastAPI Application

Audio-driven portrait animation service combining:
- JoyVASA for audio-to-motion generation
- LivePortrait for motion-to-video synthesis
"""
import asyncio
import hashlib
import ipaddress
import logging
import os
import shutil
import socket
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

import aiofiles
import httpx
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import Config
from models import (
    AnimationMode,
    HealthResponse,
    JobData,
    JobStatus,
    JobStatusResponse,
    ModelStatus,
    UploadResponse,
    VideoGenerationResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Global State
# ============================================================================

class ServiceState:
    """Global service state manager"""

    def __init__(self):
        self.joyvasa_pipeline = None
        self.liveportrait_engine = None
        self.jobs: Dict[str, JobData] = {}
        self.queue: asyncio.Queue = None
        self.workers_started = False

    async def initialize(self):
        """Initialize service components"""
        from joyvasa_pipeline import JoyVASAPipeline
        from liveportrait_engine import LivePortraitEngine

        device = Config.get_device()
        logger.info(f"Initializing service on device: {device}")

        self.joyvasa_pipeline = JoyVASAPipeline(device=device)
        self.liveportrait_engine = LivePortraitEngine(device=device)
        self.queue = asyncio.Queue(maxsize=Config.MAX_QUEUE_SIZE)

        # Pre-load models if not lazy loading
        if not Config.LAZY_LOAD:
            logger.info("Pre-loading models...")
            self.joyvasa_pipeline.load_models()
            self.liveportrait_engine.load_models()

    def shutdown(self):
        """Cleanup on shutdown"""
        if self.joyvasa_pipeline:
            self.joyvasa_pipeline.unload_models()
        if self.liveportrait_engine:
            self.liveportrait_engine.unload_models()

    def get_vram_info(self) -> Tuple[Optional[float], Optional[float]]:
        """Get VRAM usage info"""
        if torch.cuda.is_available():
            used = torch.cuda.memory_allocated() / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            return used, total
        return None, None

    def get_queue_stats(self) -> Tuple[int, int]:
        """Get queue statistics"""
        queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
        processing = sum(1 for j in self.jobs.values() if j.status == JobStatus.PROCESSING)
        return queued, processing


# Global state instance
state = ServiceState()


# ============================================================================
# Application Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(f"Starting {Config.SERVICE_NAME} v{Config.VERSION}")

    # Initialize directories
    Config.init_directories()

    # Initialize service state
    await state.initialize()

    # Start job workers
    for i in range(Config.MAX_CONCURRENT_JOBS):
        asyncio.create_task(job_worker(i))
    state.workers_started = True
    logger.info(f"Started {Config.MAX_CONCURRENT_JOBS} job workers")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    state.shutdown()


# Create FastAPI app
app = FastAPI(
    title=Config.SERVICE_NAME,
    description="Audio-driven portrait animation service using JoyVASA + LivePortrait",
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


def _validate_url(url: str) -> str:
    """Validate URL to prevent SSRF attacks"""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    # Resolve hostname to IP
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    for family, _, _, _, sockaddr in resolved_ips:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"URL resolves to blocked address: {ip}")

    return url


async def download_file(url: str, target_path: Path) -> Path:
    """Download file from URL (with SSRF protection)"""
    _validate_url(url)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
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
    content = await upload_file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > max_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size_mb}MB"
        )

    ext = upload_file.filename.split('.')[-1].lower()
    file_hash = get_file_hash(content)
    filename = f"{file_hash}.{ext}"
    target_path = target_dir / filename

    async with aiofiles.open(target_path, 'wb') as f:
        await f.write(content)

    return target_path


# ============================================================================
# Job Worker
# ============================================================================

async def job_worker(worker_id: int):
    """Background worker for processing jobs"""
    logger.info(f"Worker {worker_id} started")

    while True:
        try:
            job_id = await state.queue.get()
            job = state.jobs.get(job_id)

            if not job:
                continue

            job.start_processing()
            logger.info(f"Worker {worker_id} processing job {job_id}")

            try:
                # Progress callback
                def update_progress(progress: float, message: str):
                    job.update_stage(message, progress)
                    logger.debug(f"Job {job_id}: {progress:.0%} - {message}")

                # Run generation in thread pool
                loop = asyncio.get_event_loop()
                output_path = str(Config.VIDEOS_DIR / f"{job_id}.mp4")

                await loop.run_in_executor(
                    None,
                    process_job_sync,
                    job,
                    output_path,
                    update_progress
                )

                # Mark complete
                result_url = f"/storage/videos/{job_id}.mp4"
                job.complete(result_url)
                logger.info(f"Job {job_id} completed: {result_url}")

            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                import traceback
                traceback.print_exc()
                job.fail(str(e))

            finally:
                state.queue.task_done()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            await asyncio.sleep(1)


def process_job_sync(job: JobData, output_path: str, progress_callback):
    """Synchronous job processing"""
    # Step 1: Audio to Motion (JoyVASA)
    progress_callback(0.0, "Extracting audio features")

    motion_sequence = state.joyvasa_pipeline.audio_to_motion(
        job.audio_path,
        progress_callback=lambda p, m: progress_callback(p * 0.5, m)
    )

    # Step 2: Motion to Video (LivePortrait)
    progress_callback(0.5, "Generating video frames")

    state.liveportrait_engine.motion_to_video(
        job.image_path,
        motion_sequence,
        job.audio_path,
        output_path,
        progress_callback=lambda p, m: progress_callback(0.5 + p * 0.5, m)
    )


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
    """Health check endpoint with detailed model status"""
    vram_used, vram_total = state.get_vram_info()
    queued, processing = state.get_queue_stats()

    # Check model file existence
    file_status = Config.check_model_files()

    # Check runtime model status
    joyvasa_status = state.joyvasa_pipeline.get_model_status() if state.joyvasa_pipeline else {}
    liveportrait_status = state.liveportrait_engine.get_model_status() if state.liveportrait_engine else {}

    model_status = ModelStatus(
        joyvasa_motion_generator=file_status.get("joyvasa_motion_generator", False),
        joyvasa_motion_template=file_status.get("joyvasa_motion_template", False),
        hubert_model=file_status.get("hubert_model", False),
        appearance_extractor=file_status.get("appearance_extractor", False),
        motion_extractor=file_status.get("motion_extractor", False),
        warping_spade=file_status.get("warping_spade", False),
        stitching=file_status.get("stitching", False),
    )

    all_loaded = all([
        joyvasa_status.get("fully_loaded", False),
        liveportrait_status.get("fully_loaded", False)
    ])

    return HealthResponse(
        status="healthy" if all_loaded else "degraded",
        service=Config.SERVICE_NAME,
        version=Config.VERSION,
        models_loaded=all_loaded,
        model_status=model_status,
        device=Config.get_device(),
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
    animation_mode: AnimationMode = Form(AnimationMode.HUMAN, description="Animation mode"),
):
    """
    Generate animated video from audio and source image.

    Uses JoyVASA to convert audio to motion, then LivePortrait to animate the image.

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
    queued, processing = state.get_queue_stats()
    if queued >= Config.MAX_QUEUE_SIZE:
        raise HTTPException(status_code=503, detail="Queue is full. Please try again later.")

    # Create job
    job_id = generate_job_id()
    job = JobData(job_id, animation_mode)

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
                ext = 'wav'
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
                ext = 'jpg'
            image_path = Config.UPLOADS_DIR / f"{job_id}_image.{ext}"
            await download_file(source_url, image_path)

        # Set job input paths
        job.audio_path = str(audio_path)
        job.image_path = str(image_path)

        # Add to queue
        state.jobs[job_id] = job
        await state.queue.put(job_id)

        logger.info(f"Created job {job_id}: audio={job.audio_path}, image={job.image_path}")

        return VideoGenerationResponse(
            id=job_id,
            status=JobStatus.QUEUED,
            result_url=None,
            created_at=job.created_at
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid input for job: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Internal error creating job")


@app.get("/job-status/{job_id}", response_model=JobStatusResponse, tags=["Video Generation"])
async def get_job_status(job_id: str):
    """Get status of a video generation job"""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return job.to_response()


@app.get("/result/{job_id}", tags=["Video Generation"])
async def get_result(job_id: str):
    """Download the result video"""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != JobStatus.DONE:
        raise HTTPException(status_code=400, detail=f"Job not complete. Status: {job.status}")

    video_path = Config.VIDEOS_DIR / f"{job_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4"
    )


@app.delete("/job/{job_id}", tags=["Video Generation"])
async def delete_job(job_id: str):
    """Delete a job and its output"""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Delete output video if exists
    video_path = Config.VIDEOS_DIR / f"{job_id}.mp4"
    if video_path.exists():
        video_path.unlink()

    # Remove from jobs dict
    del state.jobs[job_id]

    return {"message": f"Job {job_id} deleted"}


@app.post("/upload-source-image", response_model=UploadResponse, tags=["Uploads"])
async def upload_source_image(file: UploadFile = File(..., description="Source face image")):
    """Upload a source image for video generation"""
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
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@app.post("/upload-audio", response_model=UploadResponse, tags=["Uploads"])
async def upload_audio(file: UploadFile = File(..., description="Audio file")):
    """Upload an audio file for video generation"""
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
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@app.post("/models/load", tags=["Models"])
async def load_models():
    """Manually trigger model loading"""
    try:
        joyvasa_loaded = state.joyvasa_pipeline.load_models()
        liveportrait_loaded = state.liveportrait_engine.load_models()

        if joyvasa_loaded and liveportrait_loaded:
            return {"message": "All models loaded successfully"}
        else:
            return {
                "message": "Some models failed to load",
                "joyvasa": joyvasa_loaded,
                "liveportrait": liveportrait_loaded
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load models: {e}")


@app.post("/models/unload", tags=["Models"])
async def unload_models():
    """Manually unload models to free memory"""
    state.joyvasa_pipeline.unload_models()
    state.liveportrait_engine.unload_models()
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
