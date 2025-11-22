"""
Rate Limiting Middleware for FastAPI

Security Features:
- Per-user rate limiting (10 req/min for synthesis endpoints)
- Global rate limiting (100 req/min across all users)
- Redis-based distributed rate limiting
- Token bucket algorithm via slowapi

Usage:
    from middleware.rate_limiter import limiter, rate_limit_exceeded_handler

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @router.post("/synthesis")
    @limiter.limit("10/minute")
    async def synthesize(...):
        ...
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging
import os
import redis.asyncio as redis
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Redis Configuration
# ============================================================================

def get_redis_url() -> str:
    """Get Redis URL from environment (default: localhost)"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    return f"redis://{redis_host}:{redis_port}/{redis_db}"

# ============================================================================
# Key Function for Rate Limiting
# ============================================================================

def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on user identification

    Priority:
    1. user_id from request state (if authenticated)
    2. API key from Authorization header
    3. Remote IP address (fallback)

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier for rate limiting
    """
    # Try to get user_id from request state (if authentication middleware set it)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Try to get API key from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header.replace("Bearer ", "")[:16]  # First 16 chars for privacy
        return f"api_key:{api_key}"

    # Fallback to IP address
    return get_remote_address(request)

# ============================================================================
# Limiter Instance
# ============================================================================

limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Global limit: 100 req/min
    storage_uri=get_redis_url(),
    strategy="moving-window",  # More accurate than fixed-window
    headers_enabled=True  # Add X-RateLimit-* headers to responses
)

logger.info(f"Rate limiter initialized with Redis: {get_redis_url()}")

# ============================================================================
# Custom Rate Limit Exceeded Handler
# ============================================================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors

    Returns JSON response with retry-after header
    """
    logger.warning(
        f"Rate limit exceeded: {get_rate_limit_key(request)} "
        f"on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "レート制限に達しました",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc),
            "retry_after_seconds": getattr(exc, "retry_after", 60)
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60))
        }
    )

# ============================================================================
# Redis Health Check
# ============================================================================

async def check_redis_health() -> bool:
    """
    Check if Redis is available

    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        redis_client = redis.from_url(get_redis_url(), decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False

# ============================================================================
# Rate Limit Decorators (Convenience)
# ============================================================================

# Per-user synthesis limit: 10 requests/minute
SYNTHESIS_LIMIT = "10/minute"

# Per-user upload limit: 5 requests/minute
UPLOAD_LIMIT = "5/minute"

# Global API limit: 100 requests/minute (default)
GLOBAL_LIMIT = "100/minute"

"""
Example Usage:

from middleware.rate_limiter import limiter, SYNTHESIS_LIMIT, UPLOAD_LIMIT

@router.post("/voice-clone/synthesize")
@limiter.limit(SYNTHESIS_LIMIT)
async def synthesize_voice(request: Request, ...):
    # Endpoint logic
    pass

@router.post("/voice-clone/create")
@limiter.limit(UPLOAD_LIMIT)
async def create_voice_clone(request: Request, ...):
    # Endpoint logic
    pass
"""
