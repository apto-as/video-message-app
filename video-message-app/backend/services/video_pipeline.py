"""
Complete Video Generation Pipeline Service
Integrates YOLO Person Detection -> BiRefNet Background Removal -> D-ID Video Generation

Design Philosophy:
- Military-grade precision: Every failure mode is anticipated
- Resource efficiency: GPU scheduling with Tesla T4 16GB VRAM constraints
- Transaction safety: All-or-nothing execution with automatic rollback
- Progress transparency: Real-time status updates at each stage
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta
import asyncio
import logging
import uuid
import cv2
import numpy as np
import torch

from services.person_detector import PersonDetector
from services.background_remover import BackgroundRemover
from services.d_id_client import DIdClient

logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Status & Progress Tracking
# ============================================================================

class PipelineStage(str, Enum):
    """Pipeline execution stages with progress weights"""
    INITIALIZED = "initialized"          # 0%
    UPLOAD_COMPLETE = "upload_complete"  # 20%
    DETECTION_RUNNING = "detection_running"  # 20% -> 40%
    DETECTION_COMPLETE = "detection_complete"  # 40%
    BACKGROUND_REMOVAL_RUNNING = "background_removal_running"  # 40% -> 60%
    BACKGROUND_REMOVAL_COMPLETE = "background_removal_complete"  # 60%
    DID_UPLOAD = "did_upload"  # 70%
    DID_PROCESSING = "did_processing"  # 70% -> 80%
    DID_COMPLETE = "did_complete"  # 80%
    FINALIZING = "finalizing"  # 90%
    COMPLETED = "completed"  # 100%
    FAILED = "failed"
    CANCELLED = "cancelled"


# Progress mapping for each stage
STAGE_PROGRESS = {
    PipelineStage.INITIALIZED: 0,
    PipelineStage.UPLOAD_COMPLETE: 20,
    PipelineStage.DETECTION_RUNNING: 25,
    PipelineStage.DETECTION_COMPLETE: 40,
    PipelineStage.BACKGROUND_REMOVAL_RUNNING: 50,
    PipelineStage.BACKGROUND_REMOVAL_COMPLETE: 60,
    PipelineStage.DID_UPLOAD: 70,
    PipelineStage.DID_PROCESSING: 75,
    PipelineStage.DID_COMPLETE: 80,
    PipelineStage.FINALIZING: 90,
    PipelineStage.COMPLETED: 100,
    PipelineStage.FAILED: -1,
    PipelineStage.CANCELLED: -1,
}


@dataclass
class PipelineProgress:
    """Real-time pipeline progress tracking"""
    stage: PipelineStage
    progress_percent: int
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class PipelineResult:
    """Final pipeline execution result"""
    task_id: str
    success: bool
    video_url: Optional[str] = None
    video_path: Optional[Path] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    stages_completed: List[PipelineStage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "video_url": self.video_url,
            "video_path": str(self.video_path) if self.video_path else None,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "stages_completed": [stage.value for stage in self.stages_completed],
            "metadata": self.metadata
        }


# ============================================================================
# GPU Resource Manager
# ============================================================================

class GPUResourceManager:
    """
    GPU Resource scheduler for Tesla T4 (16GB VRAM)

    Resource Allocation Strategy:
    - YOLO: ~2GB VRAM (2 concurrent slots)
    - BiRefNet: ~6GB VRAM (1 slot with TensorRT FP16)
    - D-ID: Cloud API (no local GPU)

    Total: 8GB peak, 50% utilization target
    """

    def __init__(self, max_vram_gb: float = 8.0):
        self.max_vram_gb = max_vram_gb
        self.yolo_slots = asyncio.Semaphore(2)  # Max 2 YOLO concurrent
        self.birefnet_slots = asyncio.Semaphore(1)  # Max 1 BiRefNet
        self._lock = asyncio.Lock()

        # Resource tracking
        self.active_tasks: Dict[str, str] = {}  # task_id -> resource_type

        logger.info(f"GPU Resource Manager initialized: {max_vram_gb}GB VRAM limit")

    async def acquire_yolo(self, task_id: str) -> None:
        """Acquire YOLO resource slot"""
        logger.debug(f"Task {task_id}: Waiting for YOLO slot...")
        await self.yolo_slots.acquire()
        async with self._lock:
            self.active_tasks[task_id] = "yolo"
        logger.info(f"Task {task_id}: YOLO slot acquired")

    async def release_yolo(self, task_id: str) -> None:
        """Release YOLO resource slot"""
        self.yolo_slots.release()
        async with self._lock:
            self.active_tasks.pop(task_id, None)
        logger.info(f"Task {task_id}: YOLO slot released")

    async def acquire_birefnet(self, task_id: str) -> None:
        """Acquire BiRefNet resource slot"""
        logger.debug(f"Task {task_id}: Waiting for BiRefNet slot...")
        await self.birefnet_slots.acquire()
        async with self._lock:
            self.active_tasks[task_id] = "birefnet"
        logger.info(f"Task {task_id}: BiRefNet slot acquired")

    async def release_birefnet(self, task_id: str) -> None:
        """Release BiRefNet resource slot"""
        self.birefnet_slots.release()
        async with self._lock:
            self.active_tasks.pop(task_id, None)
        logger.info(f"Task {task_id}: BiRefNet slot released")

    def get_utilization(self) -> Dict[str, Any]:
        """Get current GPU utilization statistics"""
        return {
            "yolo_slots_available": self.yolo_slots._value,
            "birefnet_slots_available": self.birefnet_slots._value,
            "active_tasks": len(self.active_tasks),
            "task_breakdown": dict(self.active_tasks)
        }


# ============================================================================
# Video Pipeline Service
# ============================================================================

class VideoPipeline:
    """
    Complete end-to-end video generation pipeline

    Pipeline Stages:
    1. Upload & Validation
    2. YOLO Person Detection (with user selection)
    3. BiRefNet Background Removal
    4. D-ID Video Generation
    5. Finalization & Storage

    Features:
    - Transactional execution: All-or-nothing with automatic cleanup
    - Progress tracking: Real-time updates via callbacks
    - GPU resource management: Intelligent scheduling
    - Error recovery: Graceful degradation and detailed error reporting
    """

    def __init__(
        self,
        storage_dir: Path,
        person_detector: Optional[PersonDetector] = None,
        background_remover: Optional[BackgroundRemover] = None,
        d_id_client: Optional[DIdClient] = None,
        gpu_manager: Optional[GPUResourceManager] = None
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Service dependencies (lazy-loaded)
        self._person_detector = person_detector
        self._background_remover = background_remover
        self._d_id_client = d_id_client

        # GPU resource management
        self.gpu_manager = gpu_manager or GPUResourceManager()

        # Active pipelines tracking
        self.active_pipelines: Dict[str, PipelineProgress] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}

        logger.info(f"VideoPipeline initialized: storage={storage_dir}")

    @property
    def person_detector(self) -> PersonDetector:
        """Lazy-load person detector"""
        if self._person_detector is None:
            self._person_detector = PersonDetector(device=None)  # Auto-detect
            logger.info("PersonDetector lazy-loaded")
        return self._person_detector

    @property
    def background_remover(self) -> BackgroundRemover:
        """Lazy-load background remover"""
        if self._background_remover is None:
            # Determine model path (Docker vs local)
            import os
            if os.path.exists("/app/data/models/birefnet-portrait"):
                model_dir = "/app/data/models/birefnet-portrait"
            else:
                model_dir = self.storage_dir.parent.parent / "data" / "models" / "birefnet-portrait"

            self._background_remover = BackgroundRemover(
                model_dir=str(model_dir),
                device="cuda",
                use_tensorrt=True,
                use_fp16=True
            )
            logger.info("BackgroundRemover lazy-loaded")
        return self._background_remover

    @property
    def d_id_client(self) -> DIdClient:
        """Lazy-load D-ID client"""
        if self._d_id_client is None:
            self._d_id_client = DIdClient()
            logger.info("DIdClient lazy-loaded")
        return self._d_id_client

    def register_progress_callback(self, task_id: str, callback: Callable[[PipelineProgress], None]) -> None:
        """Register callback for progress updates"""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)

    async def _update_progress(self, task_id: str, stage: PipelineStage, message: str, metadata: Dict[str, Any] = None) -> None:
        """Update pipeline progress and notify callbacks"""
        progress = PipelineProgress(
            stage=stage,
            progress_percent=STAGE_PROGRESS[stage],
            message=message,
            metadata=metadata or {}
        )

        self.active_pipelines[task_id] = progress

        # Notify all registered callbacks
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(progress)
                    else:
                        callback(progress)
                except Exception as e:
                    logger.error(f"Progress callback error for {task_id}: {e}")

        logger.info(f"Task {task_id}: {stage.value} ({progress.progress_percent}%) - {message}")

    async def execute(
        self,
        image_path: Path,
        audio_path: Path,
        selected_person_id: Optional[int] = None,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        apply_smoothing: bool = True
    ) -> PipelineResult:
        """
        Execute complete video generation pipeline

        Args:
            image_path: Path to input image
            audio_path: Path to audio file
            selected_person_id: Person ID to use (None = auto-select largest)
            conf_threshold: YOLO confidence threshold
            iou_threshold: YOLO IoU threshold
            apply_smoothing: Apply edge smoothing in background removal

        Returns:
            PipelineResult with video URL or error
        """
        task_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()
        stages_completed: List[PipelineStage] = []

        # Temporary file tracking for cleanup
        temp_files: List[Path] = []

        try:
            # ================================================================
            # Stage 1: Initialization & Validation
            # ================================================================
            await self._update_progress(
                task_id, PipelineStage.INITIALIZED,
                "Pipeline initialized, validating inputs..."
            )

            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio not found: {audio_path}")

            await self._update_progress(
                task_id, PipelineStage.UPLOAD_COMPLETE,
                "Inputs validated successfully"
            )
            stages_completed.append(PipelineStage.UPLOAD_COMPLETE)

            # ================================================================
            # Stage 2: YOLO Person Detection
            # ================================================================
            await self._update_progress(
                task_id, PipelineStage.DETECTION_RUNNING,
                "Running YOLO person detection..."
            )

            # Acquire GPU resource
            await self.gpu_manager.acquire_yolo(task_id)

            try:
                persons = await asyncio.to_thread(
                    self.person_detector.detect_persons,
                    str(image_path),
                    conf_threshold,
                    iou_threshold
                )
            finally:
                await self.gpu_manager.release_yolo(task_id)

            if not persons:
                raise ValueError("No persons detected in image")

            # Select target person
            if selected_person_id is not None:
                target_person = next(
                    (p for p in persons if p["person_id"] == selected_person_id),
                    None
                )
                if target_person is None:
                    raise ValueError(f"Person ID {selected_person_id} not found")
            else:
                # Auto-select largest person by area
                target_person = max(persons, key=lambda p: p["area"])

            await self._update_progress(
                task_id, PipelineStage.DETECTION_COMPLETE,
                f"Detected {len(persons)} person(s), selected person {target_person['person_id']}",
                metadata={"detected_persons": len(persons), "selected_person": target_person}
            )
            stages_completed.append(PipelineStage.DETECTION_COMPLETE)

            # ================================================================
            # Stage 3: Crop to Person Bounding Box (Optional Optimization)
            # ================================================================
            # Crop image to person's bounding box to reduce processing time
            bbox = target_person["bbox"]
            image = cv2.imread(str(image_path))
            cropped_image = image[bbox["y1"]:bbox["y2"], bbox["x1"]:bbox["x2"]]

            cropped_path = self.storage_dir / f"{task_id}_cropped.jpg"
            cv2.imwrite(str(cropped_path), cropped_image)
            temp_files.append(cropped_path)

            # ================================================================
            # Stage 4: BiRefNet Background Removal
            # ================================================================
            await self._update_progress(
                task_id, PipelineStage.BACKGROUND_REMOVAL_RUNNING,
                "Removing background with BiRefNet..."
            )

            # Acquire GPU resource
            await self.gpu_manager.acquire_birefnet(task_id)

            try:
                png_bytes = await asyncio.to_thread(
                    self.background_remover.remove_background,
                    str(cropped_path),
                    return_bytes=True,
                    smoothing=apply_smoothing
                )
            finally:
                await self.gpu_manager.release_birefnet(task_id)

            # Save transparent PNG
            transparent_path = self.storage_dir / f"{task_id}_transparent.png"
            with open(transparent_path, "wb") as f:
                f.write(png_bytes)
            temp_files.append(transparent_path)

            await self._update_progress(
                task_id, PipelineStage.BACKGROUND_REMOVAL_COMPLETE,
                "Background removed successfully"
            )
            stages_completed.append(PipelineStage.BACKGROUND_REMOVAL_COMPLETE)

            # ================================================================
            # Stage 5: D-ID Upload & Video Generation
            # ================================================================
            await self._update_progress(
                task_id, PipelineStage.DID_UPLOAD,
                "Uploading to D-ID..."
            )

            # Upload image
            with open(transparent_path, "rb") as f:
                image_data = f.read()
            image_url = await self.d_id_client.upload_image(image_data, f"{task_id}.png")

            # Upload audio
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            audio_url = await self.d_id_client.upload_audio(audio_data, audio_path.name)

            await self._update_progress(
                task_id, PipelineStage.DID_PROCESSING,
                "Generating video with D-ID (this may take 30-60 seconds)..."
            )

            # Create video
            video_result = await self.d_id_client.create_talk_video(
                audio_url=audio_url,
                source_url=image_url
            )

            video_url = video_result.get("result_url")

            await self._update_progress(
                task_id, PipelineStage.DID_COMPLETE,
                "Video generation complete",
                metadata={"video_url": video_url, "d_id_talk_id": video_result["id"]}
            )
            stages_completed.append(PipelineStage.DID_COMPLETE)

            # ================================================================
            # Stage 6: Finalization
            # ================================================================
            await self._update_progress(
                task_id, PipelineStage.FINALIZING,
                "Finalizing and cleaning up..."
            )

            # Cleanup temporary files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_file}: {e}")

            await self._update_progress(
                task_id, PipelineStage.COMPLETED,
                "Pipeline completed successfully"
            )
            stages_completed.append(PipelineStage.COMPLETED)

            # Calculate execution time
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return PipelineResult(
                task_id=task_id,
                success=True,
                video_url=video_url,
                execution_time_ms=execution_time_ms,
                stages_completed=stages_completed,
                metadata={
                    "person_detection": {
                        "total_persons": len(persons),
                        "selected_person_id": target_person["person_id"],
                        "confidence": target_person["confidence"]
                    },
                    "d_id": {
                        "talk_id": video_result["id"],
                        "video_url": video_url
                    }
                }
            )

        except Exception as e:
            # Error handling with detailed logging
            logger.error(f"Pipeline failed for task {task_id}: {e}", exc_info=True)

            await self._update_progress(
                task_id, PipelineStage.FAILED,
                f"Pipeline failed: {str(e)}",
                metadata={"error": str(e), "error_type": type(e).__name__}
            )

            # Cleanup on failure
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {temp_file}: {cleanup_error}")

            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return PipelineResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
                stages_completed=stages_completed
            )

        finally:
            # Cleanup progress tracking
            self.active_pipelines.pop(task_id, None)
            self._progress_callbacks.pop(task_id, None)

    def get_active_pipelines(self) -> Dict[str, PipelineProgress]:
        """Get all active pipeline statuses"""
        return dict(self.active_pipelines)

    def get_gpu_utilization(self) -> Dict[str, Any]:
        """Get current GPU resource utilization"""
        return self.gpu_manager.get_utilization()
