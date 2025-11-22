# Prosody Adjustment Integration - Implementation Pseudocode

## Overview

This document describes how prosody adjustment integrates with the existing voice synthesis pipeline (OpenVoice V2 + D-ID).

---

## Current Pipeline (Without Prosody)

```
User Input (Text + Image)
    ↓
[Frontend] → [Backend API]
    ↓
[OpenVoice Native Service]
    ├─ Voice Synthesis (base audio)
    └─ Return WAV file
    ↓
[D-ID API]
    ├─ Image + Audio → Video
    └─ Return MP4 URL
    ↓
[Backend] → [Frontend]
    └─ Display video to user
```

---

## Enhanced Pipeline (With Prosody Adjustment)

```
User Input (Text + Image + "Celebration Mode" Toggle)
    ↓
[Frontend] → [Backend API]
    ├─ text: "Happy Birthday John!"
    ├─ voice_profile_id: "openvoice_c403f011"
    ├─ enable_prosody: true  # NEW PARAMETER
    └─ prosody_preset: "celebration"  # NEW PARAMETER
    ↓
[OpenVoice Native Service]
    ├─ Voice Synthesis (base audio)
    └─ Return: base_audio.wav
    ↓
[Prosody Adjustment Service] ← NEW COMPONENT
    ├─ Load base_audio.wav
    ├─ Apply adjustments:
    │   ├─ Pitch +15%
    │   ├─ Tempo +10%
    │   └─ Energy +20%
    ├─ Calculate confidence score
    ├─ Decision:
    │   ├─ Confidence ≥ 0.7 → Use adjusted audio ✅
    │   └─ Confidence < 0.7 → Fallback to base audio ⚠️
    └─ Return: adjusted_audio.wav (or base_audio.wav)
    ↓
[D-ID API]
    ├─ Image + adjusted_audio.wav → Video
    └─ Return MP4 URL
    ↓
[Backend] → [Frontend]
    └─ Display video + confidence metadata
```

---

## Detailed Implementation

### 1. Backend API Enhancement

```python
# backend/routers/unified_voice.py

class SynthesisRequestAPI(BaseModel):
    text: str
    voice_profile_id: Optional[str]
    # ... existing fields ...

    # NEW FIELDS for prosody adjustment
    enable_prosody: bool = Field(
        default=False,
        description="Enable prosody adjustment for celebratory tone"
    )
    prosody_preset: str = Field(
        default="celebration",
        description="Prosody preset: 'celebration', 'energetic', 'joyful'"
    )
    prosody_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to use adjusted audio"
    )

@router.post("/synthesize")
async def synthesize_speech(
    request: SynthesisRequestAPI,
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """音声合成実行（プロソディ調整対応）"""

    # Step 1: Generate base audio (existing flow)
    synthesis_request = VoiceSynthesisRequest(
        text=request.text,
        voice_profile=voice_profile,
        speed=request.speed,
        pitch=request.pitch,
        volume=request.volume,
        emotion=request.emotion
    )

    result = await service.synthesize_speech(synthesis_request)
    base_audio_path = result["audio_path"]

    # Step 2: Apply prosody adjustment (if enabled)
    if request.enable_prosody:
        from services.prosody_adjuster import get_default_adjuster

        adjuster = get_default_adjuster()

        try:
            adjusted_path, confidence, details = adjuster.apply(
                audio_path=base_audio_path,
                text=request.text
            )

            # Decision: Use adjusted audio if confidence is high enough
            if confidence >= request.prosody_confidence_threshold:
                result["audio_path"] = adjusted_path
                result["prosody_adjusted"] = True
                result["prosody_confidence"] = confidence
                result["prosody_details"] = details
                logger.info(
                    f"Prosody adjustment applied successfully "
                    f"(confidence={confidence:.2f})"
                )
            else:
                result["prosody_adjusted"] = False
                result["prosody_confidence"] = confidence
                result["prosody_fallback_reason"] = (
                    f"Confidence too low ({confidence:.2f} < "
                    f"{request.prosody_confidence_threshold})"
                )
                logger.warning(
                    f"Prosody adjustment skipped: confidence {confidence:.2f} "
                    f"below threshold {request.prosody_confidence_threshold}"
                )

        except Exception as e:
            # Fallback: Use base audio if prosody adjustment fails
            result["prosody_adjusted"] = False
            result["prosody_error"] = str(e)
            logger.error(f"Prosody adjustment failed: {e}")

    else:
        result["prosody_adjusted"] = False

    return result
```

---

### 2. Frontend UI Enhancement

```typescript
// frontend/src/components/VoiceSelector.tsx

interface VoiceSynthesisOptions {
  text: string;
  voiceProfileId: string;
  // ... existing fields ...

  // NEW FIELDS
  enableProsody: boolean;
  prosodyPreset: 'celebration' | 'energetic' | 'joyful';
}

const VoiceSelector: React.FC = () => {
  const [enableProsody, setEnableProsody] = useState(false);
  const [prosodyPreset, setProsodyPreset] = useState<string>('celebration');

  return (
    <div>
      {/* Existing voice selection UI */}

      {/* NEW: Prosody Adjustment Toggle */}
      <div className="prosody-control">
        <label>
          <input
            type="checkbox"
            checked={enableProsody}
            onChange={(e) => setEnableProsody(e.target.checked)}
          />
          Enable Celebratory Tone 🎉
        </label>

        {enableProsody && (
          <select
            value={prosodyPreset}
            onChange={(e) => setProsodyPreset(e.target.value)}
          >
            <option value="celebration">Celebration 🎊</option>
            <option value="energetic">Energetic ⚡</option>
            <option value="joyful">Joyful 😊</option>
          </select>
        )}
      </div>

      <button onClick={handleSynthesize}>Generate Video</button>
    </div>
  );

  const handleSynthesize = async () => {
    const response = await fetch('/api/unified-voice/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: inputText,
        voice_profile_id: selectedVoiceId,
        enable_prosody: enableProsody,
        prosody_preset: prosodyPreset,
        prosody_confidence_threshold: 0.7
      })
    });

    const result = await response.json();

    // Display prosody adjustment status
    if (result.prosody_adjusted) {
      showToast(
        `✅ Celebratory tone applied (confidence: ${result.prosody_confidence.toFixed(2)})`,
        'success'
      );
    } else if (enableProsody) {
      showToast(
        `⚠️ Using original voice (${result.prosody_fallback_reason})`,
        'warning'
      );
    }
  };
};
```

---

### 3. Prosody Preset Configuration

```python
# backend/services/prosody_adjuster.py

PROSODY_PRESETS = {
    "celebration": {
        "pitch_shift": 1.15,   # +15% (joyful)
        "tempo_shift": 1.10,   # +10% faster (energetic)
        "energy_shift": 1.20,  # +20% louder (emphatic)
        "enable_pauses": False # Disabled (requires forced alignment)
    },

    "energetic": {
        "pitch_shift": 1.10,   # +10% (moderate pitch increase)
        "tempo_shift": 1.15,   # +15% faster (very energetic)
        "energy_shift": 1.25,  # +25% louder (high emphasis)
        "enable_pauses": False
    },

    "joyful": {
        "pitch_shift": 1.20,   # +20% (very joyful, higher risk)
        "tempo_shift": 1.05,   # +5% faster (gentle energy)
        "energy_shift": 1.15,  # +15% louder (moderate emphasis)
        "enable_pauses": False
    },

    "neutral": {
        "pitch_shift": 1.00,   # No change
        "tempo_shift": 1.00,   # No change
        "energy_shift": 1.00,  # No change
        "enable_pauses": False
    }
}

def get_adjuster_for_preset(preset_name: str) -> ProsodyAdjuster:
    """Factory function to create ProsodyAdjuster with preset parameters."""

    if preset_name not in PROSODY_PRESETS:
        logger.warning(f"Unknown preset '{preset_name}', using 'celebration'")
        preset_name = "celebration"

    params = PROSODY_PRESETS[preset_name]

    return ProsodyAdjuster(
        pitch_shift=params["pitch_shift"],
        tempo_shift=params["tempo_shift"],
        energy_shift=params["energy_shift"],
        enable_pauses=params["enable_pauses"]
    )
```

---

### 4. Error Handling & Fallback Logic

```python
# backend/services/prosody_adjuster.py

class ProsodyAdjustmentError(Exception):
    """Custom exception for prosody adjustment failures."""
    pass

def apply_prosody_with_fallback(
    base_audio_path: str,
    text: str,
    preset: str = "celebration",
    confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Apply prosody adjustment with automatic fallback.

    Returns:
        {
            "success": bool,
            "audio_path": str,  # Adjusted or base audio
            "adjusted": bool,
            "confidence": float,
            "details": dict,
            "fallback_reason": str (optional)
        }
    """
    result = {
        "success": False,
        "audio_path": base_audio_path,
        "adjusted": False,
        "confidence": 0.0,
        "details": {}
    }

    try:
        # Step 1: Create adjuster with preset
        adjuster = get_adjuster_for_preset(preset)

        # Step 2: Apply adjustments
        adjusted_path, confidence, details = adjuster.apply(
            audio_path=base_audio_path,
            text=text
        )

        result["details"] = details
        result["confidence"] = confidence

        # Step 3: Decision logic
        if confidence >= confidence_threshold:
            # Use adjusted audio
            result["success"] = True
            result["audio_path"] = adjusted_path
            result["adjusted"] = True
            logger.info(
                f"Prosody adjustment successful: "
                f"confidence={confidence:.2f} >= {confidence_threshold}"
            )

        else:
            # Fallback: Use base audio
            result["success"] = True
            result["audio_path"] = base_audio_path
            result["adjusted"] = False
            result["fallback_reason"] = (
                f"Confidence {confidence:.2f} below threshold {confidence_threshold}"
            )
            logger.warning(result["fallback_reason"])

    except ImportError as e:
        # Parselmouth not installed
        result["success"] = True  # Not an error, just feature unavailable
        result["audio_path"] = base_audio_path
        result["adjusted"] = False
        result["fallback_reason"] = f"Prosody adjustment not available: {e}"
        logger.warning(result["fallback_reason"])

    except Exception as e:
        # Unexpected error
        result["success"] = True  # Fallback to base audio
        result["audio_path"] = base_audio_path
        result["adjusted"] = False
        result["fallback_reason"] = f"Prosody adjustment failed: {e}"
        logger.error(result["fallback_reason"], exc_info=True)

    return result
```

---

### 5. Logging & Monitoring

```python
# backend/services/prosody_adjuster.py

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProsodyMetrics:
    """Track prosody adjustment performance metrics."""

    def __init__(self):
        self.total_requests = 0
        self.successful_adjustments = 0
        self.fallbacks = 0
        self.errors = 0
        self.average_latency = 0.0
        self.latencies = []

    def record_request(
        self,
        success: bool,
        adjusted: bool,
        latency_ms: float,
        confidence: float
    ):
        self.total_requests += 1

        if success and adjusted:
            self.successful_adjustments += 1
        elif success and not adjusted:
            self.fallbacks += 1
        else:
            self.errors += 1

        self.latencies.append(latency_ms)
        self.average_latency = sum(self.latencies) / len(self.latencies)

        logger.info(
            f"Prosody Metrics: "
            f"requests={self.total_requests}, "
            f"adjusted={self.successful_adjustments}, "
            f"fallbacks={self.fallbacks}, "
            f"errors={self.errors}, "
            f"avg_latency={self.average_latency:.1f}ms, "
            f"confidence={confidence:.2f}"
        )

    def get_summary(self) -> Dict[str, Any]:
        if self.total_requests == 0:
            return {"message": "No prosody adjustments performed yet"}

        return {
            "total_requests": self.total_requests,
            "successful_adjustments": self.successful_adjustments,
            "success_rate": self.successful_adjustments / self.total_requests,
            "fallback_rate": self.fallbacks / self.total_requests,
            "error_rate": self.errors / self.total_requests,
            "average_latency_ms": self.average_latency,
            "p95_latency_ms": sorted(self.latencies)[int(len(self.latencies) * 0.95)]
        }

# Global metrics instance
_prosody_metrics = ProsodyMetrics()

def get_prosody_metrics() -> ProsodyMetrics:
    return _prosody_metrics


# Instrumented apply function
def apply_prosody_with_metrics(
    base_audio_path: str,
    text: str,
    preset: str = "celebration",
    confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """Apply prosody with automatic metrics tracking."""

    start_time = time.perf_counter()

    result = apply_prosody_with_fallback(
        base_audio_path=base_audio_path,
        text=text,
        preset=preset,
        confidence_threshold=confidence_threshold
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    _prosody_metrics.record_request(
        success=result["success"],
        adjusted=result["adjusted"],
        latency_ms=latency_ms,
        confidence=result["confidence"]
    )

    return result
```

---

## Testing Strategy

### Unit Tests

```python
# backend/tests/test_prosody_adjuster.py

import pytest
from services.prosody_adjuster import ProsodyAdjuster
import parselmouth

def test_pitch_adjustment():
    """Test pitch shift increases F0 by expected amount."""
    adjuster = ProsodyAdjuster(pitch_shift=1.15, tempo_shift=1.0, energy_shift=1.0)

    # Create test audio (sine wave at 100 Hz)
    sound = parselmouth.Sound.create_tone(frequency=100, duration=1.0)

    adjusted = adjuster.adjust_pitch(sound, 1.15)

    # Verify pitch increased
    original_pitch = parselmouth.praat.call(sound, "To Pitch", 0.01, 75, 600)
    adjusted_pitch = parselmouth.praat.call(adjusted, "To Pitch", 0.01, 75, 600)

    original_f0 = parselmouth.praat.call(original_pitch, "Get mean", 0, 0, "Hertz")
    adjusted_f0 = parselmouth.praat.call(adjusted_pitch, "Get mean", 0, 0, "Hertz")

    assert adjusted_f0 / original_f0 == pytest.approx(1.15, abs=0.02)

def test_confidence_calculation():
    """Test confidence scoring correctly identifies unnatural adjustments."""
    adjuster = ProsodyAdjuster(pitch_shift=1.15, tempo_shift=1.10, energy_shift=1.20)

    # Normal adjustment (should pass)
    sound = parselmouth.Sound.create_tone(frequency=100, duration=1.0)
    adjusted = adjuster.adjust_pitch(sound, 1.15)

    confidence, details = adjuster.calculate_confidence(sound, adjusted)
    assert confidence >= 0.7
    assert details['pitch_check'] == 'PASS'

    # Extreme adjustment (should fail)
    extreme_adjusted = adjuster.adjust_pitch(sound, 1.50)  # 50% increase
    confidence_fail, details_fail = adjuster.calculate_confidence(sound, extreme_adjusted)
    assert confidence_fail < 0.5
    assert 'FAIL' in details_fail['pitch_check']
```

### Integration Tests

```python
# backend/tests/test_prosody_integration.py

import pytest
from services.unified_voice_service import UnifiedVoiceService
from services.prosody_adjuster import apply_prosody_with_fallback

@pytest.mark.asyncio
async def test_end_to_end_prosody_adjustment(tmp_path):
    """Test complete pipeline: synthesis → prosody → D-ID."""

    # Step 1: Synthesize base audio
    service = UnifiedVoiceService()
    result = await service.synthesize_speech(
        text="Happy Birthday John!",
        voice_profile_id="openvoice_c403f011"
    )

    base_audio = result["audio_path"]
    assert Path(base_audio).exists()

    # Step 2: Apply prosody adjustment
    prosody_result = apply_prosody_with_fallback(
        base_audio_path=base_audio,
        text="Happy Birthday John!",
        preset="celebration",
        confidence_threshold=0.7
    )

    assert prosody_result["success"]
    assert Path(prosody_result["audio_path"]).exists()

    # Step 3: Verify adjustment (if applied)
    if prosody_result["adjusted"]:
        assert prosody_result["confidence"] >= 0.7
        assert prosody_result["details"]["pitch_check"] == 'PASS'
```

---

## Deployment Checklist

### Prerequisites

1. **Install Parselmouth** (Mac & EC2):
   ```bash
   # Mac
   pip install praat-parselmouth==0.4.3

   # EC2
   pip install numpy==1.26.4
   pip install praat-parselmouth==0.4.3
   ```

2. **Update requirements.txt**:
   ```txt
   praat-parselmouth==0.4.3
   ```

3. **Run tests**:
   ```bash
   pytest backend/tests/test_prosody_adjuster.py -v
   pytest backend/tests/test_prosody_integration.py -v
   ```

### Deployment Steps

1. **Local Development**:
   ```bash
   cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
   docker-compose down
   docker-compose build backend  # Rebuild with new dependencies
   docker-compose up -d
   ```

2. **EC2 Production**:
   ```bash
   ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
   cd ~/video-message-app/video-message-app

   # Update backend dependencies
   cd backend
   source venv/bin/activate
   pip install praat-parselmouth==0.4.3

   # Restart services
   docker-compose restart backend
   ```

3. **Verify Deployment**:
   ```bash
   # Health check
   curl http://localhost:55433/health | jq

   # Test prosody endpoint
   curl -X POST http://localhost:55433/api/unified-voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Happy Birthday!",
       "voice_profile_id": "openvoice_c403f011",
       "enable_prosody": true,
       "prosody_preset": "celebration"
     }' | jq
   ```

---

## Performance Benchmarks (Expected)

| Metric | Target | Measured (TBD) |
|--------|--------|----------------|
| Prosody adjustment latency | <500ms | ___ ms |
| Confidence calculation | <100ms | ___ ms |
| Total pipeline overhead | <600ms | ___ ms |
| Success rate | ≥80% | ___% |
| Fallback rate | ≤20% | ___% |

---

## Rollout Plan

### Phase 1: Internal Testing (Week 1)
- Deploy to development environment
- Test with 10 sample texts (celebration-themed)
- Measure performance metrics
- Fix critical bugs

### Phase 2: Limited Beta (Week 2)
- Enable for 5 internal users
- Collect qualitative feedback
- A/B test: Prosody ON vs. OFF
- Measure user preference (target: ≥70%)

### Phase 3: Public Release (Week 3)
- Enable prosody toggle in production UI
- Default: OFF (opt-in feature)
- Monitor error rates and fallbacks
- Collect user feedback via in-app survey

### Phase 4: Optimization (Week 4+)
- Tune parameters based on user feedback
- Implement forced alignment for pause insertion
- Add more prosody presets (e.g., "Romantic", "Motivational")
- Consider ML-based confidence scoring

---

## Future Enhancements

1. **Forced Alignment for Pause Insertion**:
   - Integrate Montreal Forced Aligner (MFA)
   - Map text to audio timestamps precisely
   - Insert dynamic pauses after exclamations

2. **ML-Based Confidence Scoring**:
   - Train classifier to predict naturalness
   - Features: spectral flatness, pitch jitter, shimmer
   - Replace rule-based confidence with ML model

3. **User-Adjustable Parameters**:
   - UI sliders for pitch/tempo/energy
   - Real-time preview of adjustments
   - Save custom presets per user

4. **Emotion-Specific Prosody**:
   - Extend beyond "celebration" to other emotions
   - "Sympathy" (lower pitch, slower tempo)
   - "Excitement" (higher pitch, faster tempo)
   - "Calm" (lower energy, slower tempo)

---

## References

[1] Scherer, K. R. (2003). Vocal communication of emotion. *Speech Communication*, 40(1-2), 227-256.

[2] Banse, R., & Scherer, K. R. (1996). Acoustic profiles in vocal emotion expression. *Journal of Personality and Social Psychology*, 70(3), 614.

[3] Laver, J. (1994). *Principles of phonetics*. Cambridge University Press.

[4] Bänziger, T., & Scherer, K. R. (2005). The role of intonation in emotional expressions. *Speech Communication*, 46(3-4), 252-267.

[5] Goldman-Eisler, F. (1968). *Psycholinguistics: Experiments in spontaneous speech*. Academic Press.
