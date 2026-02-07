"""
Configuration for EchoMimic Service
Audio-driven portrait animation using EchoMimic
"""
import os
from pathlib import Path


class Config:
    """Service configuration"""

    # Service settings
    SERVICE_NAME = "EchoMimic Service"
    VERSION = "1.0.0"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8005"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Paths
    BASE_DIR = Path("/app")
    STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
    MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
    ECHOMIMIC_DIR = Path(os.getenv("ECHOMIMIC_DIR", "/app/EchoMimic"))

    # Storage subdirectories
    VIDEOS_DIR = STORAGE_DIR / "videos"
    UPLOADS_DIR = STORAGE_DIR / "uploads"
    TEMP_DIR = STORAGE_DIR / "temp"

    # EchoMimic Model Paths
    # Pretrained models from HuggingFace: BadToBest/EchoMimic
    ECHOMIMIC_PRETRAINED_DIR = MODELS_DIR / "EchoMimic"
    DENOISING_UNET = ECHOMIMIC_PRETRAINED_DIR / "denoising_unet.pth"
    REFERENCE_UNET = ECHOMIMIC_PRETRAINED_DIR / "reference_unet.pth"
    FACE_LOCATOR = ECHOMIMIC_PRETRAINED_DIR / "face_locator.pth"
    MOTION_MODULE = ECHOMIMIC_PRETRAINED_DIR / "motion_module.pth"
    # Audio processor uses Whisper instead of audio_projection
    AUDIO_PROCESSOR_DIR = ECHOMIMIC_PRETRAINED_DIR / "audio_processor"
    WHISPER_MODEL = AUDIO_PROCESSOR_DIR / "whisper_tiny.pt"

    # Base model paths (Stable Diffusion + Audio encoder)
    SD_VAE_DIR = MODELS_DIR / "sd-vae-ft-mse"
    AUDIO_ENCODER_DIR = MODELS_DIR / "wav2vec2-base-960h"
    IMAGE_ENCODER_DIR = MODELS_DIR / "sd-image-variations-diffusers"

    # Model settings
    MODEL_PRECISION = os.getenv("MODEL_PRECISION", "fp16")  # fp16 or fp32
    LAZY_LOAD = os.getenv("LAZY_LOAD", "true").lower() == "true"
    UNLOAD_IDLE_SECONDS = int(os.getenv("UNLOAD_IDLE_SECONDS", "300"))  # 5 minutes

    # VRAM management (T4 has 16GB)
    MAX_VRAM_GB = float(os.getenv("MAX_VRAM_GB", "14.0"))  # Reserve 2GB for system
    CLEAR_CACHE_AFTER_GENERATION = os.getenv("CLEAR_CACHE_AFTER_GENERATION", "true").lower() == "true"

    # Video settings
    OUTPUT_WIDTH = int(os.getenv("OUTPUT_WIDTH", "512"))
    OUTPUT_HEIGHT = int(os.getenv("OUTPUT_HEIGHT", "512"))
    OUTPUT_FPS = int(os.getenv("OUTPUT_FPS", "25"))
    OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "mp4")
    VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
    AUDIO_CODEC = os.getenv("AUDIO_CODEC", "aac")

    # EchoMimic inference settings
    CFG_SCALE = float(os.getenv("CFG_SCALE", "2.5"))
    NUM_INFERENCE_STEPS = int(os.getenv("NUM_INFERENCE_STEPS", "30"))
    CONTEXT_FRAMES = int(os.getenv("CONTEXT_FRAMES", "12"))
    CONTEXT_OVERLAP = int(os.getenv("CONTEXT_OVERLAP", "3"))

    # Animation parameters defaults
    DEFAULT_POSE_WEIGHT = float(os.getenv("DEFAULT_POSE_WEIGHT", "1.0"))
    DEFAULT_FACE_WEIGHT = float(os.getenv("DEFAULT_FACE_WEIGHT", "1.0"))
    DEFAULT_LIP_WEIGHT = float(os.getenv("DEFAULT_LIP_WEIGHT", "1.0"))

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
            # EchoMimic pretrained
            "denoising_unet": cls.DENOISING_UNET.exists(),
            "reference_unet": cls.REFERENCE_UNET.exists(),
            "face_locator": cls.FACE_LOCATOR.exists(),
            "motion_module": cls.MOTION_MODULE.exists(),
            "whisper_model": cls.WHISPER_MODEL.exists(),
            # Base models
            "sd_vae": (cls.SD_VAE_DIR / "diffusion_pytorch_model.safetensors").exists() or \
                      (cls.SD_VAE_DIR / "diffusion_pytorch_model.bin").exists(),
            "audio_encoder": (cls.AUDIO_ENCODER_DIR / "pytorch_model.bin").exists() or \
                            (cls.AUDIO_ENCODER_DIR / "model.safetensors").exists(),
            "image_encoder": cls.IMAGE_ENCODER_DIR.exists(),
        }
        return status


# Initialize directories on module load
Config.init_directories()
