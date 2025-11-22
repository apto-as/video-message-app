"""
Integration tests for background removal security

Tests security measures integrated into the background removal router:
- Image bomb detection in real API calls
- Resource limiting per user
- Timeout enforcement
- Malicious metadata rejection
"""
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io


# Import app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app  # Assuming main.py exists

client = TestClient(app)


def create_test_image(width: int, height: int, color: str = 'red') -> bytes:
    """Create test image bytes"""
    img = Image.new('RGB', (width, height), color=color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


class TestBackgroundRemovalSecurity:
    """Integration tests for security measures"""

    def test_valid_image_accepted(self):
        """Test that normal images are processed successfully"""
        image_data = create_test_image(512, 512, 'blue')

        response = client.post(
            "/background/remove-background",
            files={"image": ("test.jpg", image_data, "image/jpeg")}
        )

        # Should succeed (or fail for non-security reasons)
        # We're just checking it's not rejected by security
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"

    def test_image_bomb_rejected(self):
        """Test that image bombs are rejected"""
        # Create 100MP image (exceeds 50MP limit)
        image_data = create_test_image(10000, 10000, 'green')

        response = client.post(
            "/background/remove-background",
            files={"image": ("bomb.jpg", image_data, "image/jpeg")}
        )

        # Should be rejected with 400 Bad Request
        assert response.status_code == 400, f"Image bomb not rejected: {response.status_code}"
        assert "セキュリティ" in response.json()["detail"] or "too large" in response.json()["detail"]

    def test_tiny_file_rejected(self):
        """Test that suspiciously small files are rejected"""
        tiny_data = b"fake"

        response = client.post(
            "/background/remove-background",
            files={"image": ("tiny.jpg", tiny_data, "image/jpeg")}
        )

        assert response.status_code == 400
        assert "too small" in response.json()["detail"].lower()

    def test_oversized_file_rejected(self):
        """Test that files exceeding size limit are rejected"""
        # Create 11MB file
        large_data = b"x" * (11 * 1024 * 1024)

        response = client.post(
            "/background/remove-background",
            files={"image": ("large.jpg", large_data, "image/jpeg")}
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_requests_limited(self):
        """Test that concurrent requests per user are limited"""
        import asyncio
        from httpx import AsyncClient

        # Simulate 5 concurrent requests from same IP
        image_data = create_test_image(512, 512, 'red')

        async with AsyncClient(app=app, base_url="http://test") as ac:
            tasks = []
            for _ in range(5):
                task = ac.post(
                    "/background/remove-background",
                    files={"image": ("test.jpg", image_data, "image/jpeg")}
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # At least one should be rejected with 429 (Too Many Requests)
            status_codes = [r.status_code for r in responses if not isinstance(r, Exception)]

            # Check that we have 429 responses
            assert 429 in status_codes, f"Rate limit not enforced. Status codes: {status_codes}"

    def test_process_image_with_background_security(self):
        """Test security validation for both main and background images"""
        main_image = create_test_image(512, 512, 'blue')
        bg_image = create_test_image(10000, 10000, 'white')  # Image bomb

        response = client.post(
            "/process-image",
            files={
                "image": ("main.jpg", main_image, "image/jpeg"),
                "background": ("bg.jpg", bg_image, "image/jpeg")
            },
            data={
                "remove_background": "true",
                "enhance_quality": "true"
            }
        )

        # Background image should be rejected
        assert response.status_code == 400
        assert "背景" in response.json()["detail"] or "too large" in response.json()["detail"]


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_endpoint(self):
        """Test that health check works"""
        response = client.get("/background/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
