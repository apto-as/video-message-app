"""
Qwen3-TTS Service Models
Compatible with OpenVoice API for drop-in replacement
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProfileStatus(str, Enum):
    """Voice profile status"""
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VoiceCloneRequest(BaseModel):
    """Voice clone request"""
    voice_name: str = Field(..., description="Voice profile name")
    language: str = Field(default="ja", description="Language code")
    description: Optional[str] = Field(None, description="Description")


class VoiceSynthesisRequest(BaseModel):
    """Voice synthesis request"""
    text: str = Field(..., description="Text to synthesize")
    voice_profile_id: str = Field(..., description="Voice profile ID")
    language: str = Field(default="ja", description="Language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    pitch: float = Field(default=0.0, ge=-0.15, le=0.15, description="Pitch shift")
    volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Volume")
    pause_duration: float = Field(default=0.0, ge=0.0, le=3.0, description="End pause duration (seconds)")


class VoiceProfile(BaseModel):
    """Voice profile"""
    id: str = Field(..., description="Profile ID")
    name: str = Field(..., description="Profile name")
    language: str = Field(..., description="Language code")
    description: Optional[str] = Field(None, description="Description")
    created_at: datetime = Field(..., description="Creation timestamp")
    status: ProfileStatus = Field(..., description="Profile status")
    sample_count: int = Field(default=1, description="Number of audio samples")
    embedding_path: Optional[str] = Field(None, description="Embedding file path")
    reference_audio_path: Optional[str] = Field(None, description="Reference audio path")
    engine: str = Field(default="qwen3-tts", description="TTS engine name")


class VoiceCloneResponse(BaseModel):
    """Voice clone response - compatible with OpenVoice API"""
    success: bool = Field(..., description="Success flag")
    voice_profile_id: Optional[str] = Field(None, alias="profile_id", description="Created profile ID")
    embedding_path: Optional[str] = Field(None, description="Embedding file path")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        populate_by_name = True


class VoiceSynthesisResponse(BaseModel):
    """Voice synthesis response - compatible with OpenVoice API"""
    success: bool = Field(..., description="Success flag")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if failed")


class ModelStatus(BaseModel):
    """Model loading status"""
    loaded: bool = Field(default=False, description="Whether model is loaded")
    loading: bool = Field(default=False, description="Whether model is currently loading")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    vram_usage_mb: Optional[float] = Field(None, description="VRAM usage in MB")


class HealthCheckResponse(BaseModel):
    """Health check response - compatible with OpenVoice API"""
    status: str = Field(..., description="Service status")
    service: str = Field(default="Qwen3-TTS Service", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    pytorch_device: str = Field(..., description="PyTorch device")
    model_files_status: Dict[str, bool] = Field(default_factory=dict, description="Model file status")
    # Additional fields for Qwen3-TTS
    model_name: Optional[str] = Field(None, description="Model name")
    vram_usage_mb: Optional[float] = Field(None, description="VRAM usage in MB")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    detail: Optional[str] = Field(None, description="Error detail")
    status_code: int = Field(default=500, description="HTTP status code")


class AudioProcessingConfig(BaseModel):
    """Audio processing configuration"""
    sample_rate: int = Field(default=22050, description="Sample rate in Hz")
    channels: int = Field(default=1, description="Number of channels (mono=1)")
    bit_depth: int = Field(default=16, description="Bit depth")
    format: str = Field(default="wav", description="Audio format")
