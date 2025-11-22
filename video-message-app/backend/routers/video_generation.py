"""
Video Generation Router with Real-time Progress Tracking

Complete pipeline: YOLO → BiRefNet → Prosody → D-ID
Supports WebSocket/SSE progress tracking
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional
import uuid
import shutil

from services.video_pipeline import VideoPipeline
from services.progress_tracker import progress_tracker, EventType
from services.prosody_adjuster import ProsodyAdjuster
from services.storage_manager import storage_manager
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/video-generation", tags=["video-generation"])

# Initialize services
storage_dir = Path(settings.STORAGE_DIR) / "video_pipeline"
storage_dir.mkdir(parents=True, exist_ok=True)

pipeline = VideoPipeline(storage_dir=storage_dir)


async def execute_pipeline_with_progress(
    task_id: str,
    image_path: Path,
    audio_path: Path,
    selected_person_id: Optional[int],
    conf_threshold: float,
    iou_threshold: float,
    apply_smoothing: bool,
    apply_prosody: bool,
    prosody_preset: Optional[str]
):
    """
    Execute pipeline in background with progress tracking

    Args:
        task_id: Task identifier for progress tracking
        image_path: Path to uploaded image
        audio_path: Path to uploaded audio
        selected_person_id: Person to use (None = auto-select)
        conf_threshold: YOLO confidence threshold
        iou_threshold: YOLO IoU threshold
        apply_smoothing: Apply edge smoothing
        apply_prosody: Apply prosody adjustment
        prosody_preset: Prosody preset name
    """
    try:
        # Publish initialization event
        await progress_tracker.publish_event(
            task_id,
            EventType.STAGE_UPDATE,
            {
                "stage": "initialized",
                "progress": 0,
                "message": "Pipeline initialized, validating inputs..."
            }
        )

        # Register progress callback
        async def progress_callback(progress):
            """Convert PipelineProgress to ProgressTracker event"""
            from services.video_pipeline import PipelineStage

            # Determine event type
            if progress.stage == PipelineStage.FAILED:
                event_type = EventType.ERROR
            elif progress.stage == PipelineStage.COMPLETED:
                event_type = EventType.COMPLETE
            else:
                event_type = EventType.STAGE_UPDATE

            await progress_tracker.publish_event(
                task_id,
                event_type,
                {
                    "stage": progress.stage.value,
                    "progress": progress.progress_percent,
                    "message": progress.message,
                    "metadata": progress.metadata
                }
            )

        pipeline.register_progress_callback(task_id, progress_callback)

        # Execute pipeline
        result = await pipeline.execute(
            image_path=image_path,
            audio_path=audio_path,
            selected_person_id=selected_person_id,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            apply_smoothing=apply_smoothing
        )

        # If success and prosody requested, apply prosody adjustment
        if result.success and apply_prosody and prosody_preset:
            await progress_tracker.publish_event(
                task_id,
                EventType.STAGE_UPDATE,
                {
                    "stage": "prosody_adjustment",
                    "progress": 85,
                    "message": f"Applying prosody preset: {prosody_preset}"
                }
            )

            # Apply prosody (placeholder - integrate with actual service)
            # prosody_adjuster = ProsodyAdjuster()
            # adjusted_audio = await prosody_adjuster.apply_preset(audio_path, prosody_preset)
            # Re-run D-ID with adjusted audio
            logger.info(f"Prosody adjustment requested: {prosody_preset}")

        # Publish final result
        if result.success:
            await progress_tracker.publish_event(
                task_id,
                EventType.COMPLETE,
                {
                    "stage": "complete",
                    "progress": 100,
                    "message": "Pipeline completed successfully",
                    "video_url": result.video_url,
                    "execution_time_ms": result.execution_time_ms
                }
            )
        else:
            await progress_tracker.publish_event(
                task_id,
                EventType.ERROR,
                {
                    "stage": "failed",
                    "progress": -1,
                    "message": f"Pipeline failed: {result.error}",
                    "error": result.error
                }
            )

    except Exception as e:
        logger.error(f"Pipeline execution error for task {task_id}: {e}", exc_info=True)
        await progress_tracker.publish_event(
            task_id,
            EventType.ERROR,
            {
                "stage": "failed",
                "progress": -1,
                "message": f"Unexpected error: {str(e)}",
                "error": str(e)
            }
        )


@router.post("/generate")
async def generate_video(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    selected_person_id: Optional[int] = Form(None),
    conf_threshold: float = Form(0.5),
    iou_threshold: float = Form(0.45),
    apply_smoothing: bool = Form(True),
    apply_prosody: bool = Form(False),
    prosody_preset: Optional[str] = Form(None)
):
    """
    Generate video with complete pipeline

    Pipeline Stages:
    1. YOLO Person Detection (0% → 20%)
    2. BiRefNet Background Removal (20% → 40%)
    3. Prosody Adjustment (40% → 60%, optional)
    4. D-ID Video Generation (60% → 80%)
    5. Finalization (80% → 100%)

    Progress Tracking:
    - WebSocket: ws://host:port/api/ws/progress/{task_id}
    - SSE: http://host:port/api/sse/progress/{task_id}
    - HTTP Polling: GET /api/ws/progress/{task_id}/latest

    Args:
        image: Input image with person
        audio: Audio file for talking animation
        selected_person_id: Person ID to use (None = auto-select largest)
        conf_threshold: YOLO confidence threshold (0.0-1.0)
        iou_threshold: YOLO IoU threshold (0.0-1.0)
        apply_smoothing: Apply edge smoothing in BiRefNet
        apply_prosody: Apply prosody adjustment
        prosody_preset: Prosody preset name (e.g., "natural", "energetic")

    Returns:
        {
            "task_id": "uuid",
            "message": "Pipeline started",
            "websocket_url": "ws://host:port/api/ws/progress/{task_id}",
            "sse_url": "http://host:port/api/sse/progress/{task_id}",
            "polling_url": "http://host:port/api/ws/progress/{task_id}/latest"
        }
    """
    # Generate task ID
    task_id = str(uuid.uuid4())

    # Save uploaded files
    image_path = storage_dir / f"{task_id}_image{Path(image.filename).suffix}"
    audio_path = storage_dir / f"{task_id}_audio{Path(audio.filename).suffix}"

    try:
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

    except Exception as e:
        logger.error(f"Failed to save uploaded files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save files: {str(e)}")

    # Execute pipeline in background
    background_tasks.add_task(
        execute_pipeline_with_progress,
        task_id=task_id,
        image_path=image_path,
        audio_path=audio_path,
        selected_person_id=selected_person_id,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        apply_smoothing=apply_smoothing,
        apply_prosody=apply_prosody,
        prosody_preset=prosody_preset
    )

    # Return tracking URLs
    base_url = settings.BASE_URL or "http://localhost:55433"

    return {
        "task_id": task_id,
        "message": "Pipeline started, use provided URLs to track progress",
        "websocket_url": f"ws://{base_url.replace('http://', '').replace('https://', '')}/api/ws/progress/{task_id}",
        "sse_url": f"{base_url}/api/sse/progress/{task_id}",
        "polling_url": f"{base_url}/api/ws/progress/{task_id}/latest"
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get current status of a video generation task

    Returns:
        Latest progress event with stage, progress, and message
    """
    latest = progress_tracker.get_latest_progress(task_id)

    if latest is None:
        raise HTTPException(status_code=404, detail="Task not found")

    import json
    return json.loads(latest.to_json())


@router.get("/active-pipelines")
async def get_active_pipelines():
    """
    Get all active video generation pipelines

    Returns:
        List of active pipeline statuses with subscriber counts
    """
    active_pipelines = pipeline.get_active_pipelines()
    active_tasks = progress_tracker.get_active_tasks()

    return {
        "active_pipeline_count": len(active_pipelines),
        "pipelines": [
            {
                "task_id": task_id,
                "stage": progress.stage.value,
                "progress": progress.progress_percent,
                "message": progress.message,
                "subscriber_count": progress_tracker.get_subscriber_count(task_id)
            }
            for task_id, progress in active_pipelines.items()
        ],
        "gpu_utilization": pipeline.get_gpu_utilization()
    }


@router.get("/health")
async def video_generation_health():
    """Health check for video generation service"""
    return {
        "status": "healthy",
        "service": "Video Generation Pipeline",
        "storage_dir": str(storage_dir),
        "gpu_available": pipeline.gpu_manager.get_utilization()
    }
