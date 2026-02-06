# FasterLivePortrait Integration Investigation

## Investigation Date: 2026-02-06

## Key Findings

### 1. Architecture Understanding

**FasterLivePortrait** requires TWO inputs:
- **Source Image**: The face to animate (our cropped upper-body image)
- **Driving Video**: A video that provides motion (head movements, expressions, blinks)

The system does NOT generate "idle animations" on its own. It **transfers motion** from a driving video to the source image.

### 2. API Endpoint

```
POST /predict/
Content-Type: multipart/form-data

Required Parameters:
- source_image: UploadFile (the face image)
- driving_video: UploadFile (motion source video)
- OR driving_pickle: UploadFile (pre-extracted motion features)
- flag_is_animal: bool
- flag_pickle: bool
- flag_relative_input: bool
- flag_do_crop_input: bool
- flag_remap_input: bool
- driving_multiplier: float
- flag_stitching: bool
- flag_crop_driving_video_input: bool
- flag_video_editing_head_rotation: bool
- scale: float
- vx_ratio: float
- vy_ratio: float
- scale_crop_driving_video: float
- vx_ratio_crop_driving_video: float
- vy_ratio_crop_driving_video: float
- driving_smooth_observation_variance: float

Response: ZIP file containing output video
```

### 3. Sample Driving Videos

The repository includes sample driving videos in `assets/examples/driving/`:
- `d0.mp4`: 3.12 seconds, 512x512, 25fps
- `d3.mp4`, `d6.mp4`, `d9.mp4`, `d10.mp4`, etc.
- `d2.pkl`, `d8.pkl`: Pre-extracted motion features

### 4. MediaPipe for Commercial Use

Use `--mp` flag to enable MediaPipe instead of InsightFace for face detection.
This avoids InsightFace's license restrictions for commercial applications.

### 5. Docker Image Issues

**Problem**: `shaoguo/faster_liveportrait:v3` has TensorRT compatibility issues:
- TensorRT imports unconditionally at the Python level
- The native libraries (libnvinfer.so.8) are missing or incompatible
- GPU passthrough works differently than our existing containers

**Workaround Applied**:
1. Uninstall tensorrt Python package: `pip uninstall tensorrt -y`
2. Use ONNX inference mode: `--cfg configs/onnx_infer.yaml`

**GPU Issue**: The Docker image uses CUDA runtime that's incompatible with our driver 570.172.08 (CUDA 12.8).

### 6. Model Checkpoints

Downloaded from HuggingFace: `huggingface-cli download warmshao/FasterLivePortrait --local-dir ./checkpoints`

Size: ~2GB total for ONNX models

## Proposed Integration Architecture

### Option A: Pre-recorded Driving Videos (Recommended)

```
[Upload Image]
    → [UpperBodyCropper (512x512)]
    → [FasterLivePortrait + idle driving video]
    → [MuseTalk (lip-sync with audio)]
    → [Final Video]
```

**Implementation:**
1. Create/source a small library of "idle animation" driving videos:
   - `idle_blink_3s.mp4`: Subtle blinks, no head movement
   - `idle_nod_5s.mp4`: Gentle head nods
   - `idle_natural_10s.mp4`: Natural micro-movements

2. Loop/extend driving video to match audio duration

3. Apply LivePortrait with the driving video

4. Extract frames and apply MuseTalk lip-sync

### Option B: Skip LivePortrait for MVP

If idle animations aren't critical, we can skip LivePortrait and use:
```
[Upload Image] → [UpperBodyCropper] → [MuseTalk] → [Final Video]
```

This gives us talking avatars without natural head movements.

### Option C: Audio-Driven Animation (JoyVASA)

FasterLivePortrait supports JoyVASA which can drive animations from AUDIO.
This is the ideal solution but requires additional model downloads:
```bash
huggingface-cli download TencentGameMate/chinese-hubert-base --local-dir checkpoints/chinese-hubert-base
huggingface-cli download jdh-algo/JoyVASA --local-dir checkpoints/JoyVASA
```

## Next Steps

1. **Build Compatible Docker Image**: Create a Dockerfile based on our working MuseTalk image with FasterLivePortrait code
2. **Create Driving Videos**: Source or create appropriate idle animation driving videos
3. **Implement Service**: Create `liveportrait_service/` with FastAPI wrapper
4. **Integrate Pipeline**: Modify `lipsync.py` to optionally call LivePortrait before MuseTalk

## Technical Decisions Needed

1. **Driving Video Strategy**:
   - [ ] Use pre-recorded driving videos (simpler)
   - [ ] Implement JoyVASA audio-driven animation (more complex, better results)

2. **Docker Strategy**:
   - [ ] Build custom image based on our working base (recommended)
   - [ ] Debug the official image (time-consuming)

3. **GPU Memory Management**:
   - LivePortrait + MuseTalk must share Tesla T4's 16GB VRAM
   - Sequential loading with explicit model unloading required
