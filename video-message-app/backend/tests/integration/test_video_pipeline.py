"""
Integration Tests for Complete Video Pipeline

Test Coverage:
- End-to-end pipeline execution
- GPU resource contention
- Progress tracking
- Error recovery
- Storage lifecycle
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import cv2
import numpy as np

from services.video_pipeline import (
    VideoPipeline,
    PipelineStage,
    PipelineProgress,
    GPUResourceManager
)
from services.progress_tracker import ProgressTracker, EventType
from services.storage_manager import StorageManager, StorageTier


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage_dir = tmp_path / "pipeline_test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def sample_image(tmp_path):
    """Create sample test image with person"""
    img_path = tmp_path / "test_person.jpg"

    # Create synthetic image with person-like object
    image = np.zeros((640, 480, 3), dtype=np.uint8)
    # Draw rectangle (simulating person)
    cv2.rectangle(image, (150, 100), (350, 500), (100, 150, 200), -1)
    cv2.imwrite(str(img_path), image)

    return img_path


@pytest.fixture
def sample_audio(tmp_path):
    """Create sample audio file"""
    audio_path = tmp_path / "test_audio.wav"
    # Create minimal WAV file (44-byte header + 1 sample)
    with open(audio_path, "wb") as f:
        # WAV header (44 bytes)
        f.write(b"RIFF")
        f.write((36).to_bytes(4, "little"))  # File size - 8
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((16).to_bytes(4, "little"))  # fmt chunk size
        f.write((1).to_bytes(2, "little"))  # Audio format (PCM)
        f.write((1).to_bytes(2, "little"))  # Channels (mono)
        f.write((16000).to_bytes(4, "little"))  # Sample rate
        f.write((32000).to_bytes(4, "little"))  # Byte rate
        f.write((2).to_bytes(2, "little"))  # Block align
        f.write((16).to_bytes(2, "little"))  # Bits per sample
        f.write(b"data")
        f.write((0).to_bytes(4, "little"))  # Data chunk size

    return audio_path


@pytest.fixture
async def video_pipeline(temp_storage):
    """Create VideoPipeline instance"""
    pipeline = VideoPipeline(storage_dir=temp_storage)
    yield pipeline
    # Cleanup
    await pipeline.gpu_manager._lock.acquire()
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
        min_free_space_gb=0.1,  # Low threshold for testing
        cleanup_interval_minutes=1
    )
    await manager.start()
    yield manager
    await manager.stop()


# ============================================================================
# Unit Tests - GPUResourceManager
# ============================================================================

@pytest.mark.asyncio
class TestGPUResourceManager:
    """Test GPU resource scheduling"""

    async def test_yolo_slot_acquisition(self):
        """Test YOLO slot acquisition and release"""
        manager = GPUResourceManager()

        task_id = "test_task_1"

        # Acquire slot
        await manager.acquire_yolo(task_id)
        assert task_id in manager.active_tasks
        assert manager.active_tasks[task_id] == "yolo"

        # Release slot
        await manager.release_yolo(task_id)
        assert task_id not in manager.active_tasks

    async def test_yolo_concurrent_limit(self):
        """Test YOLO concurrent slot limit (max 2)"""
        manager = GPUResourceManager()

        # Acquire 2 slots (should succeed)
        await manager.acquire_yolo("task_1")
        await manager.acquire_yolo("task_2")

        # Try to acquire 3rd slot (should block)
        task_started = asyncio.Event()
        task_completed = asyncio.Event()

        async def acquire_third_slot():
            task_started.set()
            await manager.acquire_yolo("task_3")
            task_completed.set()
            await manager.release_yolo("task_3")

        task = asyncio.create_task(acquire_third_slot())
        await task_started.wait()

        # Give it a moment to attempt acquisition
        await asyncio.sleep(0.1)
        assert not task_completed.is_set()  # Should still be waiting

        # Release one slot
        await manager.release_yolo("task_1")

        # Now task_3 should acquire
        await asyncio.wait_for(task_completed.wait(), timeout=1.0)
        await manager.release_yolo("task_2")

    async def test_birefnet_exclusive_access(self):
        """Test BiRefNet exclusive slot (max 1)"""
        manager = GPUResourceManager()

        # Acquire slot
        await manager.acquire_birefnet("task_1")

        # Try to acquire 2nd slot (should block)
        blocked = asyncio.Event()
        completed = asyncio.Event()

        async def try_acquire():
            blocked.set()
            await manager.acquire_birefnet("task_2")
            completed.set()
            await manager.release_birefnet("task_2")

        task = asyncio.create_task(try_acquire())
        await blocked.wait()
        await asyncio.sleep(0.1)

        assert not completed.is_set()  # Should be blocked

        # Release first slot
        await manager.release_birefnet("task_1")

        # Now task_2 should acquire
        await asyncio.wait_for(completed.wait(), timeout=1.0)

    async def test_utilization_stats(self):
        """Test GPU utilization statistics"""
        manager = GPUResourceManager()

        # Initial state
        stats = manager.get_utilization()
        assert stats["yolo_slots_available"] == 2
        assert stats["birefnet_slots_available"] == 1
        assert stats["active_tasks"] == 0

        # Acquire resources
        await manager.acquire_yolo("task_1")
        await manager.acquire_birefnet("task_2")

        stats = manager.get_utilization()
        assert stats["yolo_slots_available"] == 1
        assert stats["birefnet_slots_available"] == 0
        assert stats["active_tasks"] == 2

        # Release
        await manager.release_yolo("task_1")
        await manager.release_birefnet("task_2")


# ============================================================================
# Integration Tests - ProgressTracker
# ============================================================================

@pytest.mark.asyncio
class TestProgressTracker:
    """Test real-time progress tracking"""

    async def test_publish_and_subscribe(self, progress_tracker):
        """Test basic pub-sub functionality"""
        task_id = "test_task_123"
        received_events = []

        # Subscribe in background
        async def subscribe_task():
            async for event in progress_tracker.subscribe(task_id):
                received_events.append(event)
                if len(received_events) == 3:
                    break

        subscriber = asyncio.create_task(subscribe_task())

        # Publish events
        await asyncio.sleep(0.1)  # Let subscriber register

        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE,
            {"stage": "initialized", "progress": 0}
        )

        await progress_tracker.publish_event(
            task_id, EventType.PROGRESS_UPDATE,
            {"stage": "detection_running", "progress": 25}
        )

        await progress_tracker.publish_event(
            task_id, EventType.COMPLETE,
            {"stage": "completed", "progress": 100}
        )

        # Wait for subscriber
        await asyncio.wait_for(subscriber, timeout=2.0)

        assert len(received_events) == 3
        assert received_events[0].event_type == EventType.STAGE_UPDATE
        assert received_events[2].event_type == EventType.COMPLETE

    async def test_multiple_subscribers(self, progress_tracker):
        """Test multiple clients subscribing to same task"""
        task_id = "multi_sub_task"

        events_client1 = []
        events_client2 = []

        async def client1():
            async for event in progress_tracker.subscribe(task_id):
                events_client1.append(event)
                if len(events_client1) == 2:
                    break

        async def client2():
            async for event in progress_tracker.subscribe(task_id):
                events_client2.append(event)
                if len(events_client2) == 2:
                    break

        # Start both subscribers
        sub1 = asyncio.create_task(client1())
        sub2 = asyncio.create_task(client2())

        await asyncio.sleep(0.1)

        # Publish 2 events
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event1"}
        )
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event2"}
        )

        # Wait for both
        await asyncio.wait_for(asyncio.gather(sub1, sub2), timeout=2.0)

        # Both should receive same events
        assert len(events_client1) == 2
        assert len(events_client2) == 2

    async def test_history_replay(self, progress_tracker):
        """Test historical events sent to new subscribers"""
        task_id = "history_task"

        # Publish 3 events BEFORE subscribing
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event1"}
        )
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event2"}
        )
        await progress_tracker.publish_event(
            task_id, EventType.STAGE_UPDATE, {"msg": "event3"}
        )

        # NOW subscribe
        received = []
        async for event in progress_tracker.subscribe(task_id):
            received.append(event)
            if len(received) == 3:
                break

        # Should receive historical events
        assert len(received) == 3
        assert received[0].data["msg"] == "event1"
        assert received[2].data["msg"] == "event3"


# ============================================================================
# Integration Tests - StorageManager
# ============================================================================

@pytest.mark.asyncio
class TestStorageManager:
    """Test storage lifecycle management"""

    async def test_store_and_retrieve_file(self, storage_manager, tmp_path):
        """Test file storage and metadata tracking"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Store file
        stored_path = await storage_manager.store_file(
            source_path=test_file,
            tier=StorageTier.UPLOADS,
            task_id="task_123",
            metadata={"type": "image"}
        )

        assert stored_path.exists()
        assert stored_path.parent == storage_manager.get_tier_path(StorageTier.UPLOADS)

        # Check metadata
        file_meta = storage_manager._metadata[str(stored_path)]
        assert file_meta.tier == StorageTier.UPLOADS
        assert file_meta.task_id == "task_123"
        assert file_meta.metadata["type"] == "image"

    async def test_automatic_cleanup(self, storage_manager, tmp_path):
        """Test automatic cleanup of expired files"""
        # Create and store file
        test_file = tmp_path / "expire_test.txt"
        test_file.write_text("will expire")

        stored_path = await storage_manager.store_file(
            source_path=test_file,
            tier=StorageTier.TEMP,  # 1 hour retention
            task_id="expire_task"
        )

        # Manually adjust creation time to be old
        file_meta = storage_manager._metadata[str(stored_path)]
        file_meta.created_at = datetime.utcnow() - timedelta(hours=2)

        # Run cleanup
        result = await storage_manager.cleanup_tier(StorageTier.TEMP)

        assert result["deleted_files"] == 1
        assert not stored_path.exists()

    async def test_storage_stats(self, storage_manager, tmp_path):
        """Test storage statistics"""
        # Store files in different tiers
        for tier in [StorageTier.UPLOADS, StorageTier.PROCESSED, StorageTier.VIDEOS]:
            test_file = tmp_path / f"test_{tier.value}.txt"
            test_file.write_text("test" * 100)
            await storage_manager.store_file(test_file, tier)

        # Get stats
        stats = storage_manager.get_storage_stats()

        assert stats["total_files"] == 3
        assert "uploads" in stats["tiers"]
        assert "disk" in stats
        assert stats["disk"]["free_gb"] > 0


# ============================================================================
# Integration Tests - Complete Pipeline (Mocked External Services)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestVideoPipelineMocked:
    """Test complete pipeline with mocked external services"""

    @pytest.fixture
    def mock_services(self, monkeypatch, video_pipeline):
        """Mock PersonDetector, BackgroundRemover, DIdClient"""

        # Mock PersonDetector
        class MockPersonDetector:
            def detect_persons(self, image_path, conf_threshold, iou_threshold):
                return [
                    {
                        "person_id": 0,
                        "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 400},
                        "confidence": 0.95,
                        "center": {"x": 200, "y": 225},
                        "area": 70000
                    }
                ]

        # Mock BackgroundRemover
        class MockBackgroundRemover:
            device = "cuda"
            use_tensorrt = True
            use_fp16 = True

            def remove_background(self, image_path, return_bytes=True, smoothing=True):
                # Return minimal PNG bytes
                return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        # Mock DIdClient
        class MockDIdClient:
            api_key = "test_key"

            async def upload_image(self, image_data, filename):
                return "https://d-id.com/images/test.png"

            async def upload_audio(self, audio_data, filename):
                return "https://d-id.com/audios/test.wav"

            async def create_talk_video(self, audio_url, source_url):
                return {
                    "id": "tlk_test123",
                    "status": "done",
                    "result_url": "https://d-id.com/talks/test123/video.mp4",
                    "created_at": datetime.utcnow().isoformat()
                }

        video_pipeline._person_detector = MockPersonDetector()
        video_pipeline._background_remover = MockBackgroundRemover()
        video_pipeline._d_id_client = MockDIdClient()

        return video_pipeline

    async def test_pipeline_success_path(self, mock_services, sample_image, sample_audio):
        """Test complete pipeline execution (happy path)"""
        pipeline = mock_services

        # Track progress
        progress_updates = []

        def progress_callback(progress: PipelineProgress):
            progress_updates.append(progress)

        pipeline.register_progress_callback("test_task", progress_callback)

        # Execute pipeline
        result = await pipeline.execute(
            image_path=sample_image,
            audio_path=sample_audio
        )

        # Assertions
        assert result.success is True
        assert result.video_url is not None
        assert result.error is None
        assert PipelineStage.COMPLETED in result.stages_completed

        # Check progress updates
        assert len(progress_updates) > 0
        assert progress_updates[0].stage == PipelineStage.INITIALIZED
        assert progress_updates[-1].stage == PipelineStage.COMPLETED

    async def test_pipeline_no_person_detected(self, mock_services, sample_image, sample_audio):
        """Test pipeline failure when no person detected"""
        pipeline = mock_services

        # Override detector to return empty list
        pipeline._person_detector.detect_persons = lambda *args, **kwargs: []

        result = await pipeline.execute(
            image_path=sample_image,
            audio_path=sample_audio
        )

        assert result.success is False
        assert "No persons detected" in result.error

    async def test_pipeline_missing_input_file(self, mock_services, sample_audio):
        """Test pipeline failure with missing input file"""
        pipeline = mock_services

        result = await pipeline.execute(
            image_path=Path("/nonexistent/image.jpg"),
            audio_path=sample_audio
        )

        assert result.success is False
        assert "not found" in result.error.lower()


# ============================================================================
# Load Tests - Concurrent Execution
# ============================================================================

@pytest.mark.load
@pytest.mark.asyncio
class TestConcurrentPipeline:
    """Test concurrent pipeline execution under load"""

    async def test_concurrent_execution_5_tasks(self, mock_services, sample_image, sample_audio):
        """Test 5 concurrent pipeline executions"""
        pipeline = mock_services

        # Launch 5 tasks
        tasks = [
            pipeline.execute(image_path=sample_image, audio_path=sample_audio)
            for _ in range(5)
        ]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # All should succeed
        assert all(r.success for r in results)

        # Check execution time (should benefit from parallelism)
        total_time = end_time - start_time
        assert total_time < 10.0  # With mocks, should be very fast

        # GPU utilization should not exceed limits
        gpu_stats = pipeline.get_gpu_utilization()
        assert gpu_stats["yolo_slots_available"] >= 0
        assert gpu_stats["birefnet_slots_available"] >= 0


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
class TestPipelinePerformance:
    """Performance benchmarking tests"""

    async def test_progress_update_latency(self, progress_tracker):
        """Test progress update latency (<5 seconds target)"""
        task_id = "latency_test"
        latencies = []

        async def subscriber():
            last_timestamp = None
            async for event in progress_tracker.subscribe(task_id):
                if last_timestamp:
                    latency = (event.timestamp - last_timestamp).total_seconds()
                    latencies.append(latency)
                last_timestamp = event.timestamp
                if len(latencies) == 5:
                    break

        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Publish 6 events with 1-second intervals
        for i in range(6):
            await progress_tracker.publish_event(
                task_id, EventType.PROGRESS_UPDATE, {"progress": i * 20}
            )
            await asyncio.sleep(1.0)

        await asyncio.wait_for(sub_task, timeout=10.0)

        # Check latencies
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 5.0  # Target: <5 seconds

    async def test_storage_cleanup_performance(self, storage_manager, tmp_path):
        """Test storage cleanup with 1000 files"""
        # Create 1000 test files
        for i in range(1000):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text("test")
            await storage_manager.store_file(test_file, StorageTier.TEMP)

        # Make all files expired
        for meta in storage_manager._metadata.values():
            meta.created_at = datetime.utcnow() - timedelta(hours=2)

        # Measure cleanup time
        start_time = asyncio.get_event_loop().time()
        result = await storage_manager.cleanup_tier(StorageTier.TEMP)
        end_time = asyncio.get_event_loop().time()

        cleanup_time = end_time - start_time

        assert result["deleted_files"] == 1000
        assert cleanup_time < 5.0  # Should complete in <5 seconds
