# Prosody Adjustment - Code Examples

This directory contains practical examples for using the Prosody Adjustment API.

## 📁 Examples

### 1. Basic Adjustment
**File**: `01_basic_adjustment.py`

Simplest usage with default parameters.

```bash
python 01_basic_adjustment.py
```

**What you'll learn**:
- Initialize ProsodyAdjuster
- Apply default adjustments
- Interpret confidence scores

---

### 2. Preset Usage
**File**: `02_preset_usage.py`

Use predefined presets for common scenarios.

```bash
python 02_preset_usage.py
```

**What you'll learn**:
- Available presets (celebration, calm, professional, etc.)
- Compare multiple presets
- Choose the right preset for your use case

---

### 3. VOICEVOX Integration
**File**: `03_voicevox_integration.py`

Integrate with VOICEVOX text-to-speech.

```bash
python 03_voicevox_integration.py
```

**Prerequisites**:
- VOICEVOX engine running on port 50021
- Install requests: `pip install requests`

**What you'll learn**:
- Synthesize with VOICEVOX
- Apply prosody to synthesized speech
- Save enhanced audio

---

### 4. Batch Processing
**File**: `04_batch_processing.py`

Process multiple audio files efficiently.

```bash
python 04_batch_processing.py
```

**What you'll learn**:
- Parallel processing
- Progress tracking
- Error handling in batch operations

---

### 5. Custom Parameters
**File**: `05_custom_parameters.py`

Fine-tune adjustments with custom parameters.

```bash
python 05_custom_parameters.py
```

**What you'll learn**:
- Parameter ranges and safety
- Dynamic parameter calculation
- A/B testing adjustments

---

### 6. Audio Analysis
**File**: `06_audio_analysis.py`

Analyze audio before and after adjustments.

```bash
python 06_audio_analysis.py speech.wav
```

**What you'll learn**:
- Measure pitch, tempo, energy
- Verify adjustments
- Quality assessment

---

### 7. REST API Client
**File**: `07_rest_api_client.py`

Use the Prosody API via HTTP.

```bash
python 07_rest_api_client.py
```

**Prerequisites**:
- Backend API running on port 55433

**What you'll learn**:
- Make HTTP requests
- Handle multipart file uploads
- Parse API responses

---

### 8. Real-World Scenarios
**File**: `08_real_world_scenarios.py`

Complete examples for common use cases.

```bash
python 08_real_world_scenarios.py
```

**Scenarios**:
- Birthday video messages
- Business announcements
- Meditation guides
- Customer service greetings

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Required
pip install praat-parselmouth==0.4.3
pip install numpy>=1.24.0,<2.0.0

# Optional (for specific examples)
pip install requests  # For API examples
pip install tqdm      # For progress bars
```

### 2. Prepare Audio File

Create or obtain a WAV audio file:

```bash
# Convert MP3 to WAV
ffmpeg -i input.mp3 -ar 22050 -ac 1 speech.wav

# Or use VOICEVOX/OpenVoice to generate speech
```

### 3. Run Examples

```bash
# Start with basic example
python 01_basic_adjustment.py

# Try presets
python 02_preset_usage.py

# Integrate with VOICEVOX (if available)
python 03_voicevox_integration.py
```

---

## 📚 Learning Path

### Beginner
1. `01_basic_adjustment.py` - Understand basic usage
2. `02_preset_usage.py` - Learn about presets
3. `06_audio_analysis.py` - Analyze results

### Intermediate
4. `03_voicevox_integration.py` - Integrate with TTS
5. `05_custom_parameters.py` - Fine-tune adjustments
6. `04_batch_processing.py` - Process multiple files

### Advanced
7. `07_rest_api_client.py` - Use REST API
8. `08_real_world_scenarios.py` - Build complete solutions

---

## 🛠️ Common Tasks

### Task 1: Make birthday message more joyful

```python
from services.prosody_adjuster import ProsodyAdjuster

adjuster = ProsodyAdjuster(
    pitch_shift=1.15,  # +15% higher (brighter)
    tempo_shift=1.10,  # +10% faster (energetic)
    energy_shift=1.20  # +20% louder (emphatic)
)

adjusted_path, confidence, details = adjuster.apply(
    audio_path="birthday_speech.wav",
    text="Happy Birthday!"
)
```

### Task 2: Make business announcement more professional

```python
adjuster = ProsodyAdjuster(
    pitch_shift=1.00,  # No change (neutral)
    tempo_shift=0.95,  # -5% slower (clear)
    energy_shift=1.10  # +10% louder (authoritative)
)

adjusted_path, confidence, details = adjuster.apply(
    audio_path="announcement.wav",
    text="We are pleased to announce..."
)
```

### Task 3: Make meditation guide more calming

```python
adjuster = ProsodyAdjuster(
    pitch_shift=0.95,  # -5% lower (deeper)
    tempo_shift=0.90,  # -10% slower (peaceful)
    energy_shift=0.85  # -15% softer (gentle)
)

adjusted_path, confidence, details = adjuster.apply(
    audio_path="meditation.wav",
    text="Take a deep breath..."
)
```

---

## 🔍 Troubleshooting

### Issue: "Parselmouth not available"

```bash
pip install praat-parselmouth==0.4.3
```

### Issue: Audio file not found

```python
from pathlib import Path

audio_path = Path("speech.wav")
if not audio_path.exists():
    print(f"File not found: {audio_path}")
    print(f"Current directory: {Path.cwd()}")
```

Use absolute path:
```python
audio_path = Path("speech.wav").resolve()
```

### Issue: Low confidence score

Reduce adjustment magnitude:

```python
# ❌ Too extreme
adjuster = ProsodyAdjuster(pitch_shift=1.25)  # confidence: 0.45

# ✅ More moderate
adjuster = ProsodyAdjuster(pitch_shift=1.12)  # confidence: 0.88
```

### Issue: Unnatural-sounding audio

1. Check source audio quality
2. Use presets (they're tuned for natural results)
3. Reduce parameter values

---

## 📖 Documentation

- [API Specification](../../PROSODY_API_SPEC.md) - Complete API reference
- [User Guide](../../PROSODY_USER_GUIDE.md) - Non-technical guide
- [Developer Guide](../../PROSODY_DEVELOPER_GUIDE.md) - Integration guide
- [Troubleshooting](../../PROSODY_TROUBLESHOOTING.md) - Common issues

---

## 🤝 Contributing

Found a bug or have a suggestion? Please open an issue on GitHub.

### Adding New Examples

1. Create a new file: `XX_example_name.py`
2. Follow the existing structure:
   - Docstring with description
   - Requirements list
   - Main function
   - Example usage
3. Update this README

---

## 📝 License

MIT License - See [LICENSE](../../LICENSE) for details.

---

## 💬 Support

- Email: support@example.com
- GitHub Issues: https://github.com/example/video-message-app/issues

---

*Happy coding! May your speech synthesis be natural and expressive.* 🎵
