# Prosody Adjustment - Troubleshooting Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Audience**: Developers, System Administrators

---

## Table of Contents

1. [Common Errors](#common-errors)
2. [Audio Quality Issues](#audio-quality-issues)
3. [Performance Problems](#performance-problems)
4. [Integration Issues](#integration-issues)
5. [FAQ](#faq)
6. [Diagnostic Tools](#diagnostic-tools)

---

## 1. Common Errors

### Error 1.1: Parselmouth Not Available

#### Symptoms

```python
ImportError: No module named 'parselmouth'
```

または

```
RuntimeError: Parselmouth is not installed. Install with: pip install praat-parselmouth==0.4.3
```

#### Cause

Praat-Parselmouth ライブラリがインストールされていない。

#### Solution

```bash
# Install praat-parselmouth
pip install praat-parselmouth==0.4.3

# Verify installation
python -c "import parselmouth; print(parselmouth.__version__)"
# Expected output: 0.4.3
```

#### Verification

```python
from services.prosody_adjuster import PARSELMOUTH_AVAILABLE

print(f"Parselmouth available: {PARSELMOUTH_AVAILABLE}")
# Expected: True
```

---

### Error 1.2: Invalid Parameter Range

#### Symptoms

```python
ValueError: pitch_shift must be in [0.90, 1.25], got 1.50
```

#### Cause

Adjustment parameters outside safe ranges.

#### Solution

Use parameters within the following safe ranges:

| Parameter | Minimum | Maximum | Recommended |
|-----------|---------|---------|-------------|
| `pitch_shift` | 0.90 | 1.25 | 0.95-1.20 |
| `tempo_shift` | 0.95 | 1.15 | 0.98-1.12 |
| `energy_shift` | 1.00 | 1.30 | 1.05-1.25 |

**Example Fix**:

```python
# ❌ WRONG: Out of range
adjuster = ProsodyAdjuster(pitch_shift=1.50)  # ValueError

# ✅ CORRECT: Within range
adjuster = ProsodyAdjuster(pitch_shift=1.20)  # OK
```

---

### Error 1.3: Audio File Not Found

#### Symptoms

```python
FileNotFoundError: Audio file not found: speech.wav
```

#### Cause

The specified audio file path does not exist or is incorrect.

#### Solution

1. **Check file path**:
   ```python
   from pathlib import Path

   audio_path = "speech.wav"
   if not Path(audio_path).exists():
       print(f"File not found: {audio_path}")
       print(f"Current directory: {Path.cwd()}")
   ```

2. **Use absolute path**:
   ```python
   from pathlib import Path

   # Convert to absolute path
   audio_path = Path("speech.wav").resolve()
   print(f"Using: {audio_path}")
   ```

3. **Check permissions**:
   ```bash
   ls -l speech.wav
   # Ensure file is readable (-r-- at minimum)
   ```

---

### Error 1.4: Unsupported Audio Format

#### Symptoms

```python
RuntimeError: Failed to load audio: [Errno 2] No such file or directory
```

または

```
parselmouth.PraatError: Unable to open file
```

#### Cause

Audio file is not in WAV format or is corrupted.

#### Solution

1. **Convert to WAV**:
   ```bash
   # Using FFmpeg
   ffmpeg -i input.mp3 -ar 22050 -ac 1 -sample_fmt s16 output.wav
   ```

2. **Check audio format**:
   ```python
   import parselmouth

   try:
       sound = parselmouth.Sound("audio.wav")
       print(f"Sample rate: {sound.sampling_frequency} Hz")
       print(f"Duration: {sound.duration:.2f} seconds")
       print(f"Channels: {sound.n_channels}")
   except Exception as e:
       print(f"Invalid audio format: {e}")
   ```

3. **Supported formats**:
   - ✅ WAV (PCM)
   - ❌ MP3 (convert first)
   - ❌ AAC (convert first)
   - ❌ FLAC (convert first)

---

### Error 1.5: Memory Error

#### Symptoms

```python
MemoryError: Unable to allocate array
```

または

```
numpy.core._exceptions._ArrayMemoryError: Unable to allocate array
```

#### Cause

Audio file too large or system memory insufficient.

#### Solution

1. **Check file size**:
   ```python
   from pathlib import Path

   audio_path = Path("speech.wav")
   file_size_mb = audio_path.stat().st_size / (1024 * 1024)
   print(f"File size: {file_size_mb:.1f} MB")

   # Recommended: < 50 MB
   # Maximum: 100 MB
   ```

2. **Compress audio**:
   ```bash
   # Reduce sample rate
   ffmpeg -i input.wav -ar 22050 output.wav

   # Convert to mono
   ffmpeg -i input.wav -ac 1 output.wav

   # Combine (mono + 22kHz)
   ffmpeg -i input.wav -ar 22050 -ac 1 output.wav
   ```

3. **Split long audio**:
   ```python
   import parselmouth

   sound = parselmouth.Sound("long_audio.wav")
   duration = sound.duration

   # Split into 30-second chunks
   chunk_duration = 30.0
   chunks = []

   for i, start in enumerate(range(0, int(duration), int(chunk_duration))):
       end = min(start + chunk_duration, duration)
       chunk = sound.extract_part(start, end)
       chunk_path = f"chunk_{i}.wav"
       chunk.save(chunk_path, "WAV")
       chunks.append(chunk_path)

   print(f"Split into {len(chunks)} chunks")
   ```

---

## 2. Audio Quality Issues

### Issue 2.1: Unnatural-Sounding Voice

#### Symptoms

Adjusted audio sounds robotic, unnatural, or distorted.

#### Cause

Excessive parameter adjustments or poor source audio quality.

#### Solution

1. **Reduce adjustment magnitude**:
   ```python
   # ❌ TOO EXTREME
   adjuster = ProsodyAdjuster(
       pitch_shift=1.25,  # +25% (too much)
       tempo_shift=1.15,  # +15% (too fast)
       energy_shift=1.30  # +30% (too loud)
   )

   # ✅ MODERATE (more natural)
   adjuster = ProsodyAdjuster(
       pitch_shift=1.10,  # +10%
       tempo_shift=1.05,  # +5%
       energy_shift=1.15  # +15%
   )
   ```

2. **Check confidence score**:
   ```python
   adjusted_path, confidence, details = adjuster.apply(audio_path, text)

   print(f"Confidence: {confidence:.2f}")

   if confidence < 0.70:
       print("⚠️ Low confidence - audio may sound unnatural")
       print("Details:", details)
   ```

3. **Use presets**:
   ```python
   # Presets are tuned for natural-sounding results
   adjuster = get_adjuster_from_preset("friendly")  # More natural
   ```

4. **Improve source audio**:
   - Use high-quality voice synthesis (OpenVoice > VOICEVOX for naturalness)
   - Ensure low background noise
   - Avoid pre-processing effects (reverb, echo, etc.)

---

### Issue 2.2: Audio Clipping (Distortion)

#### Symptoms

Loud popping or crackling sounds in adjusted audio.

#### Cause

Energy adjustment causes amplitude to exceed maximum value (> 1.0).

#### Solution

**Automatic Normalization** (already implemented):

```python
def adjust_energy(sound, energy_shift):
    # Scale amplitude
    adjusted_sound = sound * energy_shift

    # Normalize to prevent clipping
    max_amplitude = call(adjusted_sound, "Get maximum", 0, 0, "None")

    if max_amplitude > 0.95:
        normalization_factor = 0.95 / max_amplitude
        adjusted_sound = adjusted_sound * normalization_factor
        logger.warning(f"Energy normalized: {max_amplitude:.3f} → 0.95")

    return adjusted_sound
```

**Manual Check**:

```python
import parselmouth

sound = parselmouth.Sound("adjusted_audio.wav")
max_amplitude = sound.values.max()

print(f"Max amplitude: {max_amplitude:.3f}")

if max_amplitude > 0.99:
    print("⚠️ Clipping detected!")
else:
    print("✅ No clipping")
```

**If clipping occurs**:

1. Reduce `energy_shift`:
   ```python
   adjuster = ProsodyAdjuster(energy_shift=1.10)  # Lower value
   ```

2. Post-process with normalization:
   ```bash
   ffmpeg -i clipped_audio.wav -af "loudnorm" normalized_audio.wav
   ```

---

### Issue 2.3: Pitch Sounds Too High/Low

#### Symptoms

Voice sounds like a chipmunk (too high) or unnaturally deep (too low).

#### Cause

Excessive pitch adjustment.

#### Solution

1. **Check pitch_shift value**:
   ```python
   # For natural-sounding adjustments:
   # +10% to +15%: Brighter, more joyful
   # -5% to -10%: Deeper, more serious

   # ❌ TOO HIGH
   adjuster = ProsodyAdjuster(pitch_shift=1.30)  # Chipmunk effect

   # ✅ NATURAL
   adjuster = ProsodyAdjuster(pitch_shift=1.15)  # Bright, joyful
   ```

2. **Analyze pitch before/after**:
   ```python
   import parselmouth

   def analyze_pitch(audio_path):
       sound = parselmouth.Sound(audio_path)
       pitch = sound.to_pitch()
       mean_f0 = parselmouth.praat.call(pitch, "Get mean", 0, 0, "Hertz")
       return mean_f0

   original_f0 = analyze_pitch("original.wav")
   adjusted_f0 = analyze_pitch("adjusted.wav")

   pitch_change = (adjusted_f0 / original_f0 - 1) * 100

   print(f"Original pitch: {original_f0:.1f} Hz")
   print(f"Adjusted pitch: {adjusted_f0:.1f} Hz")
   print(f"Change: {pitch_change:+.1f}%")
   ```

3. **Recommended ranges by use case**:

   | Use Case | pitch_shift | F0 Change |
   |----------|-------------|-----------|
   | Celebration | 1.10-1.15 | +10% to +15% |
   | Professional | 0.98-1.02 | -2% to +2% |
   | Calm/Soothing | 0.95-1.00 | -5% to 0% |
   | Dramatic | 1.08-1.12 | +8% to +12% |

---

### Issue 2.4: Speech Too Fast/Slow

#### Symptoms

Adjusted audio is too rushed or unnaturally slow.

#### Cause

Excessive tempo adjustment.

#### Solution

1. **Check tempo_shift value**:
   ```python
   # For natural-sounding adjustments:
   # +5% to +10%: Energetic, engaging
   # -5% to -10%: Careful, clear

   # ❌ TOO FAST
   adjuster = ProsodyAdjuster(tempo_shift=1.20)  # Rushed

   # ✅ NATURAL
   adjuster = ProsodyAdjuster(tempo_shift=1.08)  # Energetic
   ```

2. **Calculate duration change**:
   ```python
   import parselmouth

   original = parselmouth.Sound("original.wav")
   adjusted = parselmouth.Sound("adjusted.wav")

   duration_change = (adjusted.duration / original.duration - 1) * 100

   print(f"Original duration: {original.duration:.2f}s")
   print(f"Adjusted duration: {adjusted.duration:.2f}s")
   print(f"Change: {duration_change:+.1f}%")
   ```

3. **Recommended ranges**:

   | Use Case | tempo_shift | Duration Change |
   |----------|-------------|-----------------|
   | Energetic | 1.05-1.10 | -9% to -5% |
   | Professional | 0.95-1.00 | 0% to +5% |
   | Calm | 0.90-0.95 | +5% to +11% |

---

## 3. Performance Problems

### Issue 3.1: Slow Processing

#### Symptoms

Prosody adjustment takes longer than expected.

#### Cause

Large audio files, inefficient processing, or resource constraints.

#### Solution

1. **Benchmark performance**:
   ```python
   import time
   from services.prosody_adjuster import ProsodyAdjuster

   adjuster = ProsodyAdjuster()

   start_time = time.time()
   adjusted_path, confidence, details = adjuster.apply("audio.wav", "Text")
   end_time = time.time()

   processing_time = end_time - start_time
   print(f"Processing time: {processing_time:.2f}s")

   # Get audio duration
   import parselmouth
   sound = parselmouth.Sound("audio.wav")
   audio_duration = sound.duration

   real_time_factor = processing_time / audio_duration
   print(f"Real-time factor: {real_time_factor:.2f}x")

   # Good performance: < 0.5x (2x faster than real-time)
   # Acceptable: 0.5-1.0x
   # Slow: > 1.0x
   ```

2. **Optimize audio**:
   ```bash
   # Reduce sample rate to 22kHz
   ffmpeg -i input.wav -ar 22050 output.wav

   # Convert to mono
   ffmpeg -i input.wav -ac 1 output.wav
   ```

3. **Use batch processing**:
   ```python
   from concurrent.futures import ThreadPoolExecutor

   def process_batch(audio_files, max_workers=4):
       adjuster = ProsodyAdjuster()

       def process_single(audio_file):
           return adjuster.apply(audio_file, "Text")

       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           results = list(executor.map(process_single, audio_files))

       return results
   ```

4. **Use caching**:
   ```python
   from functools import lru_cache
   import hashlib

   @lru_cache(maxsize=100)
   def adjust_cached(audio_hash, preset):
       # Check cache first
       cache_path = f"/cache/{audio_hash}_{preset}.wav"
       if Path(cache_path).exists():
           return cache_path

       # Process and cache
       adjuster = get_adjuster_from_preset(preset)
       result = adjuster.apply(audio_path, text, output_path=cache_path)
       return result[0]
   ```

---

### Issue 3.2: High Memory Usage

#### Symptoms

System runs out of memory during processing.

#### Cause

Large audio files loaded into memory.

#### Solution

1. **Monitor memory usage**:
   ```python
   import psutil
   import os

   process = psutil.Process(os.getpid())

   print(f"Memory before: {process.memory_info().rss / 1024 / 1024:.1f} MB")

   # Process audio
   adjuster = ProsodyAdjuster()
   result = adjuster.apply("audio.wav", "Text")

   print(f"Memory after: {process.memory_info().rss / 1024 / 1024:.1f} MB")
   ```

2. **Split large files**:
   ```python
   def process_large_file(audio_path, chunk_duration=30):
       """Process large audio file in chunks."""
       import parselmouth

       sound = parselmouth.Sound(audio_path)
       total_duration = sound.duration

       adjusted_chunks = []

       for start in range(0, int(total_duration), chunk_duration):
           end = min(start + chunk_duration, total_duration)

           # Extract chunk
           chunk = sound.extract_part(start, end)
           chunk_path = f"/tmp/chunk_{start}.wav"
           chunk.save(chunk_path, "WAV")

           # Adjust chunk
           adjuster = ProsodyAdjuster()
           adjusted_chunk_path, _, _ = adjuster.apply(chunk_path, "Text")
           adjusted_chunks.append(adjusted_chunk_path)

       # Concatenate chunks
       return concatenate_audio(adjusted_chunks)
   ```

3. **Cleanup temporary files**:
   ```python
   from pathlib import Path

   def cleanup_temp_files(temp_dir="/tmp"):
       """Remove temporary prosody files."""
       temp_path = Path(temp_dir)

       for file in temp_path.glob("prosody_*.wav"):
           file.unlink()
           print(f"Deleted: {file}")
   ```

---

## 4. Integration Issues

### Issue 4.1: VOICEVOX Integration Fails

#### Symptoms

```python
requests.exceptions.ConnectionError: Connection refused
```

#### Cause

VOICEVOX engine not running or wrong port.

#### Solution

1. **Check VOICEVOX service**:
   ```bash
   # Docker
   docker ps | grep voicevox

   # Expected output:
   # voicevox_engine  voicevox/voicevox_engine:cpu-latest  0.0.0.0:50021->50021/tcp
   ```

2. **Start VOICEVOX**:
   ```bash
   docker-compose up -d voicevox
   ```

3. **Test connection**:
   ```bash
   curl http://localhost:50021/version
   # Expected: {"version": "0.14.5"}
   ```

4. **Full integration test**:
   ```python
   import requests

   def test_voicevox_prosody_integration():
       # Step 1: Check VOICEVOX
       try:
           response = requests.get("http://localhost:50021/version")
           print(f"✅ VOICEVOX: {response.json()['version']}")
       except Exception as e:
           print(f"❌ VOICEVOX error: {e}")
           return

       # Step 2: Synthesize
       query_response = requests.post(
           "http://localhost:50021/audio_query",
           params={"text": "テスト", "speaker": 3}
       )

       synthesis_response = requests.post(
           "http://localhost:50021/synthesis",
           params={"speaker": 3},
           json=query_response.json()
       )

       # Save audio
       with open("/tmp/voicevox_test.wav", "wb") as f:
           f.write(synthesis_response.content)

       print("✅ VOICEVOX synthesis complete")

       # Step 3: Apply prosody
       from services.prosody_adjuster import ProsodyAdjuster

       adjuster = ProsodyAdjuster()
       result = adjuster.apply("/tmp/voicevox_test.wav", "テスト")

       print(f"✅ Prosody adjustment complete (confidence: {result[1]:.2f})")

   test_voicevox_prosody_integration()
   ```

---

### Issue 4.2: OpenVoice Integration Fails

#### Symptoms

```python
requests.exceptions.ConnectionError: Connection to http://localhost:8001 failed
```

#### Cause

OpenVoice Native Service not running.

#### Solution

1. **Check OpenVoice service**:
   ```bash
   # Check process
   ps aux | grep "python main.py"

   # Check port
   lsof -i :8001
   ```

2. **Start OpenVoice service**:
   ```bash
   # Mac (Conda environment)
   cd openvoice_native
   conda activate openvoice_v2
   python main.py

   # EC2 (venv)
   cd /home/ec2-user/video-message-app/video-message-app/openvoice_native
   source venv_py311/bin/activate
   python main.py
   ```

3. **Test connection**:
   ```bash
   curl http://localhost:8001/health
   # Expected: {"status": "healthy", ...}
   ```

4. **Check logs**:
   ```bash
   # Mac
   tail -f openvoice_native/openvoice.log

   # EC2
   tail -f /home/ec2-user/video-message-app/video-message-app/openvoice_native/openvoice.log
   ```

---

### Issue 4.3: D-ID Video Generation Fails After Prosody

#### Symptoms

D-ID API rejects adjusted audio or video looks unnatural.

#### Cause

Adjusted audio doesn't meet D-ID requirements or is too distorted.

#### Solution

1. **Check audio format**:
   ```python
   import parselmouth

   sound = parselmouth.Sound("adjusted_audio.wav")

   print(f"Sample rate: {sound.sampling_frequency} Hz")
   print(f"Duration: {sound.duration:.2f}s")
   print(f"Channels: {sound.n_channels}")

   # D-ID requirements:
   # - Sample rate: 16kHz, 22.05kHz, 44.1kHz, or 48kHz
   # - Channels: Mono or Stereo
   # - Duration: < 5 minutes
   ```

2. **Convert to D-ID format**:
   ```bash
   ffmpeg -i adjusted_audio.wav -ar 16000 -ac 1 d_id_audio.wav
   ```

3. **Verify audio quality**:
   ```python
   adjusted_path, confidence, details = adjuster.apply(audio_path, text)

   if confidence < 0.70:
       print("⚠️ Low confidence - D-ID may reject audio")
       print("Consider using milder adjustments")
   ```

4. **Use milder adjustments for D-ID**:
   ```python
   # Recommended for D-ID integration
   adjuster = ProsodyAdjuster(
       pitch_shift=1.10,  # +10% (moderate)
       tempo_shift=1.05,  # +5% (mild)
       energy_shift=1.15  # +15% (moderate)
   )
   ```

---

## 5. FAQ

### Q5.1: What's the best preset for birthday messages?

**A**: Use `celebration` preset:

```python
adjuster = get_adjuster_from_preset("celebration")
# pitch_shift=1.15, tempo_shift=1.10, energy_shift=1.20
```

This provides a joyful, energetic tone perfect for birthdays.

---

### Q5.2: Can I adjust audio multiple times?

**A**: Yes, but quality degrades with each adjustment.

```python
# ❌ NOT RECOMMENDED: Multiple adjustments
adjuster1 = ProsodyAdjuster(pitch_shift=1.10)
result1 = adjuster1.apply("audio.wav", "Text")

adjuster2 = ProsodyAdjuster(energy_shift=1.20)
result2 = adjuster2.apply(result1[0], "Text")  # Quality loss!

# ✅ RECOMMENDED: Single adjustment with combined parameters
adjuster = ProsodyAdjuster(pitch_shift=1.10, energy_shift=1.20)
result = adjuster.apply("audio.wav", "Text")
```

---

### Q5.3: How do I know if adjustments are too extreme?

**A**: Check the confidence score:

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| 0.90-1.00 | Excellent | Adjustments are safe |
| 0.70-0.89 | Good | Acceptable quality |
| 0.50-0.69 | Fair | Consider reducing adjustments |
| 0.00-0.49 | Poor | Reduce adjustments significantly |

```python
adjusted_path, confidence, details = adjuster.apply(audio_path, text)

if confidence < 0.70:
    print("⚠️ Adjustments may be too extreme")
    print(f"Details: {details}")
```

---

### Q5.4: Can I use Prosody on non-Japanese audio?

**A**: Yes, Prosody works on any language.

```python
# English
adjuster = ProsodyAdjuster()
result = adjuster.apply("english_speech.wav", "Hello, world!")

# Chinese
result = adjuster.apply("chinese_speech.wav", "你好世界")

# Spanish
result = adjuster.apply("spanish_speech.wav", "¡Hola, mundo!")
```

The PSOLA algorithm is language-independent.

---

### Q5.5: What audio sample rate should I use?

**A**: Recommended: 22.05 kHz or 44.1 kHz

| Sample Rate | Use Case | Quality | File Size |
|-------------|----------|---------|-----------|
| 16 kHz | Phone quality | Low | Small |
| 22.05 kHz | Standard synthesis | Good | Medium ✅ |
| 44.1 kHz | CD quality | Excellent | Large |
| 48 kHz | Professional | Excellent | Large |

```bash
# Convert to 22.05 kHz (recommended)
ffmpeg -i input.wav -ar 22050 output.wav
```

---

### Q5.6: Can I adjust pitch without changing tempo?

**A**: Yes, adjust only the desired parameters:

```python
# Only pitch adjustment
adjuster = ProsodyAdjuster(
    pitch_shift=1.15,  # +15%
    tempo_shift=1.00,  # No change
    energy_shift=1.00  # No change
)
```

---

### Q5.7: Why does my adjusted audio sound metallic?

**A**: Excessive pitch shift causes metallic artifacts.

**Solution**:

1. Reduce pitch_shift:
   ```python
   # ❌ TOO HIGH (metallic)
   adjuster = ProsodyAdjuster(pitch_shift=1.25)

   # ✅ MODERATE (natural)
   adjuster = ProsodyAdjuster(pitch_shift=1.12)
   ```

2. Use better source audio (higher quality synthesis).

---

### Q5.8: Can I disable specific adjustments?

**A**: Yes, set unwanted adjustments to 1.0:

```python
# Only tempo adjustment (no pitch or energy change)
adjuster = ProsodyAdjuster(
    pitch_shift=1.00,  # No change
    tempo_shift=1.10,  # +10% faster
    energy_shift=1.00  # No change
)
```

---

### Q5.9: How long can the input audio be?

**A**: Recommended: < 60 seconds

| Duration | Processing Time | Memory Usage |
|----------|----------------|--------------|
| 1-10s | 0.5-2s | Low |
| 10-30s | 2-6s | Medium |
| 30-60s | 6-15s | High |
| > 60s | 15s+ | Very High ⚠️ |

For longer audio, consider splitting into chunks.

---

### Q5.10: Can I use Prosody in real-time?

**A**: No, Prosody requires the full audio file due to the PSOLA algorithm.

**Alternatives for real-time**:

1. Pre-process audio with Prosody before real-time playback
2. Use streaming with buffering (buffer entire audio, adjust, then stream)

---

## 6. Diagnostic Tools

### Tool 6.1: Audio Analysis Script

```python
# scripts/analyze_audio.py
import parselmouth
import numpy as np
from pathlib import Path

def analyze_audio(audio_path: str):
    """Comprehensive audio analysis."""
    sound = parselmouth.Sound(audio_path)

    print(f"\n{'='*50}")
    print(f"Audio Analysis: {Path(audio_path).name}")
    print(f"{'='*50}")

    # Basic properties
    print(f"\nBasic Properties:")
    print(f"  Duration: {sound.duration:.2f} seconds")
    print(f"  Sample rate: {sound.sampling_frequency} Hz")
    print(f"  Channels: {sound.n_channels}")
    print(f"  Samples: {sound.n_samples}")

    # Amplitude analysis
    max_amplitude = sound.values.max()
    min_amplitude = sound.values.min()
    mean_amplitude = np.mean(np.abs(sound.values))

    print(f"\nAmplitude:")
    print(f"  Max: {max_amplitude:.3f}")
    print(f"  Min: {min_amplitude:.3f}")
    print(f"  Mean: {mean_amplitude:.3f}")

    if max_amplitude > 0.99 or min_amplitude < -0.99:
        print("  ⚠️ CLIPPING DETECTED!")

    # Pitch analysis
    try:
        pitch = sound.to_pitch()
        mean_f0 = parselmouth.praat.call(pitch, "Get mean", 0, 0, "Hertz")
        min_f0 = parselmouth.praat.call(pitch, "Get minimum", 0, 0, "Hertz", "Parabolic")
        max_f0 = parselmouth.praat.call(pitch, "Get maximum", 0, 0, "Hertz", "Parabolic")

        print(f"\nPitch (F0):")
        print(f"  Mean: {mean_f0:.1f} Hz")
        print(f"  Min: {min_f0:.1f} Hz")
        print(f"  Max: {max_f0:.1f} Hz")
        print(f"  Range: {max_f0 - min_f0:.1f} Hz")

    except Exception as e:
        print(f"\nPitch analysis failed: {e}")

    # Intensity analysis
    try:
        intensity = sound.to_intensity()
        mean_intensity = parselmouth.praat.call(intensity, "Get mean", 0, 0, "energy")

        print(f"\nIntensity:")
        print(f"  Mean: {mean_intensity:.1f} dB")

    except Exception as e:
        print(f"\nIntensity analysis failed: {e}")

    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_audio.py <audio_file.wav>")
        sys.exit(1)

    analyze_audio(sys.argv[1])
```

**Usage**:

```bash
python scripts/analyze_audio.py speech.wav
```

---

### Tool 6.2: Confidence Debugger

```python
# scripts/debug_confidence.py
from services.prosody_adjuster import ProsodyAdjuster

def debug_confidence(audio_path: str, text: str, **params):
    """Debug confidence scoring."""
    adjuster = ProsodyAdjuster(**params)

    print(f"\nAdjusting: {audio_path}")
    print(f"Parameters: {params}")

    adjusted_path, confidence, details = adjuster.apply(audio_path, text)

    print(f"\n{'='*50}")
    print(f"Confidence Report")
    print(f"{'='*50}")

    print(f"\nFinal Confidence: {confidence:.2f}")

    for check, result in details.items():
        if check == "final_confidence":
            continue

        status = "✅" if result == "PASS" or "PASS" in str(result) else "❌"
        print(f"  {status} {check}: {result}")

    print(f"\n{'='*50}\n")

    return confidence, details

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python debug_confidence.py <audio_file.wav>")
        sys.exit(1)

    debug_confidence(
        audio_path=sys.argv[1],
        text="Test",
        pitch_shift=1.15,
        tempo_shift=1.10,
        energy_shift=1.20
    )
```

**Usage**:

```bash
python scripts/debug_confidence.py speech.wav
```

---

### Tool 6.3: Parameter Validator

```python
# scripts/validate_parameters.py
def validate_prosody_parameters(**params):
    """Validate prosody parameters before processing."""
    errors = []
    warnings = []

    # Pitch validation
    pitch_shift = params.get("pitch_shift", 1.0)
    if not (0.90 <= pitch_shift <= 1.25):
        errors.append(f"pitch_shift out of range: {pitch_shift} (must be 0.90-1.25)")
    elif pitch_shift > 1.20:
        warnings.append(f"pitch_shift very high: {pitch_shift} (may sound unnatural)")

    # Tempo validation
    tempo_shift = params.get("tempo_shift", 1.0)
    if not (0.95 <= tempo_shift <= 1.15):
        errors.append(f"tempo_shift out of range: {tempo_shift} (must be 0.95-1.15)")
    elif tempo_shift > 1.12:
        warnings.append(f"tempo_shift very fast: {tempo_shift} (may sound rushed)")

    # Energy validation
    energy_shift = params.get("energy_shift", 1.0)
    if not (1.00 <= energy_shift <= 1.30):
        errors.append(f"energy_shift out of range: {energy_shift} (must be 1.00-1.30)")
    elif energy_shift > 1.25:
        warnings.append(f"energy_shift very high: {energy_shift} (may cause clipping)")

    # Print results
    if errors:
        print("❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("⚠️ WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("✅ All parameters valid")

    return len(errors) == 0

if __name__ == "__main__":
    validate_prosody_parameters(
        pitch_shift=1.15,
        tempo_shift=1.10,
        energy_shift=1.20
    )
```

**Usage**:

```bash
python scripts/validate_parameters.py
```

---

## Summary

### Quick Checklist for Troubleshooting

- [ ] Parselmouth is installed (`pip install praat-parselmouth==0.4.3`)
- [ ] Audio file is WAV format
- [ ] Audio file size < 100 MB
- [ ] Parameters are within safe ranges
- [ ] VOICEVOX/OpenVoice service is running (if using integration)
- [ ] Confidence score > 0.70
- [ ] No clipping detected (max amplitude < 0.99)
- [ ] Processing time is reasonable (< 1.0x real-time factor)

### Getting Help

If you still encounter issues after following this guide:

1. **Check logs**:
   ```bash
   tail -f backend/logs/prosody_adjuster.log
   ```

2. **Run diagnostic scripts**:
   ```bash
   python scripts/analyze_audio.py problem_audio.wav
   python scripts/debug_confidence.py problem_audio.wav
   ```

3. **Contact support**:
   - Email: support@example.com
   - GitHub Issues: https://github.com/example/video-message-app/issues

---

*This troubleshooting guide is maintained by the Video Message App team.*
