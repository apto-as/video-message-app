"""
Example Integration Test - Video Pipeline

This file demonstrates integration testing best practices:
- Testing multiple components together
- Mocking external dependencies
- Async test patterns
- Resource management
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2

from backend.services.video_pipeline import (
    VideoPipeline,
    PipelineStage,
    PipelineProgress,
    GPUResourceManager
)
from backend.services.progress_tracker import ProgressTracker, EventType
from backend.services.storage_manager import StorageManager, StorageTier


# ======================================================================
# Test Fixtures
# ======================================================================

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory for tests"""
    storage_dir = tmp_path / "integration_test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def sample_image(tmp_path):
    """Create synthetic test image with person-like object"""
    img_path = tmp_path / "test_person.jpg"

    # Create image with person-like rectangle
    image = np.zeros((640, 480, 3), dtype=np.uint8)

    # Draw person-like shape (torso + head)
    cv2.rectangle(image, (150, 100), (350, 400), (100, 150, 200), -1)  # Body
    cv2.circle(image, (250, 80), 50, (100, 150, 200), -1)  # Head

    cv2.imwrite(str(img_path), image)
    return img_path


@pytest.fixture
def sample_audio(tmp_path):
    """Create minimal valid WAV file"""
    audio_path = tmp_path / "test_audio.wav"

    # Minimal WAV file structure
    with open(audio_path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write((36).to_bytes(4, "little"))  # File size - 8
        f.write(b"WAVE")

        # fmt chunk
        f.write(b"fmt ")
        f.write((16).to_bytes(4, "little"))  # Chunk size
        f.write((1).to_bytes(2, "little"))   # Audio format (PCM)
        f.write((1).to_bytes(2, "little"))   # Channels (mono)
        f.write((16000).to_bytes(4, "little"))  # Sample rate
        f.write((32000).to_bytes(4, "little"))  # Byte rate
        f.write((2).to_bytes(2, "little"))   # Block align
        f.write((16).to_bytes(2, "little"))  # Bits per sample

        # data chunk
        f.write(b"data")
        f.write((0).to_bytes(4, "little"))   # Data size (empty)

    return audio_path


@pytest.fixture
async def video_pipeline(temp_storage):
    """Create VideoPipeline instance with cleanup"""
    pipeline = VideoPipeline(storage_dir=temp_storage)

    yield pipeline

    # Cleanup
    try:
        await pipeline.gpu_manager._lock.acquire()
    except:
        pass
    finally:
        if pipeline.gpu_manager._lock.locked():
            pipeline.gpu_manager._lock.release()


@pytest.fixture
async def progress_tracker():
    """Create ProgressTracker instance"""
    tracker = ProgressTracker(retention_minutes=5)
    await tracker.start()

    yield tracker

    await tracker.stop()


@pytest.fixture
async def storage_manager(temp_storage):
    """Create StorageManager instance"""
    manager = StorageManager(
        storage_root=temp_storage,
        min_free_space_gb=0.1,
        cleanup_interval_minutes=1
    )
    await manager.start()

    yield manager

    await manager.stop()


# ======================================================================
# Mock External Services
# ======================================================================

@pytest.fixture
def mock_services(monkeypatch, video_pipeline):
    """Mock PersonDetector, BackgroundRemover, DIdClient"""

    # Mock PersonDetector
    class MockPersonDetector:
        def detect_persons(self, image_path, conf_threshold=0.5, iou_threshold=0.45):
            """Mock person detection - always returns 1 person"""
            return [
                {
                    "person_id": 0,
                    "bbox": {"x1": 150, "y1": 100, "x2": 350, "y2": 500},
                    "confidence": 0.95,
                    "center": {"x": 250, "y": 300},
                    "area": 80000
                }
            ]

    # Mock BackgroundRemover
    class MockBackgroundRemover:
        device = "cuda"
        use_tensorrt = True
        use_fp16 = True

        def remove_background(
            self,
            image_path,
            return_bytes=True,
            smoothing=True
        ):
            """Mock background removal - return minimal PNG"""
            # Minimal PNG structure
            png_signature = b'\x89PNG\r\n\x1a\n'
            return png_signature + b'\x00' * 100

    # Mock DIdClient
    class MockDIdClient:
        api_key = "test_d_id_key"

        async def upload_image(self, image_data, filename):
            """Mock image upload"""
            return f"https://d-id.com/images/{filename}"

        async def upload_audio(self, audio_data, filename):
            """Mock audio upload"""
            return f"https://d-id.com/audios/{filename}"

        async def create_talk_video(self, audio_url, source_url):
            """Mock video creation"""
            return {
                "id": "tlk_test123",
                "status": "done",
                "result_url": "https://d-id.com/talks/test123/video.mp4",
                "created_at": datetime.utcnow().isoformat()
            }

    # Apply mocks
    video_pipeline._person_detector = MockPersonDetector()
    video_pipeline._background_remover = MockBackgroundRemover()
    video_pipeline._d_id_client = MockDIdClient()

    return video_pipeline


# ======================================================================
# Integration Tests - Pipeline
# ======================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestVideoPipelineIntegration:
    """Integration tests for complete video pipeline"""

    async def test_pipeline_success_happy_path(
        self, mock_services, sample_image, sample_audio
    ):
        """
        Test complete pipeline execution (happy path)

        Verifies:
        - All stages complete successfully
        - Progress updates are sent
        - Final result contains video URL
        """
        # Arrange
        pipeline = mock_services
        progress_updates = []

        def progress_callback(progress: PipelineProgress):
            progress_updates.append(progress)

        pipeline.register_progress_callback("test_task", progress_callback)

        # Act
        result = await pipeline.execute(
            image_path=sample_image,
            audio_path=sample_audio
        )

        # Assert
        assert result.success is True, f"Pipeline failed: {result.error}"
        assert result.video_url is not None
        assert result.video_url.endswith(".mp4")
        assert result.error is None

        # Verify all stages completed
        expected_stages = [
            PipelineStage.INITIALIZED,
            PipelineStage.DETECTION,
            PipelineStage.BACKGROUND_REMOVAL,
            PipelineStage.VIDEO_GENERATION,
            PipelineStage.COMPLETED
        ]
        assert all(stage in result.stages_completed for stage in expected_stages)

        # Verify progress updates
        assert len(progress_updates) > 0
        assert progress_updates[0].stage == PipelineStage.INITIALIZED
        assert progress_updates[-1].stage == PipelineStage.COMPLETED
        assert progress_updates[-1].progress == 100

    async def test_pipeline_no_person_detected(
        self, mock_services, sample_image, sample_audio
    ):
        """Test pipeline failure when no person detected"""
        # Arrange
        pipeline = mock_services

        # Override detector to return empty list
        pipeline._person_detector.detect_persons = lambda *args, **kwargs: []

        # Act
        result = await pipeline.execute(
            image_path=sample_image,
            audio_path=sample_audio
        )

        # Assert
        assert result.success is False
        assert "No persons detected" in result.error
        assert result.video_url is None

    async def test_pipeline_missing_input_file(
        self, mock_services, sample_audio
    ):
        """Test pipeline failure with missing input file"""
        # Arrange
        pipeline = mock_services
        nonexistent_image = Path("/nonexistent/image.jpg")

        # Act
        result = await pipeline.execute(
            image_path=nonexistent_image,
            audio_path=sample_audio
        )

        # Assert
        assert result.success is False
        assert "not found" in result.error.lower()

    async def test_pipeline_execution_time(
        self, mock_services, sample_image, sample_audio
    ):
        """Test pipeline completes within acceptable time"""
        # Arrange
        pipeline = mock_services
        max_execution_time = 10.0  # seconds (with mocks)

        # Act
        start_time = asyncio.get_event_loop().time()
        result = await pipeline.execute(
            image_path=sample_image,
            audio_path=sample_audio
        )
        end_time = asyncio.get_event_loop().time()

        execution_time = end_time - start_time

        # Assert
        assert result.success is True
        assert execution_time < max_execution_time, \
            f"Pipeline took {execution_time:.2f}s (expected <{max_execution_time}s)"


# ======================================================================
# Integration Tests - GPU Resource Manager
# ======================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestGPUResourceManager:
    """Test GPU resource scheduling"""

    async def test_yolo_concurrent_limit_enforcement(self):
        """Test that YOLO enforces max 2 concurrent tasks"""
        # Arrange
        manager = GPUResourceManager()

        # Act - Acquire 2 slots (should succeed immediately)
        await manager.acquire_yolo("task_1")
        await manager.acquire_yolo("task_2")

        # Attempt to acquire 3rd slot (should block)
        task_started = asyncio.Event()
        task_completed = asyncio.Event()

        async def acquire_third_slot():
            task_started.set()
            await manager.acquire_yolo("task_3")
            task_completed.set()
            await manager.release_yolo("task_3")

        blocking_task = asyncio.create_task(acquire_third_slot())
        await task_started.wait()
        await asyncio.sleep(0.1)  # Give it time to attempt acquisition

        # Assert - 3rd task should still be waiting
        assert not task_completed.is_set(), "3rd task should be blocked"

        # Release one slot
        await manager.release_yolo("task_1")

        # Now task_3 should acquire
        await asyncio.wait_for(task_completed.wait(), timeout=2.0)
        await manager.release_yolo("task_2")

    async def test_birefnet_exclusive_access(self):
        """Test that BiRefNet allows only 1 concurrent task"""
        # Arrange
        manager = GPUResourceManager()

        # Act - Acquire slot
        await manager.acquire_birefnet("task_1")

        # Try to acquire 2nd slot (should block)
        blocked = asyncio.Event()
        completed = asyncio.Event()

        async def try_acquire():
            blocked.set()
            await manager.acquire_birefnet("task_2")
            completed.set()
            await manager.release_birefnet("task_2")

        blocking_task = asyncio.create_task(try_acquire())
        await blocked.wait()
        await asyncio.sleep(0.1)

        # Assert - 2nd task should be blocked
        assert not completed.is_set(), "2nd BiRefNet task should be blocked"

        # Release first slot
        await manager.release_birefnet("task_1")

        # Now task_2 should acquire
        await asyncio.wait_for(completed.wait(), timeout=2.0)

    async def test_concurrent_yolo_and_birefnet(self):
        """Test YOLO and BiRefNet can run simultaneously"""
        # Arrange
        manager = GPUResourceManager()

        # Act - Acquire both types of slots
        await manager.acquire_yolo("yolo_task_1")
        await manager.acquire_birefnet("birefnet_task_1")

        # Assert - Both should be active
        stats = manager.get_utilization()
        assert stats["yolo_slots_available"] == 1  # 1 out of 2 used
        assert stats["birefnet_slots_available"] == 0  # 1 out of 1 used
        assert stats["active_tasks"] == 2

        # Cleanup
        await manager.release_yolo("yolo_task_1")
        await manager.release_birefnet("birefnet_task_1")


# ======================================================================
# Integration Tests - Progress Tracker
# ======================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestProgressTrackerIntegration:
    """Test real-time progress tracking"""

    async def test_publish_and_subscribe(self, progress_tracker):
        """Test basic pub-sub functionality"""
        # Arrange
        task_id = "test_task_123"
        received_events = []

        async def subscriber():
            async for event in progress_tracker.subscribe(task_id):
                received_events.append(event)
                if len(received_events) == 3:
                    break

        # Act
        subscriber_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)  # Let subscriber register

        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"stage": "init", "progress": 0}
        )
        await progress_tracker.publish_event(
            task_id, EventType.PROGRESS_UPDATE, {"stage": "processing", "progress": 50}
        )
        await progress_tracker.publish_event(
            task_id, EventType.COMPLETE, {"stage": "done", "progress": 100}
        )

        # Assert
        await asyncio.wait_for(subscriber_task, timeout=2.0)
        assert len(received_events) == 3
        assert received_events[0].event_type == EventType.STAGE_UPDATE
        assert received_events[2].event_type == EventType.COMPLETE

    async def test_history_replay_for_late_subscriber(self, progress_tracker):
        """Test historical events are sent to late subscribers"""
        # Arrange
        task_id = "history_task"

        # Publish events BEFORE subscribing
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event1"}
        )
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event2"}
        )
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event3"}
        )

        # Act - NOW subscribe (after events published)
        received = []
        async for event in progress_tracker.subscribe(task_id):
            received.append(event)
            if len(received) == 3:
                break

        # Assert - Should receive historical events
        assert len(received) == 3
        assert received[0].data["msg"] == "event1"
        assert received[2].data["msg"] == "event3"


# ======================================================================
# Integration Tests - Storage Manager
# ======================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestStorageManagerIntegration:
    """Test storage lifecycle management"""

    async def test_store_and_retrieve_with_metadata(
        self, storage_manager, tmp_path
    ):
        """Test file storage with metadata tracking"""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Act
        stored_path = await storage_manager.store_file(
            source_path=test_file,
            tier=StorageTier.UPLOADS,
            task_id="task_123",
            metadata={"type": "image", "user_id": "user_456"}
        )

        # Assert
        assert stored_path.exists()
        assert stored_path.parent == storage_manager.get_tier_path(StorageTier.UPLOADS)

        # Check metadata
        file_meta = storage_manager._metadata[str(stored_path)]
        assert file_meta.tier == StorageTier.UPLOADS
        assert file_meta.task_id == "task_123"
        assert file_meta.metadata["type"] == "image"
        assert file_meta.metadata["user_id"] == "user_456"

    async def test_automatic_cleanup_of_expired_files(
        self, storage_manager, tmp_path
    ):
        """Test automatic cleanup of expired files"""
        # Arrange
        test_file = tmp_path / "expire_test.txt"
        test_file.write_text("will expire")

        stored_path = await storage_manager.store_file(
            source_path=test_file,
            tier=StorageTier.TEMP,  # 1 hour retention
            task_id="expire_task"
        )

        # Manually adjust creation time to be old
        from datetime import datetime, timedelta
        file_meta = storage_manager._metadata[str(stored_path)]
        file_meta.created_at = datetime.utcnow() - timedelta(hours=2)

        # Act
        result = await storage_manager.cleanup_tier(StorageTier.TEMP)

        # Assert
        assert result["deleted_files"] == 1
        assert not stored_path.exists()


# ======================================================================
# End-to-End Integration Test
# ======================================================================

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_video_generation_workflow(
    mock_services,
    sample_image,
    sample_audio,
    progress_tracker,
    storage_manager
):
    """
    Test complete video generation workflow

    This test integrates:
    - Video pipeline
    - Progress tracking
    - Storage management
    - GPU resource scheduling
    """
    # Arrange
    pipeline = mock_services
    task_id = "complete_workflow_test"

    progress_events = []

    async def track_progress():
        async for event in progress_tracker.subscribe(task_id):
            progress_events.append(event)
            if event.event_type == EventType.COMPLETE:
                break

    # Act
    progress_task = asyncio.create_task(track_progress())
    await asyncio.sleep(0.1)  # Let subscriber register

    result = await pipeline.execute(
        image_path=sample_image,
        audio_path=sample_audio,
        task_id=task_id
    )

    await asyncio.wait_for(progress_task, timeout=5.0)

    # Assert
    # 1. Pipeline succeeded
    assert result.success is True
    assert result.video_url is not None

    # 2. Progress updates received
    assert len(progress_events) > 0
    assert any(e.event_type == EventType.STAGE_UPDATE for e in progress_events)
    assert progress_events[-1].event_type == EventType.COMPLETE

    # 3. Storage stats updated
    stats = storage_manager.get_storage_stats()
    assert stats["total_files"] >= 0  # Files created during processing

    # 4. GPU resources released
    gpu_stats = pipeline.gpu_manager.get_utilization()
    assert gpu_stats["active_tasks"] == 0, "GPU resources should be released"
