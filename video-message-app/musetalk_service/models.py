"""
Pydantic models for MuseTalk Lip-Sync Service API
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class VideoGenerationRequest(BaseModel):
    """Request model for video generation"""
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    source_url: Optional[str] = Field(None, description="URL to source image")

    class Config:
        json_schema_extra = {
            "example": {
                "audio_url": "https://example.com/audio.wav",
                "source_url": "https://example.com/face.jpg"
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response model for video generation"""
    id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    result_url: Optional[str] = Field(None, description="URL to generated video when complete")
    created_at: str = Field(..., description="ISO timestamp of job creation")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "result_url": None,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status query"""
    id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    result_url: Optional[str] = Field(None, description="URL to generated video when complete")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Job progress (0.0 to 1.0)")
    created_at: str = Field(..., description="ISO timestamp of job creation")
    started_at: Optional[str] = Field(None, description="ISO timestamp when processing started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when job completed")
    error: Optional[str] = Field(None, description="Error message if job failed")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "result_url": None,
                "progress": 0.45,
                "created_at": "2025-01-15T10:30:00Z",
                "started_at": "2025-01-15T10:30:05Z",
                "completed_at": None,
                "error": None
            }
        }


class UploadResponse(BaseModel):
    """Response model for file upload"""
    url: str = Field(..., description="URL to access the uploaded file")
    filename: str = Field(..., description="Stored filename")
    size: int = Field(..., description="File size in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "/storage/uploads/abc123.jpg",
                "filename": "abc123.jpg",
                "size": 102400
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    model_loaded: bool = Field(..., description="Whether the MuseTalk model is loaded")
    device: str = Field(..., description="Device being used (cuda/mps/cpu)")
    vram_used_gb: Optional[float] = Field(None, description="VRAM usage in GB (CUDA only)")
    vram_total_gb: Optional[float] = Field(None, description="Total VRAM in GB (CUDA only)")
    jobs_queued: int = Field(0, description="Number of jobs in queue")
    jobs_processing: int = Field(0, description="Number of jobs currently processing")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "MuseTalk Lip-Sync Service",
                "version": "1.0.0",
                "model_loaded": True,
                "device": "cuda",
                "vram_used_gb": 4.2,
                "vram_total_gb": 16.0,
                "jobs_queued": 2,
                "jobs_processing": 1
            }
        }


class JobData:
    """Internal job data structure"""

    def __init__(self, job_id: str):
        self.id = job_id
        self.status = JobStatus.QUEUED
        self.progress = 0.0
        self.result_url: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None

        # Input data
        self.audio_path: Optional[str] = None
        self.image_path: Optional[str] = None

    def to_response(self) -> JobStatusResponse:
        """Convert to API response model"""
        return JobStatusResponse(
            id=self.id,
            status=self.status,
            result_url=self.result_url,
            progress=self.progress,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error
        )

    def start_processing(self):
        """Mark job as processing"""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.utcnow().isoformat() + "Z"

    def complete(self, result_url: str):
        """Mark job as complete"""
        self.status = JobStatus.DONE
        self.result_url = result_url
        self.progress = 1.0
        self.completed_at = datetime.utcnow().isoformat() + "Z"

    def fail(self, error: str):
        """Mark job as failed"""
        self.status = JobStatus.ERROR
        self.error = error
        self.completed_at = datetime.utcnow().isoformat() + "Z"
