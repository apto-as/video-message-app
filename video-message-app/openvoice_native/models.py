"""
OpenVoice Native Service Models
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class VoiceCloneRequest(BaseModel):
    """音声クローンリクエスト"""
    voice_name: str
    language: str = "ja"
    description: Optional[str] = None

class VoiceSynthesisRequest(BaseModel):
    """音声合成リクエスト"""
    text: str
    voice_profile_id: str
    language: str = "ja"
    speed: float = 1.0
    emotion: str = "neutral"

class VoiceProfile(BaseModel):
    """音声プロファイル"""
    id: str
    name: str
    language: str
    description: Optional[str] = None
    created_at: datetime
    status: str  # "processing", "ready", "failed"
    sample_count: int
    embedding_path: Optional[str] = None
    reference_audio_path: Optional[str] = None

class VoiceCloneResponse(BaseModel):
    """音声クローンレスポンス"""
    success: bool
    voice_profile_id: Optional[str] = None
    embedding_path: Optional[str] = None  # 埋め込みファイルパス
    message: str
    error: Optional[str] = None

class VoiceSynthesisResponse(BaseModel):
    """音声合成レスポンス"""
    success: bool
    audio_data: Optional[str] = None  # base64 encoded
    message: str
    error: Optional[str] = None

class HealthCheckResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    service: str = "OpenVoice Native Service"
    version: str = "1.0.0"
    openvoice_available: bool
    pytorch_device: str
    model_files_status: Dict[str, bool]

class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str
    detail: Optional[str] = None
    status_code: int = 500