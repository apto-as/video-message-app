"""
Redis Cache Manager for Video Pipeline
--------------------------------------
Caches expensive operations:
- YOLO detection results (5-8 seconds per image)
- Prosody-adjusted audio (2-3 seconds per audio)
- BiRefNet masks (3-5 seconds per image)

Design:
- 30% cache hit rate target → 5-8 seconds saved per request
- TTL: 24 hours for detection, 1 hour for audio
- Max cache size: 1GB
- LRU eviction policy
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pickle

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis package not available, caching will be disabled")

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry metadata"""
    key: str
    value_type: str
    created_at: datetime
    expires_at: datetime
    size_bytes: int
    hit_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class CacheStats:
    """Cache statistics"""
    total_hits: int
    total_misses: int
    hit_rate: float
    total_entries: int
    total_size_bytes: int
    evictions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "hit_rate": round(self.hit_rate * 100, 2),
            "total_entries": self.total_entries,
            "total_size_mb": round(self.total_size_bytes / 1024**2, 2),
            "evictions": self.evictions
        }


class CacheManager:
    """
    Redis-based cache manager with intelligent caching strategies

    Cache Keys:
    - yolo:{image_hash}:{conf}:{iou} -> List[PersonDetection]
    - prosody:{audio_hash}:{speed}:{pitch} -> bytes (audio)
    - birefnet:{image_hash}:{smoothing} -> bytes (PNG)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_size_mb: int = 1024,
        enable_stats: bool = True
    ):
        self.redis_url = redis_url
        self.max_size_mb = max_size_mb
        self.enable_stats = enable_stats

        self._redis: Optional[redis.Redis] = None
        self._connected = False

        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

        logger.info(f"CacheManager initialized: redis_url={redis_url}, max_size={max_size_mb}MB")

    async def connect(self) -> bool:
        """Connect to Redis server"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, caching disabled")
            return False

        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=False)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    def _compute_hash(self, data: bytes) -> str:
        """Compute SHA256 hash of data"""
        return hashlib.sha256(data).hexdigest()[:16]

    def _build_key(self, prefix: str, *args) -> str:
        """Build cache key from prefix and arguments"""
        parts = [str(arg) for arg in args]
        return f"{prefix}:" + ":".join(parts)

    async def get_yolo_detection(
        self,
        image_path: Path,
        conf_threshold: float,
        iou_threshold: float
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached YOLO detection results"""
        if not self._connected:
            return None

        # Compute image hash
        with open(image_path, "rb") as f:
            image_hash = self._compute_hash(f.read())

        key = self._build_key("yolo", image_hash, conf_threshold, iou_threshold)

        try:
            value = await self._redis.get(key)
            if value:
                self._stats["hits"] += 1
                logger.debug(f"Cache HIT: {key}")
                return pickle.loads(value)
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_yolo_detection(
        self,
        image_path: Path,
        conf_threshold: float,
        iou_threshold: float,
        detections: List[Dict[str, Any]],
        ttl_hours: int = 24
    ) -> bool:
        """Cache YOLO detection results"""
        if not self._connected:
            return False

        # Compute image hash
        with open(image_path, "rb") as f:
            image_hash = self._compute_hash(f.read())

        key = self._build_key("yolo", image_hash, conf_threshold, iou_threshold)

        try:
            value = pickle.dumps(detections)
            await self._redis.setex(key, timedelta(hours=ttl_hours), value)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_hours}h)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def get_prosody_audio(
        self,
        audio_path: Path,
        speed: float,
        pitch: float,
        volume: float,
        emphasis: float
    ) -> Optional[bytes]:
        """Get cached prosody-adjusted audio"""
        if not self._connected:
            return None

        # Compute audio hash
        with open(audio_path, "rb") as f:
            audio_hash = self._compute_hash(f.read())

        key = self._build_key("prosody", audio_hash, speed, pitch, volume, emphasis)

        try:
            value = await self._redis.get(key)
            if value:
                self._stats["hits"] += 1
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_prosody_audio(
        self,
        audio_path: Path,
        speed: float,
        pitch: float,
        volume: float,
        emphasis: float,
        audio_bytes: bytes,
        ttl_hours: int = 1
    ) -> bool:
        """Cache prosody-adjusted audio"""
        if not self._connected:
            return False

        # Compute audio hash
        with open(audio_path, "rb") as f:
            audio_hash = self._compute_hash(f.read())

        key = self._build_key("prosody", audio_hash, speed, pitch, volume, emphasis)

        try:
            await self._redis.setex(key, timedelta(hours=ttl_hours), audio_bytes)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_hours}h, Size: {len(audio_bytes)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def get_birefnet_mask(
        self,
        image_path: Path,
        smoothing: bool
    ) -> Optional[bytes]:
        """Get cached BiRefNet mask (PNG bytes)"""
        if not self._connected:
            return None

        # Compute image hash
        with open(image_path, "rb") as f:
            image_hash = self._compute_hash(f.read())

        key = self._build_key("birefnet", image_hash, smoothing)

        try:
            value = await self._redis.get(key)
            if value:
                self._stats["hits"] += 1
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_birefnet_mask(
        self,
        image_path: Path,
        smoothing: bool,
        png_bytes: bytes,
        ttl_hours: int = 24
    ) -> bool:
        """Cache BiRefNet mask"""
        if not self._connected:
            return False

        # Compute image hash
        with open(image_path, "rb") as f:
            image_hash = self._compute_hash(f.read())

        key = self._build_key("birefnet", image_hash, smoothing)

        try:
            await self._redis.setex(key, timedelta(hours=ttl_hours), png_bytes)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_hours}h, Size: {len(png_bytes)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self._connected:
            return 0

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def clear_all(self) -> bool:
        """Clear all cache entries"""
        if not self._connected:
            return False

        try:
            await self._redis.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0

        if self._connected:
            try:
                info = await self._redis.info("memory")
                total_size_bytes = info.get("used_memory", 0)
                total_entries = await self._redis.dbsize()
            except Exception as e:
                logger.error(f"Failed to get Redis stats: {e}")
                total_size_bytes = 0
                total_entries = 0
        else:
            total_size_bytes = 0
            total_entries = 0

        return CacheStats(
            total_hits=self._stats["hits"],
            total_misses=self._stats["misses"],
            hit_rate=hit_rate,
            total_entries=total_entries,
            total_size_bytes=total_size_bytes,
            evictions=self._stats["evictions"]
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check cache health"""
        if not self._connected:
            return {
                "status": "disconnected",
                "redis_available": False
            }

        try:
            await self._redis.ping()
            info = await self._redis.info()
            stats = await self.get_stats()

            return {
                "status": "healthy",
                "redis_available": True,
                "redis_version": info.get("redis_version"),
                "used_memory_mb": round(info.get("used_memory", 0) / 1024**2, 2),
                "connected_clients": info.get("connected_clients"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "stats": stats.to_dict()
            }
        except Exception as e:
            return {
                "status": "error",
                "redis_available": False,
                "error": str(e)
            }


# Global cache instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager

    if _cache_manager is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _cache_manager = CacheManager(redis_url=redis_url)
        await _cache_manager.connect()

    return _cache_manager


async def close_cache_manager():
    """Close global cache manager"""
    global _cache_manager

    if _cache_manager:
        await _cache_manager.disconnect()
        _cache_manager = None
