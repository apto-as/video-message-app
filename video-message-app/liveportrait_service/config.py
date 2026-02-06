"""
Configuration for LivePortrait + JoyVASA Service
"""
import os
from pathlib import Path


class Config:
    """Service configuration"""

    # Service settings
    SERVICE_NAME = "LivePortrait + JoyVASA Service"
    VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8004"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Paths
    BASE_DIR = Path("/app")
    STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
    MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))

    # Storage subdirectories
    VIDEOS_DIR = STORAGE_DIR / "videos"
    UPLOADS_DIR = STORAGE_DIR / "uploads"
    TEMP_DIR = STORAGE_DIR / "temp"

    # JoyVASA Model Paths (Audio -> Motion)
    JOYVASA_DIR = MODELS_DIR / "JoyVASA"
    JOYVASA_MOTION_GENERATOR = JOYVASA_DIR / "motion_generator" / "motion_generator_hubert_chinese.pt"
    JOYVASA_MOTION_TEMPLATE = JOYVASA_DIR / "motion_template" / "motion_template.pkl"
    JOYVASA_CONFIG = JOYVASA_DIR / "config.json"  # HuggingFace uses config.json

    # HuBERT Model for Audio Feature Extraction
    HUBERT_DIR = MODELS_DIR / "chinese-hubert-base"

    # LivePortrait ONNX Model Paths
    LIVEPORTRAIT_DIR = MODELS_DIR / "liveportrait_onnx"
    APPEARANCE_EXTRACTOR = LIVEPORTRAIT_DIR / "appearance_feature_extractor.onnx"
    MOTION_EXTRACTOR = LIVEPORTRAIT_DIR / "motion_extractor.onnx"
    WARPING_SPADE = LIVEPORTRAIT_DIR / "warping_spade.onnx"
    STITCHING_MODEL = LIVEPORTRAIT_DIR / "stitching.onnx"
    STITCHING_EYE = LIVEPORTRAIT_DIR / "stitching_eye.onnx"
    STITCHING_LIP = LIVEPORTRAIT_DIR / "stitching_lip.onnx"

    # InsightFace for face detection
    INSIGHTFACE_DIR = MODELS_DIR / "insightface"

    # Model settings
    MODEL_PRECISION = os.getenv("MODEL_PRECISION", "fp16")  # fp16 or fp32
    LAZY_LOAD = os.getenv("LAZY_LOAD", "false").lower() == "true"
    UNLOAD_IDLE_SECONDS = int(os.getenv("UNLOAD_IDLE_SECONDS", "300"))  # 5 minutes

    # VRAM management (T4 has 16GB)
    MAX_VRAM_GB = float(os.getenv("MAX_VRAM_GB", "14.0"))  # Reserve 2GB for system
    CLEAR_CACHE_AFTER_GENERATION = os.getenv("CLEAR_CACHE_AFTER_GENERATION", "true").lower() == "true"

    # Video settings
    OUTPUT_RESOLUTION = int(os.getenv("OUTPUT_RESOLUTION", "512"))  # LivePortrait uses 512x512
    OUTPUT_FPS = int(os.getenv("OUTPUT_FPS", "25"))
    OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "mp4")
    VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
    AUDIO_CODEC = os.getenv("AUDIO_CODEC", "aac")

    # JoyVASA inference settings
    JOYVASA_CFG_SCALE = float(os.getenv("JOYVASA_CFG_SCALE", "1.0"))
    JOYVASA_NUM_INFERENCE_STEPS = int(os.getenv("JOYVASA_NUM_INFERENCE_STEPS", "25"))
    JOYVASA_WINDOW_SIZE = int(os.getenv("JOYVASA_WINDOW_SIZE", "25"))  # Sliding window frames

    # Job settings
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))  # Lower due to VRAM usage
    JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "900"))  # 15 minutes
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

    @classmethod
    def check_model_files(cls) -> dict:
        """Check if all required model files exist"""
        status = {
            # JoyVASA
            "joyvasa_motion_generator": cls.JOYVASA_MOTION_GENERATOR.exists(),
            "joyvasa_motion_template": cls.JOYVASA_MOTION_TEMPLATE.exists(),
            # HuBERT
            "hubert_model": (cls.HUBERT_DIR / "pytorch_model.bin").exists() or \
                           (cls.HUBERT_DIR / "model.safetensors").exists(),
            # LivePortrait ONNX
            "appearance_extractor": cls.APPEARANCE_EXTRACTOR.exists(),
            "motion_extractor": cls.MOTION_EXTRACTOR.exists(),
            "warping_spade": cls.WARPING_SPADE.exists(),
            "stitching": cls.STITCHING_MODEL.exists(),
        }
        return status


# Initialize directories on module load
Config.init_directories()
