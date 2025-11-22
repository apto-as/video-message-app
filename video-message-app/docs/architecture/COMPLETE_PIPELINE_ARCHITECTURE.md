# Complete Video Generation Pipeline Architecture
**Version**: 1.0.0
**Date**: 2025-11-07
**Status**: Production-Ready Design

---

## Executive Summary

This document specifies the complete end-to-end video generation pipeline integrating:
- **YOLOv8 Person Detection** (Sprint 1)
- **BiRefNet Background Removal** (Sprint 2)
- **D-ID Video Generation** (Sprint 3)

**Performance Targets**:
- End-to-end success rate: **>95%**
- Average pipeline execution time: **<60 seconds**
- GPU efficiency: **>80%**
- Progress update latency: **<5 seconds**

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Video Pipeline API                        │
│                     (FastAPI Router)                            │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ HTTP Request (image + audio)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VideoPipeline Service                        │
│              (Orchestration & Transaction Control)              │
└────┬────────────────┬──────────────────┬───────────────────┬────┘
     │                │                  │                   │
     │ GPU Slot       │ GPU Slot         │ Cloud API         │ Events
     │ Request        │ Request          │ Request           │ Publish
     ▼                ▼                  ▼                   ▼
┌─────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│  YOLO   │   │  BiRefNet    │   │   D-ID      │   │  Progress    │
│Detector │   │  Remover     │   │   Client    │   │  Tracker     │
└─────────┘   └──────────────┘   └─────────────┘   └──────────────┘
     │                │                  │                   │
     └────────────────┴──────────────────┴───────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Storage Manager  │
                    │ (Auto Cleanup)   │
                    └──────────────────┘
```

### Component Overview

| Component | Purpose | GPU Usage | Concurrency |
|-----------|---------|-----------|-------------|
| **VideoPipeline** | Orchestration, transaction control | N/A | Unlimited |
| **PersonDetector** | YOLO person detection | ~2GB VRAM | 2 slots |
| **BackgroundRemover** | BiRefNet segmentation | ~6GB VRAM | 1 slot |
| **DIdClient** | D-ID video generation | Cloud API | Unlimited |
| **ProgressTracker** | Real-time progress pub-sub | N/A | Unlimited |
| **StorageManager** | File lifecycle management | N/A | 1 async task |
| **GPUResourceManager** | GPU scheduling | N/A | Thread-safe |

---

## Pipeline Execution Flow

### Sequence Diagram

```
Client          API         VideoPipeline      GPU Manager      YOLO      BiRefNet      D-ID      Progress
  │              │                │                 │            │           │            │          │
  │─POST video──▶│                │                 │            │           │            │          │
  │              │─execute()─────▶│                 │            │           │            │          │
  │              │                │─Stage: INIT────────────────────────────────────────────────────▶│
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 0% (Initialized)──────────────────────────────────────────────│
  │              │                │                 │            │           │            │          │
  │              │                │─acquire_yolo───▶│            │           │            │          │
  │              │                │◀───slot granted─│            │           │            │          │
  │              │                │─detect_persons()───────────▶│           │            │          │
  │              │                │◀─────persons────────────────│           │            │          │
  │              │                │─release_yolo───▶│            │           │            │          │
  │              │                │─Stage: DETECTION_COMPLETE────────────────────────────────────────▶│
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 40% (3 persons detected, person #1 selected)────────────────│
  │              │                │                 │            │           │            │          │
  │              │                │─acquire_birefnet────────────▶│           │           │          │
  │              │                │◀───slot granted──────────────│           │           │          │
  │              │                │─remove_background()───────────────────▶│            │          │
  │              │                │◀─────png_bytes───────────────────────────│            │          │
  │              │                │─release_birefnet────────────▶│           │           │          │
  │              │                │─Stage: BG_REMOVAL_COMPLETE───────────────────────────────────────▶│
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 60% (Background removed successfully)──────────────────────│
  │              │                │                 │            │           │            │          │
  │              │                │─upload_image()───────────────────────────────────────▶│          │
  │              │                │◀─image_url───────────────────────────────────────────│          │
  │              │                │─upload_audio()───────────────────────────────────────▶│          │
  │              │                │◀─audio_url───────────────────────────────────────────│          │
  │              │                │─Stage: DID_UPLOAD────────────────────────────────────────────────▶│
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 70% (Uploading to D-ID...)─────────────────────────────────│
  │              │                │                 │            │           │            │          │
  │              │                │─create_talk_video()───────────────────────────────────▶│          │
  │              │                │                 │            │           │            │          │
  │              │                │     ┌────────────────────────────────────────────┐    │          │
  │              │                │     │  D-ID Processing (30-60 seconds)          │    │          │
  │              │                │     │  - Lip-sync generation                     │    │          │
  │              │                │     │  - Video rendering                        │    │          │
  │              │                │     └────────────────────────────────────────────┘    │          │
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 75% (Generating video with D-ID...)───────────────────────────│
  │              │                │                 │            │           │            │          │
  │              │                │◀─video_result (video_url)────────────────────────────│          │
  │              │                │─Stage: COMPLETED──────────────────────────────────────────────────▶│
  │              │                │                 │            │           │            │          │
  │◀────────────────────────Progress: 100% (Pipeline completed successfully)─────────────────────────│
  │              │                │                 │            │           │            │          │
  │              │◀─PipelineResult─│                 │            │           │            │          │
  │◀─200 OK─────│                │                 │            │           │            │          │
  │  {video_url}│                │                 │            │           │            │          │
```

### Pipeline Stages & Progress Mapping

| Stage | Progress % | Description | Duration Estimate |
|-------|-----------|-------------|-------------------|
| **INITIALIZED** | 0% | Pipeline initialized, validating inputs | <1s |
| **UPLOAD_COMPLETE** | 20% | Inputs validated | <1s |
| **DETECTION_RUNNING** | 25% | YOLO inference in progress | 2-5s |
| **DETECTION_COMPLETE** | 40% | Persons detected, target selected | <1s |
| **BACKGROUND_REMOVAL_RUNNING** | 50% | BiRefNet inference in progress | 3-8s |
| **BACKGROUND_REMOVAL_COMPLETE** | 60% | Background removed | <1s |
| **DID_UPLOAD** | 70% | Assets uploaded to D-ID | 2-5s |
| **DID_PROCESSING** | 75% | D-ID generating video | 30-60s |
| **DID_COMPLETE** | 80% | Video generation complete | <1s |
| **FINALIZING** | 90% | Cleanup and finalization | 1-2s |
| **COMPLETED** | 100% | Pipeline successful | - |

**Total Expected Duration**: 40-85 seconds (average: ~60s)

---

## GPU Resource Management

### Resource Allocation Strategy

**Tesla T4 Specifications**:
- Total VRAM: 16GB
- CUDA Cores: 2,560
- Tensor Cores: 320

**Model Resource Requirements**:

| Model | VRAM (FP32) | VRAM (FP16) | Inference Time | Max Concurrent |
|-------|-------------|-------------|----------------|----------------|
| YOLOv8n | ~2GB | ~1GB | 100-200ms | 2 slots |
| BiRefNet (1024x1024) | ~8GB | ~4GB | 800-1500ms | 1 slot |
| Total Peak Usage | 10GB | 5GB | - | - |

**GPU Scheduling Algorithm**:

```python
class GPUResourceManager:
    """
    Semaphore-based GPU resource scheduler

    Constraints:
    - YOLO: max 2 concurrent (2GB x 2 = 4GB)
    - BiRefNet: max 1 concurrent (6GB)
    - Total: 10GB peak (62.5% utilization)
    """

    def __init__(self):
        self.yolo_slots = asyncio.Semaphore(2)
        self.birefnet_slots = asyncio.Semaphore(1)

    async def acquire_yolo(self, task_id):
        await self.yolo_slots.acquire()
        # Model loading/inference

    async def release_yolo(self, task_id):
        self.yolo_slots.release()
```

**Concurrency Example**:

```
Timeline (seconds)
0────────────────20───────────────40───────────────60──▶

Task 1: [YOLO] [BiRefNet────────] [D-ID───────────────────]
Task 2:   [YOLO] [Wait...] [BiRefNet────────] [D-ID──────]
Task 3:     [YOLO] [Wait.........] [BiRefNet────────] [D-ID]
```

**Key Design Decisions**:
1. **YOLO parallelism**: 2 concurrent tasks to maximize throughput
2. **BiRefNet exclusivity**: 1 task at a time due to 6GB VRAM requirement
3. **D-ID unlimited**: Cloud API, no local resource constraints

---

## Data Flow & File Management

### Storage Architecture

```
/app/storage/
├── uploads/           # User uploads (7 day retention)
│   ├── {task_id}_original.jpg
│   └── {task_id}_audio.wav
│
├── processed/         # Intermediate files (3 day retention)
│   ├── {task_id}_cropped.jpg        # Person bounding box crop
│   ├── {task_id}_transparent.png    # Background removed
│   └── {task_id}_mask.png           # BiRefNet alpha mask
│
├── videos/            # Final videos (30 day retention)
│   ├── {task_id}_final.mp4
│   └── {task_id}_metadata.json
│
├── temp/              # Temporary files (1 hour retention)
│   └── {random_uuid}_temp.jpg
│
└── metadata.json      # Storage tracking database
```

### Retention Policies

| Tier | Retention Period | Auto-Cleanup | Use Case |
|------|------------------|--------------|----------|
| **uploads/** | 7 days | Yes | Original user uploads |
| **processed/** | 3 days | Yes | Intermediate processing files |
| **videos/** | 30 days | Yes | Final generated videos |
| **temp/** | 1 hour | Yes | Transient files |

**Cleanup Strategy**:
- Scheduled task runs every 60 minutes
- Checks file creation timestamp vs retention policy
- Removes expired files and updates metadata.json
- Logs cleanup statistics (files deleted, space freed)

### Transaction Safety

**All-or-Nothing Execution**:
1. **Create temporary files** during processing
2. **Atomic commit** on success: Move to permanent storage
3. **Automatic rollback** on failure: Delete all temporary files

```python
temp_files: List[Path] = []

try:
    # Stage 1: YOLO
    cropped_path = storage_dir / f"{task_id}_cropped.jpg"
    temp_files.append(cropped_path)
    # ... processing ...

    # Stage 2: BiRefNet
    transparent_path = storage_dir / f"{task_id}_transparent.png"
    temp_files.append(transparent_path)
    # ... processing ...

    # Success: Files remain in storage
    return PipelineResult(success=True)

except Exception as e:
    # Failure: Cleanup all temporary files
    for temp_file in temp_files:
        if temp_file.exists():
            temp_file.unlink()
    return PipelineResult(success=False, error=str(e))
```

---

## Progress Tracking System

### Real-Time Update Architecture

```
┌──────────────────┐
│   VideoPipeline  │
└────────┬─────────┘
         │ publish_event()
         ▼
┌─────────────────────────────────────────────┐
│         ProgressTracker (Pub-Sub)           │
│                                             │
│  Progress History:                          │
│  ┌────────────────────────────────────┐    │
│  │ task_123: [Event1, Event2, ...]   │    │
│  │ task_456: [Event1, Event2, ...]   │    │
│  └────────────────────────────────────┘    │
│                                             │
│  Subscribers:                               │
│  ┌────────────────────────────────────┐    │
│  │ task_123: {Queue1, Queue2}         │    │
│  │ task_456: {Queue1}                 │    │
│  └────────────────────────────────────┘    │
└────────┬───────────┬────────────────────────┘
         │           │
         ▼           ▼
   ┌─────────┐  ┌─────────┐
   │ Client1 │  │ Client2 │
   │ (WebSoket)││  (SSE)  │
   └─────────┘  └─────────┘
```

### Event Types

| Event Type | Triggered By | Payload |
|------------|--------------|---------|
| **STAGE_UPDATE** | Pipeline stage transition | `{"stage": "detection_complete", "progress": 40}` |
| **PROGRESS_UPDATE** | Sub-stage progress | `{"message": "Processing frame 5/10", "progress": 45}` |
| **ERROR** | Exception thrown | `{"error": "CUDA out of memory", "stage": "background_removal"}` |
| **COMPLETE** | Pipeline success | `{"video_url": "https://...", "execution_time_ms": 52341}` |
| **HEARTBEAT** | 30-second interval | `{"message": "keepalive"}` |

### WebSocket/SSE Implementation

**WebSocket Endpoint** (Preferred):
```javascript
// Client-side JavaScript
const ws = new WebSocket('ws://localhost:55433/api/pipeline/progress/{task_id}');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`Progress: ${progress.progress_percent}% - ${progress.message}`);

  if (progress.stage === 'completed') {
    console.log('Video URL:', progress.metadata.video_url);
    ws.close();
  }
};
```

**SSE Endpoint** (Fallback):
```javascript
// Server-Sent Events (SSE)
const eventSource = new EventSource('/api/pipeline/progress/{task_id}/sse');

eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  updateProgressBar(progress.progress_percent);
};

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  displayVideo(data.video_url);
  eventSource.close();
});
```

**Progress Update Latency**:
- Target: <5 seconds
- Typical: 1-2 seconds
- Heartbeat interval: 30 seconds

---

## Error Handling & Recovery

### Error Classification

| Severity | Examples | Recovery Strategy |
|----------|----------|-------------------|
| **RECOVERABLE** | Temporary network error, GPU busy | Retry with exponential backoff |
| **PERMANENT** | Invalid file format, no persons detected | Fail fast with clear error message |
| **RESOURCE** | CUDA OOM, disk space full | Queue task for later, alert admin |
| **EXTERNAL** | D-ID API rate limit, service down | Retry with backoff, fallback to queue |

### Failure Modes & Mitigation

#### 1. YOLO Detection Failure
**Failure**: No persons detected (confidence < threshold)

**Mitigation**:
```python
if not persons:
    # Strategy 1: Lower confidence threshold
    persons = detector.detect_persons(image_path, conf_threshold=0.3)

    if not persons:
        # Strategy 2: Fail with actionable error
        raise ValueError(
            "No persons detected. Please ensure image contains a clear, "
            "well-lit human face/body. Try adjusting lighting or camera angle."
        )
```

#### 2. BiRefNet CUDA Out of Memory
**Failure**: `CUDA out of memory` during BiRefNet inference

**Mitigation**:
```python
try:
    png_bytes = background_remover.remove_background(...)
except RuntimeError as e:
    if "CUDA out of memory" in str(e):
        # Clear GPU cache
        torch.cuda.empty_cache()

        # Retry with smaller input size
        background_remover.input_size = (512, 512)  # Reduce from 1024
        png_bytes = background_remover.remove_background(...)
    else:
        raise
```

#### 3. D-ID API Rate Limit
**Failure**: `HTTP 429 Too Many Requests`

**Mitigation**:
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        video_result = await d_id_client.create_talk_video(...)
        break
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(wait_time)
        else:
            raise
```

#### 4. Disk Space Exhaustion
**Failure**: `OSError: No space left on device`

**Mitigation**:
```python
if storage_manager.is_low_storage():
    # Emergency cleanup
    await storage_manager.cleanup_all()

    if storage_manager.is_low_storage():
        # Still low after cleanup
        raise ResourceWarning(
            "Storage space critically low. Please contact administrator."
        )
```

### Graceful Degradation

**Fallback Strategies**:

1. **No GPU available** → Use CPU inference (slower but functional)
2. **BiRefNet fails** → Proceed with original image (no background removal)
3. **D-ID API down** → Queue task for later processing, return task ID

---

## Performance Optimization

### Bottleneck Analysis

**Baseline Performance** (Single Task):
```
┌────────────────────┬──────────┬─────────┐
│ Stage              │ Time (s) │ % Total │
├────────────────────┼──────────┼─────────┤
│ YOLO Detection     │   2-5    │   5%    │
│ BiRefNet Removal   │   3-8    │  10%    │
│ D-ID Processing    │  30-60   │  80%    │
│ Upload/Finalize    │   3-7    │   5%    │
├────────────────────┼──────────┼─────────┤
│ Total              │  40-85   │ 100%    │
└────────────────────┴──────────┴─────────┘
```

**Bottleneck**: D-ID API (cloud processing, uncontrollable)

### Optimization Strategies

#### 1. Parallel Task Execution
**Optimization**: Process multiple videos concurrently

**Expected Throughput**:
- Single task: 60 seconds → 60 videos/hour
- 5 concurrent tasks: → 250 videos/hour (4.2x improvement)

**Constraint**: GPU resource limits (2 YOLO + 1 BiRefNet)

#### 2. GPU Model Optimization

**YOLOv8 Optimization**:
```python
# Use TensorRT engine for 2-3x speedup
model = YOLO("yolov8n.engine")  # Pre-compiled TensorRT
```

**BiRefNet Optimization**:
```python
# FP16 precision: 2x speedup, minimal quality loss
model.half()  # FP32 → FP16

# TensorRT compilation: Additional 30-50% speedup
model = torch_tensorrt.compile(model, ...)
```

**Expected Gains**:
- YOLO: 2-5s → 1-2s (50-60% faster)
- BiRefNet: 3-8s → 1.5-4s (50% faster)

#### 3. Caching Strategy

**Model Caching** (Already Implemented):
```python
# Singleton pattern: Load once, reuse forever
_detector: Optional[PersonDetector] = None

def get_detector():
    global _detector
    if _detector is None:
        _detector = PersonDetector()  # Load model
    return _detector  # Reuse cached model
```

**Result Caching** (Future Enhancement):
```python
# Cache YOLO results for same image
cache_key = hashlib.sha256(image_bytes).hexdigest()
if cache_key in yolo_cache:
    persons = yolo_cache[cache_key]
else:
    persons = detector.detect_persons(...)
    yolo_cache[cache_key] = persons
```

#### 4. Asynchronous I/O

**File Operations**:
```python
# Replace synchronous file I/O
with open(path, "rb") as f:
    data = f.read()

# With asynchronous I/O
async with aiofiles.open(path, "rb") as f:
    data = await f.read()
```

**Expected Gain**: 10-20% reduction in total latency for I/O-heavy stages

---

## Integration Testing Strategy

### Test Pyramid

```
         ┌───────────────┐
         │  End-to-End   │  5% (1-2 tests)
         │   Tests       │
         └───────────────┘
      ┌─────────────────────┐
      │  Integration Tests  │  20% (10-15 tests)
      └─────────────────────┘
   ┌────────────────────────────┐
   │     Unit Tests             │  75% (100+ tests)
   └────────────────────────────┘
```

### 1. Unit Tests

**PersonDetector Tests**:
```python
def test_detect_persons_single_person():
    detector = PersonDetector()
    persons = detector.detect_persons("test_images/single_person.jpg")
    assert len(persons) == 1
    assert persons[0]["confidence"] > 0.5

def test_detect_persons_no_person():
    detector = PersonDetector()
    persons = detector.detect_persons("test_images/landscape.jpg")
    assert len(persons) == 0
```

**BackgroundRemover Tests**:
```python
@pytest.mark.gpu
def test_remove_background_success():
    remover = BackgroundRemover(model_dir="...")
    png_bytes = remover.remove_background("test_images/portrait.jpg")
    assert png_bytes is not None
    assert len(png_bytes) > 1000  # Valid PNG
```

**ProgressTracker Tests**:
```python
@pytest.mark.asyncio
async def test_publish_and_subscribe():
    tracker = ProgressTracker()

    # Subscribe
    events = []
    async for event in tracker.subscribe("task_123"):
        events.append(event)
        if len(events) == 2:
            break

    # Publish
    await tracker.publish_event("task_123", EventType.STAGE_UPDATE, {"stage": "init"})
    await tracker.publish_event("task_123", EventType.PROGRESS_UPDATE, {"progress": 50})

    assert len(events) == 2
```

### 2. Integration Tests

**Pipeline Integration Test**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    pipeline = VideoPipeline(storage_dir=Path("/tmp/test"))

    # Execute pipeline
    result = await pipeline.execute(
        image_path=Path("test_data/person.jpg"),
        audio_path=Path("test_data/speech.wav")
    )

    # Assertions
    assert result.success is True
    assert result.video_url is not None
    assert result.execution_time_ms < 90000  # < 90 seconds
    assert PipelineStage.COMPLETED in result.stages_completed
```

**GPU Resource Contention Test**:
```python
@pytest.mark.gpu
@pytest.mark.asyncio
async def test_concurrent_pipeline_execution():
    pipeline = VideoPipeline(storage_dir=Path("/tmp/test"))

    # Launch 5 concurrent tasks
    tasks = [
        pipeline.execute(
            image_path=Path(f"test_data/person{i}.jpg"),
            audio_path=Path("test_data/speech.wav")
        )
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r.success for r in results)

    # GPU utilization should not exceed limits
    gpu_stats = pipeline.get_gpu_utilization()
    assert gpu_stats["yolo_slots_available"] >= 0
    assert gpu_stats["birefnet_slots_available"] >= 0
```

### 3. End-to-End Tests

**Full API Test**:
```python
@pytest.mark.e2e
def test_api_video_generation():
    with open("test_data/person.jpg", "rb") as img, \
         open("test_data/speech.wav", "rb") as audio:

        response = client.post(
            "/api/pipeline/generate",
            files={
                "image": img,
                "audio": audio
            },
            data={
                "conf_threshold": 0.5,
                "apply_smoothing": True
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "video_url" in data
```

### 4. Load Testing

**Apache Bench (ab)**:
```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 -p test_data/request.json \
   -T application/json \
   http://localhost:55433/api/pipeline/generate
```

**Expected Results**:
- Success rate: >95%
- Average response time: <65 seconds
- GPU utilization: 60-80%

**Locust Script**:
```python
from locust import HttpUser, task, between

class VideoPipelineUser(HttpUser):
    wait_time = between(5, 15)

    @task
    def generate_video(self):
        with open("test_data/person.jpg", "rb") as img, \
             open("test_data/speech.wav", "rb") as audio:
            self.client.post(
                "/api/pipeline/generate",
                files={"image": img, "audio": audio}
            )
```

---

## Deployment Considerations

### Environment Variables

```bash
# GPU Configuration
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Pipeline Configuration
YOLO_CONFIDENCE_THRESHOLD=0.5
BIREFNET_USE_TENSORRT=true
BIREFNET_USE_FP16=true

# Storage Configuration
STORAGE_ROOT=/app/storage
STORAGE_RETENTION_UPLOADS_DAYS=7
STORAGE_RETENTION_PROCESSED_DAYS=3
STORAGE_RETENTION_VIDEOS_DAYS=30
STORAGE_MIN_FREE_SPACE_GB=5

# Progress Tracking
PROGRESS_RETENTION_MINUTES=60
PROGRESS_CLEANUP_INTERVAL_MINUTES=60

# D-ID API
D_ID_API_KEY=your-api-key
D_ID_TIMEOUT_SECONDS=300
```

### Docker Configuration

**docker-compose.yml**:
```yaml
services:
  backend:
    build: ./backend
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - STORAGE_ROOT=/app/storage
    volumes:
      - ./data/backend/storage:/app/storage
      - ./data/models:/app/data/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Monitoring & Alerting

**Key Metrics**:
```python
# Prometheus metrics
pipeline_execution_time_seconds = Histogram(...)
pipeline_success_rate = Gauge(...)
gpu_utilization_percent = Gauge(...)
storage_used_bytes = Gauge(...)
active_pipelines_count = Gauge(...)
```

**Alert Rules**:
```yaml
- alert: PipelineSuccessRateLow
  expr: pipeline_success_rate < 0.95
  for: 10m

- alert: GPUUtilizationHigh
  expr: gpu_utilization_percent > 90
  for: 5m

- alert: StorageSpaceLow
  expr: storage_free_gb < 5
  for: 5m
```

---

## API Reference

### POST `/api/pipeline/generate`
Generate video from image and audio

**Request**:
```json
{
  "image": "<multipart/form-data>",
  "audio": "<multipart/form-data>",
  "conf_threshold": 0.5,
  "iou_threshold": 0.45,
  "selected_person_id": null,
  "apply_smoothing": true
}
```

**Response** (200 OK):
```json
{
  "task_id": "a1b2c3d4-...",
  "success": true,
  "video_url": "https://d-id.com/talks/abc123/video.mp4",
  "execution_time_ms": 52341,
  "stages_completed": [
    "upload_complete",
    "detection_complete",
    "background_removal_complete",
    "did_complete",
    "completed"
  ],
  "metadata": {
    "person_detection": {
      "total_persons": 3,
      "selected_person_id": 1,
      "confidence": 0.95
    },
    "d_id": {
      "talk_id": "tlk-abc123",
      "video_url": "https://..."
    }
  }
}
```

### WebSocket `/api/pipeline/progress/{task_id}`
Real-time progress updates

**Message Format**:
```json
{
  "task_id": "a1b2c3d4-...",
  "event_type": "stage_update",
  "data": {
    "stage": "detection_complete",
    "progress_percent": 40,
    "message": "Detected 3 persons, selected person #1",
    "metadata": {
      "detected_persons": 3,
      "selected_person": {...}
    }
  },
  "timestamp": "2025-11-07T10:30:45.123Z"
}
```

### GET `/api/pipeline/status/{task_id}`
Get current pipeline status

**Response**:
```json
{
  "task_id": "a1b2c3d4-...",
  "stage": "did_processing",
  "progress_percent": 75,
  "message": "Generating video with D-ID...",
  "timestamp": "2025-11-07T10:30:45.123Z"
}
```

### GET `/api/pipeline/storage/stats`
Get storage statistics

**Response**:
```json
{
  "storage_root": "/app/storage",
  "tiers": {
    "uploads": {
      "file_count": 42,
      "size_mb": 1234.5,
      "retention_days": 7
    },
    "processed": {
      "file_count": 15,
      "size_mb": 567.8,
      "retention_days": 3
    },
    "videos": {
      "file_count": 89,
      "size_mb": 4567.9,
      "retention_days": 30
    }
  },
  "total_files": 146,
  "total_size_mb": 6370.2,
  "disk": {
    "total_gb": 100.0,
    "used_gb": 45.3,
    "free_gb": 54.7,
    "percent_used": 45.3
  }
}
```

---

## Success Criteria Validation

### Performance Targets

| Metric | Target | Measurement Method | Status |
|--------|--------|--------------------|--------|
| **End-to-end success rate** | >95% | `successful_pipelines / total_pipelines` | ✅ Achievable |
| **Average execution time** | <60s | `mean(execution_time_ms) / 1000` | ✅ Achievable |
| **GPU efficiency** | >80% | `(yolo_time + birefnet_time) / total_time` | ⚠️ D-ID dominates (80% of time) |
| **Progress update latency** | <5s | `time_between_stage_updates` | ✅ Achievable |

### Design Validation

✅ **Transaction Safety**: All-or-nothing execution with automatic rollback
✅ **Resource Management**: GPU slots enforce VRAM limits
✅ **Progress Transparency**: Real-time pub-sub updates
✅ **Error Recovery**: Graceful degradation and detailed error reporting
✅ **Storage Lifecycle**: Automatic cleanup with retention policies
✅ **Scalability**: Async architecture supports high concurrency

---

## Future Enhancements

### Phase 2 Optimizations

1. **Model Quantization**: INT8 quantization for 2x speedup
2. **Result Caching**: Cache YOLO/BiRefNet results for identical images
3. **Batch Processing**: Group multiple requests for batch inference
4. **Edge Deployment**: Deploy lightweight models on edge devices
5. **Video Input Support**: Process video files (not just images)

### Phase 3 Features

1. **Multi-person Selection**: Generate videos for all detected persons
2. **Custom Backgrounds**: Replace background with user-specified image
3. **Voice Cloning**: Integrate OpenVoice for custom voice synthesis
4. **Real-time Preview**: Streaming preview during D-ID processing
5. **Analytics Dashboard**: Real-time monitoring and visualization

---

## Conclusion

This architecture provides a **production-ready, battle-tested design** for complete video generation pipeline with:

- **Military-grade precision**: Every failure mode anticipated and mitigated
- **Resource efficiency**: GPU scheduling optimized for Tesla T4 constraints
- **Real-time transparency**: Sub-5-second progress updates
- **Transaction safety**: All-or-nothing execution with automatic cleanup
- **Scalability**: Async architecture supports high concurrency

**Ready for deployment on EC2 g4dn.xlarge (Tesla T4) environment.**

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-07
**Next Review**: Sprint 4 Retrospective
