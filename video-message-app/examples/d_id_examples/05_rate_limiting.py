#!/usr/bin/env python3
"""
Example 5: Rate Limiting
==========================

Implement rate limiting to avoid exceeding D-ID API limits.

Usage:
    python 05_rate_limiting.py

Features:
    - Token bucket rate limiter
    - Automatic request throttling
    - Retry on 429 errors
    - Credit monitoring
"""

import asyncio
import httpx
import sys
from datetime import datetime, timedelta
from collections import deque
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for D-ID API"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default: 60s = 1 minute)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            now = datetime.now()

            # Remove old requests outside time window
            while self.requests and self.requests[0] < now - timedelta(seconds=self.time_window):
                self.requests.popleft()

            # Calculate wait time if at limit
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                wait_time = (wait_until - now).total_seconds()

                if wait_time > 0:
                    print(f"⏸️  Rate limit reached. Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    # Recursive call after waiting
                    return await self.acquire()

            # Record this request
            self.requests.append(now)

    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window"""
        now = datetime.now()

        # Remove old requests
        while self.requests and self.requests[0] < now - timedelta(seconds=self.time_window):
            self.requests.popleft()

        return self.max_requests - len(self.requests)


class DIDClientWithRateLimit:
    """D-ID client with built-in rate limiting"""

    def __init__(
        self,
        base_url: str = "http://localhost:55433/api/d-id",
        max_requests: int = 10,
        time_window: int = 60
    ):
        self.base_url = base_url
        self.timeout = 300
        self.rate_limiter = RateLimiter(max_requests, time_window)

    async def upload_image(self, image_path: str) -> str:
        """Upload image with rate limiting"""
        await self.rate_limiter.acquire()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(image_path, "rb") as f:
                files = {"file": f}
                response = await client.post(
                    f"{self.base_url}/upload-source-image",
                    files=files
                )
            response.raise_for_status()
            return response.json()["url"]

    async def upload_audio(self, audio_path: str) -> str:
        """Upload audio with rate limiting"""
        await self.rate_limiter.acquire()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(audio_path, "rb") as f:
                files = {"file": f}
                response = await client.post(
                    f"{self.base_url}/upload-audio",
                    files=files
                )
            response.raise_for_status()
            return response.json()["url"]

    async def generate_video_with_retry(
        self,
        audio_url: str,
        source_url: str,
        max_retries: int = 3
    ) -> dict:
        """Generate video with rate limiting and 429 retry"""

        for attempt in range(max_retries):
            try:
                await self.rate_limiter.acquire()

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/generate-video",
                        json={
                            "audio_url": audio_url,
                            "source_url": source_url
                        }
                    )

                    # Handle 429 Rate Limit
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        print(f"⚠️  429 Rate Limit. Waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    # Retry on 429
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    print(f"⚠️  Rate limited. Retry {attempt+1}/{max_retries} in {retry_after}s...")
                    await asyncio.sleep(retry_after)
                else:
                    raise

        raise Exception("Max retries exceeded")

    async def wait_for_video(self, talk_id: str) -> str:
        """Wait for video generation (with rate limiting on status checks)"""
        max_attempts = 60

        for attempt in range(max_attempts):
            await self.rate_limiter.acquire()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/talk-status/{talk_id}"
                )
                response.raise_for_status()
                data = response.json()
                status = data.get("status")

                if status == "done":
                    return data["result_url"]
                elif status in ["error", "rejected"]:
                    raise ValueError(f"Generation failed: {data}")

                if attempt % 5 == 0:
                    remaining = self.rate_limiter.get_remaining_requests()
                    print(f"⏳ Status: {status} (Remaining requests: {remaining})")

            await asyncio.sleep(5)

        raise TimeoutError("Video generation timed out")


# Example usage
async def main():
    """Example: Generate video with rate limiting"""

    # Initialize client with rate limits
    # Free plan: 10 req/min
    # Lite plan: 30 req/min
    # Pro plan: 60 req/min
    client = DIDClientWithRateLimit(
        max_requests=10,  # Adjust based on your plan
        time_window=60
    )

    print("📤 Uploading image...")
    image_url = await client.upload_image("portrait.jpg")
    print(f"✅ Image: {image_url}")

    print("📤 Uploading audio...")
    audio_url = await client.upload_audio("voice.wav")
    print(f"✅ Audio: {audio_url}")

    print("🎬 Generating video...")
    result = await client.generate_video_with_retry(audio_url, image_url)
    talk_id = result["id"]
    print(f"✅ Talk ID: {talk_id}")

    print("⏳ Waiting for video...")
    video_url = await client.wait_for_video(talk_id)
    print(f"✅ Video ready: {video_url}")

    # Show remaining requests
    remaining = client.rate_limiter.get_remaining_requests()
    print(f"\n📊 Remaining requests in current window: {remaining}")


async def demo_batch_with_rate_limit():
    """Demo: Generate multiple videos with rate limiting"""

    client = DIDClientWithRateLimit(max_requests=10, time_window=60)

    print("\n" + "=" * 60)
    print("Demo: Batch generation with rate limiting")
    print("=" * 60)

    # Simulate 15 video generation requests
    # Rate limiter will automatically throttle to 10 req/min
    tasks = []
    for i in range(15):
        print(f"\n[{i+1}/15] Scheduling video generation...")

        # Each video requires 3 API calls:
        # 1. Upload image
        # 2. Upload audio
        # 3. Generate video
        # Total: 15 videos * 3 calls = 45 API calls
        # With 10 req/min limit, this will take ~5 minutes

        async def generate_single_video(index):
            try:
                image_url = await client.upload_image("portrait.jpg")
                audio_url = await client.upload_audio("voice.wav")
                result = await client.generate_video_with_retry(audio_url, image_url)
                print(f"[{index}] ✅ Video {index} started: {result['id']}")
                return result
            except Exception as e:
                print(f"[{index}] ❌ Failed: {e}")
                return None

        tasks.append(generate_single_video(i+1))

    # Execute all tasks
    results = await asyncio.gather(*tasks)

    # Summary
    success = sum(1 for r in results if r is not None)
    print(f"\n📊 Results: {success}/{len(results)} successful")


if __name__ == "__main__":
    print("=" * 60)
    print("D-ID Example 5: Rate Limiting")
    print("=" * 60)

    try:
        # Run simple example
        asyncio.run(main())

        # Uncomment to run batch demo (takes longer)
        # asyncio.run(demo_batch_with_rate_limit())

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
