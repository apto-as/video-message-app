"""
Optimized D-ID API Client with connection pooling and retry logic
"""

import os
import asyncio
from typing import Dict, Any, Optional
import logging
from contextlib import asynccontextmanager

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from core.config import settings
from services.rate_limiter import get_rate_limiter, Priority

logger = logging.getLogger(__name__)


class DIdAPIError(Exception):
    """Base exception for D-ID API errors"""
    pass


class DIdRateLimitError(DIdAPIError):
    """Rate limit exceeded error"""
    pass


class DIdServerError(DIdAPIError):
    """D-ID server error (5xx)"""
    pass


class OptimizedDIdClient:
    """
    Optimized D-ID API Client with:
    - Connection pooling
    - Exponential backoff retry logic
    - Rate limiting
    - Proper error handling
    - Resource management
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_concurrent: int = 10,
        redis_url: Optional[str] = None,
        pool_limits: Optional[httpx.Limits] = None
    ):
        """
        Initialize optimized D-ID client

        Args:
            api_key: D-ID API key (defaults to environment variable)
            max_concurrent: Maximum concurrent requests
            redis_url: Redis URL for distributed rate limiting
            pool_limits: Custom connection pool limits
        """
        # API Key
        self.api_key = (
            api_key or
            getattr(settings, 'did_api_key', '') or
            os.getenv("DID_API_KEY", os.getenv("D_ID_API_KEY", ""))
        )

        if not self.api_key:
            logger.warning(
                "DID_API_KEY not configured. Check .env file or environment variables."
            )

        self.base_url = "https://api.d-id.com"

        # Connection pooling configuration
        self.pool_limits = pool_limits or httpx.Limits(
            max_connections=max_concurrent,
            max_keepalive_connections=max_concurrent // 2,
            keepalive_expiry=30.0
        )

        # Timeout configuration
        self.timeout = httpx.Timeout(
            connect=10.0,  # Connection timeout
            read=300.0,    # Read timeout (5 minutes for video generation)
            write=10.0,    # Write timeout
            pool=5.0       # Pool timeout
        )

        # HTTP client (lazy initialization)
        self._client: Optional[httpx.AsyncClient] = None

        # Rate limiter
        self.rate_limiter = get_rate_limiter(
            max_concurrent=max_concurrent,
            redis_url=redis_url
        )

        logger.info(
            f"Optimized D-ID client initialized: "
            f"max_concurrent={max_concurrent}, "
            f"pool_limits={self.pool_limits}"
        )

    @property
    def headers(self) -> Dict[str, str]:
        """API request headers"""
        return {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client (lazy initialization)"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=self.pool_limits,
                http2=True  # Enable HTTP/2
            )
            logger.info("HTTP client initialized with connection pooling")

        return self._client

    @asynccontextmanager
    async def _rate_limited_request(self, priority: Priority = Priority.NORMAL):
        """Context manager for rate-limited requests"""
        request_id = await self.rate_limiter.acquire(
            priority=priority,
            timeout=60.0  # 1 minute timeout for acquiring slot
        )

        try:
            yield request_id
        finally:
            await self.rate_limiter.release(request_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, DIdServerError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Raises:
            DIdAPIError: API error
        """
        client = await self._get_client()

        try:
            response = await client.request(method, endpoint, **kwargs)

            # Handle specific status codes
            if response.status_code == 429:
                raise DIdRateLimitError("Rate limit exceeded")
            elif 500 <= response.status_code < 600:
                raise DIdServerError(f"Server error: {response.status_code}")

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise DIdAPIError(f"API error: {e.response.status_code}") from e

    async def upload_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
        priority: Priority = Priority.NORMAL
    ) -> str:
        """
        Upload image to D-ID

        Args:
            image_data: Image binary data
            filename: Filename (optional)
            priority: Request priority

        Returns:
            Uploaded image URL
        """
        async with self._rate_limited_request(priority):
            files = {
                "image": (filename or "image.jpg", image_data, "image/jpeg")
            }

            response = await self._request_with_retry(
                "POST",
                "/images",
                headers={"Authorization": f"Basic {self.api_key}"},
                files=files
            )

            result = response.json()
            image_url = result.get("url")

            logger.info(f"Image uploaded successfully: {image_url}")
            return image_url

    async def upload_audio(
        self,
        audio_data: bytes,
        filename: Optional[str] = None,
        priority: Priority = Priority.NORMAL
    ) -> str:
        """
        Upload audio to D-ID

        Args:
            audio_data: Audio binary data
            filename: Filename (optional)
            priority: Request priority

        Returns:
            Uploaded audio URL
        """
        async with self._rate_limited_request(priority):
            files = {
                "audio": (filename or "audio.wav", audio_data, "audio/wav")
            }

            response = await self._request_with_retry(
                "POST",
                "/audios",
                headers={"Authorization": f"Basic {self.api_key}"},
                files=files
            )

            result = response.json()
            audio_url = result.get("url")

            logger.info(f"Audio uploaded successfully: {audio_url}")
            return audio_url

    async def create_talk_video(
        self,
        audio_url: str,
        source_url: str,
        priority: Priority = Priority.NORMAL,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create lip-sync video from audio

        Args:
            audio_url: Audio file URL
            source_url: Source image/video URL
            priority: Request priority
            config: Additional configuration options

        Returns:
            Generated video information
        """
        async with self._rate_limited_request(priority):
            # Request body
            body = {
                "script": {
                    "type": "audio",
                    "audio_url": audio_url
                },
                "source_url": source_url,
                "config": config or {
                    "stitch": True,
                    "pad_audio": 0.0
                }
            }

            # Create video
            response = await self._request_with_retry(
                "POST",
                "/talks",
                headers=self.headers,
                json=body
            )

            talk_data = response.json()
            talk_id = talk_data.get("id")

            if not talk_id:
                raise DIdAPIError("Failed to get video ID")

            logger.info(f"Video generation started: {talk_id}")

            # Wait for completion
            result = await self._wait_for_video(talk_id)
            return result

    async def _wait_for_video(
        self,
        talk_id: str,
        max_attempts: int = 60,
        poll_interval: float = 5.0
    ) -> Dict[str, Any]:
        """
        Wait for video generation completion

        Args:
            talk_id: Talk ID
            max_attempts: Maximum polling attempts
            poll_interval: Polling interval (seconds)

        Returns:
            Completed video information

        Raises:
            TimeoutError: Video generation timeout
            DIdAPIError: Generation failed
        """
        for attempt in range(max_attempts):
            try:
                response = await self._request_with_retry(
                    "GET",
                    f"/talks/{talk_id}",
                    headers=self.headers
                )

                data = response.json()
                status = data.get("status")

                if status == "done":
                    logger.info(f"Video generation completed: {talk_id}")
                    return data

                elif status in ("error", "rejected"):
                    error_msg = data.get("error", {}).get(
                        "description", "Unknown error"
                    )
                    raise DIdAPIError(f"Video generation failed: {error_msg}")

                # Still processing
                logger.debug(
                    f"Video generation in progress... "
                    f"({attempt + 1}/{max_attempts})"
                )
                await asyncio.sleep(poll_interval)

            except httpx.HTTPStatusError as e:
                logger.error(f"Status check error: {e.response.status_code}")
                raise DIdAPIError("Failed to check video status") from e

        raise TimeoutError(f"Video generation timeout after {max_attempts * poll_interval}s")

    async def get_talk_status(self, talk_id: str) -> Dict[str, Any]:
        """
        Get video generation status

        Args:
            talk_id: Talk ID

        Returns:
            Status information
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"/talks/{talk_id}",
                headers=self.headers
            )
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": "Failed to get status"}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics

        Returns:
            Statistics dictionary
        """
        rate_limiter_stats = await self.rate_limiter.get_stats()

        client_stats = {
            "api_key_configured": bool(self.api_key),
            "client_initialized": self._client is not None,
            "client_closed": self._client.is_closed if self._client else True,
            "pool_limits": {
                "max_connections": self.pool_limits.max_connections,
                "max_keepalive": self.pool_limits.max_keepalive_connections
            }
        }

        return {
            "client": client_stats,
            "rate_limiter": rate_limiter_stats
        }

    async def close(self):
        """Close client and cleanup resources"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            logger.info("HTTP client closed")

        await self.rate_limiter.close()


# Singleton instance
_optimized_client: Optional[OptimizedDIdClient] = None


def get_optimized_d_id_client(
    max_concurrent: int = 10,
    redis_url: Optional[str] = None
) -> OptimizedDIdClient:
    """
    Get optimized D-ID client singleton

    Args:
        max_concurrent: Maximum concurrent requests
        redis_url: Redis URL for distributed rate limiting

    Returns:
        OptimizedDIdClient instance
    """
    global _optimized_client

    if _optimized_client is None:
        _optimized_client = OptimizedDIdClient(
            max_concurrent=max_concurrent,
            redis_url=redis_url
        )

    return _optimized_client
