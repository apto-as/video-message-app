#!/usr/bin/env python3
"""
Example 4: Batch Video Generation
===================================

Generate multiple videos in parallel for improved efficiency.

Usage:
    python 04_batch_generation.py

Features:
    - Parallel video generation
    - Progress tracking
    - Error handling per video
    - Summary report
"""

import asyncio
import httpx
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class BatchVideoGenerator:
    """Generate multiple D-ID videos in parallel"""

    def __init__(self, base_url: str = "http://localhost:55433/api/d-id"):
        self.base_url = base_url
        self.timeout = 300
        self.results = []

    async def upload_file(
        self,
        client: httpx.AsyncClient,
        file_path: str,
        endpoint: str
    ) -> str:
        """Upload a file and return its URL"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = await client.post(
                f"{self.base_url}/{endpoint}",
                files=files
            )
        response.raise_for_status()
        return response.json()["url"]

    async def generate_single_video(
        self,
        client: httpx.AsyncClient,
        request: Dict[str, Any],
        index: int
    ) -> Dict[str, Any]:
        """Generate a single video and return result"""
        try:
            name = request.get("name", f"video_{index}")
            print(f"[{index}] 🎬 Starting: {name}")

            # Upload image
            image_url = await self.upload_file(
                client,
                request["image_path"],
                "upload-source-image"
            )

            # Upload audio
            audio_url = await self.upload_file(
                client,
                request["audio_path"],
                "upload-audio"
            )

            # Generate video
            response = await client.post(
                f"{self.base_url}/generate-video",
                json={
                    "audio_url": audio_url,
                    "source_url": image_url
                }
            )
            response.raise_for_status()
            result = response.json()
            talk_id = result["id"]

            # Poll status
            video_url = await self.wait_for_video(client, talk_id, index)

            print(f"[{index}] ✅ Done: {name}")
            return {
                "index": index,
                "name": name,
                "status": "success",
                "video_url": video_url,
                "talk_id": talk_id
            }

        except Exception as e:
            print(f"[{index}] ❌ Failed: {str(e)}")
            return {
                "index": index,
                "name": request.get("name", f"video_{index}"),
                "status": "error",
                "error": str(e)
            }

    async def wait_for_video(
        self,
        client: httpx.AsyncClient,
        talk_id: str,
        index: int
    ) -> str:
        """Wait for video generation to complete"""
        max_attempts = 60
        for attempt in range(max_attempts):
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

            if attempt % 5 == 0:  # Print every 25 seconds
                print(f"[{index}] ⏳ Processing... ({status})")

            await asyncio.sleep(5)

        raise TimeoutError("Video generation timed out")

    async def generate_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate multiple videos in parallel"""

        print(f"\n📦 Batch Generation: {len(requests)} videos")
        print("=" * 60)

        start_time = datetime.now()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Create tasks for parallel execution
            tasks = [
                self.generate_single_video(client, req, i)
                for i, req in enumerate(requests, start=1)
            ]

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=False)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate summary
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count

        print("\n" + "=" * 60)
        print("📊 Batch Generation Summary")
        print("=" * 60)
        print(f"Total videos: {len(requests)}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {error_count}")
        print(f"⏱️  Total time: {duration:.1f}s")
        print(f"⚡ Average: {duration/len(requests):.1f}s per video")
        print("=" * 60)

        return results


# Example usage
async def main():
    """Example: Generate 5 videos in parallel"""

    # Define batch requests
    requests = [
        {
            "name": "Greeting Video",
            "image_path": "portrait_1.jpg",
            "audio_path": "greeting.wav"
        },
        {
            "name": "Tutorial Video",
            "image_path": "portrait_2.jpg",
            "audio_path": "tutorial.wav"
        },
        {
            "name": "Thank You Video",
            "image_path": "portrait_3.jpg",
            "audio_path": "thanks.wav"
        },
        {
            "name": "Announcement Video",
            "image_path": "portrait_4.jpg",
            "audio_path": "announcement.wav"
        },
        {
            "name": "Promotion Video",
            "image_path": "portrait_5.jpg",
            "audio_path": "promotion.wav"
        }
    ]

    # Verify files exist (in real use)
    # For demo, we'll create placeholder requests
    demo_requests = [
        {
            "name": f"Demo Video {i}",
            "image_path": "portrait.jpg",  # Use same files
            "audio_path": "voice.wav"
        }
        for i in range(1, 4)  # Generate 3 videos
    ]

    # Generate videos
    generator = BatchVideoGenerator()
    results = await generator.generate_batch(demo_requests)

    # Print results
    print("\n📋 Detailed Results:")
    for result in results:
        print(f"\n{result['index']}. {result['name']}")
        print(f"   Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   Video: {result['video_url']}")
        else:
            print(f"   Error: {result['error']}")


if __name__ == "__main__":
    print("=" * 60)
    print("D-ID Example 4: Batch Video Generation")
    print("=" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
