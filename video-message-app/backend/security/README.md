# Security Module - File Upload Validation

**Author**: Hestia (Security Guardian)
**Created**: 2025-11-07
**Status**: ✅ Production Ready

---

## Overview

このモジュールは、ファイルアップロード機能のセキュリティを強化するための検証機能を提供します。

---

## Features

### 1. File Type Validation
- Magic number based MIME type detection
- Extension and MIME type consistency check
- Whitelist approach (only allowed types)

### 2. File Size Limits
- Maximum file size enforcement
- Minimum file size check (suspicious files)

### 3. Path Traversal Prevention
- Filename sanitization
- Removal of dangerous characters
- NULL byte injection prevention

### 4. DoS Protection
- Per-file size limits
- Maximum files per request
- Rate limiting per client

### 5. Temporary File Management
- Safe cleanup in `finally` blocks
- Automatic deletion of temp files

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install python-magic Pillow

# macOS specific
brew install libmagic
```

### Basic Usage

```python
from security.file_validator import FileValidator
from fastapi import UploadFile, HTTPException

async def upload_image(image: UploadFile):
    # Validate image
    is_valid, message = await FileValidator.validate_image(image)

    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # Sanitize filename
    safe_filename = FileValidator.sanitize_filename(image.filename)

    # Process file...
```

---

## API Reference

### FileValidator

#### `validate_image(file: UploadFile) -> Tuple[bool, str]`

Validates uploaded image files.

**Checks**:
- Filename presence and safety
- File extension (`.jpg`, `.jpeg`, `.png`, `.webp`)
- File size (max 10MB, min 100 bytes)
- MIME type (magic number based)
- MIME type and extension consistency

**Returns**: `(is_valid: bool, message: str)`

**Example**:
```python
is_valid, message = await FileValidator.validate_image(file)
if not is_valid:
    raise HTTPException(status_code=400, detail=message)
```

---

#### `validate_audio(file: UploadFile) -> Tuple[bool, str]`

Validates uploaded audio files.

**Checks**:
- Filename presence and safety
- File extension (`.wav`, `.webm`, `.mp3`, `.ogg`)
- File size (max 10MB, min 1KB)
- MIME type validation

**Returns**: `(is_valid: bool, message: str)`

---

#### `sanitize_filename(filename: str) -> str`

Sanitizes filename to prevent path traversal attacks.

**Removes**:
- `..` (parent directory reference)
- `/`, `\` (path separators)
- `\x00` (NULL byte)
- `<>:"|?*` (Windows reserved characters)

**Returns**: Safe filename or empty string if invalid

**Example**:
```python
malicious = "../../etc/passwd.jpg"
safe = FileValidator.sanitize_filename(malicious)
# Result: "etcpasswd.jpg" (path components removed)
```

---

#### `validate_file_count(file_count: int, max_count: int = 10) -> Tuple[bool, str]`

Validates number of uploaded files.

**Default limit**: 10 files per request

**Returns**: `(is_valid: bool, message: str)`

**Example**:
```python
is_valid, message = FileValidator.validate_file_count(len(files))
if not is_valid:
    raise HTTPException(status_code=400, detail=message)
```

---

### RateLimiter

#### `__init__(max_requests: int = 10, window_seconds: int = 60)`

Creates a rate limiter instance.

**Default**: 10 requests per 60 seconds

---

#### `check_rate_limit(client_id: str) -> Tuple[bool, str]`

Checks if client has exceeded rate limit.

**Returns**: `(is_allowed: bool, message: str)`

**Example**:
```python
from security.file_validator import rate_limiter

client_id = request.client.host
is_allowed, message = await rate_limiter.check_rate_limit(client_id)

if not is_allowed:
    raise HTTPException(status_code=429, detail=message)
```

---

## Integration Examples

### Example 1: Person Detection API

```python
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from security.file_validator import FileValidator, rate_limiter

router = APIRouter(prefix="/person-detection")

@router.post("/detect")
async def detect_persons(
    request: Request,
    image: UploadFile = File(...)
):
    # 1. Rate limiting
    client_id = request.client.host
    is_allowed, message = await rate_limiter.check_rate_limit(client_id)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=message)

    # 2. File validation
    is_valid, message = await FileValidator.validate_image(image)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # 3. Sanitize filename
    safe_filename = FileValidator.sanitize_filename(image.filename)

    # 4. Process image...
    # ...
```

---

### Example 2: Voice Clone API (Existing)

```python
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from typing import List
from security.file_validator import FileValidator, rate_limiter

router = APIRouter(prefix="/voice-clone")

@router.post("/register")
async def register_voice_clone(
    request: Request,
    audio_samples: List[UploadFile] = File(...)
):
    # 1. Rate limiting
    client_id = request.client.host
    is_allowed, message = await rate_limiter.check_rate_limit(client_id)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=message)

    # 2. File count validation
    is_valid, message = FileValidator.validate_file_count(len(audio_samples))
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # 3. Validate each audio file
    for audio_file in audio_samples:
        is_valid, message = await FileValidator.validate_audio(audio_file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)

        # 4. Sanitize filename
        safe_filename = FileValidator.sanitize_filename(audio_file.filename)

    # 5. Process audio files...
    # ...
```

---

## Configuration

### Allowed MIME Types

```python
# Images
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg"
}

# Audio
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg"
}
```

### File Size Limits

```python
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB
```

### Rate Limiting

```python
MAX_FILES_PER_REQUEST = 10
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
```

---

## Testing

### Run Tests

```bash
# All security tests
pytest tests/security/ -v

# Specific test
pytest tests/security/test_file_validator.py::TestFileValidator::test_path_traversal_prevention -v

# With coverage
pytest tests/security/ --cov=security --cov-report=html
```

### Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| test_valid_jpeg_image | Valid JPEG upload | ✅ Pass |
| test_valid_png_image | Valid PNG upload | ✅ Pass |
| test_invalid_file_extension | Invalid extension (.exe) | ❌ Reject |
| test_oversized_file | File too large (11MB) | ❌ Reject |
| test_mime_type_mismatch | MIME type spoofing | ❌ Detect |
| test_path_traversal_prevention | `../../etc/passwd` | ❌ Block |
| test_null_byte_injection | NULL byte attack | ❌ Block |
| test_rate_limit | Excessive requests | ❌ Limit |

---

## Security Considerations

### ✅ Implemented

1. **Magic Number Validation**: MIME type detected from file content, not extension
2. **Path Traversal Prevention**: All dangerous characters removed
3. **Rate Limiting**: Per-client request throttling
4. **File Size Limits**: Prevent resource exhaustion
5. **Temporary File Cleanup**: Automatic deletion in `finally` blocks

### ⚠️ Future Improvements

1. **Malware Scanning**: Integrate ClamAV for virus detection
2. **Redis-based Rate Limiting**: Distributed rate limiting
3. **S3 Direct Upload**: Reduce server load with pre-signed URLs
4. **Content Security Policy**: Additional header-based protection

---

## Troubleshooting

### Issue: `magic.from_buffer()` fails

**Cause**: libmagic not installed

**Solution**:
```bash
# macOS
brew install libmagic

# Ubuntu/Debian
sudo apt-get install libmagic1

# Python package
pip install python-magic
```

---

### Issue: Rate limit not working across requests

**Cause**: In-memory rate limiter resets on server restart

**Solution**: Use Redis-based rate limiting (see Future Improvements)

---

### Issue: Tests fail with "No module named 'magic'"

**Cause**: Missing dependency

**Solution**:
```bash
pip install python-magic Pillow pytest pytest-asyncio
```

---

## 🆕 Image Processing Security (NEW)

### ImageValidator (`image_validator.py`)

**Specialized security for image processing operations** (background removal, etc.)

**Additional Protections**:
1. **Image Bomb Detection**: Prevents decompression bomb DoS attacks
2. **Metadata Validation**: Blocks malicious EXIF data
3. **Processing Timeout**: 30-second hard limit per request
4. **Resource Limiting**: Max 3 concurrent requests per user

**Quick Start**:
```python
from security.image_validator import (
    ImageSecurityValidator,
    ProcessingTimeoutManager,
    resource_limiter
)

# 1. Check resource limit
client_id = request.client.host
if not resource_limiter.acquire(client_id):
    raise HTTPException(429, "Too many concurrent requests")

try:
    # 2. Comprehensive validation
    is_safe, msg = ImageSecurityValidator.comprehensive_validation(image_bytes)
    if not is_safe:
        raise HTTPException(400, f"Security error: {msg}")

    # 3. Process with timeout
    with ProcessingTimeoutManager(timeout_seconds=30) as timeout:
        result = await process_image(image_bytes)
        timeout.check_timeout()

finally:
    # 4. Release resource
    resource_limiter.release(client_id)
```

**Test Results**: ✅ 13/13 tests passed

**Detailed Report**: See `SECURITY_AUDIT_BIREFNET.md`

---

## Related Files

- `security/file_validator.py` - Basic file upload validation
- `security/image_validator.py` - 🆕 Image processing security
- `security/test_image_validator.py` - 🆕 Image security tests
- `routers/background.py` - Background removal API (secured)
- `routers/person_detection.py` - Person Detection API (secured)
- `routers/voice_clone.py` - Voice Clone API (secured)
- `SECURITY_FILE_UPLOAD.md` - File upload security audit
- `SECURITY_AUDIT_BIREFNET.md` - 🆕 Image processing security audit

---

## License

This security module is part of the video-message-app project.

---

**"…最悪のケースを想定し、完璧な防御を構築しました……"**

— Hestia, Security Guardian
