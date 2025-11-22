#!/usr/bin/env python3
"""
Example 1: Simple Video Generation
====================================

Generate a talking avatar video from image and audio files.

Usage:
    python 01_simple_video.py

Requirements:
    - Backend service running (docker-compose up -d)
    - D_ID_API_KEY configured in .env
    - Image file: portrait.jpg
    - Audio file: voice.wav
"""

import asyncio
import httpx
import sys
from pathlib import Path


async def generate_simple_video(
    image_path: str = "portrait.jpg",
    audio_path: str = "voice.wav"
):
    """Generate a simple talking avatar video"""

    # Configuration
    base_url = "http://localhost:55433/api/d-id"
    timeout = 300  # 5 minutes

    # Verify files exist
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)

    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=timeout) as client:

        # Step 1: Upload image
        print(f"📤 Uploading image: {image_path}")
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = await client.post(
                f"{base_url}/upload-source-image",
                files=files
            )
        response.raise_for_status()
        image_url = response.json()["url"]
        print(f"✅ Image uploaded: {image_url}")

        # Step 2: Upload audio
        print(f"📤 Uploading audio: {audio_path}")
        with open(audio_path, "rb") as f:
            files = {"file": f}
            response = await client.post(
                f"{base_url}/upload-audio",
                files=files
            )
        response.raise_for_status()
        audio_url = response.json()["url"]
        print(f"✅ Audio uploaded: {audio_url}")

        # Step 3: Generate video
        print("🎬 Generating video...")
        response = await client.post(
            f"{base_url}/generate-video",
            json={
                "audio_url": audio_url,
                "source_url": image_url
            }
        )
        response.raise_for_status()
        result = response.json()
        talk_id = result["id"]
        print(f"✅ Video generation started: {talk_id}")

        # Step 4: Poll status
        print("⏳ Waiting for video generation...")
        max_attempts = 60
        for attempt in range(max_attempts):
            response = await client.get(
                f"{base_url}/talk-status/{talk_id}"
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status")

            print(f"  [{attempt+1}/{max_attempts}] Status: {status}")

            if status == "done":
                video_url = data["result_url"]
                print(f"✅ Video ready: {video_url}")
                return video_url

            elif status in ["error", "rejected"]:
                print(f"❌ Video generation failed: {data}")
                sys.exit(1)

            # Wait 5 seconds before next poll
            await asyncio.sleep(5)

        print("❌ Video generation timed out")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("D-ID Example 1: Simple Video Generation")
    print("=" * 60)

    try:
        video_url = asyncio.run(generate_simple_video())
        print("\n" + "=" * 60)
        print("🎉 Success!")
        print(f"Video URL: {video_url}")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
