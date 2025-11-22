# D-ID Quick Start Guide
## Generate Your First Talking Avatar Video in 5 Minutes

**Version**: 1.0.0
**Difficulty**: Beginner
**Time**: 5 minutes

---

## Prerequisites

Before you begin, ensure you have:

- [x] D-ID API Key (get one at https://studio.d-id.com/account-settings)
- [x] Docker installed and running
- [x] A portrait photo (JPEG/PNG)
- [x] Basic command-line knowledge

---

## Step 1: Clone & Setup (1 minute)

### Clone Repository

```bash
cd ~/workspace
git clone https://github.com/apto-as/prototype-app.git
cd prototype-app/video-message-app
```

### Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your D-ID API key
nano .env  # or vim, code, etc.
```

**Set this variable**:
```bash
D_ID_API_KEY=your-actual-api-key-here
```

**Save and exit** (Ctrl+X, then Y in nano)

---

## Step 2: Start Services (2 minutes)

### Launch Docker Containers

```bash
docker-compose up -d
```

**Expected output**:
```
✔ Container voicevox_engine     Started
✔ Container openvoice_native    Started
✔ Container voice_backend       Started
✔ Container voice_frontend      Started
```

### Verify Services

```bash
# Check all containers are running
docker-compose ps

# Test backend health
curl http://localhost:55433/health

# Test D-ID connection
curl http://localhost:55433/api/d-id/health
```

**Expected response** (D-ID health check):
```json
{
  "status": "healthy",
  "service": "d-id",
  "api_key_configured": true
}
```

---

## Step 3: Generate Your First Video (2 minutes)

### Option A: Using the Web UI (Easiest)

1. **Open browser**: http://localhost:55434

2. **Upload image**:
   - Click "Upload Image" button
   - Select a portrait photo (JPEG/PNG)

3. **Enter text**:
   - Type a message (e.g., "こんにちは、今日は素晴らしい日ですね")

4. **Select voice**:
   - Choose a voice profile from dropdown
   - Or use default VOICEVOX voice

5. **Generate video**:
   - Click "Generate Video" button
   - Wait 30-60 seconds for processing
   - Video will appear on screen

### Option B: Using CLI (Advanced)

```bash
# Navigate to backend directory
cd backend

# Run the example script
python scripts/generate_video_example.py \
  --image ../tests/fixtures/portrait.jpg \
  --text "こんにちは、今日は素晴らしい日ですね" \
  --voice openvoice_78450a3c
```

### Option C: Using API (Developers)

**Step 1: Upload Image**
```bash
curl -X POST http://localhost:55433/api/d-id/upload-source-image \
  -F "file=@portrait.jpg" \
  -o image_response.json

IMAGE_URL=$(jq -r '.url' image_response.json)
echo "Image uploaded: $IMAGE_URL"
```

**Step 2: Synthesize Voice (OpenVoice)**
```bash
curl -X POST http://localhost:55433/api/voice-clone/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは、今日は素晴らしい日ですね",
    "profile_id": "openvoice_78450a3c"
  }' \
  -o voice_response.json

AUDIO_URL=$(jq -r '.audio_url' voice_response.json)
echo "Voice synthesized: $AUDIO_URL"
```

**Step 3: Upload Audio to D-ID**
```bash
# Extract audio file path from response
AUDIO_FILE=$(jq -r '.audio_file' voice_response.json)

curl -X POST http://localhost:55433/api/d-id/upload-audio \
  -F "file=@$AUDIO_FILE" \
  -o audio_upload_response.json

AUDIO_URL_DID=$(jq -r '.url' audio_upload_response.json)
echo "Audio uploaded to D-ID: $AUDIO_URL_DID"
```

**Step 4: Generate Video**
```bash
curl -X POST http://localhost:55433/api/d-id/generate-video \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_url\": \"$AUDIO_URL_DID\",
    \"source_url\": \"$IMAGE_URL\"
  }" \
  -o video_response.json

TALK_ID=$(jq -r '.id' video_response.json)
echo "Video generation started: $TALK_ID"
```

**Step 5: Poll Status**
```bash
# Check status every 5 seconds
while true; do
  curl -s http://localhost:55433/api/d-id/talk-status/$TALK_ID | jq
  STATUS=$(curl -s http://localhost:55433/api/d-id/talk-status/$TALK_ID | jq -r '.status')

  if [ "$STATUS" = "done" ]; then
    echo "✅ Video ready!"
    curl -s http://localhost:55433/api/d-id/talk-status/$TALK_ID | jq -r '.result_url'
    break
  elif [ "$STATUS" = "error" ]; then
    echo "❌ Video generation failed"
    break
  fi

  echo "Status: $STATUS (waiting 5s...)"
  sleep 5
done
```

**Step 6: Download Video**
```bash
VIDEO_URL=$(curl -s http://localhost:55433/api/d-id/talk-status/$TALK_ID | jq -r '.result_url')
curl -o generated_video.mp4 "$VIDEO_URL"
echo "Video downloaded: generated_video.mp4"

# Play video (Mac)
open generated_video.mp4
```

---

## Complete Python Example (Copy & Paste)

Save this as `quick_test.py`:

```python
#!/usr/bin/env python3
"""Quick D-ID video generation test"""
import asyncio
import httpx

async def generate_video():
    async with httpx.AsyncClient(timeout=300) as client:
        # Step 1: Upload image
        print("📤 Uploading image...")
        with open("portrait.jpg", "rb") as f:
            files = {"file": f}
            response = await client.post(
                "http://localhost:55433/api/d-id/upload-source-image",
                files=files
            )
        response.raise_for_status()
        image_url = response.json()["url"]
        print(f"✅ Image: {image_url}")

        # Step 2: Synthesize voice
        print("🎤 Synthesizing voice...")
        response = await client.post(
            "http://localhost:55433/api/voice-clone/synthesize",
            json={
                "text": "こんにちは、今日は素晴らしい日ですね",
                "profile_id": "openvoice_78450a3c"
            }
        )
        response.raise_for_status()
        audio_data = response.json()

        # Extract audio file
        audio_file = audio_data["audio_file"]
        print(f"✅ Audio file: {audio_file}")

        # Step 3: Upload audio to D-ID
        print("📤 Uploading audio to D-ID...")
        with open(audio_file, "rb") as f:
            files = {"file": f}
            response = await client.post(
                "http://localhost:55433/api/d-id/upload-audio",
                files=files
            )
        response.raise_for_status()
        audio_url = response.json()["url"]
        print(f"✅ Audio: {audio_url}")

        # Step 4: Generate video
        print("🎬 Generating video...")
        response = await client.post(
            "http://localhost:55433/api/d-id/generate-video",
            json={
                "audio_url": audio_url,
                "source_url": image_url
            }
        )
        response.raise_for_status()
        result = response.json()
        talk_id = result["id"]
        print(f"✅ Talk ID: {talk_id}")

        # Step 5: Poll status
        print("⏳ Waiting for video generation...")
        for attempt in range(60):
            response = await client.get(
                f"http://localhost:55433/api/d-id/talk-status/{talk_id}"
            )
            response.raise_for_status()
            data = response.json()
            status = data["status"]

            print(f"  [{attempt+1}/60] Status: {status}")

            if status == "done":
                video_url = data["result_url"]
                print(f"✅ Video ready: {video_url}")
                return video_url
            elif status in ["error", "rejected"]:
                print(f"❌ Failed: {data}")
                return None

            await asyncio.sleep(5)

        print("❌ Timeout")
        return None

if __name__ == "__main__":
    video_url = asyncio.run(generate_video())
    if video_url:
        print(f"\n🎉 Success! Video URL:\n{video_url}")
    else:
        print("\n😞 Generation failed")
```

**Run it**:
```bash
python quick_test.py
```

---

## Troubleshooting

### ❌ Problem: "API key not configured"

**Solution**:
```bash
# Verify .env file
cat .env | grep D_ID_API_KEY

# Should output: D_ID_API_KEY=your-actual-key-here
# If not, edit .env and add the key

# Restart backend
docker-compose restart backend
```

### ❌ Problem: "Connection refused"

**Solution**:
```bash
# Check if Docker is running
docker ps

# If empty, start services
docker-compose up -d

# Check logs
docker-compose logs backend
```

### ❌ Problem: "Image upload failed"

**Solution**:
- **File too large**: Compress image to < 10 MB
- **Invalid format**: Convert to JPEG/PNG
- **Wrong path**: Use absolute path or verify file exists

```bash
# Check image size
ls -lh portrait.jpg

# Convert to JPEG (Mac/Linux)
convert portrait.png portrait.jpg

# Compress image
convert portrait.jpg -quality 85 portrait_compressed.jpg
```

### ❌ Problem: "Video generation timed out"

**Solution**:
- **Network issue**: Check internet connection
- **D-ID service down**: Visit https://status.d-id.com/
- **Audio too long**: Trim audio to < 5 minutes

```bash
# Check D-ID API status
curl -I https://api.d-id.com/

# Should return: HTTP/2 200
```

---

## Next Steps

🎉 **Congratulations!** You've successfully generated your first D-ID video.

### Learn More

- **Full Documentation**: [D_ID_INTEGRATION_SPEC.md](./D_ID_INTEGRATION_SPEC.md)
- **Troubleshooting Guide**: [D_ID_TROUBLESHOOTING.md](./D_ID_TROUBLESHOOTING.md)
- **API Reference**: [D_ID_INTEGRATION_SPEC.md#4-api-endpoints](./D_ID_INTEGRATION_SPEC.md#4-api-endpoints)

### Explore Advanced Features

- **Voice Cloning**: Use OpenVoice V2 to clone your own voice
- **Multiple Voices**: Try different VOICEVOX speakers
- **Background Music**: Add BGM to videos
- **Batch Processing**: Generate multiple videos in parallel

### Join the Community

- **GitHub Issues**: Report bugs or request features
- **Discord**: Join our developer community
- **Support**: support@video-message-app.com

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ D-ID Quick Reference                                    │
├─────────────────────────────────────────────────────────┤
│ Web UI:     http://localhost:55434                      │
│ API Docs:   http://localhost:55433/docs                 │
│ Health:     http://localhost:55433/api/d-id/health      │
├─────────────────────────────────────────────────────────┤
│ Upload Image:                                           │
│   curl -X POST .../upload-source-image -F "file=@..."   │
│                                                         │
│ Upload Audio:                                           │
│   curl -X POST .../upload-audio -F "file=@..."          │
│                                                         │
│ Generate Video:                                         │
│   curl -X POST .../generate-video -d '{...}'            │
│                                                         │
│ Check Status:                                           │
│   curl .../talk-status/{talk_id}                        │
└─────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-07
**Maintained by**: Muses (Knowledge Architect)

*"最初の一歩は、素晴らしい旅の始まりです。"*
