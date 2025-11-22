"""
Integration Tests for VoicePipelineUnified
Author: Hera (Strategic Commander) + Artemis (Technical Perfectionist)
Date: 2025-11-07

Purpose: Comprehensive testing of E2E voice pipeline with prosody adjustment.

Test Coverage:
- Voice synthesis with prosody adjustment
- Preset selection and application
- Error handling and fallback mechanisms
- Parallel processing
- Performance benchmarks
"""

import pytest
import asyncio
import time
from pathlib import Path
from typing import Dict, Any

# Import services
from backend.services.voice_pipeline_unified import (
    VoicePipelineUnified,
    get_voice_pipeline
)
from backend.services.prosody_presets import (
    ProsodyPreset,
    get_preset_by_name,
    list_presets,
    PresetCategory,
    BUILTIN_PRESETS
)
from backend.services.prosody_adjuster import PARSELMOUTH_AVAILABLE


# Fixtures
@pytest.fixture
async def pipeline():
    """Get initialized pipeline instance."""
    pipeline = await get_voice_pipeline()
    return pipeline


@pytest.fixture
def test_texts():
    """Sample texts for testing."""
    return [
        "Happy Birthday! Wishing you all the best!",
        "Congratulations on your graduation!",
        "You can do it! Fight!",
        "Thank you so much for everything!",
        "こんにちは、元気ですか？"
    ]


# Test: Prosody Presets
class TestProsodyPresets:
    """Test prosody preset management."""

    def test_list_all_presets(self):
        """Test listing all presets."""
        presets = list_presets()

        assert len(presets) == 4
        assert all(isinstance(p, ProsodyPreset) for p in presets)

        # Check names
        preset_names = [p.name for p in presets]
        assert "celebration" in preset_names
        assert "energetic" in preset_names
        assert "joyful" in preset_names
        assert "neutral" in preset_names

    def test_list_presets_by_category(self):
        """Test filtering presets by category."""
        celebration_presets = list_presets(category=PresetCategory.CELEBRATION)
        assert len(celebration_presets) == 1
        assert celebration_presets[0].name == "celebration"

    def test_get_preset_by_name(self):
        """Test getting preset by name."""
        preset = get_preset_by_name("celebration")

        assert preset.name == "celebration"
        assert preset.pitch_shift == 1.15
        assert preset.tempo_shift == 1.10
        assert preset.energy_shift == 1.20

    def test_get_preset_invalid_name(self):
        """Test getting preset with invalid name."""
        with pytest.raises(ValueError, match="Preset not found"):
            get_preset_by_name("invalid_preset")

    def test_preset_parameter_validation(self):
        """Test preset parameter validation."""
        # Invalid pitch_shift
        with pytest.raises(ValueError, match="pitch_shift"):
            ProsodyPreset(
                name="invalid",
                display_name="Invalid",
                category=PresetCategory.CUSTOM,
                pitch_shift=1.50,  # Out of range
                tempo_shift=1.10,
                energy_shift=1.20,
                description="Test",
                icon="🚫"
            )

        # Invalid tempo_shift
        with pytest.raises(ValueError, match="tempo_shift"):
            ProsodyPreset(
                name="invalid",
                display_name="Invalid",
                category=PresetCategory.CUSTOM,
                pitch_shift=1.15,
                tempo_shift=1.30,  # Out of range
                energy_shift=1.20,
                description="Test",
                icon="🚫"
            )


# Test: VoicePipelineUnified Initialization
class TestPipelineInitialization:
    """Test pipeline initialization."""

    @pytest.mark.asyncio
    async def test_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline is not None
        assert pipeline._initialized is True
        assert pipeline.voice_service is not None
        assert pipeline.storage_manager is not None

        if PARSELMOUTH_AVAILABLE:
            assert pipeline.prosody_adjuster is not None

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test singleton pattern."""
        pipeline1 = await get_voice_pipeline()
        pipeline2 = await get_voice_pipeline()

        assert pipeline1 is pipeline2


# Test: Voice Synthesis with Prosody
@pytest.mark.skipif(
    not PARSELMOUTH_AVAILABLE,
    reason="Parselmouth not available"
)
class TestVoiceSynthesisWithProsody:
    """Test voice synthesis with prosody adjustment."""

    @pytest.mark.asyncio
    async def test_synthesize_with_prosody_enabled(self, pipeline):
        """Test voice synthesis with prosody adjustment."""
        result = await pipeline.synthesize_with_prosody(
            text="Happy Birthday!",
            voice_profile_id="voicevox_3",  # ずんだもん (ノーマル)
            prosody_preset="celebration",
            enable_prosody=True
        )

        assert result is not None
        assert "audio_path" in result
        assert "prosody_adjusted" in result
        assert "confidence" in result
        assert "processing_time_ms" in result

        # Check audio file exists
        audio_path = Path(result["audio_path"])
        assert audio_path.exists()

        # Check prosody metadata
        if result["prosody_adjusted"]:
            assert result["confidence"] >= 0.7
            assert "details" in result
        else:
            # Fallback to original
            assert "fallback_reason" in result

    @pytest.mark.asyncio
    async def test_synthesize_with_prosody_disabled(self, pipeline):
        """Test voice synthesis without prosody adjustment."""
        result = await pipeline.synthesize_with_prosody(
            text="Hello, this is a test.",
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )

        assert result is not None
        assert result["prosody_adjusted"] is False
        assert result["fallback_reason"] == "disabled_by_user"

    @pytest.mark.asyncio
    async def test_synthesize_with_different_presets(self, pipeline):
        """Test voice synthesis with different presets."""
        presets = ["celebration", "energetic", "joyful", "neutral"]

        for preset_name in presets:
            result = await pipeline.synthesize_with_prosody(
                text="Test message.",
                voice_profile_id="voicevox_3",
                prosody_preset=preset_name,
                enable_prosody=True
            )

            assert result is not None
            assert "audio_path" in result

    @pytest.mark.asyncio
    async def test_synthesize_with_invalid_voice_profile(self, pipeline):
        """Test synthesis with invalid voice profile."""
        with pytest.raises(RuntimeError, match="Voice synthesis failed"):
            await pipeline.synthesize_with_prosody(
                text="Test",
                voice_profile_id="invalid_profile_id",
                enable_prosody=True
            )


# Test: Parallel Processing
class TestParallelProcessing:
    """Test parallel voice synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_multiple_parallel(self, pipeline, test_texts):
        """Test parallel synthesis of multiple voices."""
        requests = [
            {
                "text": text,
                "voice_profile_id": "voicevox_3",
                "prosody_preset": "celebration",
                "enable_prosody": False  # Disable for speed
            }
            for text in test_texts[:3]  # Test with 3 requests
        ]

        start_time = time.perf_counter()
        results = await pipeline.synthesize_multiple_parallel(
            requests=requests,
            max_parallel=5
        )
        elapsed_time = time.perf_counter() - start_time

        # Check results
        assert len(results) == 3
        assert all(r["success"] for r in results)

        # Parallel should be faster than sequential
        # (Though with overhead, might not be significantly faster for small batches)
        print(f"Parallel processing time: {elapsed_time:.2f}s")

    @pytest.mark.asyncio
    async def test_parallel_with_errors(self, pipeline):
        """Test parallel processing with some requests failing."""
        requests = [
            {
                "text": "Valid request 1",
                "voice_profile_id": "voicevox_3",
                "enable_prosody": False
            },
            {
                "text": "Invalid request",
                "voice_profile_id": "invalid_profile",
                "enable_prosody": False
            },
            {
                "text": "Valid request 2",
                "voice_profile_id": "voicevox_3",
                "enable_prosody": False
            },
        ]

        results = await pipeline.synthesize_multiple_parallel(requests)

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True


# Test: Performance Benchmarks
class TestPerformanceBenchmarks:
    """Test performance benchmarks."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_benchmark_synthesis_without_prosody(self, pipeline):
        """Benchmark voice synthesis without prosody."""
        num_samples = 10

        latencies = []
        for i in range(num_samples):
            start_time = time.perf_counter()

            await pipeline.synthesize_with_prosody(
                text=f"Test message {i}",
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )

            latency = time.perf_counter() - start_time
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\nSynthesis without prosody:")
        print(f"  Average latency: {avg_latency:.2f}s")
        print(f"  P95 latency: {p95_latency:.2f}s")

        # Target: <10s
        assert avg_latency < 10.0

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    @pytest.mark.skipif(not PARSELMOUTH_AVAILABLE, reason="Parselmouth not available")
    async def test_benchmark_synthesis_with_prosody(self, pipeline):
        """Benchmark voice synthesis with prosody adjustment."""
        num_samples = 10

        latencies = []
        confidence_scores = []

        for i in range(num_samples):
            start_time = time.perf_counter()

            result = await pipeline.synthesize_with_prosody(
                text=f"Happy Birthday number {i}!",
                voice_profile_id="voicevox_3",
                prosody_preset="celebration",
                enable_prosody=True
            )

            latency = time.perf_counter() - start_time
            latencies.append(latency)

            if result["prosody_adjusted"]:
                confidence_scores.append(result["confidence"])

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        print(f"\nSynthesis with prosody:")
        print(f"  Average latency: {avg_latency:.2f}s")
        print(f"  P95 latency: {p95_latency:.2f}s")
        print(f"  Average confidence: {avg_confidence:.2f}")
        print(f"  Adjusted rate: {len(confidence_scores) / num_samples:.1%}")

        # Target: <15s
        assert avg_latency < 15.0

        # Target: Confidence ≥0.70
        if confidence_scores:
            assert avg_confidence >= 0.70


# Test: Health Check
class TestHealthCheck:
    """Test pipeline health check."""

    @pytest.mark.asyncio
    async def test_health_check(self, pipeline):
        """Test pipeline health check."""
        health = await pipeline.health_check()

        assert health is not None
        assert "pipeline" in health
        assert "services" in health

        # Check service statuses
        assert "voice" in health["services"]
        assert "prosody" in health["services"]
        assert "storage" in health["services"]

        # Overall pipeline should be healthy or degraded
        assert health["pipeline"] in ["healthy", "degraded"]


# Test: Error Handling
class TestErrorHandling:
    """Test error handling and fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_fallback_on_low_confidence(self, pipeline):
        """Test fallback to original audio on low confidence."""
        # This test requires a specific audio that would produce low confidence
        # For now, we test the logic by mocking (TODO: implement mock)
        pass

    @pytest.mark.asyncio
    async def test_fallback_on_prosody_error(self, pipeline):
        """Test fallback on prosody adjustment error."""
        # Mock prosody adjuster to raise error
        # TODO: implement mock
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
