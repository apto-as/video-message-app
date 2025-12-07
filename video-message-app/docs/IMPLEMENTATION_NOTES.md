# Implementation Notes - Recent Features

This document provides technical details about recent implementations in the Video Message App.

---

## Table of Contents
1. [Person Detection - Transparent Padding Control](#person-detection---transparent-padding-control)
2. [Voice Quality Enhancement](#voice-quality-enhancement)
3. [Parameter Flow Architecture](#parameter-flow-architecture)
4. [Testing Recommendations](#testing-recommendations)

---

## Person Detection - Transparent Padding Control

**Issue**: #1
**Implementation Date**: 2024-12-07
**Status**: ✅ Completed

### Overview

Added UI controls to allow users to customize transparent padding around extracted persons. This feature addresses the need for better integration with D-ID video generation, which requires proper spacing around detected faces.

### Technical Implementation

#### 1. Frontend State Management

**File**: `frontend/src/components/PersonDetection.js`

```javascript
// New state variables (Lines 25-26)
const [transparentPaddingSize, setTransparentPaddingSize] = useState(300);
const [addTransparentPadding, setAddTransparentPadding] = useState(true);
```

**State Behavior**:
- `transparentPaddingSize`: Controls the pixel size of transparent border (0-500px)
- `addTransparentPadding`: Boolean flag to enable/disable the feature
- Both states are passed to the extraction API when processing images

#### 2. UI Components

**File**: `frontend/src/components/PersonDetection.js` (Lines 323-346)

```jsx
<div className="padding-control">
  {/* Checkbox to enable/disable */}
  <label className="padding-checkbox">
    <input
      type="checkbox"
      checked={addTransparentPadding}
      onChange={(e) => setAddTransparentPadding(e.target.checked)}
    />
    透明パディングを追加
  </label>

  {/* Conditional slider (only shown when enabled) */}
  {addTransparentPadding && (
    <label className="padding-slider">
      パディングサイズ: {transparentPaddingSize}px
      <input
        type="range"
        min="0"
        max="500"
        step="50"
        value={transparentPaddingSize}
        onChange={(e) => setTransparentPaddingSize(parseInt(e.target.value))}
      />
    </label>
  )}
</div>
```

**UX Design Decisions**:
- Checkbox first: Simple on/off control
- Conditional slider: Prevents confusion when padding is disabled
- Step size of 50px: Reasonable granularity for most use cases
- Real-time value display: User sees exact padding size

#### 3. API Integration

**File**: `frontend/src/services/api.js`

```javascript
export const extractSelectedPersons = async (
  imageFile,
  selectedPersonIds,
  confThreshold = 0.5,
  padding = 20,
  addTransparentPadding = true,      // New parameter
  transparentPaddingSize = 300       // New parameter
) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('person_ids', JSON.stringify(selectedPersonIds));
  formData.append('conf_threshold', confThreshold.toString());
  formData.append('padding', padding.toString());
  formData.append('add_transparent_padding', addTransparentPadding.toString());
  formData.append('transparent_padding_size', transparentPaddingSize.toString());

  // ... rest of API call
};
```

**Parameter Flow**:
1. User adjusts slider/checkbox → State update
2. User clicks "抽出" button → `handleExtract()` called
3. `extractSelectedPersons()` invoked with current state values
4. FormData sent to backend `/api/person-detection/extract` endpoint
5. Backend processes image with specified padding parameters

### Backend Considerations

**Backend Endpoint**: `/api/person-detection/extract` (not modified in this issue)

The backend already supported these parameters. This frontend change enables users to access existing functionality through the UI.

**Expected Backend Behavior**:
- When `add_transparent_padding=true`:
  - Original person bounding box extracted
  - Transparent border added around person (size = `transparent_padding_size`)
  - Result: Larger image with transparent padding

- When `add_transparent_padding=false`:
  - Only the person bounding box is extracted
  - Minimal padding (20px, controlled by `padding` parameter)
  - Result: Tight crop around person

### Why This Feature Matters

**D-ID Video Generation Compatibility**:
- D-ID requires proper face centering and spacing
- Too tight crops may cut off facial features
- Transparent padding ensures:
  - Face remains centered
  - Sufficient space for avatar movement
  - No abrupt edges in generated videos

**User Control**:
- Different use cases require different padding:
  - Profile photos: Tight crop (100px)
  - Talking avatars: Medium padding (300px, default)
  - Full-body videos: Large padding (500px)

---

## Voice Quality Enhancement

**Issue**: #2
**Implementation Date**: 2024-12-07
**Status**: ✅ Completed

### Overview

Enhanced voice synthesis quality by adding fine-grained control parameters for both VOICEVOX (intonation) and OpenVoice (pitch/volume). This allows users to customize speech characteristics for more natural and expressive audio output.

### Technical Implementation

#### 1. Unified Voice Service Layer

**File**: `backend/services/unified_voice_service.py`

**Key Changes**:

**Request Model Extension** (Lines 44-51):
```python
class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    voice_profile: VoiceProfile
    speed: float = Field(default=1.0, ge=0.1, le=3.0)
    pitch: float = Field(default=0.0, ge=-0.15, le=0.15)      # NEW
    volume: float = Field(default=1.0, ge=0.0, le=2.0)        # NEW
    intonation: float = Field(default=1.0, ge=0.0, le=2.0)    # NEW
    emotion: str = "neutral"
```

**VOICEVOX Synthesis** (Lines 242-260):
```python
async def _synthesize_voicevox(self, request: VoiceSynthesisRequest) -> bytes:
    """VOICEVOX音声合成"""
    if not self.voicevox_client:
        raise Exception("VOICEVOXクライアントが初期化されていません")

    profile = request.voice_profile
    speaker_id = profile.speaker_id

    if speaker_id is None:
        raise ValueError("VOICEVOX話者IDが指定されていません")

    return await self.voicevox_client.text_to_speech(
        text=request.text,
        speaker_id=speaker_id,
        speed_scale=request.speed,
        pitch_scale=request.pitch,
        intonation_scale=request.intonation,    # NEW: Intonation control
        volume_scale=request.volume
    )
```

**OpenVoice Synthesis** (Lines 262-314):
```python
async def _synthesize_openvoice(self, request: VoiceSynthesisRequest) -> bytes:
    """OpenVoice音声合成"""
    # ... profile validation ...

    if profile.voice_type == VoiceType.CLONED:
        # Clone voice synthesis
        return await self.openvoice_client.synthesize_with_clone(
            text=request.text,
            voice_profile=profile_dict,
            language=profile.language,
            speed=request.speed,
            pitch=request.pitch,        # NEW: Pitch control
            volume=request.volume,      # NEW: Volume control
            emotion=request.emotion
        )
```

#### 2. OpenVoice Hybrid Client

**File**: `backend/services/openvoice_hybrid_client.py`

**Enhanced Function Signature** (Lines 95-104):
```python
async def synthesize_with_clone(
    self,
    text: str,
    voice_profile: Dict[str, Any],
    language: str = "ja",
    speed: float = 1.0,
    pitch: float = 0.0,        # NEW: -0.15 to +0.15
    volume: float = 1.0,       # NEW: 0.0 to 2.0
    emotion: str = "neutral"
) -> Optional[bytes]:
```

**Parameter Forwarding** (Lines 122-130):
```python
result = await self.native_client.synthesize_with_clone(
    text=text,
    profile_id=profile_id,
    language=language,
    speed=speed,
    pitch=pitch,      # Forwarded to native service
    volume=volume     # Forwarded to native service
)
```

#### 3. OpenVoice Native Client (HTTP API)

**File**: `backend/services/openvoice_native_client.py` (not shown in code, but updated)

**HTTP Endpoint**: `POST /voice-clone/synthesize`

**Expected Request Body**:
```json
{
  "text": "こんにちは、世界",
  "profile_id": "openvoice_c403f011",
  "language": "ja",
  "speed": 1.0,
  "pitch": 0.05,      // NEW: +5% pitch increase
  "volume": 1.2       // NEW: 20% volume boost
}
```

**Backend Processing** (OpenVoice Native Service):
1. MeloTTS generates speech from text
2. FFmpeg post-processing applies:
   ```bash
   ffmpeg -i input.wav \
          -af "atempo={speed},asetrate={sample_rate * (1 + pitch)},volume={volume}" \
          output.wav
   ```
3. Processed audio returned as bytes

### Parameter Ranges and Effects

#### VOICEVOX Parameters

| Parameter | Range | Default | Effect |
|-----------|-------|---------|--------|
| `speed` | 0.1 - 3.0 | 1.0 | Speech rate (0.5 = half speed, 2.0 = double speed) |
| `pitch` | -0.15 - +0.15 | 0.0 | Voice pitch (negative = lower, positive = higher) |
| **`intonation`** | **0.0 - 2.0** | **1.0** | **Expressiveness (0.5 = flat, 1.5 = dramatic)** |
| `volume` | 0.0 - 2.0 | 1.0 | Output volume (0.5 = quiet, 2.0 = loud) |

**Intonation Scale Examples**:
- **0.5**: Monotone reading (news anchor style)
- **1.0**: Natural speech (default)
- **1.5**: Expressive speech (storytelling)
- **2.0**: Very emotional (acting/audiobook)

#### OpenVoice Parameters

| Parameter | Range | Default | Effect |
|-----------|-------|---------|--------|
| `speed` | 0.1 - 3.0 | 1.0 | Speech rate (same as VOICEVOX) |
| **`pitch`** | **-0.15 - +0.15** | **0.0** | **FFmpeg pitch shift (semitones)** |
| **`volume`** | **0.0 - 2.0** | **1.0** | **FFmpeg volume gain** |
| `emotion` | String | "neutral" | Reserved for future use |

**Pitch Adjustment Examples**:
- **-0.10**: Deeper voice (masculine effect)
- **0.0**: Original pitch
- **+0.10**: Higher voice (feminine effect)

**Volume Adjustment Examples**:
- **0.5**: Whisper/quiet speech
- **1.0**: Normal volume
- **1.5**: Louder speech (presentational)

### Why These Parameters?

**VOICEVOX - Intonation Control**:
- Japanese TTS often sounds flat/robotic
- Intonation scaling adds natural prosody variations
- Critical for:
  - Audiobooks (dramatic reading)
  - Customer service bots (friendly tone)
  - Educational content (engaging speech)

**OpenVoice - Pitch/Volume**:
- FFmpeg post-processing allows audio manipulation
- Pitch adjustment:
  - Voice cloning may not capture exact pitch
  - Gender transformation (masculine ↔ feminine)
  - Character voice creation
- Volume normalization:
  - Ensures consistent audio levels
  - Compensates for quiet reference recordings
  - Matches target platform requirements (D-ID, etc.)

### Implementation Challenges

#### Challenge 1: Parameter Validation
**Problem**: Invalid ranges could crash audio processing
**Solution**: Pydantic Field validators with strict bounds
```python
pitch: float = Field(default=0.0, ge=-0.15, le=0.15)  # Greater-equal, Less-equal
```

#### Challenge 2: Service Compatibility
**Problem**: Native service must support new parameters
**Solution**: Graceful degradation - if parameters not supported, use defaults

#### Challenge 3: User Interface
**Problem**: Too many parameters confuse users
**Solution**:
- Group by provider (VOICEVOX tab, OpenVoice tab)
- Provide presets ("Natural", "Expressive", "Monotone")
- Advanced mode for fine-tuning

---

## Parameter Flow Architecture

This diagram shows how parameters flow through the system:

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (React)                                            │
│                                                             │
│  User Input (Sliders/Checkboxes)                          │
│    ├─ Padding Size: 300px                                 │
│    ├─ Add Padding: true                                   │
│    ├─ Speed: 1.0                                          │
│    ├─ Pitch: 0.05                                         │
│    ├─ Volume: 1.2                                         │
│    └─ Intonation: 1.5                                     │
│                                                             │
│  ↓ State Update (React Hooks)                             │
│                                                             │
│  API Call (services/api.js)                                │
│    ├─ extractSelectedPersons(...)                         │
│    └─ synthesizeSpeech(...)                               │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP Request (FormData/JSON)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                          │
│                                                             │
│  Router Layer                                              │
│    ├─ /api/person-detection/extract                       │
│    └─ /api/unified-voice/synthesize                       │
│                                                             │
│  ↓ Parameter Extraction & Validation                      │
│                                                             │
│  Service Layer (Pydantic Models)                           │
│    ├─ VoiceSynthesisRequest                               │
│    │    ├─ speed: float                                   │
│    │    ├─ pitch: float                                   │
│    │    ├─ volume: float                                  │
│    │    └─ intonation: float                              │
│    │                                                       │
│    └─ UnifiedVoiceService                                 │
│         ├─ _synthesize_voicevox()                         │
│         │    └─ voicevox_client.text_to_speech(           │
│         │          intonation_scale=request.intonation)   │
│         │                                                  │
│         └─ _synthesize_openvoice()                        │
│              └─ openvoice_client.synthesize_with_clone(   │
│                    pitch=request.pitch,                   │
│                    volume=request.volume)                 │
│                                                             │
│  ↓ Native Service Client                                  │
│                                                             │
│  HTTP Client (OpenVoiceNativeClient)                       │
│    POST /voice-clone/synthesize                           │
│    Body: { text, profile_id, speed, pitch, volume }       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP Request
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ OpenVoice Native Service (Python)                          │
│                                                             │
│  FastAPI Endpoint                                          │
│    @app.post("/voice-clone/synthesize")                   │
│                                                             │
│  ↓ MeloTTS Synthesis                                       │
│                                                             │
│  OpenVoiceV2 Processing                                    │
│    ├─ Load voice profile embedding                        │
│    ├─ Generate speech with MeloTTS                        │
│    └─ Apply tone color conversion                         │
│                                                             │
│  ↓ FFmpeg Post-Processing                                 │
│                                                             │
│  FFmpeg Audio Filters                                      │
│    -af "atempo={speed},                                   │
│        asetrate={rate * (1 + pitch)},                     │
│        volume={volume}"                                   │
│                                                             │
│  ↓ Return Audio Bytes                                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Observations

1. **Type Safety**: Pydantic models enforce type/range validation at service layer
2. **Separation of Concerns**:
   - Frontend: User interaction & state management
   - Backend Service: Business logic & orchestration
   - Native Service: Audio processing & FFmpeg
3. **Parameter Propagation**: Each layer passes parameters down without modification
4. **Error Handling**: Invalid parameters rejected early (Pydantic validation)

---

## Testing Recommendations

### Unit Tests

#### Person Detection Padding
```javascript
// Frontend unit test (Jest + React Testing Library)
test('padding slider updates state correctly', () => {
  render(<PersonDetection />);

  const slider = screen.getByLabelText(/パディングサイズ/);
  fireEvent.change(slider, { target: { value: '400' } });

  expect(screen.getByText(/400px/)).toBeInTheDocument();
});

test('padding checkbox disables slider', () => {
  render(<PersonDetection />);

  const checkbox = screen.getByLabelText(/透明パディングを追加/);
  fireEvent.click(checkbox);

  expect(screen.queryByLabelText(/パディングサイズ/)).not.toBeInTheDocument();
});
```

#### Voice Quality Parameters
```python
# Backend unit test (pytest)
def test_voice_synthesis_request_validation():
    # Valid request
    request = VoiceSynthesisRequest(
        text="テスト",
        voice_profile=mock_profile,
        pitch=0.1,
        volume=1.5,
        intonation=1.2
    )
    assert request.pitch == 0.1

    # Invalid pitch (out of range)
    with pytest.raises(ValidationError):
        VoiceSynthesisRequest(
            text="テスト",
            voice_profile=mock_profile,
            pitch=0.5  # Exceeds max 0.15
        )
```

### Integration Tests

#### End-to-End Padding Test
```python
async def test_extract_persons_with_custom_padding():
    """Test person extraction with custom transparent padding"""

    # Upload test image
    with open("tests/fixtures/test_photo.jpg", "rb") as f:
        response = await client.post(
            "/api/person-detection/detect",
            files={"image": f}
        )

    detected = response.json()
    person_ids = [p["person_id"] for p in detected["persons"]]

    # Extract with custom padding
    with open("tests/fixtures/test_photo.jpg", "rb") as f:
        response = await client.post(
            "/api/person-detection/extract",
            files={"image": f},
            data={
                "person_ids": json.dumps(person_ids),
                "add_transparent_padding": "true",
                "transparent_padding_size": "400"  # Custom size
            }
        )

    assert response.status_code == 200

    # Verify image has proper padding
    result_image = Image.open(io.BytesIO(response.content))
    # Check image dimensions increased by ~800px (400px * 2 sides)
```

#### End-to-End Voice Quality Test
```python
async def test_voice_synthesis_with_quality_parameters():
    """Test voice synthesis with pitch/volume/intonation"""

    request_data = {
        "text": "こんにちは、テストです",
        "voice_profile_id": "voicevox_3",
        "speed": 1.0,
        "pitch": 0.05,
        "volume": 1.2,
        "intonation": 1.5
    }

    response = await client.post(
        "/api/unified-voice/synthesize",
        json=request_data
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"

    # Verify audio properties
    audio_data = response.content
    assert len(audio_data) > 1000  # Non-empty audio

    # Optional: Check audio metadata
    # (Sample rate, duration, RMS volume level, etc.)
```

### Manual Testing Checklist

#### Person Detection - Transparent Padding
- [ ] Upload image with multiple persons
- [ ] Detect persons successfully
- [ ] Select 1 person
- [ ] Adjust padding slider to 0px → Verify tight crop
- [ ] Adjust padding slider to 500px → Verify large transparent border
- [ ] Disable padding checkbox → Verify slider disappears
- [ ] Enable padding checkbox → Verify slider reappears with previous value
- [ ] Extract person and download → Verify PNG has transparency
- [ ] Load extracted PNG in image editor → Verify padding dimensions

#### Voice Quality - VOICEVOX
- [ ] Select VOICEVOX voice (e.g., ずんだもん)
- [ ] Set intonation to 0.5 → Play audio → Verify flat/monotone speech
- [ ] Set intonation to 1.0 → Play audio → Verify normal speech
- [ ] Set intonation to 2.0 → Play audio → Verify expressive speech
- [ ] Adjust volume to 0.5 → Verify quieter output
- [ ] Adjust volume to 2.0 → Verify louder output

#### Voice Quality - OpenVoice
- [ ] Select OpenVoice clone profile
- [ ] Set pitch to -0.10 → Play audio → Verify deeper voice
- [ ] Set pitch to +0.10 → Play audio → Verify higher voice
- [ ] Set volume to 0.5 → Verify quieter output
- [ ] Set volume to 1.5 → Verify louder output
- [ ] Combine pitch +0.05, volume 1.2 → Verify cumulative effect

### Performance Testing

#### Padding Processing Time
```python
import time

def test_padding_performance():
    """Ensure padding doesn't significantly slow down extraction"""

    # Baseline: No padding
    start = time.time()
    extract_persons(image, person_ids, add_transparent_padding=False)
    baseline_time = time.time() - start

    # With padding
    start = time.time()
    extract_persons(image, person_ids, add_transparent_padding=True,
                    transparent_padding_size=300)
    padding_time = time.time() - start

    # Padding should add < 50% overhead
    assert padding_time < baseline_time * 1.5
```

#### Voice Synthesis Quality (FFmpeg Processing)
```python
def test_ffmpeg_processing_time():
    """Ensure pitch/volume processing doesn't cause delays"""

    # Baseline: No FFmpeg processing
    start = time.time()
    synthesize(text, profile_id, pitch=0.0, volume=1.0)
    baseline_time = time.time() - start

    # With FFmpeg processing
    start = time.time()
    synthesize(text, profile_id, pitch=0.1, volume=1.5)
    processed_time = time.time() - start

    # FFmpeg should add < 30% overhead
    assert processed_time < baseline_time * 1.3
```

---

## Future Enhancements

### Person Detection
1. **Adaptive Padding**: Auto-calculate optimal padding based on face size
2. **Aspect Ratio Lock**: Maintain specific aspect ratios for video platforms
3. **Padding Color**: Allow custom background colors (not just transparent)
4. **Multiple Exports**: Generate multiple versions with different padding settings

### Voice Quality
1. **Preset Profiles**: Pre-configured voice styles ("Narrator", "Cheerful", "Serious")
2. **Real-time Preview**: Live audio preview while adjusting parameters
3. **Voice Equalizer**: Advanced audio filtering (bass boost, treble, reverb)
4. **Emotion Synthesis**: Implement emotion parameter for OpenVoice (happy, sad, angry)
5. **Batch Processing**: Apply same settings to multiple text inputs

---

**Document Version**: 1.0
**Last Updated**: 2024-12-07
**Maintained By**: Development Team
