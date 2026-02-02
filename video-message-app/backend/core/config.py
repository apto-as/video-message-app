from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os

class Settings(BaseSettings):
    cors_origins: List[str] = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:55434").split(","))
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    did_api_key: Optional[str] = Field(
        default=None,
        alias="DID_API_KEY",
        description="D-ID API key for lip-sync video generation"
    )

    # 環境変数パス管理
    docker_env: str = os.environ.get('DOCKER_ENV', 'false')
    storage_root_path: str = os.environ.get('STORAGE_ROOT_PATH', '/app/storage/voices')
    voicevox_base_url: str = os.environ.get('VOICEVOX_BASE_URL', 'http://voicevox_engine:50021')
    openvoice_api_url: str = os.environ.get('OPENVOICE_API_URL', 'http://host.docker.internal:8001')
    debug_mode: str = os.environ.get('DEBUG_MODE', 'false')
    log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
    base_url: str = os.environ.get('BASE_URL', 'http://localhost:55433')
    storage_dir: str = os.environ.get('STORAGE_DIR', '/app/storage')

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

settings = Settings()