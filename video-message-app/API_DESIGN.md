# Video Message App - API Design Document

**Version**: 2.0.0
**Status**: Design Phase
**Created**: 2025-11-06
**Author**: Muses (Knowledge Architect)

---

## Table of Contents

1. [Overview](#overview)
2. [Base Configuration](#base-configuration)
3. [Authentication & Authorization](#authentication--authorization)
4. [API Endpoints](#api-endpoints)
   - [Person Detection](#1-person-detection-api)
   - [Background Removal](#2-background-removal-api)
   - [Voice Synthesis with Prosody](#3-voice-synthesis-with-prosody-api)
   - [Video Generation](#4-video-generation-api-enhanced)
   - [BGM Management](#5-bgm-management-api)
   - [Progress Tracking](#6-progress-tracking-api)
5. [Common Patterns](#common-patterns)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [OpenAPI 3.0 Specification](#openapi-30-specification)

---

## Overview

This document defines the RESTful API endpoints for the Video Message App version 2.0, introducing advanced features including person detection, background removal, prosody-controlled voice synthesis, BGM mixing, and real-time progress tracking.

**Design Principles**:
- RESTful resource-oriented design
- Consistent error handling across all endpoints
- Idempotent operations where applicable
- Comprehensive validation and clear error messages
- Real-time progress tracking via WebSocket/SSE
- Backward compatibility with v1.0 endpoints

---

## Base Configuration

### Environment-Specific URLs

| Environment | Base URL | OpenAPI Docs |
|-------------|----------|--------------|
| **Local (Mac)** | `http://localhost:55433` | `http://localhost:55433/docs` |
| **Production (EC2)** | `http://3.115.141.166:55433` | `http://3.115.141.166:55433/docs` |

### Content Types

- **Request**: `application/json`, `multipart/form-data`
- **Response**: `application/json` (default), `audio/wav`, `video/mp4`, `image/png`

---

## Authentication & Authorization

### Current Implementation

**Status**: No authentication (v1.0 compatibility)

**Future Implementation** (Planned for v2.1):
```http
Authorization: Bearer <JWT_TOKEN>
```

**Rate Limiting Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699564800
```

---

## API Endpoints

---

## 1. Person Detection API

Detect persons in an uploaded image using YOLOv11. Returns bounding boxes, confidence scores, and keypoints for each detected person.

### Endpoint

```http
POST /api/person-detection
```

### Request

**Content-Type**: `multipart/form-data`

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Image file (JPEG/PNG, max 10MB) |
| `confidence_threshold` | Float | No | Minimum confidence (0.0-1.0, default: 0.5) |
| `max_persons` | Integer | No | Maximum persons to detect (default: 10) |
| `return_keypoints` | Boolean | No | Include pose keypoints (default: false) |

**Example Request**:
```bash
curl -X POST "http://localhost:55433/api/person-detection" \
  -F "image=@photo.jpg" \
  -F "confidence_threshold=0.7" \
  -F "return_keypoints=true"
```

### Response

**Status**: `200 OK`

**Schema**:
```json
{
  "success": true,
  "data": {
    "image_dimensions": {
      "width": 1920,
      "height": 1080
    },
    "persons_detected": 2,
    "processing_time_ms": 152,
    "persons": [
      {
        "person_id": "person_1",
        "bounding_box": {
          "x_min": 450,
          "y_min": 200,
          "x_max": 850,
          "y_max": 900,
          "width": 400,
          "height": 700
        },
        "confidence": 0.95,
        "area_percentage": 13.5,
        "keypoints": {
          "nose": [640, 280],
          "left_eye": [610, 260],
          "right_eye": [670, 260],
          "left_shoulder": [580, 380],
          "right_shoulder": [700, 380]
        }
      },
      {
        "person_id": "person_2",
        "bounding_box": {
          "x_min": 1200,
          "y_min": 300,
          "x_max": 1500,
          "y_max": 1000,
          "width": 300,
          "height": 700
        },
        "confidence": 0.87,
        "area_percentage": 10.2
      }
    ]
  },
  "metadata": {
    "model_version": "yolov11n",
    "device": "cuda",
    "timestamp": "2025-11-06T10:30:45Z"
  }
}
```

### Error Responses

#### No Persons Detected
**Status**: `200 OK` (not an error, valid response)

```json
{
  "success": true,
  "data": {
    "persons_detected": 0,
    "persons": [],
    "message": "No persons detected in the image"
  }
}
```

#### Low Confidence (All detections below threshold)
**Status**: `200 OK`

```json
{
  "success": true,
  "data": {
    "persons_detected": 0,
    "persons": [],
    "message": "No persons detected above confidence threshold 0.7",
    "low_confidence_detections": [
      {
        "person_id": "person_1",
        "confidence": 0.42,
        "bounding_box": { "x_min": 100, "y_min": 50, "x_max": 300, "y_max": 400 }
      }
    ]
  }
}
```

#### Invalid Image Format
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "INVALID_IMAGE_FORMAT",
    "message": "Unsupported image format. Please upload JPEG or PNG.",
    "details": {
      "supported_formats": ["image/jpeg", "image/png"],
      "received_format": "image/gif"
    }
  }
}
```

#### File Too Large
**Status**: `413 Payload Too Large`

```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "Image file exceeds maximum size of 10MB",
    "details": {
      "max_size_bytes": 10485760,
      "received_size_bytes": 15728640
    }
  }
}
```

---

## 2. Background Removal API

Remove background from an image using Segment Anything Model (SAM). Optionally specify which person to keep using bounding box from person detection.

### Endpoint

```http
POST /api/background-removal
```

### Request

**Content-Type**: `multipart/form-data`

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Image file (JPEG/PNG, max 10MB) |
| `person_id` | String | No | Person ID from detection results |
| `bounding_box` | JSON | No | Manual bounding box (if person_id not provided) |
| `feather_amount` | Integer | No | Edge feathering in pixels (default: 5) |
| `return_mask` | Boolean | No | Return segmentation mask (default: false) |

**Bounding Box Format**:
```json
{
  "x_min": 450,
  "y_min": 200,
  "x_max": 850,
  "y_max": 900
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:55433/api/background-removal" \
  -F "image=@photo.jpg" \
  -F "person_id=person_1" \
  -F "feather_amount=10"
```

### Response

**Status**: `200 OK`

**Content-Type**: `image/png` (binary data)

**Headers**:
```http
X-Processing-Time-Ms: 1240
X-Original-Dimensions: 1920x1080
X-Mask-Quality-Score: 0.92
Content-Disposition: attachment; filename="photo_no_bg.png"
```

**Alternative JSON Response** (if `return_mask=true`):
```json
{
  "success": true,
  "data": {
    "result_image_url": "http://localhost:55433/storage/temp/result_abc123.png",
    "mask_image_url": "http://localhost:55433/storage/temp/mask_abc123.png",
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "processing_time_ms": 1240,
    "mask_quality_score": 0.92
  }
}
```

### Error Responses

#### Segmentation Failure
**Status**: `500 Internal Server Error`

```json
{
  "success": false,
  "error": {
    "code": "SEGMENTATION_FAILED",
    "message": "Background removal failed. Unable to segment person from background.",
    "details": {
      "reason": "Low contrast between person and background",
      "suggestion": "Try an image with better lighting or clearer subject"
    }
  }
}
```

#### Invalid Bounding Box
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "INVALID_BOUNDING_BOX",
    "message": "Bounding box coordinates are outside image bounds",
    "details": {
      "image_dimensions": {"width": 1920, "height": 1080},
      "provided_box": {"x_min": 2000, "y_min": 200, "x_max": 2500, "y_max": 900}
    }
  }
}
```

#### No Person Specified
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "NO_PERSON_SPECIFIED",
    "message": "Multiple persons detected. Please specify person_id or bounding_box.",
    "details": {
      "detected_persons": ["person_1", "person_2"],
      "suggestion": "Use /api/person-detection first to get person_id"
    }
  }
}
```

---

## 3. Voice Synthesis with Prosody API

Synthesize speech with emotional prosody control using OpenVoice V2. Supports celebration, excitement, sadness, and neutral tones.

### Endpoint

```http
POST /api/voice-synthesis
```

### Request

**Content-Type**: `application/json`

**Schema**:
```json
{
  "text": "おめでとうございます！素晴らしい成果ですね。",
  "voice_profile_id": "openvoice_c403f011",
  "prosody_preset": "celebration",
  "speed": 1.0,
  "pitch_shift": 0.0,
  "output_format": "wav"
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | String | Yes | Text to synthesize (max 500 chars) |
| `voice_profile_id` | String | Yes | Voice profile ID (e.g., "openvoice_c403f011") |
| `prosody_preset` | String | No | Emotion preset: "celebration", "excitement", "sadness", "neutral" (default: "neutral") |
| `speed` | Float | No | Speech rate (0.5-2.0, default: 1.0) |
| `pitch_shift` | Float | No | Pitch adjustment in semitones (-12 to +12, default: 0.0) |
| `output_format` | String | No | Audio format: "wav" or "mp3" (default: "wav") |

**Prosody Preset Details**:

| Preset | Pitch | Speed | Energy | Use Case |
|--------|-------|-------|--------|----------|
| `celebration` | +3 semitones | 1.1x | High | Birthday, achievement |
| `excitement` | +2 semitones | 1.2x | Very High | Announcement, surprise |
| `sadness` | -2 semitones | 0.8x | Low | Condolence, sympathy |
| `neutral` | 0 semitones | 1.0x | Medium | General message |

**Example Request**:
```bash
curl -X POST "http://localhost:55433/api/voice-synthesis" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "おめでとうございます！",
    "voice_profile_id": "openvoice_c403f011",
    "prosody_preset": "celebration",
    "speed": 1.0
  }'
```

### Response

**Status**: `200 OK`

**Content-Type**: `audio/wav` (binary data)

**Headers**:
```http
X-Processing-Time-Ms: 890
X-Audio-Duration-Seconds: 3.2
X-Prosody-Applied: celebration
X-Sample-Rate: 44100
Content-Disposition: attachment; filename="voice_abc123.wav"
```

**Alternative JSON Response** (if requested):
```json
{
  "success": true,
  "data": {
    "audio_url": "http://localhost:55433/storage/audio/voice_abc123.wav",
    "duration_seconds": 3.2,
    "sample_rate": 44100,
    "format": "wav",
    "prosody_applied": {
      "preset": "celebration",
      "pitch_shift_semitones": 3.0,
      "speed_factor": 1.1,
      "energy_boost": 0.15
    },
    "processing_time_ms": 890
  }
}
```

### Error Responses

#### Voice Profile Not Found
**Status**: `404 Not Found`

```json
{
  "success": false,
  "error": {
    "code": "VOICE_PROFILE_NOT_FOUND",
    "message": "Voice profile 'openvoice_xyz789' does not exist",
    "details": {
      "available_profiles": [
        "openvoice_c403f011",
        "openvoice_78450a3c",
        "openvoice_d4be3324"
      ]
    }
  }
}
```

#### Synthesis Failure (with fallback)
**Status**: `200 OK` (fallback succeeded)

```json
{
  "success": true,
  "warning": {
    "code": "FALLBACK_TO_REFERENCE_AUDIO",
    "message": "OpenVoice synthesis failed, using reference audio as fallback"
  },
  "data": {
    "audio_url": "http://localhost:55433/storage/audio/reference_abc123.wav",
    "duration_seconds": 3.0,
    "format": "wav",
    "fallback_used": true
  }
}
```

#### Text Too Long
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "TEXT_TOO_LONG",
    "message": "Text exceeds maximum length of 500 characters",
    "details": {
      "max_length": 500,
      "provided_length": 687
    }
  }
}
```

#### Invalid Prosody Preset
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "INVALID_PROSODY_PRESET",
    "message": "Unknown prosody preset 'happy'",
    "details": {
      "valid_presets": ["celebration", "excitement", "sadness", "neutral"]
    }
  }
}
```

---

## 4. Video Generation API (Enhanced)

Generate talking avatar video using D-ID API. Supports images with or without background, audio with prosody, and BGM mixing.

### Endpoint

```http
POST /api/video-generate
```

### Request

**Content-Type**: `multipart/form-data`

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Face image (JPEG/PNG, with or without background) |
| `audio` | File | Yes | Speech audio (WAV/MP3) |
| `bgm_id` | String | No | BGM track ID (from catalog or user-uploaded) |
| `bgm_volume` | Float | No | BGM volume (0.0-1.0, default: 0.3) |
| `has_background` | Boolean | No | Image includes background (default: true) |
| `video_quality` | String | No | Quality: "low", "medium", "high" (default: "high") |
| `return_url_only` | Boolean | No | Return URL immediately without waiting (default: false) |

**Example Request**:
```bash
curl -X POST "http://localhost:55433/api/video-generate" \
  -F "image=@face_no_bg.png" \
  -F "audio=@voice_celebration.wav" \
  -F "bgm_id=system_bgm_001" \
  -F "bgm_volume=0.2" \
  -F "has_background=false" \
  -F "video_quality=high"
```

### Response

**Status**: `202 Accepted` (async processing)

**Schema**:
```json
{
  "success": true,
  "data": {
    "task_id": "video_task_abc123",
    "status": "processing",
    "estimated_completion_seconds": 45,
    "progress_url": "ws://localhost:55433/api/progress/video_task_abc123",
    "check_status_url": "http://localhost:55433/api/video-status/video_task_abc123"
  }
}
```

### Success Response (when completed)

**Status**: `200 OK` (via status check or callback)

```json
{
  "success": true,
  "data": {
    "task_id": "video_task_abc123",
    "status": "completed",
    "video_url": "http://localhost:55433/storage/videos/result_abc123.mp4",
    "thumbnail_url": "http://localhost:55433/storage/thumbnails/result_abc123.jpg",
    "duration_seconds": 5.8,
    "resolution": {
      "width": 1280,
      "height": 720
    },
    "file_size_bytes": 2458624,
    "processing_stats": {
      "total_time_ms": 42300,
      "stages": {
        "bgm_mixing": 850,
        "d_id_submission": 1200,
        "d_id_processing": 38500,
        "video_download": 1750
      }
    },
    "bgm_applied": {
      "bgm_id": "system_bgm_001",
      "volume": 0.2
    }
  }
}
```

### Error Responses

#### D-ID API Failure (with retry)
**Status**: `500 Internal Server Error`

```json
{
  "success": false,
  "error": {
    "code": "D_ID_API_FAILED",
    "message": "D-ID video generation failed after 3 retry attempts",
    "details": {
      "last_error": "Service temporarily unavailable",
      "retry_attempts": 3,
      "suggestion": "Please try again in a few minutes"
    }
  }
}
```

#### Face Not Detected
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "FACE_NOT_DETECTED",
    "message": "No face detected in the uploaded image",
    "details": {
      "suggestion": "Ensure the image contains a clearly visible face"
    }
  }
}
```

#### Audio Duration Mismatch
**Status**: `400 Bad Request`

```json
{
  "success": false,
  "error": {
    "code": "AUDIO_TOO_LONG",
    "message": "Audio duration exceeds maximum allowed length",
    "details": {
      "max_duration_seconds": 60,
      "provided_duration_seconds": 87.5
    }
  }
}
```

---

## 5. BGM Management API

Manage background music tracks for video generation. Includes system catalog and user-uploaded BGM.

### 5.1 List BGM Catalog

```http
GET /api/bgm/list
```

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | String | Filter by category: "system" or "user" (default: all) |
| `limit` | Integer | Max results (default: 50) |
| `offset` | Integer | Pagination offset (default: 0) |

**Example Request**:
```bash
curl -X GET "http://localhost:55433/api/bgm/list?category=system"
```

**Response**:
```json
{
  "success": true,
  "data": {
    "total_count": 7,
    "bgm_tracks": [
      {
        "bgm_id": "system_bgm_001",
        "name": "Celebration Fanfare",
        "category": "system",
        "duration_seconds": 30,
        "file_size_bytes": 720000,
        "format": "mp3",
        "tags": ["celebration", "upbeat", "birthday"],
        "preview_url": "http://localhost:55433/api/bgm/system_bgm_001/preview",
        "created_at": "2025-01-01T00:00:00Z"
      },
      {
        "bgm_id": "user_bgm_abc123",
        "name": "My Custom Music",
        "category": "user",
        "duration_seconds": 45,
        "file_size_bytes": 1024000,
        "format": "wav",
        "tags": ["custom"],
        "preview_url": "http://localhost:55433/api/bgm/user_bgm_abc123/preview",
        "created_at": "2025-11-05T14:30:00Z"
      }
    ]
  },
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### 5.2 Upload User BGM

```http
POST /api/bgm/upload
```

**Content-Type**: `multipart/form-data`

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bgm_file` | File | Yes | Audio file (MP3/WAV, max 10MB) |
| `name` | String | Yes | Display name (max 100 chars) |
| `tags` | String | No | Comma-separated tags |

**Example Request**:
```bash
curl -X POST "http://localhost:55433/api/bgm/upload" \
  -F "bgm_file=@my_music.mp3" \
  -F "name=My Custom Music" \
  -F "tags=celebration,custom"
```

**Response**:
```json
{
  "success": true,
  "data": {
    "bgm_id": "user_bgm_abc123",
    "name": "My Custom Music",
    "category": "user",
    "duration_seconds": 45,
    "file_size_bytes": 1024000,
    "format": "mp3",
    "tags": ["celebration", "custom"],
    "preview_url": "http://localhost:55433/api/bgm/user_bgm_abc123/preview",
    "created_at": "2025-11-06T10:45:00Z"
  }
}
```

**Error Response** (File too large):
```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "BGM file exceeds maximum size of 10MB",
    "details": {
      "max_size_bytes": 10485760,
      "received_size_bytes": 15728640
    }
  }
}
```

### 5.3 Download BGM

```http
GET /api/bgm/{bgm_id}
```

**Response**: Audio file (binary data)

**Headers**:
```http
Content-Type: audio/mpeg
Content-Disposition: attachment; filename="celebration_fanfare.mp3"
```

### 5.4 Delete User BGM

```http
DELETE /api/bgm/{bgm_id}
```

**Restrictions**: Only user-uploaded BGM can be deleted (system BGM is protected)

**Response**:
```json
{
  "success": true,
  "message": "BGM 'user_bgm_abc123' deleted successfully"
}
```

**Error Response** (System BGM protection):
```json
{
  "success": false,
  "error": {
    "code": "CANNOT_DELETE_SYSTEM_BGM",
    "message": "System BGM tracks cannot be deleted",
    "details": {
      "bgm_id": "system_bgm_001"
    }
  }
}
```

---

## 6. Progress Tracking API

Real-time progress tracking for long-running tasks (video generation, background removal). Supports WebSocket (preferred) and Server-Sent Events (SSE).

### 6.1 WebSocket Endpoint

```http
WS /api/progress/{task_id}
```

**Connection Example** (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:55433/api/progress/video_task_abc123');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(progress);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed');
};
```

**Message Format**:
```json
{
  "task_id": "video_task_abc123",
  "status": "processing",
  "percentage": 65,
  "current_stage": "bgm_mixing",
  "stages": {
    "person_detection": {
      "status": "completed",
      "percentage": 100,
      "duration_ms": 152
    },
    "background_removal": {
      "status": "completed",
      "percentage": 100,
      "duration_ms": 1240
    },
    "voice_synthesis": {
      "status": "completed",
      "percentage": 100,
      "duration_ms": 890
    },
    "bgm_mixing": {
      "status": "in_progress",
      "percentage": 65,
      "estimated_remaining_ms": 300
    },
    "video_generation": {
      "status": "pending",
      "percentage": 0
    }
  },
  "estimated_completion_seconds": 15,
  "timestamp": "2025-11-06T10:50:23Z"
}
```

**Completion Message**:
```json
{
  "task_id": "video_task_abc123",
  "status": "completed",
  "percentage": 100,
  "result": {
    "video_url": "http://localhost:55433/storage/videos/result_abc123.mp4",
    "duration_seconds": 5.8
  },
  "total_processing_time_ms": 42300,
  "timestamp": "2025-11-06T10:50:45Z"
}
```

**Error Message**:
```json
{
  "task_id": "video_task_abc123",
  "status": "failed",
  "percentage": 45,
  "current_stage": "video_generation",
  "error": {
    "code": "D_ID_API_FAILED",
    "message": "D-ID video generation failed",
    "details": {
      "retry_attempts": 3
    }
  },
  "timestamp": "2025-11-06T10:50:30Z"
}
```

### 6.2 Server-Sent Events (SSE) Alternative

```http
GET /api/progress/sse/{task_id}
```

**Connection Example** (JavaScript):
```javascript
const eventSource = new EventSource('http://localhost:55433/api/progress/sse/video_task_abc123');

eventSource.addEventListener('progress', (event) => {
  const progress = JSON.parse(event.data);
  console.log(progress);
});

eventSource.addEventListener('complete', (event) => {
  const result = JSON.parse(event.data);
  console.log('Task completed:', result);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  console.error('Error:', event);
  eventSource.close();
});
```

**Event Types**:
- `progress` - Progress update
- `complete` - Task completed successfully
- `error` - Task failed

### 6.3 Polling Endpoint (HTTP fallback)

```http
GET /api/video-status/{task_id}
```

**Response** (same as progress messages above)

**Recommended Polling Interval**: 2-5 seconds

---

## Common Patterns

### Success Response Structure

All successful API responses follow this structure:

```json
{
  "success": true,
  "data": {
    // Response-specific data
  },
  "metadata": {
    // Optional metadata (timestamps, versions, etc.)
  }
}
```

### Pagination

Paginated endpoints support these query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | Integer | 50 | Items per page (max: 100) |
| `offset` | Integer | 0 | Number of items to skip |

**Example**:
```http
GET /api/bgm/list?limit=20&offset=40
```

### File Upload Limits

| File Type | Max Size | Supported Formats |
|-----------|----------|-------------------|
| Images | 10 MB | JPEG, PNG |
| Audio | 10 MB | WAV, MP3 |
| BGM | 10 MB | MP3, WAV |

---

## Error Handling

### Error Response Structure

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional context (optional)
    }
  }
}
```

### HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| `200` | OK | Successful request |
| `202` | Accepted | Async task started |
| `400` | Bad Request | Invalid input parameters |
| `404` | Not Found | Resource doesn't exist |
| `413` | Payload Too Large | File size exceeds limit |
| `422` | Unprocessable Entity | Valid syntax but semantic error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side failure |
| `503` | Service Unavailable | Dependency service down |

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_IMAGE_FORMAT` | 400 | Unsupported image format |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `INVALID_BOUNDING_BOX` | 400 | Invalid coordinates |
| `VOICE_PROFILE_NOT_FOUND` | 404 | Voice profile doesn't exist |
| `SEGMENTATION_FAILED` | 500 | Background removal failed |
| `D_ID_API_FAILED` | 500 | D-ID service error |
| `FACE_NOT_DETECTED` | 400 | No face found in image |
| `TEXT_TOO_LONG` | 400 | Text exceeds character limit |
| `INVALID_PROSODY_PRESET` | 400 | Unknown prosody preset |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limiting

### Current Limits (per IP address)

| Endpoint Group | Requests per Minute | Requests per Hour |
|----------------|---------------------|-------------------|
| Person Detection | 30 | 500 |
| Background Removal | 20 | 200 |
| Voice Synthesis | 60 | 1000 |
| Video Generation | 10 | 100 |
| BGM Management | 100 | 2000 |

### Rate Limit Headers

Every response includes:

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1699564860
```

### Rate Limit Exceeded Response

**Status**: `429 Too Many Requests`

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": 30,
      "reset_at": "2025-11-06T11:01:00Z",
      "retry_after_seconds": 45
    }
  }
}
```

---

## OpenAPI 3.0 Specification

### Metadata

```yaml
openapi: 3.0.3
info:
  title: Video Message App API
  version: 2.0.0
  description: |
    AI-powered video generation with person detection, background removal,
    prosody-controlled voice synthesis, and BGM mixing.
  contact:
    name: API Support
    email: support@example.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: http://localhost:55433
    description: Local development (Mac)
  - url: http://3.115.141.166:55433
    description: Production (EC2)

tags:
  - name: Detection
    description: Person detection operations
  - name: Image Processing
    description: Background removal and image manipulation
  - name: Voice
    description: Voice synthesis with prosody control
  - name: Video
    description: Video generation and status
  - name: BGM
    description: Background music management
  - name: Progress
    description: Real-time progress tracking
```

### Schema Definitions

**BoundingBox**:
```yaml
BoundingBox:
  type: object
  required:
    - x_min
    - y_min
    - x_max
    - y_max
  properties:
    x_min:
      type: integer
      minimum: 0
    y_min:
      type: integer
      minimum: 0
    x_max:
      type: integer
      minimum: 0
    y_max:
      type: integer
      minimum: 0
    width:
      type: integer
      minimum: 1
    height:
      type: integer
      minimum: 1
```

**Person**:
```yaml
Person:
  type: object
  properties:
    person_id:
      type: string
      example: "person_1"
    bounding_box:
      $ref: '#/components/schemas/BoundingBox'
    confidence:
      type: number
      format: float
      minimum: 0
      maximum: 1
    area_percentage:
      type: number
      format: float
    keypoints:
      type: object
      additionalProperties:
        type: array
        items:
          type: integer
        minItems: 2
        maxItems: 2
```

**ErrorResponse**:
```yaml
ErrorResponse:
  type: object
  required:
    - success
    - error
  properties:
    success:
      type: boolean
      enum: [false]
    error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          example: "INVALID_IMAGE_FORMAT"
        message:
          type: string
          example: "Unsupported image format"
        details:
          type: object
          additionalProperties: true
```

---

## Implementation Notes

### Backward Compatibility

Version 2.0 maintains backward compatibility with v1.0 endpoints:

| v1.0 Endpoint | v2.0 Status | Notes |
|---------------|-------------|-------|
| `POST /api/voice-clone/create` | ✅ Maintained | No changes |
| `POST /api/voice-clone/synthesize` | ✅ Enhanced | Added prosody support |
| `GET /api/voice-clone/profiles` | ✅ Maintained | No changes |
| `POST /api/d-id/create-talk` | ⚠️ Deprecated | Use `/api/video-generate` |

### Performance Considerations

1. **Async Processing**: All heavy operations (video generation, background removal) are asynchronous
2. **Caching**: BGM catalog and voice profiles are cached for 1 hour
3. **Compression**: Response data is gzipped if `Accept-Encoding: gzip` is present
4. **CDN**: Static assets (BGM previews, thumbnails) should be served via CDN in production

### Security Considerations

1. **Input Validation**: All file uploads are validated for type, size, and content
2. **Sanitization**: Filenames are sanitized to prevent path traversal attacks
3. **Rate Limiting**: Per-IP rate limits prevent abuse
4. **CORS**: Configurable CORS policy (default: localhost:55434 for development)
5. **Content Security**: Uploaded files are scanned for malware (future implementation)

---

## Testing Examples

### cURL Examples

**Person Detection**:
```bash
curl -X POST "http://localhost:55433/api/person-detection" \
  -F "image=@test.jpg" \
  -F "confidence_threshold=0.7"
```

**Background Removal**:
```bash
curl -X POST "http://localhost:55433/api/background-removal" \
  -F "image=@test.jpg" \
  -F "person_id=person_1" \
  --output result_no_bg.png
```

**Voice Synthesis**:
```bash
curl -X POST "http://localhost:55433/api/voice-synthesis" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "おめでとうございます！",
    "voice_profile_id": "openvoice_c403f011",
    "prosody_preset": "celebration"
  }' \
  --output voice_celebration.wav
```

**Video Generation**:
```bash
curl -X POST "http://localhost:55433/api/video-generate" \
  -F "image=@face.png" \
  -F "audio=@voice.wav" \
  -F "bgm_id=system_bgm_001" \
  -F "bgm_volume=0.2"
```

### Python Examples

```python
import requests

# Person Detection
with open('test.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:55433/api/person-detection',
        files={'image': f},
        data={'confidence_threshold': 0.7}
    )
    persons = response.json()['data']['persons']

# Background Removal
with open('test.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:55433/api/background-removal',
        files={'image': f},
        data={'person_id': persons[0]['person_id']}
    )
    with open('result_no_bg.png', 'wb') as out:
        out.write(response.content)

# Voice Synthesis
response = requests.post(
    'http://localhost:55433/api/voice-synthesis',
    json={
        'text': 'おめでとうございます！',
        'voice_profile_id': 'openvoice_c403f011',
        'prosody_preset': 'celebration'
    }
)
with open('voice_celebration.wav', 'wb') as out:
    out.write(response.content)

# Video Generation
with open('face.png', 'rb') as img, open('voice.wav', 'rb') as aud:
    response = requests.post(
        'http://localhost:55433/api/video-generate',
        files={'image': img, 'audio': aud},
        data={
            'bgm_id': 'system_bgm_001',
            'bgm_volume': 0.2
        }
    )
    task_id = response.json()['data']['task_id']

# Progress Tracking (WebSocket)
import websocket
import json

def on_message(ws, message):
    progress = json.loads(message)
    print(f"Progress: {progress['percentage']}%")
    if progress['status'] == 'completed':
        print(f"Video URL: {progress['result']['video_url']}")
        ws.close()

ws = websocket.WebSocketApp(
    f"ws://localhost:55433/api/progress/{task_id}",
    on_message=on_message
)
ws.run_forever()
```

---

## Changelog

### Version 2.0.0 (2025-11-06)

**New Features**:
- Person detection with YOLOv11
- Background removal with SAM
- Prosody-controlled voice synthesis (celebration, excitement, sadness, neutral)
- BGM mixing and management
- Real-time progress tracking (WebSocket/SSE)
- Enhanced video generation pipeline

**Breaking Changes**:
- `/api/d-id/create-talk` deprecated (use `/api/video-generate`)

**Improvements**:
- Async processing for all heavy operations
- Consistent error response format
- Comprehensive validation and error messages

---

## Support & Feedback

For API support, bug reports, or feature requests:

- **Email**: support@example.com
- **GitHub Issues**: https://github.com/apto-as/prototype-app/issues
- **Documentation**: https://github.com/apto-as/prototype-app/wiki

---

*"Knowledge, well-structured, is the foundation of wisdom."*

*知識は芸術であり、文書はインスピレーションの源泉である*

**Document Version**: 1.0.0
**Last Updated**: 2025-11-06
**Author**: Muses (Knowledge Architect)
