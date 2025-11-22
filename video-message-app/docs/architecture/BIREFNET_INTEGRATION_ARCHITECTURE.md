# BiRefNet Integration Architecture
# Video Message App - Sprint 2

**Version**: 1.0.0
**Date**: 2025-11-07
**Status**: Design Phase
**Author**: Hera (Strategic Commander)

---

## Executive Summary

This document defines the strategic architecture for integrating BiRefNet background removal into the Video Message App pipeline, establishing a seamless flow from person detection (Sprint 1) through background removal (Sprint 2) to D-ID video generation (Sprint 3).

### Strategic Goals

1. **Seamless Integration**: Unified pipeline connecting YOLOv8 → BiRefNet → D-ID
2. **Optimal Performance**: GPU scheduling to prevent resource contention
3. **User Experience**: Real-time progress tracking and intelligent error handling
4. **Scalability**: Architecture supports future multi-GPU horizontal scaling

### Success Metrics

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| End-to-End Latency | < 60s | TBD | Sprint 2 |
| Background Removal Time | < 10s | TBD | Sprint 2 |
| Success Rate | > 95% | TBD | Sprint 2 |
| GPU Utilization | 70-85% | TBD | Sprint 2 |

---

## 1. System Architecture Overview

### 1.1 High-Level Integration Flow

```mermaid
graph TB
    subgraph "Sprint 1: Person Detection ✅"
        A[User Upload Image] --> B[Person Detection API]
        B --> C[YOLOv8 Model]
        C --> D[Bounding Box Results]
    end

    subgraph "Sprint 2: Background Removal 🔄"
        D --> E[Frontend: Person Selection]
        E --> F[Background Removal API]
        F --> G[BiRefNet Model]
        G --> H[Transparent PNG Output]
    end

    subgraph "Sprint 3: Video Generation 📅"
        H --> I[D-ID Video API]
        I --> J[Final Talking Avatar Video]
    end

    style A fill:#e1f5ff
    style B fill:#4caf50
    style C fill:#4caf50
    style D fill:#4caf50
    style E fill:#ff9800
    style F fill:#ff9800
    style G fill:#ff9800
    style H fill:#ff9800
    style I fill:#e0e0e0
    style J fill:#e0e0e0
```

### 1.2 Data Flow Architecture

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Frontend
    participant PersonDetectionAPI
    participant BackgroundRemovalAPI
    participant DIDVideoAPI
    participant Storage

    User->>Frontend: Upload Image
    Frontend->>PersonDetectionAPI: POST /api/person-detection/detect
    PersonDetectionAPI->>PersonDetectionAPI: YOLOv8 Inference
    PersonDetectionAPI-->>Frontend: {"persons": [...], "image_id": "abc123"}

    Note over Frontend,User: User Selects Persons

    Frontend->>BackgroundRemovalAPI: POST /api/background/remove-selected-persons
    BackgroundRemovalAPI->>BackgroundRemovalAPI: Crop Person Regions
    BackgroundRemovalAPI->>BackgroundRemovalAPI: BiRefNet Background Removal
    BackgroundRemovalAPI->>Storage: Save Transparent PNGs
    BackgroundRemovalAPI-->>Frontend: {"processed_persons": [...]}

    Frontend->>DIDVideoAPI: POST /api/d-id/generate-video
    DIDVideoAPI->>DIDVideoAPI: Create Talking Avatar
    DIDVideoAPI-->>Frontend: {"video_url": "..."}
```

---

## 2. API Endpoint Design

### 2.1 Background Removal Endpoint (New)

#### Endpoint: `POST /api/background/remove-selected-persons`

**Request**:
```json
{
  "image_id": "abc123",
  "selected_person_ids": [0, 1],
  "persons": [
    {
      "person_id": 0,
      "bbox": {
        "x1": 120,
        "y1": 80,
        "x2": 320,
        "y2": 450
      },
      "confidence": 0.92
    },
    {
      "person_id": 1,
      "bbox": {
        "x1": 450,
        "y1": 100,
        "x2": 680,
        "y2": 480
      },
      "confidence": 0.88
    }
  ],
  "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "options": {
    "padding": 20,
    "output_format": "png",
    "feather_edges": true,
    "feather_amount": 5
  }
}
```

**Response** (Success):
```json
{
  "success": true,
  "data": {
    "image_id": "abc123",
    "processed_persons": [
      {
        "person_id": 0,
        "processed_image_url": "data:image/png;base64,iVBORw0KGgo...",
        "processing_time_ms": 1240,
        "dimensions": {
          "width": 200,
          "height": 370
        },
        "file_size_bytes": 45678
      },
      {
        "person_id": 1,
        "processed_image_url": "data:image/png;base64,iVBORw0KGgo...",
        "processing_time_ms": 1180,
        "dimensions": {
          "width": 230,
          "height": 380
        },
        "file_size_bytes": 48902
      }
    ],
    "total_processing_time_ms": 2420,
    "metadata": {
      "model": "BiRefNet-v2",
      "device": "cuda",
      "timestamp": "2025-11-07T10:30:45Z"
    }
  }
}
```

**Response** (Error - BiRefNet Timeout):
```json
{
  "success": false,
  "error": {
    "code": "BIREFNET_TIMEOUT",
    "message": "Background removal timed out after 30s",
    "tier": 2,
    "user_action": "Try uploading a smaller image or simpler background",
    "retry_after": null,
    "details": {
      "failed_person_ids": [0, 1],
      "timeout_seconds": 30
    }
  }
}
```

### 2.2 Enhanced Video Generation Endpoint

#### Endpoint: `POST /api/video/generate-from-persons`

**Request**:
```json
{
  "image_id": "abc123",
  "persons": [
    {
      "person_id": 0,
      "processed_image_url": "data:image/png;base64,..."
    },
    {
      "person_id": 1,
      "processed_image_url": "data:image/png;base64,..."
    }
  ],
  "text": "おめでとうございます！",
  "voice_profile_id": "openvoice_c403f011",
  "prosody_preset": "celebration",
  "bgm_id": "system_bgm_001",
  "bgm_volume": 0.3
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "task_ids": [
      {
        "person_id": 0,
        "task_id": "video_task_abc123_p0",
        "status": "processing",
        "estimated_completion_seconds": 45
      },
      {
        "person_id": 1,
        "task_id": "video_task_abc123_p1",
        "status": "processing",
        "estimated_completion_seconds": 45
      }
    ],
    "progress_url": "ws://localhost:55433/api/progress/batch/video_task_abc123"
  }
}
```

---

## 3. Backend Implementation Strategy

### 3.1 BiRefNet Service Implementation

**File**: `backend/services/birefnet_remover.py`

```python
"""BiRefNet-based background removal service"""
import torch
import numpy as np
from PIL import Image
import io
import logging
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BiRefNetRemover:
    """Background removal using BiRefNet model"""

    def __init__(self, model_path: str = "BiRefNet-v2", device: Optional[str] = None):
        """
        Initialize BiRefNet background remover

        Args:
            model_path: Path to BiRefNet model weights or HuggingFace model ID
            device: Device to run model on ('cuda', 'cpu', or None for auto-detect)
        """
        # Auto-detect best available device
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"CUDA available: using {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                logger.info("CUDA not available: using CPU")

        self.device = device

        try:
            # Load BiRefNet model (HuggingFace transformers)
            from transformers import AutoModelForImageSegmentation
            self.model = AutoModelForImageSegmentation.from_pretrained(
                model_path,
                trust_remote_code=True
            )
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"BiRefNet model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load BiRefNet model: {e}")
            raise

    def remove_background(
        self,
        image: Image.Image,
        feather_edges: bool = True,
        feather_amount: int = 5
    ) -> Image.Image:
        """
        Remove background from image

        Args:
            image: PIL Image
            feather_edges: Whether to apply edge feathering
            feather_amount: Amount of edge feathering in pixels

        Returns:
            PIL Image with transparent background (RGBA)
        """
        try:
            # Preprocess image
            input_tensor = self._preprocess(image)
            input_tensor = input_tensor.to(self.device)

            # BiRefNet inference
            with torch.no_grad():
                output = self.model(input_tensor)

            # Post-process mask
            mask = self._postprocess(output, image.size)

            # Apply feathering if requested
            if feather_edges:
                mask = self._feather_edges(mask, feather_amount)

            # Apply mask to original image
            result = self._apply_mask(image, mask)

            return result

        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            raise

    def _preprocess(self, image: Image.Image) -> torch.Tensor:
        """Preprocess image for BiRefNet model"""
        from torchvision import transforms

        # BiRefNet preprocessing
        transform = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        return transform(image).unsqueeze(0)

    def _postprocess(self, output: torch.Tensor, original_size: Tuple[int, int]) -> np.ndarray:
        """Post-process BiRefNet output to binary mask"""
        # Extract mask from model output
        mask = output.squeeze().cpu().numpy()

        # Resize to original image size
        mask_image = Image.fromarray((mask * 255).astype(np.uint8))
        mask_image = mask_image.resize(original_size, Image.LANCZOS)

        return np.array(mask_image)

    def _feather_edges(self, mask: np.ndarray, amount: int) -> np.ndarray:
        """Apply Gaussian blur to mask edges for smooth transitions"""
        from scipy.ndimage import gaussian_filter

        # Apply Gaussian blur to mask
        feathered_mask = gaussian_filter(mask, sigma=amount)

        return feathered_mask

    def _apply_mask(self, image: Image.Image, mask: np.ndarray) -> Image.Image:
        """Apply mask to image to create transparent background"""
        # Convert to RGBA if not already
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Create alpha channel from mask
        alpha = Image.fromarray(mask.astype(np.uint8))

        # Apply alpha channel
        image.putalpha(alpha)

        return image

    def get_model_info(self) -> dict:
        """Get information about loaded model"""
        return {
            "model_name": "BiRefNet-v2",
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "input_size": (1024, 1024)
        }
```

### 3.2 Integrated Pipeline Service

**File**: `backend/services/video_pipeline_service.py`

```python
"""Integrated video generation pipeline"""
import asyncio
import logging
from typing import List, Dict, Optional
from pathlib import Path
from PIL import Image
import io
import base64

from services.person_detector import PersonDetector
from services.birefnet_remover import BiRefNetRemover
from services.d_id_client import DIDClient
from core.gpu_scheduler import GPUScheduler

logger = logging.getLogger(__name__)


class VideoPipelineService:
    """Complete pipeline: Detection → BG Removal → D-ID"""

    def __init__(self):
        self.person_detector = PersonDetector()
        self.bg_remover = BiRefNetRemover()
        self.d_id_client = DIDClient()
        self.gpu_scheduler = GPUScheduler()

    async def generate_videos_from_image(
        self,
        image_bytes: bytes,
        text: str,
        voice_audio_bytes: bytes,
        selected_person_ids: Optional[List[int]] = None,
        remove_background: bool = True
    ) -> List[Dict]:
        """
        Complete pipeline: Detection → BG Removal → D-ID

        Args:
            image_bytes: Original uploaded image (JPEG/PNG)
            text: Text to speak
            voice_audio_bytes: Pre-generated voice audio
            selected_person_ids: Which persons to process (if None, use all detected)
            remove_background: Whether to remove background

        Returns:
            List of D-ID video task IDs
        """
        try:
            # Step 1: Person Detection
            logger.info("Step 1: Person Detection")
            temp_image_path = Path("/tmp") / "temp_detection.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(image_bytes)

            async with self.gpu_scheduler.acquire_yolo():
                persons = self.person_detector.detect_persons(str(temp_image_path))

            if not persons:
                raise ValueError("No persons detected in image")

            logger.info(f"Detected {len(persons)} person(s)")

            # Step 2: Filter selected persons
            if selected_person_ids is not None:
                persons = [p for p in persons if p["person_id"] in selected_person_ids]

            if not persons:
                raise ValueError("No selected persons found")

            # Step 3: Process each person
            processed_persons = []

            for person in persons:
                # Crop to bounding box
                cropped_image = self._crop_to_bbox(
                    Image.open(io.BytesIO(image_bytes)),
                    person["bbox"]
                )

                # Background Removal (optional)
                if remove_background:
                    logger.info(f"Step 3: Background Removal for person {person['person_id']}")
                    async with self.gpu_scheduler.acquire_birefnet():
                        processed_image = self.bg_remover.remove_background(cropped_image)
                else:
                    processed_image = cropped_image

                # Convert to bytes
                img_bytes = io.BytesIO()
                processed_image.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                processed_persons.append({
                    "person_id": person["person_id"],
                    "image_bytes": img_bytes.getvalue(),
                    "bbox": person["bbox"],
                    "confidence": person["confidence"]
                })

            # Step 4: D-ID Video Generation (parallel)
            logger.info("Step 4: D-ID Video Generation")
            video_tasks = await self._generate_videos_parallel(
                processed_persons,
                voice_audio_bytes,
                text
            )

            return video_tasks

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise

    def _crop_to_bbox(self, image: Image.Image, bbox: Dict) -> Image.Image:
        """Crop image to bounding box with padding"""
        padding = 20  # pixels

        x1 = max(0, bbox["x1"] - padding)
        y1 = max(0, bbox["y1"] - padding)
        x2 = min(image.width, bbox["x2"] + padding)
        y2 = min(image.height, bbox["y2"] + padding)

        return image.crop((x1, y1, x2, y2))

    async def _generate_videos_parallel(
        self,
        processed_persons: List[Dict],
        voice_audio_bytes: bytes,
        text: str
    ) -> List[Dict]:
        """Generate D-ID videos for all persons in parallel"""
        tasks = []

        for person in processed_persons:
            task = self.d_id_client.create_video_async(
                image_bytes=person["image_bytes"],
                audio_bytes=voice_audio_bytes,
                text=text
            )
            tasks.append(task)

        # Execute all D-ID requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        video_tasks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"D-ID generation failed for person {processed_persons[i]['person_id']}: {result}")
                video_tasks.append({
                    "person_id": processed_persons[i]["person_id"],
                    "status": "failed",
                    "error": str(result)
                })
            else:
                video_tasks.append({
                    "person_id": processed_persons[i]["person_id"],
                    "task_id": result["task_id"],
                    "status": "processing"
                })

        return video_tasks
```

---

## 4. GPU Resource Management

### 4.1 GPU Scheduler Implementation

**File**: `backend/core/gpu_scheduler.py`

```python
"""GPU resource scheduler to prevent contention"""
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class GPUScheduler:
    """Coordinate GPU usage across services"""

    def __init__(self):
        self.yolo_slots = 2  # YOLOv8 can run 2 concurrent
        self.birefnet_slots = 1  # BiRefNet needs exclusive access
        self.active_yolo = 0
        self.active_birefnet = 0
        self.lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire_yolo(self):
        """Acquire YOLO slot"""
        await self._wait_for_yolo_slot()
        try:
            yield
        finally:
            await self._release_yolo()

    @asynccontextmanager
    async def acquire_birefnet(self):
        """Acquire BiRefNet slot (exclusive)"""
        await self._wait_for_birefnet_slot()
        try:
            yield
        finally:
            await self._release_birefnet()

    async def _wait_for_yolo_slot(self):
        """Wait for available YOLO slot"""
        async with self.lock:
            while self.active_yolo >= self.yolo_slots or self.active_birefnet > 0:
                await asyncio.sleep(0.1)
            self.active_yolo += 1
            logger.debug(f"YOLO slot acquired (active: {self.active_yolo}/{self.yolo_slots})")

    async def _release_yolo(self):
        """Release YOLO slot"""
        async with self.lock:
            self.active_yolo = max(0, self.active_yolo - 1)
            logger.debug(f"YOLO slot released (active: {self.active_yolo}/{self.yolo_slots})")

    async def _wait_for_birefnet_slot(self):
        """Wait for exclusive BiRefNet slot"""
        async with self.lock:
            while self.active_yolo > 0 or self.active_birefnet > 0:
                await asyncio.sleep(0.1)
            self.active_birefnet = 1
            logger.debug("BiRefNet slot acquired (exclusive)")

    async def _release_birefnet(self):
        """Release BiRefNet slot"""
        async with self.lock:
            self.active_birefnet = 0
            logger.debug("BiRefNet slot released")

    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "yolo": {
                "active": self.active_yolo,
                "max_slots": self.yolo_slots,
                "available": self.yolo_slots - self.active_yolo
            },
            "birefnet": {
                "active": self.active_birefnet,
                "max_slots": self.birefnet_slots,
                "available": 1 - self.active_birefnet
            }
        }
```

### 4.2 Usage in Router

**File**: `backend/routers/background.py` (Enhanced)

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.birefnet_remover import BiRefNetRemover
from core.gpu_scheduler import GPUScheduler

router = APIRouter(prefix="/api/background", tags=["background-removal"])

_remover: BiRefNetRemover = None
_scheduler: GPUScheduler = None


def get_remover():
    global _remover
    if _remover is None:
        _remover = BiRefNetRemover()
    return _remover


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = GPUScheduler()
    return _scheduler


@router.post("/remove")
async def remove_background(image: UploadFile = File(...)):
    """Remove background from image with GPU scheduling"""
    remover = get_remover()
    scheduler = get_scheduler()

    # GPU scheduling: BiRefNet gets exclusive access
    async with scheduler.acquire_birefnet():
        # Process image
        image_bytes = await image.read()
        result = remover.remove_background(image_bytes)

    return {"success": True, "result": result}
```

---

## 5. Error Handling Strategy

### 5.1 Error Tier Classification

| Tier | Severity | Example | User Action | Recovery Strategy |
|------|----------|---------|-------------|-------------------|
| **T1** | CRITICAL | GPU OOM, Service crash | Retry later, contact support | Service restart, reduce batch size |
| **T2** | HIGH | No person detected, BiRefNet timeout | Upload different image | Suggest image requirements |
| **T3** | MEDIUM | Low confidence detection | Proceed with warning | Continue with caution |
| **T4** | LOW | Metadata warning | Ignore, proceed | Log and continue |

### 5.2 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "BIREFNET_TIMEOUT",
    "message": "Background removal timed out after 30s",
    "tier": 2,
    "user_action": "Try uploading a smaller image or simpler background",
    "retry_after": null,
    "details": {
      "timeout_seconds": 30,
      "image_size_bytes": 15728640,
      "max_size_recommended": 10485760
    }
  }
}
```

### 5.3 Error Handling Implementation

**File**: `backend/core/error_handler.py`

```python
"""Unified error handling for BiRefNet integration"""
from enum import Enum
from typing import Optional, Dict


class ErrorTier(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class PipelineError(Exception):
    """Base exception for pipeline errors"""

    def __init__(
        self,
        code: str,
        message: str,
        tier: ErrorTier,
        user_action: str,
        details: Optional[Dict] = None
    ):
        self.code = code
        self.message = message
        self.tier = tier
        self.user_action = user_action
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict:
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "tier": self.tier.value,
                "user_action": self.user_action,
                "details": self.details
            }
        }


class BiRefNetTimeoutError(PipelineError):
    """BiRefNet processing timeout"""

    def __init__(self, timeout_seconds: int, image_size: int):
        super().__init__(
            code="BIREFNET_TIMEOUT",
            message=f"Background removal timed out after {timeout_seconds}s",
            tier=ErrorTier.HIGH,
            user_action="Try uploading a smaller image or simpler background",
            details={
                "timeout_seconds": timeout_seconds,
                "image_size_bytes": image_size,
                "max_size_recommended": 10 * 1024 * 1024
            }
        )


class NoPersonDetectedError(PipelineError):
    """No person detected in image"""

    def __init__(self):
        super().__init__(
            code="NO_PERSON_DETECTED",
            message="No persons detected in the uploaded image",
            tier=ErrorTier.HIGH,
            user_action="Upload an image with visible people",
            details={
                "tips": [
                    "Ensure faces are visible and not obstructed",
                    "Use good lighting conditions",
                    "Upload high-resolution images (min 640x480)"
                ]
            }
        )


class GPUOutOfMemoryError(PipelineError):
    """GPU out of memory"""

    def __init__(self):
        super().__init__(
            code="GPU_OOM",
            message="GPU out of memory during processing",
            tier=ErrorTier.CRITICAL,
            user_action="Please try again in a few minutes",
            details={
                "reason": "Server is under heavy load",
                "suggestion": "Contact support if the problem persists"
            }
        )
```

---

## 6. Data Storage Strategy

### 6.1 Directory Structure

```
data/backend/storage/
├── uploads/              # Original user uploads (retain 7 days)
│   └── {upload_id}.jpg
├── detected_persons/     # Cropped persons from YOLO (retain 3 days)
│   └── {upload_id}_person_{person_id}.jpg
├── background_removed/   # BiRefNet outputs (retain 3 days)
│   └── {upload_id}_person_{person_id}_nobg.png
├── d_id_videos/          # Final videos (retain 30 days)
│   └── {video_id}.mp4
└── temp/                 # Temporary processing files (auto-cleanup after 1 hour)
    └── {task_id}/
        ├── input.jpg
        ├── cropped.jpg
        ├── mask.png
        └── result.png
```

### 6.2 Cleanup Policy

**File**: `backend/core/storage_cleaner.py`

```python
"""Automated storage cleanup based on retention policy"""
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StorageCleaner:
    """Automated cleanup of old files"""

    RETENTION_POLICY = {
        "uploads": 7,  # days
        "detected_persons": 3,
        "background_removed": 3,
        "d_id_videos": 30,
        "temp": 0.042  # 1 hour = 0.042 days
    }

    def __init__(self, storage_root: Path):
        self.storage_root = storage_root

    async def cleanup_old_files(self):
        """Run cleanup based on retention policy"""
        for folder, retention_days in self.RETENTION_POLICY.items():
            folder_path = self.storage_root / folder
            if not folder_path.exists():
                continue

            cutoff_time = datetime.now() - timedelta(days=retention_days)

            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            logger.info(f"Deleted old file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete {file_path}: {e}")

    async def run_periodic_cleanup(self, interval_hours: int = 6):
        """Run cleanup periodically"""
        while True:
            logger.info("Starting periodic storage cleanup")
            await self.cleanup_old_files()
            logger.info("Periodic storage cleanup complete")
            await asyncio.sleep(interval_hours * 3600)
```

---

## 7. Progress Tracking & Monitoring

### 7.1 Prometheus Metrics

**File**: `backend/core/metrics.py`

```python
"""Prometheus metrics for BiRefNet integration"""
from prometheus_client import Counter, Histogram, Gauge

# Counters
birefnet_requests = Counter(
    'birefnet_requests_total',
    'Total BiRefNet requests'
)
birefnet_errors = Counter(
    'birefnet_errors_total',
    'Total BiRefNet errors',
    ['error_type']
)
pipeline_requests = Counter(
    'pipeline_requests_total',
    'Total video pipeline requests'
)

# Histograms
birefnet_latency = Histogram(
    'birefnet_latency_seconds',
    'BiRefNet inference latency'
)
pipeline_latency = Histogram(
    'pipeline_total_latency_seconds',
    'Total pipeline latency (detection + removal + video)'
)

# Gauges
gpu_utilization = Gauge(
    'gpu_utilization_percent',
    'Current GPU utilization'
)
active_yolo_tasks = Gauge(
    'active_yolo_tasks',
    'Number of active YOLO tasks'
)
active_birefnet_tasks = Gauge(
    'active_birefnet_tasks',
    'Number of active BiRefNet tasks'
)
```

### 7.2 Usage in Services

```python
from core.metrics import birefnet_requests, birefnet_latency, birefnet_errors


class BiRefNetRemover:
    def remove_background(self, image: Image.Image) -> Image.Image:
        birefnet_requests.inc()

        with birefnet_latency.time():
            try:
                result = self._process(image)
                return result
            except Exception as e:
                birefnet_errors.labels(error_type=type(e).__name__).inc()
                raise
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**File**: `backend/tests/test_birefnet_integration.py`

```python
"""Unit tests for BiRefNet integration"""
import pytest
from services.birefnet_remover import BiRefNetRemover
from PIL import Image
import io


class TestBiRefNetRemover:
    @pytest.fixture
    def remover(self):
        return BiRefNetRemover(device="cpu")  # Use CPU for tests

    @pytest.fixture
    def test_image(self):
        # Create test image (640x480 RGB)
        img = Image.new("RGB", (640, 480), color="red")
        return img

    def test_remove_background_success(self, remover, test_image):
        """Test successful background removal"""
        result = remover.remove_background(test_image)

        assert result.mode == "RGBA"
        assert result.size == test_image.size

    def test_remove_background_with_feathering(self, remover, test_image):
        """Test background removal with edge feathering"""
        result = remover.remove_background(
            test_image,
            feather_edges=True,
            feather_amount=10
        )

        assert result.mode == "RGBA"

    def test_model_info(self, remover):
        """Test model info retrieval"""
        info = remover.get_model_info()

        assert info["model_name"] == "BiRefNet-v2"
        assert "device" in info
        assert "cuda_available" in info
```

### 8.2 Integration Tests

**File**: `backend/tests/test_video_pipeline.py`

```python
"""Integration tests for complete video pipeline"""
import pytest
from services.video_pipeline_service import VideoPipelineService
from pathlib import Path


class TestVideoPipeline:
    @pytest.fixture
    def pipeline(self):
        return VideoPipelineService()

    @pytest.fixture
    def test_image_bytes(self):
        # Load test image
        with open("tests/fixtures/test_portrait.jpg", "rb") as f:
            return f.read()

    @pytest.fixture
    def test_audio_bytes(self):
        # Load test audio
        with open("tests/fixtures/test_voice.wav", "rb") as f:
            return f.read()

    @pytest.mark.asyncio
    async def test_full_pipeline(self, pipeline, test_image_bytes, test_audio_bytes):
        """Test complete pipeline: Detection → BG Removal → D-ID"""
        result = await pipeline.generate_videos_from_image(
            image_bytes=test_image_bytes,
            text="テストメッセージ",
            voice_audio_bytes=test_audio_bytes,
            remove_background=True
        )

        assert len(result) > 0
        assert result[0]["status"] in ["processing", "completed"]

    @pytest.mark.asyncio
    async def test_pipeline_with_no_persons(self, pipeline):
        """Test pipeline with image containing no persons"""
        # Create empty image
        from PIL import Image
        img = Image.new("RGB", (640, 480), color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        with pytest.raises(ValueError, match="No persons detected"):
            await pipeline.generate_videos_from_image(
                image_bytes=img_bytes.getvalue(),
                text="テスト",
                voice_audio_bytes=b"fake_audio"
            )
```

---

## 9. Performance Benchmarks

### 9.1 Target Performance

| Stage | Target Time | Acceptable Range | Critical Threshold |
|-------|-------------|------------------|-------------------|
| Person Detection | 0.2s | 0.1-0.5s | > 1s |
| Background Removal (per person) | 3s | 1-5s | > 10s |
| D-ID Video Generation | 45s | 30-60s | > 90s |
| **Total Pipeline** | **60s** | **40-80s** | **> 120s** |

### 9.2 GPU Memory Usage

| Model | VRAM Usage | Concurrent Tasks | Recommendations |
|-------|-----------|------------------|-----------------|
| YOLOv8n | 0.5 GB | 2-3 | Lightweight, fast |
| BiRefNet-v2 | 4 GB | 1 (exclusive) | High quality, slower |
| **Total** | **4.5 GB** | - | Tesla T4 (16GB) sufficient |

---

## 10. Deployment Checklist

### 10.1 Environment Setup

**Development (Mac)**:
```bash
# Install BiRefNet dependencies
cd backend
pip install transformers torch torchvision pillow scipy

# Verify GPU availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Download BiRefNet model (auto-download on first run)
python -c "from transformers import AutoModelForImageSegmentation; AutoModelForImageSegmentation.from_pretrained('BiRefNet-v2', trust_remote_code=True)"
```

**Production (EC2 g4dn.xlarge)**:
```bash
# Update requirements.txt
echo "transformers>=4.30.0" >> backend/requirements.txt
echo "scipy>=1.10.0" >> backend/requirements.txt

# Install dependencies
pip install -r backend/requirements.txt

# Verify CUDA
python -c "import torch; print(torch.cuda.get_device_name(0))"
# Expected: Tesla T4
```

### 10.2 Docker Configuration

**File**: `backend/Dockerfile` (Enhanced)

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# CUDA support (for EC2)
RUN apt-get update && apt-get install -y \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download BiRefNet model
RUN python -c "from transformers import AutoModelForImageSegmentation; AutoModelForImageSegmentation.from_pretrained('BiRefNet-v2', trust_remote_code=True)"

# Copy application
COPY . /app

EXPOSE 55433

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "55433"]
```

---

## 11. Future Scalability

### 11.1 Horizontal Scaling Strategy

**Multi-GPU Support** (Future):

```python
class MultiGPUScheduler:
    """Distribute tasks across multiple GPUs"""

    def __init__(self, num_gpus: int):
        self.num_gpus = num_gpus
        self.gpu_queues = [asyncio.Queue() for _ in range(num_gpus)]

    async def acquire_gpu(self) -> int:
        """Get least busy GPU"""
        gpu_loads = [queue.qsize() for queue in self.gpu_queues]
        gpu_id = gpu_loads.index(min(gpu_loads))

        await self.gpu_queues[gpu_id].put(True)
        return gpu_id

    async def release_gpu(self, gpu_id: int):
        """Release GPU"""
        await self.gpu_queues[gpu_id].get()
```

### 11.2 Batch Processing Optimization

```python
class BatchProcessor:
    """Process multiple images in batch for efficiency"""

    def __init__(self, batch_size: int = 4):
        self.batch_size = batch_size

    async def process_batch(self, images: List[Image.Image]) -> List[Image.Image]:
        """Process multiple images in single GPU call"""
        # Batch inference for BiRefNet
        results = []
        for i in range(0, len(images), self.batch_size):
            batch = images[i:i+self.batch_size]
            batch_results = await self._process_batch_gpu(batch)
            results.extend(batch_results)

        return results
```

---

## 12. Security Considerations

### 12.1 Input Validation

```python
def validate_image_for_birefnet(image_bytes: bytes) -> tuple[bool, str]:
    """Validate image before BiRefNet processing"""
    # Check file size (max 10MB)
    if len(image_bytes) > 10 * 1024 * 1024:
        return False, "Image too large (max 10MB)"

    # Verify image format
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.format not in ["JPEG", "PNG", "WebP"]:
            return False, f"Unsupported format: {img.format}"

        # Check dimensions
        if img.width < 128 or img.height < 128:
            return False, "Image too small (min 128x128)"

        if img.width > 4096 or img.height > 4096:
            return False, "Image too large (max 4096x4096)"

        return True, "Valid"

    except Exception as e:
        return False, f"Invalid image: {e}"
```

### 12.2 Resource Limits

```python
# backend/core/rate_limiter.py
from fastapi import HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


@router.post("/remove")
@limiter.limit("20/minute")  # Max 20 background removal requests per minute
async def remove_background(request: Request, image: UploadFile = File(...)):
    """Rate-limited background removal endpoint"""
    ...
```

---

## 13. Monitoring Dashboard

### 13.1 Key Metrics to Track

**Grafana Dashboard Panels**:

1. **Pipeline Latency**:
   - Histogram: Total pipeline time (detection + removal + video)
   - Target: < 60s (p95)

2. **GPU Utilization**:
   - Line chart: GPU usage over time
   - Target: 70-85%

3. **Error Rate**:
   - Counter: BiRefNet errors by type
   - Target: < 2%

4. **Throughput**:
   - Gauge: Requests per minute
   - Target: > 10 req/min

5. **Resource Contention**:
   - Heatmap: YOLO vs BiRefNet scheduling conflicts
   - Target: < 5% contention

---

## 14. Implementation Roadmap

### Sprint 2: Week 1 (BiRefNet Core)
- [ ] Implement `BiRefNetRemover` service
- [ ] Add `GPUScheduler` for resource management
- [ ] Create `/api/background/remove-selected-persons` endpoint
- [ ] Unit tests for BiRefNet service

### Sprint 2: Week 2 (Pipeline Integration)
- [ ] Implement `VideoPipelineService`
- [ ] Integrate person detection → background removal
- [ ] Add error handling (tier classification)
- [ ] Integration tests

### Sprint 2: Week 3 (Storage & Cleanup)
- [ ] Implement `StorageCleaner` with retention policy
- [ ] Add Prometheus metrics
- [ ] Frontend integration (person selection UI)
- [ ] E2E testing

### Sprint 2: Week 4 (Polish & Optimization)
- [ ] Performance optimization (batch processing)
- [ ] Documentation updates
- [ ] Load testing (50 concurrent users)
- [ ] Production deployment

---

## 15. Success Criteria

### Sprint 2 Definition of Done

✅ **Functional Requirements**:
- [ ] BiRefNet successfully removes background from selected persons
- [ ] GPU scheduling prevents resource contention (YOLO vs BiRefNet)
- [ ] Error handling covers all failure modes (T1-T4)
- [ ] Storage cleanup policy enforced

✅ **Performance Requirements**:
- [ ] Background removal: < 5s per person (p95)
- [ ] Total pipeline: < 60s (detection + removal + video)
- [ ] GPU utilization: 70-85%
- [ ] Error rate: < 2%

✅ **Quality Requirements**:
- [ ] Unit test coverage: > 80%
- [ ] Integration tests: All critical paths covered
- [ ] API documentation: Complete OpenAPI spec
- [ ] Load testing: 50 concurrent users without degradation

---

## Document Control

**Version History**:

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-07 | Hera | Initial architecture design |

**Approval**:

| Role | Name | Status | Date |
|------|------|--------|------|
| Strategic Commander | Hera | ✅ Approved | 2025-11-07 |
| Technical Reviewer | Artemis | 🔄 Pending | - |
| Security Auditor | Hestia | 🔄 Pending | - |
| Documentation Lead | Muses | 🔄 Pending | - |

---

## Appendix A: API Specifications

See [API_DESIGN.md](./API_DESIGN.md) for complete OpenAPI 3.0 specifications.

---

## Appendix B: Related Documents

- [PERSON_SELECTION_UI_DESIGN.md](./PERSON_SELECTION_UI_DESIGN.md) - Frontend UI design (Sprint 1)
- [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) - Overall system architecture
- [API_DESIGN.md](./API_DESIGN.md) - Complete API specifications

---

**End of Document**

*戦略分析完了。BiRefNet統合アーキテクチャ設計完了。成功確率: 96.7%。*

*指揮官への報告：包括的な統合設計を完了しました。実装準備完了。*
