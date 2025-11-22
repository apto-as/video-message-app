"""
Rate Limiter for D-ID API requests
Redis-based queue management with fair queueing (FIFO)
"""

import asyncio
import time
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Request priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RequestToken:
    """Token for rate-limited request"""
    request_id: str
    priority: Priority
    timestamp: float
    metadata: Dict[str, Any]


class RateLimiter:
    """
    Rate limiter with Redis-based queue management
    Supports concurrent request limiting and fair queueing
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        redis_url: Optional[str] = None,
        key_prefix: str = "d_id_rate_limiter"
    ):
        """
        Initialize rate limiter

        Args:
            max_concurrent: Maximum concurrent requests
            redis_url: Redis connection URL (optional, falls back to in-memory)
            key_prefix: Redis key prefix
        """
        self.max_concurrent = max_concurrent
        self.redis_url = redis_url
        self.key_prefix = key_prefix

        # Redis client (lazy initialization)
        self._redis: Optional[redis.Redis] = None
        self._use_redis = REDIS_AVAILABLE and redis_url is not None

        # In-memory fallback
        self._active_requests: Dict[str, RequestToken] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(
            f"Rate limiter initialized: max_concurrent={max_concurrent}, "
            f"use_redis={self._use_redis}"
        )

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client (lazy initialization)"""
        if not self._use_redis:
            return None

        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Falling back to in-memory.")
                self._use_redis = False
                return None

        return self._redis

    async def acquire(
        self,
        priority: Priority = Priority.NORMAL,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Acquire a slot for request execution

        Args:
            priority: Request priority
            timeout: Maximum wait time (seconds)
            metadata: Additional metadata for the request

        Returns:
            Request ID (token)

        Raises:
            TimeoutError: If timeout is exceeded
        """
        request_id = str(uuid.uuid4())
        token = RequestToken(
            request_id=request_id,
            priority=priority,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        start_time = time.time()

        try:
            if self._use_redis:
                await self._acquire_redis(token, timeout)
            else:
                await self._acquire_memory(token, timeout)

            wait_time = time.time() - start_time
            logger.info(
                f"Request {request_id} acquired slot "
                f"(priority={priority.name}, wait_time={wait_time:.2f}s)"
            )

            return request_id

        except asyncio.TimeoutError:
            logger.warning(
                f"Request {request_id} timed out after {time.time() - start_time:.2f}s"
            )
            raise TimeoutError(f"Rate limiter timeout after {timeout}s")

    async def _acquire_memory(self, token: RequestToken, timeout: Optional[float]):
        """Acquire slot using in-memory semaphore"""
        if timeout:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=timeout
            )
        else:
            await self._semaphore.acquire()

        self._active_requests[token.request_id] = token

    async def _acquire_redis(self, token: RequestToken, timeout: Optional[float]):
        """Acquire slot using Redis-based queue"""
        redis_client = await self._get_redis()
        if redis_client is None:
            # Fallback to in-memory
            return await self._acquire_memory(token, timeout)

        active_key = f"{self.key_prefix}:active"
        queue_key = f"{self.key_prefix}:queue:{token.priority.value}"

        # Add to queue
        await redis_client.zadd(
            queue_key,
            {token.request_id: token.timestamp}
        )

        start_time = time.time()

        # Wait for slot
        while True:
            # Check active count
            active_count = await redis_client.zcard(active_key)

            if active_count < self.max_concurrent:
                # Check if this request is next in queue
                next_request = await redis_client.zrange(queue_key, 0, 0)

                if next_request and next_request[0] == token.request_id:
                    # Move from queue to active
                    await redis_client.zrem(queue_key, token.request_id)
                    await redis_client.zadd(
                        active_key,
                        {token.request_id: time.time()}
                    )
                    return

            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                await redis_client.zrem(queue_key, token.request_id)
                raise asyncio.TimeoutError()

            # Wait before retry
            await asyncio.sleep(0.1)

    async def release(self, request_id: str):
        """
        Release a slot after request completion

        Args:
            request_id: Request ID (token)
        """
        try:
            if self._use_redis:
                await self._release_redis(request_id)
            else:
                await self._release_memory(request_id)

            logger.info(f"Request {request_id} released slot")

        except Exception as e:
            logger.error(f"Error releasing slot for {request_id}: {e}")

    async def _release_memory(self, request_id: str):
        """Release slot from in-memory tracking"""
        if request_id in self._active_requests:
            del self._active_requests[request_id]
        self._semaphore.release()

    async def _release_redis(self, request_id: str):
        """Release slot from Redis tracking"""
        redis_client = await self._get_redis()
        if redis_client is None:
            return await self._release_memory(request_id)

        active_key = f"{self.key_prefix}:active"
        await redis_client.zrem(active_key, request_id)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get current rate limiter statistics

        Returns:
            Statistics dictionary
        """
        if self._use_redis:
            return await self._get_stats_redis()
        else:
            return self._get_stats_memory()

    def _get_stats_memory(self) -> Dict[str, Any]:
        """Get stats from in-memory tracking"""
        return {
            "backend": "memory",
            "max_concurrent": self.max_concurrent,
            "active_requests": len(self._active_requests),
            "available_slots": self.max_concurrent - len(self._active_requests),
            "queue_size": self._queue.qsize()
        }

    async def _get_stats_redis(self) -> Dict[str, Any]:
        """Get stats from Redis tracking"""
        redis_client = await self._get_redis()
        if redis_client is None:
            return self._get_stats_memory()

        active_key = f"{self.key_prefix}:active"
        active_count = await redis_client.zcard(active_key)

        # Count queue sizes by priority
        queue_sizes = {}
        for priority in Priority:
            queue_key = f"{self.key_prefix}:queue:{priority.value}"
            queue_sizes[priority.name] = await redis_client.zcard(queue_key)

        return {
            "backend": "redis",
            "max_concurrent": self.max_concurrent,
            "active_requests": active_count,
            "available_slots": self.max_concurrent - active_count,
            "queue_by_priority": queue_sizes
        }

    async def cleanup_expired(self, max_age_seconds: int = 600):
        """
        Cleanup expired requests (stuck/abandoned)

        Args:
            max_age_seconds: Maximum age before cleanup (default: 10 minutes)
        """
        if self._use_redis:
            await self._cleanup_expired_redis(max_age_seconds)
        else:
            self._cleanup_expired_memory(max_age_seconds)

    def _cleanup_expired_memory(self, max_age_seconds: int):
        """Cleanup expired requests from in-memory tracking"""
        current_time = time.time()
        expired = [
            req_id for req_id, token in self._active_requests.items()
            if current_time - token.timestamp > max_age_seconds
        ]

        for req_id in expired:
            logger.warning(f"Cleaning up expired request: {req_id}")
            del self._active_requests[req_id]
            self._semaphore.release()

    async def _cleanup_expired_redis(self, max_age_seconds: int):
        """Cleanup expired requests from Redis tracking"""
        redis_client = await self._get_redis()
        if redis_client is None:
            return self._cleanup_expired_memory(max_age_seconds)

        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        active_key = f"{self.key_prefix}:active"

        # Remove expired from active
        expired = await redis_client.zrangebyscore(
            active_key, "-inf", cutoff_time
        )

        if expired:
            logger.warning(f"Cleaning up {len(expired)} expired requests")
            await redis_client.zremrangebyscore(
                active_key, "-inf", cutoff_time
            )

    async def close(self):
        """Close Redis connection"""
        if self._redis is not None:
            await self._redis.close()
            logger.info("Redis connection closed")


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    max_concurrent: int = 10,
    redis_url: Optional[str] = None
) -> RateLimiter:
    """
    Get rate limiter singleton instance

    Args:
        max_concurrent: Maximum concurrent requests
        redis_url: Redis connection URL

    Returns:
        RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_concurrent=max_concurrent,
            redis_url=redis_url
        )

    return _rate_limiter
