"""
End-to-End Tests for Complete Video Pipeline
Author: Hestia (Security Guardian) + Artemis (Technical Perfectionist)
Date: 2025-11-07

Purpose: Comprehensive E2E testing of the complete pipeline:
  Text → Voice Synthesis → YOLO Detection → BiRefNet Background Removal → D-ID Video Generation

Test Coverage:
- Happy path (95% success rate verification)
- Partial failures (each stage)
- Critical failures (cascading errors)
- Performance benchmarks (latency, throughput)
- Security validation (input validation, resource limits)
- GPU resource contention
- Storage lifecycle
- Progress tracking
"""

import pytest
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import shutil
from datetime import datetime, timedelta

# Import services
from backend.services.video_pipeline import (
    VideoPipeline,
    PipelineStage,
    PipelineProgress,
    PipelineResult,
    GPUResourceManager
)
from backend.services.voice_pipeline_unified import VoicePipelineUnified, get_voice_pipeline
from backend.services.storage_manager import StorageManager, StorageTier
from backend.services.progress_tracker import ProgressTracker, EventType
from backend.services.d_id_client import DIdClient


# ============================================================================
# Fixtures - Test Data & Services
# ============================================================================

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage_dir = tmp_path / "e2e_test_storage"
    storage_dir.mkdir()
    yield storage_dir
    # Cleanup
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


@pytest.fixture
def sample_texts():
    """Sample texts for voice synthesis"""
    return [
        "Happy Birthday! Wishing you all the best!",  # Short, emotional
        "Congratulations on your graduation! You worked so hard for this moment.",  # Medium
        "こんにちは、元気ですか？今日はとても良い天気ですね。",  # Japanese
        "This is a long test message with multiple sentences. "
        "It should test the robustness of the voice synthesis system. "
        "We want to ensure it handles longer texts properly.",  # Long
        "",  # Empty (edge case)
    ]


@pytest.fixture
def sample_images(tmp_path):
    """Create sample images for testing"""
    import cv2
    import numpy as np

    images = []

    # 1. Image with person (normal case)
    img1 = np.zeros((640, 480, 3), dtype=np.uint8)
    cv2.rectangle(img1, (150, 100), (350, 500), (100, 150, 200), -1)  # Person-like object
    img1_path = tmp_path / "person_normal.jpg"
    cv2.imwrite(str(img1_path), img1)
    images.append({"path": img1_path, "has_person": True, "label": "normal"})

    # 2. Image with multiple persons
    img2 = np.zeros((640, 480, 3), dtype=np.uint8)
    cv2.rectangle(img2, (100, 100), (250, 500), (100, 150, 200), -1)  # Person 1
    cv2.rectangle(img2, (300, 150), (450, 550), (120, 170, 220), -1)  # Person 2
    img2_path = tmp_path / "person_multiple.jpg"
    cv2.imwrite(str(img2_path), img2)
    images.append({"path": img2_path, "has_person": True, "label": "multiple"})

    # 3. Image without person
    img3 = np.zeros((640, 480, 3), dtype=np.uint8)
    cv2.circle(img3, (240, 320), 50, (255, 255, 255), -1)  # Just a circle
    img3_path = tmp_path / "no_person.jpg"
    cv2.imwrite(str(img3_path), img3)
    images.append({"path": img3_path, "has_person": False, "label": "no_person"})

    # 4. Image with complex background
    img4 = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
    cv2.rectangle(img4, (200, 100), (400, 500), (100, 150, 200), -1)  # Person
    img4_path = tmp_path / "complex_background.jpg"
    cv2.imwrite(str(img4_path), img4)
    images.append({"path": img4_path, "has_person": True, "label": "complex"})

    # 5. Small image (edge case)
    img5 = np.zeros((64, 48, 3), dtype=np.uint8)
    cv2.rectangle(img5, (10, 5), (50, 40), (100, 150, 200), -1)
    img5_path = tmp_path / "small_image.jpg"
    cv2.imwrite(str(img5_path), img5)
    images.append({"path": img5_path, "has_person": True, "label": "small"})

    return images


@pytest.fixture
async def voice_pipeline():
    """Get voice pipeline instance"""
    pipeline = await get_voice_pipeline()
    return pipeline


@pytest.fixture
async def video_pipeline(temp_storage):
    """Get video pipeline instance"""
    pipeline = VideoPipeline(storage_dir=temp_storage)
    yield pipeline
    # Cleanup GPU resources
    await pipeline.gpu_manager._lock.acquire()
    pipeline.gpu_manager._lock.release()


@pytest.fixture
async def progress_tracker():
    """Get progress tracker instance"""
    tracker = ProgressTracker(retention_minutes=5)
    await tracker.start()
    yield tracker
    await tracker.stop()


@pytest.fixture
async def storage_manager(temp_storage):
    """Get storage manager instance"""
    manager = StorageManager(
        storage_root=temp_storage,
        min_free_space_gb=0.1,
        cleanup_interval_minutes=1
    )
    await manager.start()
    yield manager
    await manager.stop()


# ============================================================================
# Test: E2E Happy Path
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2EHappyPath:
    """Test complete pipeline execution (happy path)"""

    async def test_complete_pipeline_success(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """
        Test: Complete pipeline from text to video

        Stages:
        1. Voice Synthesis (VOICEVOX/OpenVoice)
        2. Person Detection (YOLO)
        3. Background Removal (BiRefNet)
        4. Video Generation (D-ID)

        Expected: 95% success rate
        """
        # Select valid image (with person)
        test_image = next(img for img in sample_images if img["has_person"] and img["label"] == "normal")
        test_text = sample_texts[0]  # "Happy Birthday!"

        # Track progress
        task_id = f"e2e_test_{int(time.time())}"
        progress_updates = []

        def progress_callback(progress: PipelineProgress):
            progress_updates.append(progress)

        # Stage 1: Voice Synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",  # ずんだもん
            prosody_preset="celebration",
            enable_prosody=True
        )

        assert voice_result is not None
        assert "audio_path" in voice_result
        audio_path = Path(voice_result["audio_path"])
        assert audio_path.exists()

        # Stage 2-4: Video Pipeline
        video_pipeline.register_progress_callback(task_id, progress_callback)

        start_time = time.perf_counter()
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=audio_path
        )
        elapsed_time = time.perf_counter() - start_time

        # Assertions
        assert result.success is True, f"Pipeline failed: {result.error}"
        assert result.video_url is not None
        assert result.error is None
        assert PipelineStage.COMPLETED in result.stages_completed

        # Check all stages completed
        expected_stages = [
            PipelineStage.INITIALIZED,
            PipelineStage.DETECTION_RUNNING,
            PipelineStage.DETECTION_COMPLETED,
            PipelineStage.BACKGROUND_REMOVAL_RUNNING,
            PipelineStage.BACKGROUND_REMOVAL_COMPLETED,
            PipelineStage.VIDEO_GENERATION_RUNNING,
            PipelineStage.VIDEO_GENERATION_COMPLETED,
            PipelineStage.COMPLETED
        ]

        for stage in expected_stages:
            assert stage in result.stages_completed, f"Missing stage: {stage}"

        # Check progress updates
        assert len(progress_updates) >= len(expected_stages)
        assert progress_updates[0].stage == PipelineStage.INITIALIZED
        assert progress_updates[-1].stage == PipelineStage.COMPLETED
        assert progress_updates[-1].percentage == 100

        # Performance check
        print(f"\n✅ E2E Pipeline Success:")
        print(f"   Total time: {elapsed_time:.2f}s")
        print(f"   Video URL: {result.video_url}")
        print(f"   Stages: {len(result.stages_completed)}")

        # Target: Complete in <60 seconds
        assert elapsed_time < 60.0, f"Pipeline too slow: {elapsed_time:.2f}s"

    async def test_pipeline_with_japanese_text(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """Test pipeline with Japanese text"""
        test_image = next(img for img in sample_images if img["has_person"])
        test_text = sample_texts[2]  # Japanese text

        # Voice synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",
            enable_prosody=False  # Disable for speed
        )

        assert voice_result is not None
        audio_path = Path(voice_result["audio_path"])

        # Video pipeline
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=audio_path
        )

        assert result.success is True
        assert result.video_url is not None

    async def test_pipeline_with_long_text(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """Test pipeline with long text"""
        test_image = next(img for img in sample_images if img["has_person"])
        test_text = sample_texts[3]  # Long text

        # Voice synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )

        assert voice_result is not None
        audio_path = Path(voice_result["audio_path"])

        # Video pipeline
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=audio_path
        )

        assert result.success is True


# ============================================================================
# Test: E2E Error Scenarios
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2EErrorScenarios:
    """Test error handling and fallback mechanisms"""

    async def test_no_person_detected(self, voice_pipeline, video_pipeline, sample_texts, sample_images):
        """Test: Image with no person detected"""
        # Get image without person
        test_image = next(img for img in sample_images if not img["has_person"])
        test_text = sample_texts[0]

        # Voice synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )
        audio_path = Path(voice_result["audio_path"])

        # Video pipeline (should fail)
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=audio_path
        )

        # Expected: Failure with clear error message
        assert result.success is False
        assert "No persons detected" in result.error or "no person" in result.error.lower()
        assert PipelineStage.DETECTION_COMPLETED in result.stages_completed
        assert PipelineStage.BACKGROUND_REMOVAL_RUNNING not in result.stages_completed

    async def test_invalid_image_path(self, voice_pipeline, video_pipeline, sample_texts):
        """Test: Non-existent image file"""
        test_text = sample_texts[0]

        # Voice synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )
        audio_path = Path(voice_result["audio_path"])

        # Video pipeline with invalid image
        result = await video_pipeline.execute(
            image_path=Path("/nonexistent/image.jpg"),
            audio_path=audio_path
        )

        assert result.success is False
        assert "not found" in result.error.lower() or "does not exist" in result.error.lower()

    async def test_invalid_audio_path(self, video_pipeline, sample_images):
        """Test: Non-existent audio file"""
        test_image = next(img for img in sample_images if img["has_person"])

        # Video pipeline with invalid audio
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=Path("/nonexistent/audio.wav")
        )

        assert result.success is False

    async def test_empty_text_input(self, voice_pipeline, video_pipeline, sample_images):
        """Test: Empty text input"""
        test_image = next(img for img in sample_images if img["has_person"])

        # Voice synthesis with empty text (should fail or produce silent audio)
        with pytest.raises(Exception):
            await voice_pipeline.synthesize_with_prosody(
                text="",
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )

    async def test_invalid_voice_profile(self, voice_pipeline, sample_texts):
        """Test: Invalid voice profile ID"""
        test_text = sample_texts[0]

        with pytest.raises(RuntimeError, match="Voice synthesis failed"):
            await voice_pipeline.synthesize_with_prosody(
                text=test_text,
                voice_profile_id="invalid_profile_9999",
                enable_prosody=False
            )

    async def test_corrupted_audio_file(self, video_pipeline, sample_images, tmp_path):
        """Test: Corrupted audio file"""
        test_image = next(img for img in sample_images if img["has_person"])

        # Create corrupted audio file
        corrupted_audio = tmp_path / "corrupted.wav"
        corrupted_audio.write_bytes(b"NOT A VALID WAV FILE")

        # Should handle gracefully
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=corrupted_audio
        )

        # Expected: Failure or graceful degradation
        # (Depends on D-ID's validation)
        if not result.success:
            assert "audio" in result.error.lower() or "invalid" in result.error.lower()


# ============================================================================
# Test: E2E Performance Benchmarks
# ============================================================================

@pytest.mark.e2e
@pytest.mark.benchmark
@pytest.mark.asyncio
class TestE2EPerformance:
    """Test pipeline performance benchmarks"""

    async def test_latency_measurement(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """
        Test: Measure end-to-end latency

        Target:
        - Voice synthesis: <10s
        - Video pipeline: <50s
        - Total: <60s
        """
        test_image = next(img for img in sample_images if img["has_person"] and img["label"] == "normal")
        test_text = sample_texts[0]

        # Measure voice synthesis
        start_voice = time.perf_counter()
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=test_text,
            voice_profile_id="voicevox_3",
            enable_prosody=False  # Disable for speed
        )
        voice_latency = time.perf_counter() - start_voice

        audio_path = Path(voice_result["audio_path"])

        # Measure video pipeline
        start_video = time.perf_counter()
        result = await video_pipeline.execute(
            image_path=test_image["path"],
            audio_path=audio_path
        )
        video_latency = time.perf_counter() - start_video

        total_latency = voice_latency + video_latency

        print(f"\n📊 Latency Measurements:")
        print(f"   Voice synthesis: {voice_latency:.2f}s")
        print(f"   Video pipeline: {video_latency:.2f}s")
        print(f"   Total: {total_latency:.2f}s")

        # Assertions
        assert voice_latency < 10.0, f"Voice synthesis too slow: {voice_latency:.2f}s"
        assert video_latency < 50.0, f"Video pipeline too slow: {video_latency:.2f}s"
        assert total_latency < 60.0, f"Total latency too high: {total_latency:.2f}s"

    async def test_throughput_parallel(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """
        Test: Parallel processing throughput

        Target: 5 concurrent requests
        """
        test_image = next(img for img in sample_images if img["has_person"])
        test_texts_batch = sample_texts[:5]  # 5 requests

        # Voice synthesis (sequential for simplicity)
        audio_paths = []
        for text in test_texts_batch:
            if text:  # Skip empty
                voice_result = await voice_pipeline.synthesize_with_prosody(
                    text=text,
                    voice_profile_id="voicevox_3",
                    enable_prosody=False
                )
                audio_paths.append(Path(voice_result["audio_path"]))

        # Video pipeline (parallel)
        tasks = [
            video_pipeline.execute(
                image_path=test_image["path"],
                audio_path=audio_path
            )
            for audio_path in audio_paths
        ]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed_time = time.perf_counter() - start_time

        # Count successes
        successful = sum(1 for r in results if isinstance(r, PipelineResult) and r.success)
        total = len(results)

        print(f"\n📈 Throughput Test:")
        print(f"   Requests: {total}")
        print(f"   Successful: {successful}")
        print(f"   Total time: {elapsed_time:.2f}s")
        print(f"   Avg per request: {elapsed_time / total:.2f}s")

        # Target: At least 80% success rate
        success_rate = successful / total
        assert success_rate >= 0.80, f"Success rate too low: {success_rate:.1%}"

        # Parallel should be faster than sequential
        # (With GPU limits, some queuing is expected)
        avg_time_per_request = elapsed_time / total
        assert avg_time_per_request < 60.0  # Each request <60s on average


# ============================================================================
# Test: E2E Resource Management
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2EResourceManagement:
    """Test GPU resource management and storage lifecycle"""

    async def test_gpu_resource_contention(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """
        Test: GPU resource scheduling under contention

        YOLO: max 2 concurrent
        BiRefNet: max 1 concurrent
        """
        test_image = next(img for img in sample_images if img["has_person"])

        # Voice synthesis
        voice_result = await voice_pipeline.synthesize_with_prosody(
            text=sample_texts[0],
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )
        audio_path = Path(voice_result["audio_path"])

        # Launch 3 concurrent tasks (exceeds limits)
        tasks = [
            video_pipeline.execute(
                image_path=test_image["path"],
                audio_path=audio_path
            )
            for _ in range(3)
        ]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed_time = time.perf_counter() - start_time

        # All should eventually succeed (with queuing)
        assert all(r.success for r in results)

        # Check GPU stats
        gpu_stats = video_pipeline.get_gpu_utilization()
        print(f"\n🎮 GPU Resource Management:")
        print(f"   YOLO slots available: {gpu_stats['yolo_slots_available']}")
        print(f"   BiRefNet slots available: {gpu_stats['birefnet_slots_available']}")
        print(f"   Total time: {elapsed_time:.2f}s")

    async def test_storage_lifecycle(
        self,
        storage_manager,
        tmp_path
    ):
        """Test storage tier management and cleanup"""
        # Create test files in different tiers
        test_files = []
        for tier in [StorageTier.UPLOADS, StorageTier.PROCESSED, StorageTier.VIDEOS, StorageTier.TEMP]:
            test_file = tmp_path / f"test_{tier.value}.dat"
            test_file.write_bytes(b"x" * 1024)  # 1KB

            stored_path = await storage_manager.store_file(
                source_path=test_file,
                tier=tier,
                task_id=f"task_{tier.value}"
            )
            test_files.append((tier, stored_path))

        # Check stats
        stats = storage_manager.get_storage_stats()
        assert stats["total_files"] == 4

        # Expire TEMP files
        for meta in storage_manager._metadata.values():
            if meta.tier == StorageTier.TEMP:
                meta.created_at = datetime.utcnow() - timedelta(hours=2)

        # Cleanup
        result = await storage_manager.cleanup_tier(StorageTier.TEMP)
        assert result["deleted_files"] == 1

        # Verify TEMP deleted, others remain
        temp_tier, temp_path = next((t, p) for t, p in test_files if t == StorageTier.TEMP)
        assert not temp_path.exists()

        for tier, path in test_files:
            if tier != StorageTier.TEMP:
                assert path.exists()


# ============================================================================
# Test: E2E Success Rate Verification
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestE2ESuccessRate:
    """Verify 95% success rate target"""

    async def test_success_rate_100_requests(
        self,
        voice_pipeline,
        video_pipeline,
        sample_texts,
        sample_images
    ):
        """
        Test: Run 100 E2E requests and verify ≥95% success rate

        This is a comprehensive test that simulates real-world usage.
        """
        num_requests = 100

        # Select valid images and texts
        valid_images = [img for img in sample_images if img["has_person"]]
        valid_texts = [t for t in sample_texts if t]  # Non-empty

        results = []

        for i in range(num_requests):
            # Rotate through test data
            test_image = valid_images[i % len(valid_images)]
            test_text = valid_texts[i % len(valid_texts)]

            try:
                # Voice synthesis
                voice_result = await voice_pipeline.synthesize_with_prosody(
                    text=test_text,
                    voice_profile_id="voicevox_3",
                    enable_prosody=False
                )
                audio_path = Path(voice_result["audio_path"])

                # Video pipeline
                result = await video_pipeline.execute(
                    image_path=test_image["path"],
                    audio_path=audio_path
                )

                results.append({
                    "success": result.success,
                    "error": result.error,
                    "request_id": i
                })

            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "request_id": i
                })

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{num_requests}")

        # Calculate success rate
        successful = sum(1 for r in results if r["success"])
        success_rate = successful / num_requests

        print(f"\n🎯 Success Rate Verification:")
        print(f"   Total requests: {num_requests}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {num_requests - successful}")
        print(f"   Success rate: {success_rate:.1%}")

        # Target: ≥95%
        assert success_rate >= 0.95, f"Success rate below target: {success_rate:.1%} < 95%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "e2e"])
