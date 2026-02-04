"""
Configuration for MuseTalk Lip-Sync Service
"""
import os
from pathlib import Path


class Config:
    """Service configuration"""

    # Service settings
    SERVICE_NAME = "MuseTalk Lip-Sync Service"
    VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8003"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Paths
    BASE_DIR = Path("/app")
    STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
    MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
    MUSETALK_DIR = Path(os.getenv("MUSETALK_DIR", "/app/MuseTalk"))

    # Storage subdirectories
    VIDEOS_DIR = STORAGE_DIR / "videos"
    UPLOADS_DIR = STORAGE_DIR / "uploads"
    TEMP_DIR = STORAGE_DIR / "temp"

    # Model settings
    MODEL_PRECISION = os.getenv("MODEL_PRECISION", "fp16")  # fp16 or fp32
    LAZY_LOAD = os.getenv("LAZY_LOAD", "true").lower() == "true"
    UNLOAD_IDLE_SECONDS = int(os.getenv("UNLOAD_IDLE_SECONDS", "300"))  # 5 minutes

    # VRAM management (T4 has 16GB)
    MAX_VRAM_GB = float(os.getenv("MAX_VRAM_GB", "14.0"))  # Reserve 2GB for system
    CLEAR_CACHE_AFTER_GENERATION = os.getenv("CLEAR_CACHE_AFTER_GENERATION", "true").lower() == "true"

    # Video settings
    OUTPUT_RESOLUTION = int(os.getenv("OUTPUT_RESOLUTION", "256"))
    OUTPUT_FPS = int(os.getenv("OUTPUT_FPS", "25"))
    OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "mp4")
    VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
    AUDIO_CODEC = os.getenv("AUDIO_CODEC", "aac")

    # Job settings
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))
    JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "600"))  # 10 minutes
    MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "10"))

    # File limits
    MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
    MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "50"))
    MAX_AUDIO_DURATION_SECONDS = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "300"))  # 5 minutes

    # Supported formats
    SUPPORTED_IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp"}
    SUPPORTED_AUDIO_FORMATS = {"wav", "mp3", "m4a", "ogg", "flac"}

    @classmethod
    def init_directories(cls):
        """Create necessary directories"""
        for directory in [cls.VIDEOS_DIR, cls.UPLOADS_DIR, cls.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_device(cls) -> str:
        """Get the appropriate device for inference"""
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"


# Initialize directories on module load
Config.init_directories()
