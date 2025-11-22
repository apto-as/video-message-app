"""
Optimized D-ID Video Generation API Router
With connection pooling, rate limiting, and proper error handling
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
import os

from services.d_id_client_optimized import (
    get_optimized_d_id_client,
    DIdAPIError,
    DIdRateLimitError,
    Priority
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class VideoGenerationRequest(BaseModel):
    """Video generation request"""
    audio_url: str = Field(..., description="Audio file URL")
    source_url: str = Field(..., description="Source image/video URL")
    priority: str = Field(
        default="normal",
        description="Request priority: low, normal, high, critical"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional configuration options"
    )

    def get_priority(self) -> Priority:
        """Convert string priority to enum"""
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.NORMAL,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }
        return priority_map.get(self.priority.lower(), Priority.NORMAL)


class VideoGenerationResponse(BaseModel):
    """Video generation response"""
    id: str
    status: str
    result_url: Optional[str] = None
    created_at: str
    message: Optional[str] = None


class UploadResponse(BaseModel):
    """Upload response"""
    url: str
    message: str = "Upload successful"


class StatusResponse(BaseModel):
    """Status response"""
    id: str
    status: str
    result_url: Optional[str] = None
    created_at: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class StatsResponse(BaseModel):
    """Statistics response"""
    client: Dict[str, Any]
    rate_limiter: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    api_key_configured: bool
    rate_limiter: Dict[str, Any]


# Dependency: Get optimized client
def get_client():
    """Get optimized D-ID client"""
    redis_url = os.getenv("REDIS_URL")  # Optional
    return get_optimized_d_id_client(
        max_concurrent=10,
        redis_url=redis_url
    )


@router.post("/generate-video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """
    Generate video using D-ID API with optimized client

    Features:
    - Connection pooling
    - Rate limiting (10 concurrent max)
    - Retry logic with exponential backoff
    - Priority-based queueing

    Args:
        request: Video generation request

    Returns:
        Generated video information

    Raises:
        HTTPException: If generation fails
    """
    client = get_client()

    try:
        logger.info(
            f"Video generation request: audio_url={request.audio_url}, "
            f"priority={request.priority}"
        )

        # Generate video with priority
        result = await client.create_talk_video(
            audio_url=request.audio_url,
            source_url=request.source_url,
            priority=request.get_priority(),
            config=request.config
        )

        return VideoGenerationResponse(
            id=result["id"],
            status=result["status"],
            result_url=result.get("result_url"),
            created_at=result["created_at"],
            message="Video generated successfully"
        )

    except DIdRateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )

    except DIdAPIError as e:
        logger.error(f"D-ID API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/talk-status/{talk_id}", response_model=StatusResponse)
async def get_talk_status(talk_id: str):
    """
    Get video generation status

    Args:
        talk_id: D-ID talk ID

    Returns:
        Video generation status

    Raises:
        HTTPException: If status check fails
    """
    client = get_client()

    try:
        status = await client.get_talk_status(talk_id)

        if "error" in status:
            raise HTTPException(
                status_code=500,
                detail=status["error"]
            )

        return StatusResponse(
            id=talk_id,
            status=status.get("status", "unknown"),
            result_url=status.get("result_url"),
            created_at=status.get("created_at"),
            error=status.get("error")
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get video status"
        )


@router.post("/upload-source-image", response_model=UploadResponse)
async def upload_source_image(
    file: UploadFile = File(...),
    priority: str = Query(default="normal", description="Upload priority")
):
    """
    Upload source image to D-ID

    Args:
        file: Image file
        priority: Upload priority

    Returns:
        Uploaded image URL

    Raises:
        HTTPException: If upload fails
    """
    client = get_client()

    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an image file."
            )

        # Read file data
        image_data = await file.read()

        # Parse priority
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.NORMAL,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }
        priority_enum = priority_map.get(priority.lower(), Priority.NORMAL)

        # Upload to D-ID
        image_url = await client.upload_image(
            image_data,
            filename=file.filename,
            priority=priority_enum
        )

        logger.info(f"Image uploaded: {image_url}")

        return UploadResponse(
            url=image_url,
            message="Image uploaded successfully"
        )

    except DIdRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )

    except DIdAPIError as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/upload-audio", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    priority: str = Query(default="normal", description="Upload priority")
):
    """
    Upload audio file to D-ID

    Args:
        file: Audio file
        priority: Upload priority

    Returns:
        Uploaded audio URL

    Raises:
        HTTPException: If upload fails
    """
    client = get_client()

    try:
        # Validate file type
        allowed_types = [
            'audio/wav', 'audio/mp3', 'audio/mpeg',
            'audio/mp4', 'audio/flac', 'audio/m4a'
        ]

        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed: WAV, MP3, MP4, FLAC, M4A"
            )

        # Read file data
        audio_data = await file.read()

        # Parse priority
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.NORMAL,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }
        priority_enum = priority_map.get(priority.lower(), Priority.NORMAL)

        # Upload to D-ID
        audio_url = await client.upload_audio(
            audio_data,
            filename=file.filename,
            priority=priority_enum
        )

        logger.info(f"Audio uploaded: {audio_url}")

        return UploadResponse(
            url=audio_url,
            message="Audio uploaded successfully"
        )

    except DIdRateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )

    except DIdAPIError as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Audio upload failed: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get D-ID client and rate limiter statistics

    Returns:
        Statistics information
    """
    client = get_client()

    try:
        stats = await client.get_stats()
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Service health status
    """
    client = get_client()

    try:
        stats = await client.get_stats()

        return HealthResponse(
            status="healthy",
            service="d-id-optimized",
            api_key_configured=stats["client"]["api_key_configured"],
            rate_limiter=stats["rate_limiter"]
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="d-id-optimized",
            api_key_configured=False,
            rate_limiter={"error": str(e)}
        )


@router.post("/cleanup-expired")
async def cleanup_expired_requests(
    max_age_seconds: int = Query(
        default=600,
        description="Maximum age in seconds before cleanup"
    )
):
    """
    Cleanup expired/stuck requests from rate limiter

    Args:
        max_age_seconds: Maximum age before cleanup (default: 10 minutes)

    Returns:
        Cleanup result
    """
    client = get_client()

    try:
        await client.rate_limiter.cleanup_expired(max_age_seconds)

        return {
            "message": "Cleanup completed",
            "max_age_seconds": max_age_seconds
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Cleanup failed"
        )
