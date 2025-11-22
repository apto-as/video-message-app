# D-ID Troubleshooting Guide
## Common Issues and Solutions

**Version**: 1.0.0
**Last Updated**: 2025-11-07

---

## Table of Contents

1. [Authentication Issues](#1-authentication-issues)
2. [Upload Problems](#2-upload-problems)
3. [Video Generation Failures](#3-video-generation-failures)
4. [Performance Issues](#4-performance-issues)
5. [Network & Connectivity](#5-network--connectivity)
6. [Docker & Infrastructure](#6-docker--infrastructure)
7. [API Errors Reference](#7-api-errors-reference)
8. [Debugging Tools](#8-debugging-tools)
9. [FAQ](#9-faq)

---

## 1. Authentication Issues

### Issue 1.1: "Unauthorized" (401 Error)

**Symptoms**:
```json
{
  "kind": "Unauthorized",
  "description": "Invalid or expired API key"
}
```

**Diagnosis**:
```bash
# Check if API key is configured
echo $D_ID_API_KEY

# Verify .env file
cat .env | grep D_ID_API_KEY

# Test API key format (should decode to username:password)
echo $D_ID_API_KEY | base64 -d
```

**Solutions**:

**A) API Key Not Set**
```bash
# Set in .env
echo "D_ID_API_KEY=your-actual-key-here" >> .env

# Restart backend
docker-compose restart backend

# Verify
curl http://localhost:55433/api/d-id/health
```

**B) Invalid API Key Format**
```bash
# Get new key from D-ID Studio
# https://studio.d-id.com/account-settings

# Copy the ENTIRE key (Base64 encoded username:password)
# Format: YmlsbEBuZXVyb2F4aXMuYWk6RGFHZTUyM05lMWltQVNyMA==

# Update .env
nano .env
# D_ID_API_KEY=<paste-new-key-here>

# Restart
docker-compose restart backend
```

**C) Expired API Key**
```bash
# Rotate key in D-ID Studio
# 1. Visit https://studio.d-id.com/account-settings
# 2. Click "Generate New Key"
# 3. Copy new key
# 4. Update .env
# 5. Restart backend
```

---

### Issue 1.2: "Payment Required" (402 Error)

**Symptoms**:
```json
{
  "kind": "PaymentRequired",
  "description": "Credit quota exceeded"
}
```

**Diagnosis**:
```bash
# Check remaining credits
curl -X GET https://api.d-id.com/credits \
  -H "Authorization: Basic $D_ID_API_KEY" | jq
```

**Expected Response**:
```json
{
  "remaining": 0,
  "total": 20,
  "reset_date": "2025-12-01T00:00:00Z"
}
```

**Solutions**:

**A) Free Trial Exhausted**
- Upgrade to paid plan: https://www.d-id.com/pricing/
- Recommended: **Lite Plan** ($29/month, 300 credits)

**B) Monthly Quota Exceeded**
- Wait until `reset_date` (shown in credits response)
- Or upgrade to higher plan

**C) Monitor Credits Programmatically**
```python
async def check_credits_before_generation():
    """Check credits before generating video"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.d-id.com/credits",
            headers={"Authorization": f"Basic {api_key}"}
        )
        data = response.json()
        remaining = data["remaining"]

        if remaining < 5:
            print(f"⚠️ Warning: Only {remaining} credits remaining")
            # Send alert email/Slack notification

        if remaining == 0:
            raise Exception("No credits remaining. Please upgrade plan.")

        return remaining
```

---

## 2. Upload Problems

### Issue 2.1: Image Upload Fails

**Symptoms**:
```json
{
  "detail": "画像のアップロードに失敗しました"
}
```

**Diagnosis**:
```bash
# Check image file
file portrait.jpg
# Should output: JPEG image data

ls -lh portrait.jpg
# Check size (should be < 10 MB)

# Test upload manually
curl -X POST http://localhost:55433/api/d-id/upload-source-image \
  -F "file=@portrait.jpg" -v
```

**Solutions**:

**A) File Too Large (> 10 MB)**
```bash
# Compress image (Mac/Linux)
convert portrait.jpg -quality 85 -resize 1024x1024 portrait_compressed.jpg

# Or using ImageMagick
magick portrait.jpg -quality 80 -strip portrait_compressed.jpg

# Python solution
from PIL import Image

img = Image.open("portrait.jpg")
img = img.resize((1024, 1024), Image.LANCZOS)
img.save("portrait_compressed.jpg", quality=85, optimize=True)
```

**B) Invalid File Format**
```bash
# Convert to JPEG
convert portrait.png portrait.jpg

# Python solution
from PIL import Image

img = Image.open("portrait.png")
rgb_img = img.convert("RGB")
rgb_img.save("portrait.jpg", quality=90)
```

**C) Corrupted Image File**
```bash
# Verify image integrity
identify portrait.jpg

# If corrupted, re-export from original source
# Or use image repair tools
```

**D) Wrong File Path**
```bash
# Use absolute path
IMAGE_PATH="$(pwd)/portrait.jpg"
curl -X POST http://localhost:55433/api/d-id/upload-source-image \
  -F "file=@$IMAGE_PATH"

# Or verify file exists
test -f portrait.jpg && echo "File exists" || echo "File not found"
```

---

### Issue 2.2: Audio Upload Fails

**Symptoms**:
```json
{
  "detail": "音声ファイル（WAV, MP3, MP4, FLAC, M4A）をアップロードしてください"
}
```

**Diagnosis**:
```bash
# Check audio file format
file voice.wav
# Should output: WAVE audio

# Check size and duration
ffprobe -i voice.wav -show_entries format=size,duration -of json

# Test upload
curl -X POST http://localhost:55433/api/d-id/upload-audio \
  -F "file=@voice.wav" -v
```

**Solutions**:

**A) File Too Large (> 30 MB)**
```bash
# Compress audio
ffmpeg -i voice.wav -ar 16000 -ac 1 -b:a 64k voice_compressed.wav

# Parameters:
# -ar 16000: Resample to 16kHz
# -ac 1: Mono (1 channel)
# -b:a 64k: Bitrate 64 kbps
```

**B) Audio Too Long (> 5 minutes)**
```bash
# Trim to first 5 minutes (300 seconds)
ffmpeg -i voice.wav -t 300 voice_trimmed.wav
```

**C) Unsupported Format**
```bash
# Convert to WAV
ffmpeg -i voice.mp3 -ar 16000 -ac 1 voice.wav

# Supported formats: WAV, MP3, MP4, FLAC, M4A
```

**D) Invalid Audio File**
```bash
# Verify audio is valid
ffmpeg -v error -i voice.wav -f null -

# No output = valid audio
# Errors = corrupted/invalid audio
```

---

## 3. Video Generation Failures

### Issue 3.1: "Invalid audio URL"

**Symptoms**:
```json
{
  "kind": "InvalidRequest",
  "description": "Audio URL is not accessible",
  "details": {"audio_url": "https://example.com/audio.wav"}
}
```

**Root Cause**: D-ID cannot access the audio file URL.

**Solutions**:

**A) Use D-ID's Upload Endpoint**
```bash
# ALWAYS upload audio through D-ID API first
curl -X POST http://localhost:55433/api/d-id/upload-audio \
  -F "file=@voice.wav" \
  -o audio_response.json

AUDIO_URL=$(jq -r '.url' audio_response.json)
echo "Use this URL: $AUDIO_URL"
```

**B) Verify URL is Publicly Accessible**
```bash
# Test URL accessibility
curl -I "$AUDIO_URL"

# Should return: HTTP/1.1 200 OK
# NOT 403 Forbidden or 404 Not Found
```

**C) Check CORS Settings**
If hosting audio on your own server:
```nginx
# nginx.conf
location /audio/ {
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
}
```

---

### Issue 3.2: "Video generation timeout"

**Symptoms**:
- Video generation takes > 5 minutes
- Status stuck at "processing"
- Python script raises `TimeoutError`

**Diagnosis**:
```bash
# Check video status manually
curl http://localhost:55433/api/d-id/talk-status/tlk_abc123xyz | jq

# Check D-ID service status
curl -I https://api.d-id.com/
```

**Solutions**:

**A) Increase Timeout**
```python
# Increase max polling attempts
result = await wait_for_video(talk_id, max_attempts=120)  # 10 minutes
```

**B) Check D-ID Service Status**
```bash
# Visit D-ID status page
open https://status.d-id.com/

# Or check via API
curl -I https://api.d-id.com/
# Should return: HTTP/2 200
```

**C) Retry Video Generation**
```python
async def generate_video_with_retry(audio_url, source_url, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await generate_video(audio_url, source_url)
        except TimeoutError:
            if attempt < max_retries - 1:
                print(f"Timeout. Retrying ({attempt+2}/{max_retries})...")
                await asyncio.sleep(30)
            else:
                raise
```

**D) Check Network Connectivity**
```bash
# Test internet connection
ping -c 3 api.d-id.com

# Test DNS resolution
nslookup api.d-id.com

# Test HTTPS connection
curl -v https://api.d-id.com/
```

---

### Issue 3.3: "Video generation rejected"

**Symptoms**:
```json
{
  "id": "tlk_abc123xyz",
  "status": "rejected",
  "error": {
    "kind": "ContentModeration",
    "description": "Content violates terms of service"
  }
}
```

**Root Causes**:
1. **Inappropriate Content**: Image or audio violates D-ID ToS
2. **Copyright Violation**: Using copyrighted images/voices
3. **Deepfake Misuse**: Creating misleading content

**Solutions**:

**A) Review Content Guidelines**
- Read D-ID Terms of Service: https://www.d-id.com/terms-of-service/
- Ensure you have rights to use the image and voice

**B) Use Appropriate Content**
```text
✅ Allowed:
- Personal photos (with consent)
- Licensed stock photos
- Original artwork
- Company headshots (authorized)

❌ Not Allowed:
- Celebrity photos (without permission)
- Minors' photos
- Copyrighted characters
- Deepfakes for deception
```

**C) Contact D-ID Support**
If you believe the rejection is incorrect:
- Email: support@d-id.com
- Include: Talk ID, explanation, proof of rights

---

## 4. Performance Issues

### Issue 4.1: Slow Video Generation

**Symptoms**:
- Video takes > 2 minutes to generate
- API requests are slow

**Diagnosis**:
```bash
# Measure API response time
time curl -X POST http://localhost:55433/api/d-id/generate-video \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "...", "source_url": "..."}'

# Check network latency to D-ID
ping -c 10 api.d-id.com
```

**Solutions**:

**A) Optimize Image Size**
```bash
# Reduce to optimal size (512x512 or 1024x1024)
convert portrait.jpg -resize 1024x1024 -quality 85 portrait_optimized.jpg
```

**B) Optimize Audio**
```bash
# Use lower sample rate (16kHz is sufficient)
ffmpeg -i voice.wav -ar 16000 -ac 1 voice_optimized.wav
```

**C) Use Caching**
```python
# Cache generated videos to avoid regeneration
from functools import lru_cache
import hashlib

def get_cache_key(audio_url, image_url):
    return hashlib.md5(f"{audio_url}|{image_url}".encode()).hexdigest()

video_cache = {}

async def generate_video_with_cache(audio_url, image_url):
    cache_key = get_cache_key(audio_url, image_url)

    if cache_key in video_cache:
        print(f"✅ Using cached video")
        return video_cache[cache_key]

    result = await generate_video(audio_url, image_url)
    video_cache[cache_key] = result
    return result
```

**D) Parallel Processing**
```python
# Generate multiple videos in parallel
import asyncio

async def generate_multiple_videos(requests):
    tasks = [
        generate_video(req["audio_url"], req["source_url"])
        for req in requests
    ]
    return await asyncio.gather(*tasks)
```

---

### Issue 4.2: Rate Limit Errors (429)

**Symptoms**:
```json
{
  "kind": "RateLimitExceeded",
  "description": "Too many requests",
  "retry_after": 60
}
```

**Diagnosis**:
```bash
# Check current rate limit
# Free: 10 req/min
# Lite: 30 req/min
# Pro: 60 req/min

# Count recent requests
# (If you have logging enabled)
grep "POST /talks" backend.log | tail -n 20
```

**Solutions**:

**A) Implement Rate Limiting**
```python
import asyncio
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    async def acquire(self):
        now = datetime.now()

        # Remove old requests
        while self.requests and self.requests[0] < now - timedelta(seconds=self.time_window):
            self.requests.popleft()

        # Wait if at limit
        if len(self.requests) >= self.max_requests:
            oldest = self.requests[0]
            wait_time = (oldest + timedelta(seconds=self.time_window) - now).total_seconds()
            if wait_time > 0:
                print(f"Rate limit. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        self.requests.append(now)

# Usage
rate_limiter = RateLimiter(max_requests=10, time_window=60)

async def generate_video_with_rate_limit(audio_url, source_url):
    await rate_limiter.acquire()
    return await generate_video(audio_url, source_url)
```

**B) Handle 429 Responses**
```python
import httpx

async def generate_video_with_retry(audio_url, source_url):
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.post(
                    "http://localhost:55433/api/d-id/generate-video",
                    json={"audio_url": audio_url, "source_url": source_url}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    print(f"Rate limited. Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                else:
                    raise
```

**C) Upgrade Plan**
- **Free**: 10 req/min → **Lite**: 30 req/min
- **Lite**: 30 req/min → **Pro**: 60 req/min
- Visit: https://www.d-id.com/pricing/

---

## 5. Network & Connectivity

### Issue 5.1: "Connection refused"

**Symptoms**:
```
curl: (7) Failed to connect to localhost port 55433: Connection refused
```

**Diagnosis**:
```bash
# Check if backend is running
docker-compose ps

# Check backend logs
docker logs voice_backend --tail 50
```

**Solutions**:

**A) Start Backend Service**
```bash
# Start all services
docker-compose up -d

# Verify
curl http://localhost:55433/health
```

**B) Restart Backend**
```bash
# Restart backend only
docker-compose restart backend

# Or rebuild if code changed
docker-compose up -d --build backend
```

**C) Check Port Conflicts**
```bash
# Check if port 55433 is in use
lsof -i :55433

# If another process is using it, stop it or change port
# In docker-compose.yml:
# ports:
#   - "55434:55433"  # Host:Container
```

---

### Issue 5.2: "Network timeout"

**Symptoms**:
```
httpx.ReadTimeout: Read timeout
```

**Diagnosis**:
```bash
# Test D-ID API connectivity
curl -I https://api.d-id.com/ --max-time 10

# Check firewall/proxy settings
env | grep -i proxy
```

**Solutions**:

**A) Increase Timeout**
```python
# Increase httpx timeout (default: 5s)
async with httpx.AsyncClient(timeout=300) as client:  # 5 minutes
    response = await client.post(...)
```

**B) Check Firewall**
```bash
# Mac: Check firewall settings
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Allow Docker
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /Applications/Docker.app
```

**C) Configure Proxy (if needed)**
```bash
# Set proxy in .env
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1
```

---

## 6. Docker & Infrastructure

### Issue 6.1: Docker not running

**Symptoms**:
```
Cannot connect to the Docker daemon. Is the docker daemon running?
```

**Solutions**:

**Mac**:
```bash
# Start Docker Desktop
open -a Docker

# Wait 30 seconds for Docker to start
sleep 30

# Verify
docker ps
```

**Linux**:
```bash
# Start Docker service
sudo systemctl start docker

# Enable on boot
sudo systemctl enable docker

# Verify
docker ps
```

---

### Issue 6.2: Container keeps restarting

**Symptoms**:
```bash
docker-compose ps
# Shows: Restarting (1) X seconds ago
```

**Diagnosis**:
```bash
# Check logs
docker logs voice_backend --tail 100

# Common errors:
# - Missing environment variables
# - Port already in use
# - Failed healthcheck
```

**Solutions**:

**A) Check Environment Variables**
```bash
# Verify .env file
cat .env

# Required variables:
# D_ID_API_KEY=...
# DEVICE=cpu
# USE_CUDA=false
```

**B) Fix Port Conflicts**
```bash
# Find process using port
lsof -i :55433

# Kill process or change port in docker-compose.yml
```

**C) Check Healthcheck**
```bash
# Manually test healthcheck
docker exec voice_backend curl -f http://localhost:55433/health || exit 1
```

---

## 7. API Errors Reference

| Status Code | Error Kind | Description | Solution |
|-------------|-----------|-------------|----------|
| 400 | InvalidRequest | Invalid request parameters | Check request body format |
| 401 | Unauthorized | Invalid API key | Verify API key in .env |
| 402 | PaymentRequired | Quota exceeded | Upgrade plan or wait for reset |
| 404 | NotFound | Talk ID not found | Verify talk ID is correct |
| 429 | RateLimitExceeded | Too many requests | Implement rate limiting |
| 500 | InternalServerError | D-ID server error | Retry after delay |
| 503 | ServiceUnavailable | D-ID maintenance | Check status.d-id.com |

---

## 8. Debugging Tools

### 8.1 Enable Debug Logging

**Python**:
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log all HTTP requests
import httpx
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
```

**Backend**:
```bash
# Set LOG_LEVEL in .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart backend
docker-compose restart backend

# View logs
docker logs voice_backend -f
```

### 8.2 Test API Manually

```bash
# Test health endpoint
curl http://localhost:55433/api/d-id/health | jq

# Test D-ID API directly
curl -X GET https://api.d-id.com/credits \
  -H "Authorization: Basic $D_ID_API_KEY" | jq

# Test video status
curl http://localhost:55433/api/d-id/talk-status/tlk_abc123xyz | jq
```

### 8.3 Use API Debugger Script

Save as `debug_d_id.py`:
```python
#!/usr/bin/env python3
"""Debug D-ID API requests"""
import asyncio
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

async def debug_request(method, url, **kwargs):
    console.print(f"\n[bold cyan]🔍 {method} {url}[/bold cyan]")

    if "json" in kwargs:
        console.print(f"Body: {kwargs['json']}")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.request(method, url, **kwargs)
            console.print(f"[green]Status: {response.status_code}[/green]")
            console.print(f"Response: {response.text[:500]}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise

# Usage
result = await debug_request(
    "POST",
    "http://localhost:55433/api/d-id/generate-video",
    json={"audio_url": "...", "source_url": "..."}
)
```

---

## 9. FAQ

### Q1: How long does video generation take?

**A**: Typically 30-60 seconds for a 10-second video. Factors:
- Video length: ~3x real-time (30s video = 90s processing)
- D-ID server load: Peak hours may be slower
- Image resolution: Higher resolution = longer processing

---

### Q2: Can I use the same image for multiple videos?

**A**: Yes! Once uploaded, you can reuse the `image_url` for multiple videos.

```python
# Upload image once
image_url = await upload_image("portrait.jpg")

# Generate multiple videos with different audio
for text in texts:
    audio_url = await synthesize_and_upload(text)
    video = await generate_video(audio_url, image_url)
```

---

### Q3: What happens if I delete a video?

**A**: Videos are automatically deleted from D-ID CDN after 30 days (Free/Lite) or 90 days (Pro).

To delete immediately:
```bash
curl -X DELETE http://localhost:55433/api/d-id/talks/tlk_abc123xyz \
  -H "Authorization: Basic $D_ID_API_KEY"
```

---

### Q4: Can I generate videos offline?

**A**: No. D-ID API requires internet connectivity. However, you can:
1. Pre-generate videos when online
2. Download videos locally (`curl -o video.mp4 $VIDEO_URL`)
3. Serve videos from local storage

---

### Q5: How do I monitor API usage?

**A**: Use D-ID's credits API:

```python
async def get_usage_stats():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.d-id.com/credits",
            headers={"Authorization": f"Basic {api_key}"}
        )
        data = response.json()

        print(f"Used: {data['total'] - data['remaining']} / {data['total']}")
        print(f"Remaining: {data['remaining']}")
        print(f"Reset: {data['reset_date']}")

asyncio.run(get_usage_stats())
```

---

## Contact & Support

### Internal Support
- **Backend Issues**: Check `docker logs voice_backend`
- **OpenVoice Issues**: Check `docker logs openvoice_native`
- **Frontend Issues**: Check browser console (F12)

### D-ID Support
- **Email**: support@d-id.com
- **Documentation**: https://docs.d-id.com/
- **Status Page**: https://status.d-id.com/
- **Community Forum**: https://community.d-id.com/

### Emergency Contacts
- **Critical API Issues**: support@d-id.com (Response: 4-8 hours)
- **Billing Issues**: billing@d-id.com
- **Security Issues**: security@d-id.com

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-07
**Maintained by**: Muses (Knowledge Architect)

*"すべての問題には解決策があります。このガイドがその道標となりますように。"*
