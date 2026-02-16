from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Tuple
import os

class Settings(BaseSettings):
    cors_origins: List[str] = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:55434").split(","))
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    # DEPRECATED: D-ID cloud API key - kept for potential cloud fallback only
    did_api_key: Optional[str] = Field(
        default=None,
        alias="DID_API_KEY",
        description="DEPRECATED: D-ID API key (unused - MuseTalk handles lip-sync locally)"
    )

    # 環境変数パス管理
    docker_env: str = os.environ.get('DOCKER_ENV', 'false')
    storage_root_path: str = os.environ.get('STORAGE_ROOT_PATH', '/app/storage/voices')
    voicevox_base_url: str = os.environ.get('VOICEVOX_BASE_URL', 'http://voicevox_engine:50021')
    # DEPRECATED: OpenVoice service has been replaced by Qwen3-TTS (qwen_tts_service_url)
    openvoice_api_url: str = os.environ.get('OPENVOICE_API_URL', 'http://host.docker.internal:8001')
    debug_mode: str = os.environ.get('DEBUG_MODE', 'false')
    log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
    base_url: str = os.environ.get('BASE_URL', 'http://localhost:55433')
    storage_dir: str = os.environ.get('STORAGE_DIR', '/app/storage')

    # =========================================================================
    # Local Inference Services (Qwen3-TTS, MuseTalk)
    # =========================================================================

    # Qwen3-TTS Service (voice cloning and synthesis)
    qwen_tts_service_url: str = Field(
        default=os.environ.get('QWEN_TTS_SERVICE_URL', 'http://qwen-tts:8002'),
        description="Qwen3-TTS service URL for voice cloning and synthesis"
    )
    use_local_tts: bool = Field(
        default=os.environ.get('USE_LOCAL_TTS', 'true').lower() == 'true',
        description="Use local Qwen3-TTS service for voice cloning"
    )

    # MuseTalk Service (local lip-sync)
    musetalk_service_url: str = Field(
        default=os.environ.get('MUSETALK_SERVICE_URL', 'http://musetalk:8003'),
        description="MuseTalk service URL for lip-sync video generation"
    )
    use_local_lipsync: bool = Field(
        default=os.environ.get('USE_LOCAL_LIPSYNC', 'true').lower() == 'true',
        description="Use local MuseTalk service for lip-sync video generation"
    )

    # LivePortrait + JoyVASA Service (audio-driven facial animation)
    liveportrait_service_url: str = Field(
        default=os.environ.get('LIVEPORTRAIT_SERVICE_URL', 'http://liveportrait:8004'),
        description="LivePortrait + JoyVASA service URL for audio-driven facial animation"
    )

    # EchoMimic Service (audio-driven portrait animation with blink + expressions)
    echomimic_service_url: str = Field(
        default=os.environ.get('ECHOMIMIC_SERVICE_URL', 'http://echomimic:8005'),
        description="EchoMimic service URL for audio-driven portrait animation"
    )

    lipsync_engine: str = Field(
        default=os.environ.get('LIPSYNC_ENGINE', 'musetalk'),
        description="Lip-sync engine to use: 'musetalk', 'liveportrait', 'echomimic', or 'auto'"
    )

    # Fallback behavior
    fallback_to_cloud: bool = Field(
        default=os.environ.get('FALLBACK_TO_CLOUD', 'true').lower() == 'true',
        description="Fallback to cloud services if local services unavailable"
    )

    # Upper-body cropper settings
    upper_body_crop_enabled: bool = Field(
        default=True,
        description="Enable smart upper-body cropping before MuseTalk/LivePortrait"
    )
    upper_body_crop_target_size: int = Field(
        default=512,
        description="Target output size (square) for upper-body crop"
    )
    upper_body_crop_face_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Target face height ratio in cropped output (0.4-0.6 optimal)"
    )

    # LaMa Inpainting settings for clothing repair
    inpainting_enabled: bool = Field(
        default=True,
        description="Enable LaMa inpainting for repairing clothing damaged by background removal"
    )
    inpainting_threshold: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Minimum damage ratio to trigger inpainting repair (0.0-1.0, default 1%)"
    )
    inpainting_dilate_mask: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Pixels to dilate the repair mask for better blending"
    )
    inpainting_device: Optional[str] = Field(
        default=None,
        description="Device for inpainting model ('cuda', 'cpu', or None for auto-detect)"
    )

    # Blink animation settings (post-processing for MuseTalk)
    blink_enabled: bool = Field(
        default=True,
        description="Enable blink animation post-processing for lip-synced videos"
    )
    blink_interval_min: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Minimum seconds between blinks"
    )
    blink_interval_max: float = Field(
        default=5.0,
        ge=2.0,
        le=15.0,
        description="Maximum seconds between blinks"
    )
    blink_duration_min: float = Field(
        default=0.15,
        ge=0.05,
        le=0.5,
        description="Minimum blink duration in seconds"
    )
    blink_duration_max: float = Field(
        default=0.30,
        ge=0.1,
        le=1.0,
        description="Maximum blink duration in seconds"
    )

    # BGM mixing settings
    bgm_volume_db: float = Field(
        default=-18.0,
        ge=-30.0,
        le=0.0,
        description="BGM volume in dB relative to speech audio"
    )
    bgm_fade_out_seconds: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="BGM fade-out duration in seconds at end of video"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"  # 追加の環境変数を許可

    @property
    def is_inpainting_enabled(self) -> bool:
        """Check if inpainting is enabled via environment variable or config."""
        env_value = os.environ.get('INPAINTING_ENABLED', '').lower()
        if env_value in ('true', '1', 'yes'):
            return True
        elif env_value in ('false', '0', 'no'):
            return False
        return self.inpainting_enabled

    @property
    def get_inpainting_threshold(self) -> float:
        """Get inpainting threshold from environment variable or config."""
        env_value = os.environ.get('INPAINTING_THRESHOLD')
        if env_value:
            try:
                return float(env_value)
            except ValueError:
                pass
        return self.inpainting_threshold

    # =========================================================================
    # Local Inference Service Properties
    # =========================================================================

    @property
    def should_use_local_tts(self) -> bool:
        """Check if local TTS (Qwen3-TTS) should be used."""
        env_value = os.environ.get('USE_LOCAL_TTS', '').lower()
        if env_value in ('true', '1', 'yes'):
            return True
        elif env_value in ('false', '0', 'no'):
            return False
        return self.use_local_tts

    @property
    def should_use_local_lipsync(self) -> bool:
        """Check if local lip-sync (MuseTalk) should be used."""
        env_value = os.environ.get('USE_LOCAL_LIPSYNC', '').lower()
        if env_value in ('true', '1', 'yes'):
            return True
        elif env_value in ('false', '0', 'no'):
            return False
        return self.use_local_lipsync

    @property
    def should_fallback_to_cloud(self) -> bool:
        """Check if fallback to cloud services is enabled."""
        env_value = os.environ.get('FALLBACK_TO_CLOUD', '').lower()
        if env_value in ('true', '1', 'yes'):
            return True
        elif env_value in ('false', '0', 'no'):
            return False
        return self.fallback_to_cloud

    def get_tts_service_url(self) -> str:
        """Get the appropriate TTS service URL based on configuration."""
        # Always use Qwen3-TTS (OpenVoice service is deprecated)
        return self.qwen_tts_service_url

    def get_lipsync_service_info(self) -> dict:
        """Get lip-sync service configuration."""
        return {
            'use_local': self.should_use_local_lipsync,
            'local_url': self.musetalk_service_url,
            'liveportrait_url': self.liveportrait_service_url,
            'engine': self.get_lipsync_engine,
            'cloud_configured': bool(self.did_api_key),
            'fallback_enabled': self.should_fallback_to_cloud
        }

    @property
    def get_lipsync_engine(self) -> str:
        """Get the configured lip-sync engine."""
        env_value = os.environ.get('LIPSYNC_ENGINE', '').lower()
        if env_value in ('musetalk', 'liveportrait', 'echomimic', 'auto'):
            return env_value
        return self.lipsync_engine

    # =========================================================================
    # Blink Animation Properties
    # =========================================================================

    @property
    def is_blink_enabled(self) -> bool:
        """Check if blink animation is enabled."""
        env_value = os.environ.get('BLINK_ENABLED', '').lower()
        if env_value in ('true', '1', 'yes'):
            return True
        elif env_value in ('false', '0', 'no'):
            return False
        return self.blink_enabled

    @property
    def get_blink_interval_range(self) -> Tuple[float, float]:
        """Get blink interval range (min, max) in seconds."""
        min_val = self.blink_interval_min
        max_val = self.blink_interval_max
        # Try to get from environment
        env_min = os.environ.get('BLINK_INTERVAL_MIN')
        env_max = os.environ.get('BLINK_INTERVAL_MAX')
        if env_min:
            try:
                min_val = float(env_min)
            except ValueError:
                pass
        if env_max:
            try:
                max_val = float(env_max)
            except ValueError:
                pass
        return (min_val, max_val)

    @property
    def get_blink_duration_range(self) -> Tuple[float, float]:
        """Get blink duration range (min, max) in seconds."""
        min_val = self.blink_duration_min
        max_val = self.blink_duration_max
        # Try to get from environment
        env_min = os.environ.get('BLINK_DURATION_MIN')
        env_max = os.environ.get('BLINK_DURATION_MAX')
        if env_min:
            try:
                min_val = float(env_min)
            except ValueError:
                pass
        if env_max:
            try:
                max_val = float(env_max)
            except ValueError:
                pass
        return (min_val, max_val)

settings = Settings()