"""
Adapter to integrate VideoPipeline with ProgressTracker

Converts VideoPipeline's PipelineProgress to ProgressTracker events
"""

from services.video_pipeline import VideoPipeline, PipelineProgress, PipelineStage
from services.progress_tracker import progress_tracker, EventType
from core.logging import get_logger
from pathlib import Path
from typing import Optional

logger = get_logger(__name__)


# Mapping from PipelineStage to ProgressTracker stage names
STAGE_MAPPING = {
    PipelineStage.INITIALIZED: "initialized",
    PipelineStage.UPLOAD_COMPLETE: "upload_complete",
    PipelineStage.DETECTION_RUNNING: "yolo_detection",
    PipelineStage.DETECTION_COMPLETE: "yolo_detection",
    PipelineStage.BACKGROUND_REMOVAL_RUNNING: "birefnet_removal",
    PipelineStage.BACKGROUND_REMOVAL_COMPLETE: "birefnet_removal",
    PipelineStage.DID_UPLOAD: "d_id_upload",
    PipelineStage.DID_PROCESSING: "d_id_processing",
    PipelineStage.DID_COMPLETE: "d_id_complete",
    PipelineStage.FINALIZING: "finalizing",
    PipelineStage.COMPLETED: "complete",
    PipelineStage.FAILED: "failed",
    PipelineStage.CANCELLED: "cancelled",
}


async def pipeline_progress_callback(task_id: str, progress: PipelineProgress) -> None:
    """
    Callback to convert VideoPipeline progress to ProgressTracker events

    Args:
        task_id: Task identifier
        progress: PipelineProgress from VideoPipeline
    """
    # Determine event type
    if progress.stage == PipelineStage.FAILED:
        event_type = EventType.ERROR
    elif progress.stage == PipelineStage.COMPLETED:
        event_type = EventType.COMPLETE
    else:
        event_type = EventType.STAGE_UPDATE

    # Build event data
    data = {
        "stage": STAGE_MAPPING.get(progress.stage, progress.stage.value),
        "progress": progress.progress_percent,
        "message": progress.message,
        "metadata": progress.metadata
    }

    # Publish to ProgressTracker
    await progress_tracker.publish_event(task_id, event_type, data)

    logger.debug(
        f"Published progress event: task_id={task_id}, "
        f"stage={progress.stage.value}, progress={progress.progress_percent}%"
    )


class VideoPipelineWithProgress(VideoPipeline):
    """
    Extended VideoPipeline with automatic progress tracking

    This wrapper automatically publishes progress updates to the ProgressTracker
    """

    async def execute(
        self,
        image_path: Path,
        audio_path: Path,
        selected_person_id: Optional[int] = None,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        apply_smoothing: bool = True,
        task_id: Optional[str] = None
    ):
        """
        Execute pipeline with automatic progress tracking

        Args:
            image_path: Path to input image
            audio_path: Path to audio file
            selected_person_id: Person ID to use (None = auto-select)
            conf_threshold: YOLO confidence threshold
            iou_threshold: YOLO IoU threshold
            apply_smoothing: Apply edge smoothing
            task_id: Optional task ID (will be generated if not provided)

        Returns:
            PipelineResult
        """
        # Register progress callback
        result = await super().execute(
            image_path=image_path,
            audio_path=audio_path,
            selected_person_id=selected_person_id,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            apply_smoothing=apply_smoothing
        )

        # Extract task_id from result
        actual_task_id = task_id or result.task_id

        # Register callback for this task
        self.register_progress_callback(
            actual_task_id,
            lambda progress: pipeline_progress_callback(actual_task_id, progress)
        )

        return result
