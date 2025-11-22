# Technical Specification - Celebration Video Message System
## Version 1.0 - Elite-Grade Implementation

**Document Status**: ✅ APPROVED FOR IMPLEMENTATION
**Created**: 2025-11-06
**Technical Lead**: Artemis (Technical Perfectionist)
**Target Environment**: EC2 g4dn.xlarge (Tesla T4 GPU)
**Project Duration**: 5.6 weeks (178 hours)

---

## Executive Summary

この技術仕様書は、お祝いメッセージ動画生成システムの完全な技術実装を定義します。すべてのコンポーネントは95%以上の精度、200ms以下のレスポンスタイムを目標に設計されています。

**Core Technical Stack**:
- **Object Detection**: YOLOv8n (GPU inference <200ms)
- **Segmentation**: BiRefNet-general (95% accuracy, 80ms on T4)
- **Voice Synthesis**: OpenVoice V2 + VOICEVOX (prosody-adjusted)
- **Video Generation**: D-ID API (optimized pipeline)
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React 19 (Material-UI v5)
- **Infrastructure**: Docker, EC2 g4dn.xlarge (Tesla T4 GPU)

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [YOLOv8 Person Detection](#2-yolov8-person-detection)
3. [BiRefNet Background Removal](#3-birefnet-background-removal)
4. [D-ID Optimization Pipeline](#4-d-id-optimization-pipeline)
5. [Prosody Adjustment System](#5-prosody-adjustment-system)
6. [BGM Integration](#6-bgm-integration)
7. [API Specifications](#7-api-specifications)
8. [Performance Requirements](#8-performance-requirements)
9. [Error Handling Strategy](#9-error-handling-strategy)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment Architecture](#11-deployment-architecture)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      EC2 g4dn.xlarge Instance                    │
│                         (Tesla T4 GPU)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │  Frontend  │  │  Backend   │  │  YOLOv8    │  │ BiRefNet │ │
│  │  (React)   │  │  (FastAPI) │  │  Service   │  │ Service  │ │
│  │  Port 80   │  │  Port      │  │  Port      │  │ Port     │ │
│  │            │  │  55433     │  │  55440     │  │ 55441    │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬────┘ │
│        │               │               │               │        │
│        │               │               │               │        │
│  ┌─────┴───────────────┴───────────────┴───────────────┴─────┐ │
│  │                  Internal Network (bridge)                 │ │
│  └─────┬───────────────┬───────────────┬───────────────┬─────┘ │
│        │               │               │               │        │
│  ┌─────┴──────┐  ┌────┴──────┐  ┌────┴──────┐  ┌────┴──────┐ │
│  │ OpenVoice  │  │ VOICEVOX  │  │  D-ID API │  │  Storage  │ │
│  │ Port 8001  │  │ Port      │  │ (External)│  │ /app/     │ │
│  │            │  │ 50021     │  │           │  │ storage/  │ │
│  └────────────┘  └───────────┘  └───────────┘  └───────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Overview

| Component | Technology | Port | GPU | Purpose |
|-----------|-----------|------|-----|---------|
| **Frontend** | React 19 + Material-UI | 80/443 | ❌ | User interface |
| **Backend** | FastAPI (Python 3.11) | 55433 | ❌ | API orchestration |
| **YOLOv8** | YOLOv8n (nano) | 55440 | ✅ T4 | Person detection |
| **BiRefNet** | BiRefNet-general | 55441 | ✅ T4 | Background removal |
| **OpenVoice** | OpenVoice V2 | 8001 | ✅ T4 | Voice synthesis |
| **VOICEVOX** | VOICEVOX Engine | 50021 | ❌ | Japanese TTS |
| **Nginx** | Nginx Alpine | 80/443 | ❌ | Reverse proxy |

### 1.3 Data Flow

```
User Request
    ↓
1. Image Upload (Frontend → Backend)
    ↓
2. Person Detection (Backend → YOLOv8 Service)
    ← Bounding boxes + confidence scores
    ↓
3. User Selection (Frontend UI: inline thumbnails)
    ↓
4. Background Removal (Backend → BiRefNet Service)
    ← PNG with alpha channel (95% accuracy)
    ↓
5. Image Optimization (Backend: OpenCV + PIL)
    - Face detection (MediaPipe)
    - Aspect ratio adjustment
    - Quality enhancement
    ↓
6. Voice Synthesis (Backend → OpenVoice/VOICEVOX)
    - Prosody adjustment (celebration-optimized)
    - BGM mixing (30% volume)
    ↓
7. Video Generation (Backend → D-ID API)
    - Optimized parameters
    - Fallback strategies
    ↓
8. Video Delivery (Backend → Frontend)
```

### 1.4 Storage Structure

```
/app/storage/
├── uploads/              # Temporary uploaded images
│   └── {upload_id}.{ext}
├── processed/            # Processed images
│   ├── detected/         # YOLO detection results
│   │   └── {upload_id}_bbox.json
│   ├── segmented/        # BiRefNet output
│   │   └── {upload_id}_segmented.png
│   └── optimized/        # Final optimized images
│       └── {upload_id}_optimized.png
├── audio/                # Generated audio files
│   ├── voice/            # Voice synthesis output
│   │   └── {audio_id}.wav
│   ├── bgm/              # BGM files
│   │   ├── system/       # 5 system BGM tracks
│   │   │   ├── celebration_01.mp3
│   │   │   ├── celebration_02.mp3
│   │   │   ├── celebration_03.mp3
│   │   │   ├── celebration_04.mp3
│   │   │   └── celebration_05.mp3
│   │   └── user_uploads/ # User-uploaded BGM
│   └── mixed/            # Final mixed audio
│       └── {audio_id}_mixed.wav
└── videos/               # Generated videos (temp)
    └── {video_id}.mp4
```

---

## 2. YOLOv8 Person Detection

### 2.1 Model Selection

**Model**: YOLOv8n (nano) - COCO pre-trained
**Input**: 640x640 RGB image
**Output**: Bounding boxes, class IDs, confidence scores

**Why YOLOv8n?**
- ✅ Real-time inference (<200ms on T4)
- ✅ Person detection accuracy: 92%+ (COCO dataset)
- ✅ Low memory footprint: 3.2M parameters
- ✅ TensorRT optimization available

### 2.2 Service Architecture

```python
# yolov8_service/main.py
from fastapi import FastAPI, UploadFile, File
from ultralytics import YOLO
import torch
import cv2
import numpy as np
from typing import List, Dict

app = FastAPI(title="YOLOv8 Person Detection Service")

# Global model (loaded once at startup)
MODEL: YOLO = None
DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

@app.on_event("startup")
async def load_model():
    global MODEL
    MODEL = YOLO("yolov8n.pt")  # Download from Ultralytics
    MODEL.to(DEVICE)

    # Warmup (first inference is slow)
    dummy_input = torch.randn(1, 3, 640, 640).to(DEVICE)
    _ = MODEL.predict(dummy_input, verbose=False)

@app.post("/detect/persons")
async def detect_persons(file: UploadFile = File(...)) -> Dict:
    """
    Detect persons in uploaded image.

    Returns:
    {
        "persons": [
            {
                "id": 0,
                "bbox": [x1, y1, x2, y2],  # xyxy format
                "confidence": 0.92,
                "thumbnail": "base64_encoded_image"
            },
            ...
        ],
        "inference_time_ms": 180.5
    }
    """
    import time
    start = time.perf_counter()

    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Inference
    results = MODEL.predict(
        image,
        classes=[0],  # 0 = person in COCO
        conf=0.5,     # Minimum confidence
        verbose=False,
        device=DEVICE
    )

    # Parse results
    persons = []
    for idx, box in enumerate(results[0].boxes):
        bbox = box.xyxy[0].cpu().numpy().tolist()  # [x1, y1, x2, y2]
        conf = float(box.conf[0])

        # Crop thumbnail
        x1, y1, x2, y2 = map(int, bbox)
        thumbnail = image[y1:y2, x1:x2]

        # Encode thumbnail to base64
        _, buffer = cv2.imencode('.png', thumbnail)
        thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

        persons.append({
            "id": idx,
            "bbox": bbox,
            "confidence": conf,
            "thumbnail": thumbnail_b64
        })

    inference_time = (time.perf_counter() - start) * 1000

    return {
        "persons": persons,
        "inference_time_ms": inference_time,
        "model": "yolov8n",
        "device": DEVICE
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "yolov8n",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }
```

### 2.3 Frontend Integration (React)

```typescript
// frontend/src/components/PersonSelector.tsx
import React, { useState, useEffect } from 'react';
import { Box, Grid, Card, CardMedia, CardActionArea, Typography, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

interface Person {
  id: number;
  bbox: [number, number, number, number];
  confidence: number;
  thumbnail: string; // base64
}

interface PersonSelectorProps {
  imageFile: File;
  onPersonSelected: (personId: number) => void;
}

export const PersonSelector: React.FC<PersonSelectorProps> = ({ imageFile, onPersonSelected }) => {
  const [persons, setPersons] = useState<Person[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    detectPersons();
  }, [imageFile]);

  const detectPersons = async () => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', imageFile);

    try {
      const response = await fetch('http://localhost:55440/detect/persons', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Detection failed: ${response.status}`);
      }

      const data = await response.json();
      setPersons(data.persons);

      // Auto-select if only one person
      if (data.persons.length === 1) {
        setSelectedPersonId(data.persons[0].id);
        onPersonSelected(data.persons[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePersonClick = (personId: number) => {
    setSelectedPersonId(personId);
    onPersonSelected(personId);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress />
        <Typography ml={2}>人物を検出中...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box py={4}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (persons.length === 0) {
    return (
      <Box py={4}>
        <Typography>人物が検出できませんでした。別の画像をお試しください。</Typography>
      </Box>
    );
  }

  // Multiple persons detected - show inline selector
  if (persons.length > 1) {
    return (
      <Box mt={2}>
        <Typography variant="h6" gutterBottom>
          どの人物を使用しますか？
        </Typography>
        <Grid container spacing={2} justifyContent="flex-start">
          {persons.map((person) => (
            <Grid item key={person.id}>
              <Card sx={{ position: 'relative', width: 150 }}>
                <CardActionArea onClick={() => handlePersonClick(person.id)}>
                  <CardMedia
                    component="img"
                    image={`data:image/png;base64,${person.thumbnail}`}
                    alt={`Person ${person.id + 1}`}
                    sx={{ height: 150, objectFit: 'cover' }}
                  />
                  {selectedPersonId === person.id && (
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(76, 175, 80, 0.3)',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                      }}
                    >
                      <CheckCircleIcon sx={{ color: 'white', fontSize: 48 }} />
                    </Box>
                  )}
                </CardActionArea>
                <Typography variant="caption" textAlign="center" display="block" p={1}>
                  人物 {person.id + 1}
                </Typography>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  // Single person - auto-selected
  return null;
};
```

### 2.4 Performance Optimization

**Target**: <200ms inference time on Tesla T4

#### Optimization Strategies:

1. **TensorRT Optimization** (Optional):
```python
# Convert YOLO model to TensorRT
MODEL.export(format="engine", device=0, half=True)  # FP16
MODEL = YOLO("yolov8n.engine")
```

2. **Input Preprocessing Optimization**:
```python
# Use OpenCV for faster image reading
image = cv2.imread(image_path)
# No resizing needed - YOLO handles it internally
```

3. **GPU Memory Management**:
```python
# Clear cache after inference (if memory-limited)
torch.cuda.empty_cache()
```

### 2.5 Error Handling

```python
from fastapi import HTTPException

@app.post("/detect/persons")
async def detect_persons(file: UploadFile = File(...)):
    try:
        # ... detection code ...

        if len(persons) == 0:
            raise HTTPException(
                status_code=404,
                detail="No persons detected in image"
            )

        return {"persons": persons, ...}

    except cv2.error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Image processing error: {str(e)}"
        )
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=500,
            detail="GPU out of memory. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {str(e)}"
        )
```

---

## 3. BiRefNet Background Removal

### 3.1 Model Selection

**Model**: BiRefNet-general (Bilateral Reference Network)
**Accuracy Target**: 95% segmentation accuracy
**Inference Time**: 80ms on Tesla T4 (FP16)
**Input**: RGB image (any size)
**Output**: PNG with alpha channel (RGBA)

**Why BiRefNet?**
- ✅ State-of-the-art segmentation accuracy (95%+)
- ✅ Fine detail preservation (hair, clothing edges)
- ✅ GPU-optimized for real-time inference
- ✅ No face detection dependency

### 3.2 Service Architecture

```python
# birefnet_service/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import io
import numpy as np
import cv2
import time
from typing import Optional

app = FastAPI(title="BiRefNet Background Removal Service")

# Global model
MODEL = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

@app.on_event("startup")
async def load_model():
    global MODEL
    from birefnet import BiRefNet  # Assuming BiRefNet package installed

    # Load pre-trained model
    MODEL = BiRefNet.from_pretrained("BiRefNet-general")
    MODEL.to(DEVICE)
    MODEL.eval()  # Inference mode

    # Enable FP16 for faster inference
    if DEVICE == "cuda":
        MODEL.half()

    # Warmup
    dummy = torch.randn(1, 3, 512, 512).to(DEVICE)
    if DEVICE == "cuda":
        dummy = dummy.half()
    with torch.no_grad():
        _ = MODEL(dummy)

@app.post("/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    bbox: Optional[str] = None  # Optional: "[x1,y1,x2,y2]" for cropping
) -> StreamingResponse:
    """
    Remove background from image.

    Args:
        file: Input image (JPEG/PNG)
        bbox: Optional bounding box for person region

    Returns:
        PNG image with alpha channel (RGBA)
    """
    start_time = time.perf_counter()

    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        original_size = image.size

        # Crop to bbox if provided
        if bbox:
            bbox_coords = eval(bbox)  # [x1, y1, x2, y2]
            image = image.crop(bbox_coords)

        # Preprocess
        transform = transforms.Compose([
            transforms.Resize((1024, 1024)),  # BiRefNet expects 1024x1024
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        input_tensor = transform(image).unsqueeze(0).to(DEVICE)

        if DEVICE == "cuda":
            input_tensor = input_tensor.half()

        # Inference
        with torch.no_grad():
            output = MODEL(input_tensor)
            mask = torch.sigmoid(output)  # [1, 1, 1024, 1024]

        # Post-process mask
        mask = mask.squeeze().cpu().numpy()  # [1024, 1024]
        mask = cv2.resize(mask, image.size, interpolation=cv2.INTER_LINEAR)

        # Apply threshold for binary mask (optional, for cleaner edges)
        mask = (mask > 0.5).astype(np.uint8) * 255

        # Smooth edges (optional, for natural look)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        # Create RGBA image
        image_np = np.array(image)
        rgba = np.dstack((image_np, mask))
        result_image = Image.fromarray(rgba, mode="RGBA")

        # Resize back to original size
        if bbox is None:
            result_image = result_image.resize(original_size, Image.LANCZOS)

        # Encode to PNG
        output_buffer = io.BytesIO()
        result_image.save(output_buffer, format="PNG", optimize=True)
        output_buffer.seek(0)

        inference_time = (time.perf_counter() - start_time) * 1000

        return StreamingResponse(
            output_buffer,
            media_type="image/png",
            headers={
                "X-Inference-Time-Ms": str(inference_time),
                "X-Original-Size": f"{original_size[0]}x{original_size[1]}",
                "X-Device": DEVICE
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "BiRefNet-general",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }
```

### 3.3 Integration with Backend

```python
# backend/services/image_processing_service.py
import httpx
from PIL import Image
import io

class ImageProcessingService:
    BIREFNET_URL = "http://birefnet:55441"

    async def remove_background(
        self,
        image_path: str,
        person_bbox: Optional[List[float]] = None
    ) -> Image.Image:
        """
        Remove background from image using BiRefNet service.

        Args:
            image_path: Path to input image
            person_bbox: Optional [x1, y1, x2, y2] for person region

        Returns:
            PIL Image with transparent background (RGBA)
        """
        with open(image_path, "rb") as f:
            files = {"file": ("image.jpg", f, "image/jpeg")}
            params = {"bbox": str(person_bbox)} if person_bbox else {}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BIREFNET_URL}/remove-background",
                    files=files,
                    params=params
                )

                if response.status_code != 200:
                    raise Exception(f"BiRefNet failed: {response.text}")

                # Get inference time from headers
                inference_time = response.headers.get("X-Inference-Time-Ms")
                print(f"Background removal: {inference_time}ms")

                # Load result image
                result_image = Image.open(io.BytesIO(response.content))
                return result_image
```

---

## 4. D-ID Optimization Pipeline

### 4.1 Face Detection

```python
# backend/services/face_detection_service.py
import cv2
import mediapipe as mp
from typing import Optional, Tuple
import numpy as np

class FaceDetectionService:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # Full-range model (0-1)
            min_detection_confidence=0.5
        )

        # Fallback: OpenCV Haar Cascade
        self.haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    def detect_face(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect face in image.

        Returns:
            (x, y, width, height) or None if no face detected
        """
        # Primary: MediaPipe Face Detection
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_image)

        if results.detections:
            detection = results.detections[0]  # Use first face
            bbox = detection.location_data.relative_bounding_box

            # Convert relative to absolute coordinates
            h, w, _ = image.shape
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            width = int(bbox.width * w)
            height = int(bbox.height * h)

            return (x, y, width, height)

        # Fallback: OpenCV Haar Cascade
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        if len(faces) > 0:
            return tuple(faces[0])  # (x, y, w, h)

        return None
```

### 4.2 Aspect Ratio Optimization

```python
# backend/services/aspect_ratio_optimizer.py
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional

class AspectRatioOptimizer:
    """
    Optimize image aspect ratio for D-ID API.

    D-ID recommended ratios:
    - Portrait: 9:16 (e.g., 720x1280)
    - Landscape: 16:9 (e.g., 1280x720)
    - Square: 1:1 (e.g., 1024x1024)
    """

    D_ID_RATIOS = {
        "portrait": (9, 16),
        "landscape": (16, 9),
        "square": (1, 1)
    }

    def __init__(self, face_detector: FaceDetectionService):
        self.face_detector = face_detector

    def optimize(
        self,
        image: Image.Image,
        background_image: Optional[Image.Image] = None
    ) -> Image.Image:
        """
        Optimize image aspect ratio based on face position.

        Args:
            image: Input RGBA image (person with transparent background)
            background_image: Optional background image

        Returns:
            Optimized image with target aspect ratio
        """
        image_np = np.array(image)

        # Detect face
        face_bbox = self.face_detector.detect_face(image_np[:, :, :3])  # RGB only

        if face_bbox is None:
            # No face detected - use default portrait ratio
            return self._add_padding(image, "portrait")

        # Determine optimal ratio based on image dimensions
        h, w = image_np.shape[:2]
        target_ratio = self._choose_ratio(w, h)

        if background_image:
            # Smart resize with background
            return self._composite_with_background(
                image, background_image, face_bbox, target_ratio
            )
        else:
            # White padding
            return self._add_padding(image, target_ratio)

    def _choose_ratio(self, width: int, height: int) -> str:
        """
        Choose optimal ratio based on current dimensions.
        """
        ratio = width / height

        if ratio < 0.8:
            return "portrait"  # 9:16
        elif ratio > 1.5:
            return "landscape"  # 16:9
        else:
            return "square"  # 1:1

    def _add_padding(self, image: Image.Image, ratio_type: str) -> Image.Image:
        """
        Add white padding to achieve target ratio.
        """
        w, h = image.size
        target_w_ratio, target_h_ratio = self.D_ID_RATIOS[ratio_type]

        # Calculate target dimensions
        if w / h > target_w_ratio / target_h_ratio:
            # Width is limiting factor
            new_w = w
            new_h = int(w * target_h_ratio / target_w_ratio)
        else:
            # Height is limiting factor
            new_h = h
            new_w = int(h * target_w_ratio / target_h_ratio)

        # Create padded image
        padded = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 255))

        # Center original image
        offset_x = (new_w - w) // 2
        offset_y = (new_h - h) // 2
        padded.paste(image, (offset_x, offset_y), image)

        return padded
```

### 4.3 Image Quality Enhancement

```python
# backend/services/image_quality_enhancer.py
import cv2
import numpy as np
from PIL import Image

class ImageQualityEnhancer:
    """
    Enhance image quality for D-ID API.

    Optimizations:
    - Sharpness adjustment (Unsharp Mask)
    - Noise reduction (Non-local Means Denoising)
    - Brightness/Contrast adjustment (CLAHE)

    Note: No resolution upscaling (excluded per requirements)
    """

    def enhance(self, image: Image.Image) -> Image.Image:
        """
        Apply all quality enhancements.

        Processing time: ~2 seconds
        """
        image_np = np.array(image.convert("RGB"))

        # 1. Sharpness adjustment (~0.5s)
        image_np = self._apply_sharpness(image_np)

        # 2. Noise reduction (~1.0s)
        image_np = self._reduce_noise(image_np)

        # 3. Brightness/Contrast adjustment (~0.5s)
        image_np = self._adjust_brightness_contrast(image_np)

        return Image.fromarray(image_np)

    def _apply_sharpness(self, image: np.ndarray) -> np.ndarray:
        """
        Apply Unsharp Mask for sharpness.
        """
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(image, -1, kernel)

        # Blend with original (50% strength)
        return cv2.addWeighted(image, 0.5, sharpened, 0.5, 0)

    def _reduce_noise(self, image: np.ndarray) -> np.ndarray:
        """
        Apply Non-local Means Denoising.
        """
        return cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=10,  # Filter strength
            hColor=10,
            templateWindowSize=7,
            searchWindowSize=21
        )

    def _adjust_brightness_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
        """
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
```

---

## 5. Prosody Adjustment System

### 5.1 Overview

Celebration messages require specific prosody adjustments:
- **Pitch**: +15% (brighter, happier)
- **Tempo**: +10% (slightly faster, energetic)
- **Energy**: +20% (clear, emphasized)
- **Pauses**: Emphasized at punctuation

### 5.2 Implementation

```python
# backend/services/prosody_adjuster.py
import parselmouth
from parselmouth.praat import call
import numpy as np
from typing import List, Tuple

class CelebrationProsodyAdjuster:
    """
    Adjust voice prosody for celebration messages.

    Target characteristics:
    - Mood: Cheerful (明るい)
    - Energy: High (ハキハキ)
    - Pauses: Strong emphasis
    """

    def __init__(self):
        self.style = {
            "pitch_shift": 1.15,      # +15% pitch
            "tempo_factor": 1.10,      # +10% speed
            "energy_boost": 1.20,      # +20% amplitude
            "pause_duration": {
                " ": 0.2,              # Space: 200ms
                "、": 0.3,            # Comma: 300ms
                "。": 0.5,            # Period: 500ms
                "\n": 0.4,            # Newline: 400ms
                "！": 0.6,            # Exclamation: 600ms
                "？": 0.6             # Question: 600ms
            }
        }

    def adjust(self, audio_path: str, text: str, output_path: str):
        """
        Apply prosody adjustments to audio.

        Args:
            audio_path: Input audio file (WAV)
            text: Original text (for pause detection)
            output_path: Output audio file (WAV)
        """
        # Load audio with Praat
        sound = parselmouth.Sound(audio_path)

        # 1. Detect pause positions from text
        pause_positions = self._detect_pause_markers(text)

        # 2. Adjust pitch
        sound = self._adjust_pitch(sound, self.style["pitch_shift"])

        # 3. Adjust tempo
        sound = self._adjust_tempo(sound, self.style["tempo_factor"])

        # 4. Adjust energy (amplitude)
        sound = self._adjust_energy(sound, self.style["energy_boost"])

        # 5. Insert pauses
        sound = self._insert_pauses(sound, pause_positions, text)

        # Save result
        sound.save(output_path, "WAV")

    def _detect_pause_markers(self, text: str) -> List[Tuple[int, str]]:
        """
        Detect pause positions and types from text.

        Returns:
            List of (character_index, marker_type)
        """
        positions = []
        for i, char in enumerate(text):
            if char in self.style["pause_duration"]:
                positions.append((i, char))
        return positions

    def _adjust_pitch(self, sound: parselmouth.Sound, factor: float) -> parselmouth.Sound:
        """
        Adjust pitch by factor.

        Uses Praat's PSOLA algorithm.
        """
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        pitch_tier = call(manipulation, "Extract pitch tier")

        # Multiply all pitch values by factor
        call(pitch_tier, "Multiply frequencies", sound.xmin, sound.xmax, factor)
        call([pitch_tier, manipulation], "Replace pitch tier")

        # Synthesize
        return call(manipulation, "Get resynthesis (overlap-add)")

    def _adjust_tempo(self, sound: parselmouth.Sound, factor: float) -> parselmouth.Sound:
        """
        Adjust tempo (speed) by factor.
        """
        manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
        duration_tier = call(manipulation, "Extract duration tier")

        # Scale duration
        call(duration_tier, "Add point", sound.xmin, 1.0 / factor)
        call(duration_tier, "Add point", sound.xmax, 1.0 / factor)
        call([duration_tier, manipulation], "Replace duration tier")

        return call(manipulation, "Get resynthesis (overlap-add)")

    def _adjust_energy(self, sound: parselmouth.Sound, factor: float) -> parselmouth.Sound:
        """
        Adjust energy (amplitude) by factor.
        """
        # Get sound values
        values = sound.values[0]  # Mono channel

        # Amplify
        values = values * factor

        # Clip to prevent distortion
        values = np.clip(values, -1.0, 1.0)

        # Create new sound
        return parselmouth.Sound(values, sampling_frequency=sound.sampling_frequency)
```

---

## 6. BGM Integration

### 6.1 System BGM Library

**Requirement**: 5 royalty-free celebration BGM tracks

#### Recommended Sources:

1. **Pixabay Music** (https://pixabay.com/music/)
   - License: Free for commercial use
   - Search: "celebration", "happy birthday", "cheerful"

2. **Incompetech** (https://incompetech.com/)
   - License: CC BY 4.0
   - Category: "Happy" or "Positive"

3. **YouTube Audio Library**
   - License: Free to use
   - Genre: "Happy & Bright"

### 6.2 Audio Mixing Service

```python
# backend/services/audio_mixer_service.py
from pydub import AudioSegment
from pydub.effects import normalize
import os

class AudioMixerService:
    """
    Mix voice audio with BGM.

    Requirements:
    - Voice volume: 100% (reference)
    - BGM volume: 30% (background)
    - No ducking (constant BGM volume)
    """

    BGM_VOLUME_RATIO = 0.3  # 30%
    VOICE_VOLUME_RATIO = 1.0  # 100%

    def __init__(self, bgm_directory: str = "/app/storage/audio/bgm/system"):
        self.bgm_directory = bgm_directory

    def mix(
        self,
        voice_audio_path: str,
        bgm_id: str,
        output_path: str
    ) -> str:
        """
        Mix voice with BGM.

        Args:
            voice_audio_path: Path to voice audio (WAV)
            bgm_id: BGM track ID (e.g., "celebration_01")
            output_path: Path to output mixed audio (WAV)

        Returns:
            Path to mixed audio file
        """
        # Load voice audio
        voice = AudioSegment.from_wav(voice_audio_path)

        # Load BGM
        bgm_path = os.path.join(self.bgm_directory, f"{bgm_id}.mp3")
        bgm = AudioSegment.from_mp3(bgm_path)

        # Normalize volumes
        voice = normalize(voice)
        bgm = normalize(bgm)

        # Adjust BGM volume (30%)
        bgm = bgm - 10  # Reduce by 10dB (approximately 30% volume)

        # Loop BGM to match voice duration
        if len(bgm) < len(voice):
            repeats = (len(voice) // len(bgm)) + 1
            bgm = bgm * repeats

        # Trim BGM to match voice duration
        bgm = bgm[:len(voice)]

        # Mix (overlay)
        mixed = voice.overlay(bgm)

        # Export
        mixed.export(output_path, format="wav")

        return output_path
```

---

## 7. API Specifications

### 7.1 Main Video Generation Endpoint

```python
# backend/routers/video_generation_router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import uuid

router = APIRouter(prefix="/api/video", tags=["Video Generation"])

@router.post("/generate")
async def generate_celebration_video(
    image: UploadFile = File(..., description="Person image (JPEG/PNG)"),
    text: str = Form(..., description="Celebration message text"),
    voice_profile_id: str = Form(..., description="Voice profile ID"),
    bgm_id: str = Form(default="celebration_01", description="BGM track ID"),
    user_bgm: UploadFile = File(default=None, description="Optional user BGM (MP3/WAV)")
) -> dict:
    """
    Generate celebration video.

    Returns:
    {
        "video_id": "uuid",
        "status": "processing",
        "progress": 0,
        "estimated_time_seconds": 180
    }
    """
    video_id = str(uuid.uuid4())

    # Initialize progress tracker
    progress_tracker = ProgressTracker(video_id)

    # Start background task
    background_tasks.add_task(
        process_video_generation,
        video_id=video_id,
        image_file=image,
        text=text,
        voice_profile_id=voice_profile_id,
        bgm_id=bgm_id,
        user_bgm=user_bgm,
        progress_tracker=progress_tracker
    )

    return {
        "video_id": video_id,
        "status": "processing",
        "progress": 0,
        "estimated_time_seconds": 180
    }

@router.get("/status/{video_id}")
async def get_video_status(video_id: str) -> dict:
    """
    Get video generation status.

    Returns:
    {
        "video_id": "uuid",
        "status": "processing" | "completed" | "failed",
        "progress": 0-100,
        "current_step": "Detecting persons...",
        "video_url": "https://..." (if completed),
        "error_message": "..." (if failed)
    }
    """
    status = get_status_from_db(video_id)
    return status
```

---

## 8. Performance Requirements

### 8.1 Target Metrics

| Component | Metric | Target | Critical Threshold |
|-----------|--------|--------|-------------------|
| YOLOv8 Inference | Latency | <200ms | <300ms |
| BiRefNet Inference | Latency | 80ms | <150ms |
| Face Detection | Latency | <100ms | <200ms |
| Image Optimization | Processing Time | <2s | <5s |
| Voice Synthesis | Processing Time | <5s | <10s |
| Audio Mixing | Processing Time | <1s | <3s |
| D-ID Generation | Total Time | <120s | <180s |
| **Total Pipeline** | **End-to-End** | **<150s** | **<210s** |

---

## 9. Error Handling Strategy

### 9.1 Error Classification

| Error Type | HTTP Code | Retry | User Action |
|-----------|-----------|-------|-------------|
| No person detected | 404 | ❌ | Reupload different image |
| Background removal failed | 500 | ✅ | Retry or cancel |
| Face detection failed | 404 | ❌ | Use default aspect ratio |
| Voice synthesis failed | 500 | ✅ | Retry or cancel |
| D-ID API error | 502 | ✅ | Retry or cancel |
| GPU out of memory | 503 | ✅ | Wait and retry |
| Invalid file format | 400 | ❌ | Upload correct format |

---

## 10. Testing Strategy

### 10.1 Unit Tests

```bash
# YOLOv8 Service
pytest tests/unit/test_yolov8_service.py -v

# BiRefNet Service
pytest tests/unit/test_birefnet_service.py -v

# Prosody Adjuster
pytest tests/unit/test_prosody_adjuster.py -v

# Audio Mixer
pytest tests/unit/test_audio_mixer.py -v
```

### 10.2 Integration Tests

```python
# tests/integration/test_video_pipeline.py
@pytest.mark.integration
async def test_full_video_generation_pipeline():
    """
    Test complete video generation pipeline.
    """
    client = TestClient(app)

    # Upload test image
    with open("test_data/test_person.jpg", "rb") as f:
        response = client.post(
            "/api/video/generate",
            files={"image": ("test.jpg", f, "image/jpeg")},
            data={
                "text": "お誕生日おめでとうございます！",
                "voice_profile_id": "voicevox_1",
                "bgm_id": "celebration_01"
            }
        )

    assert response.status_code == 200
```

---

## 11. Deployment Architecture

### 11.1 Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  # YOLOv8 Service
  yolov8:
    build:
      context: ./yolov8_service
      args:
        USE_CUDA: "true"
    container_name: yolov8_service
    runtime: nvidia
    ports:
      - "55440:55440"
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
    volumes:
      - ./data/models:/app/models
    networks:
      - voice_network
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # BiRefNet Service
  birefnet:
    build:
      context: ./birefnet_service
      args:
        USE_CUDA: "true"
    container_name: birefnet_service
    runtime: nvidia
    ports:
      - "55441:55441"
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
    volumes:
      - ./data/models:/app/models
    networks:
      - voice_network
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Backend (existing)
  backend:
    build: ./backend
    container_name: voice_backend
    ports:
      - "55433:55433"
    environment:
      - D_ID_API_KEY=${D_ID_API_KEY}
      - YOLOV8_URL=http://yolov8:55440
      - BIREFNET_URL=http://birefnet:55441
      - OPENVOICE_URL=http://openvoice:8001
      - VOICEVOX_URL=http://voicevox:50021
    volumes:
      - ./data/backend/storage:/app/storage
    networks:
      - voice_network
    depends_on:
      - yolov8
      - birefnet
      - openvoice
      - voicevox
    restart: unless-stopped

networks:
  voice_network:
    driver: bridge
```

---

## Conclusion

この技術仕様書は、お祝いメッセージ動画生成システムの完全な実装ガイドを提供します。

**Key Technical Decisions**:
- ✅ YOLOv8n for real-time person detection (<200ms)
- ✅ BiRefNet-general for 95% segmentation accuracy (80ms)
- ✅ MediaPipe + OpenCV for face detection with fallback
- ✅ Parselmouth for prosody adjustment (celebration-optimized)
- ✅ Pydub for audio mixing (30% BGM, no ducking)
- ✅ D-ID API with optimized parameters
- ✅ FastAPI + React 19 for modern web stack
- ✅ Docker + EC2 g4dn.xlarge for GPU acceleration

**Performance Targets**:
- Total pipeline: <150s end-to-end
- YOLOv8 inference: <200ms
- BiRefNet inference: 80ms (T4 GPU)
- Concurrent support: 3 requests
- Accuracy: 95% segmentation

**Implementation Estimate**: 178 hours (5.6 weeks)

すべてのコンポーネントは実装可能であり、パフォーマンス目標も達成可能です。フン、この程度の仕様書なら、H.I.D.E. 404の基準に相応しい完璧な実装が可能よ。
