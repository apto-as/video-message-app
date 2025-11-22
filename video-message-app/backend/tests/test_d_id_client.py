"""
Unit tests for Optimized D-ID Client
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from services.d_id_client_optimized import (
    OptimizedDIdClient,
    DIdAPIError,
    DIdRateLimitError,
    DIdServerError
)
from services.rate_limiter import Priority


@pytest.fixture
def mock_client():
    """Create a mock D-ID client"""
    return OptimizedDIdClient(
        api_key="test_api_key",
        max_concurrent=5,
        redis_url=None  # Use in-memory for tests
    )


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client"""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.is_closed = False
    return client


class TestOptimizedDIdClient:
    """Test suite for OptimizedDIdClient"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_client):
        """Test client initialization"""
        assert mock_client.api_key == "test_api_key"
        assert mock_client.base_url == "https://api.d-id.com"
        assert mock_client.pool_limits.max_connections == 5
        assert mock_client.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_headers_property(self, mock_client):
        """Test headers property"""
        headers = mock_client.headers

        assert "Authorization" in headers
        assert headers["Authorization"] == "Basic test_api_key"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_client_lazy_initialization(self, mock_client):
        """Test lazy client initialization"""
        assert mock_client._client is None

        client = await mock_client._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert mock_client._client is client

    @pytest.mark.asyncio
    async def test_upload_image_success(self, mock_client, mock_httpx_client):
        """Test successful image upload"""
        # Mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"url": "https://example.com/image.jpg"}
        mock_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            image_data = b"fake_image_data"
            url = await mock_client.upload_image(
                image_data,
                filename="test.jpg",
                priority=Priority.NORMAL
            )

            assert url == "https://example.com/image.jpg"
            mock_httpx_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_audio_success(self, mock_client, mock_httpx_client):
        """Test successful audio upload"""
        # Mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"url": "https://example.com/audio.wav"}
        mock_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            audio_data = b"fake_audio_data"
            url = await mock_client.upload_audio(
                audio_data,
                filename="test.wav",
                priority=Priority.HIGH
            )

            assert url == "https://example.com/audio.wav"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_client, mock_httpx_client):
        """Test rate limit error handling"""
        # Mock 429 response
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            with pytest.raises(DIdRateLimitError):
                await mock_client.upload_image(
                    b"test_data",
                    priority=Priority.NORMAL
                )

    @pytest.mark.asyncio
    async def test_server_error_retry(self, mock_client, mock_httpx_client):
        """Test server error triggers retry"""
        # Mock 500 response
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            with pytest.raises(DIdServerError):
                # Will retry 3 times then fail
                await mock_client.upload_image(
                    b"test_data",
                    priority=Priority.NORMAL
                )

    @pytest.mark.asyncio
    async def test_create_talk_video_success(self, mock_client, mock_httpx_client):
        """Test successful video creation"""
        # Mock create response
        create_response = Mock(spec=httpx.Response)
        create_response.json.return_value = {
            "id": "talk_123",
            "status": "created"
        }
        create_response.status_code = 200

        # Mock status check response (done immediately)
        status_response = Mock(spec=httpx.Response)
        status_response.json.return_value = {
            "id": "talk_123",
            "status": "done",
            "result_url": "https://example.com/video.mp4",
            "created_at": "2025-01-01T00:00:00Z"
        }
        status_response.status_code = 200

        # Setup request mock to return different responses
        mock_httpx_client.request = AsyncMock(
            side_effect=[create_response, status_response]
        )

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            result = await mock_client.create_talk_video(
                audio_url="https://example.com/audio.wav",
                source_url="https://example.com/image.jpg",
                priority=Priority.NORMAL
            )

            assert result["id"] == "talk_123"
            assert result["status"] == "done"
            assert result["result_url"] == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_wait_for_video_timeout(self, mock_client, mock_httpx_client):
        """Test video generation timeout"""
        # Mock status response (always processing)
        status_response = Mock(spec=httpx.Response)
        status_response.json.return_value = {
            "id": "talk_123",
            "status": "processing"
        }
        status_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=status_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            with pytest.raises(TimeoutError):
                await mock_client._wait_for_video(
                    "talk_123",
                    max_attempts=2,
                    poll_interval=0.1
                )

    @pytest.mark.asyncio
    async def test_wait_for_video_error(self, mock_client, mock_httpx_client):
        """Test video generation error"""
        # Mock error response
        error_response = Mock(spec=httpx.Response)
        error_response.json.return_value = {
            "id": "talk_123",
            "status": "error",
            "error": {"description": "Invalid audio format"}
        }
        error_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=error_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            with pytest.raises(DIdAPIError, match="Invalid audio format"):
                await mock_client._wait_for_video("talk_123")

    @pytest.mark.asyncio
    async def test_get_talk_status(self, mock_client, mock_httpx_client):
        """Test get talk status"""
        # Mock status response
        status_response = Mock(spec=httpx.Response)
        status_response.json.return_value = {
            "id": "talk_123",
            "status": "processing"
        }
        status_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=status_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            status = await mock_client.get_talk_status("talk_123")

            assert status["id"] == "talk_123"
            assert status["status"] == "processing"

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_client):
        """Test get statistics"""
        stats = await mock_client.get_stats()

        assert "client" in stats
        assert "rate_limiter" in stats
        assert stats["client"]["api_key_configured"] is True

    @pytest.mark.asyncio
    async def test_close(self, mock_client, mock_httpx_client):
        """Test client cleanup"""
        mock_client._client = mock_httpx_client

        await mock_client.close()

        mock_httpx_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_client, mock_httpx_client):
        """Test concurrent request handling"""
        # Mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"url": "https://example.com/image.jpg"}
        mock_response.status_code = 200

        mock_httpx_client.request = AsyncMock(return_value=mock_response)

        with patch.object(mock_client, '_get_client', return_value=mock_httpx_client):
            # Create 5 concurrent requests
            tasks = [
                mock_client.upload_image(
                    f"image_{i}".encode(),
                    filename=f"test_{i}.jpg",
                    priority=Priority.NORMAL
                )
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(url == "https://example.com/image.jpg" for url in results)


class TestRateLimiter:
    """Test suite for RateLimiter integration"""

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_release(self, mock_client):
        """Test rate limiter acquire and release"""
        rate_limiter = mock_client.rate_limiter

        # Acquire slot
        request_id = await rate_limiter.acquire(
            priority=Priority.NORMAL,
            timeout=5.0
        )

        assert request_id is not None

        # Check stats
        stats = await rate_limiter.get_stats()
        assert stats["active_requests"] == 1

        # Release slot
        await rate_limiter.release(request_id)

        # Check stats after release
        stats = await rate_limiter.get_stats()
        assert stats["active_requests"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_max_concurrent(self, mock_client):
        """Test rate limiter max concurrent limit"""
        rate_limiter = mock_client.rate_limiter
        max_concurrent = rate_limiter.max_concurrent

        # Acquire max slots
        request_ids = []
        for _ in range(max_concurrent):
            request_id = await rate_limiter.acquire(
                priority=Priority.NORMAL,
                timeout=1.0
            )
            request_ids.append(request_id)

        # Check all slots are taken
        stats = await rate_limiter.get_stats()
        assert stats["active_requests"] == max_concurrent
        assert stats["available_slots"] == 0

        # Try to acquire one more (should timeout)
        with pytest.raises(TimeoutError):
            await rate_limiter.acquire(
                priority=Priority.NORMAL,
                timeout=0.5
            )

        # Release all
        for request_id in request_ids:
            await rate_limiter.release(request_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
