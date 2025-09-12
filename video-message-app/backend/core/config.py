from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os

class Settings(BaseSettings):
    cors_origins: List[str] = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:55434").split(","))
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    did_api_key: Optional[str] = None  # D-ID API key for lip-sync video generation
    
    # 環境変数パス管理
    docker_env: str = os.environ.get('DOCKER_ENV', 'false')
    storage_root_path: str = os.environ.get('STORAGE_ROOT_PATH', '/app/storage/voices')
    voicevox_base_url: str = os.environ.get('VOICEVOX_BASE_URL', 'http://voicevox_engine:50021')
    openvoice_api_url: str = os.environ.get('OPENVOICE_API_URL', 'http://host.docker.internal:8001')
    debug_mode: str = os.environ.get('DEBUG_MODE', 'false')
    log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 追加の環境変数を許可

settings = Settings()