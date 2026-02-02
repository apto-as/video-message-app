"""
Qwen3-TTS Service Configuration
"""

import os
from pathlib import Path
from pydantic import BaseModel
from typing import List


class Qwen3TTSConfig(BaseModel):
    """Qwen3-TTS Service configuration"""

    # Service settings
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False

    # File path settings
    # Docker: QWEN_BASE_DIR=/app, STORAGE_PATH=/app/storage
    # Native: Path(__file__).parent
    base_dir: Path = Path(os.getenv("QWEN_BASE_DIR", str(Path(__file__).parent)))
    storage_dir: Path = Path(os.getenv("STORAGE_PATH", str(Path(__file__).parent / "storage")))
    models_dir: Path = Path(os.getenv("MODELS_PATH", str(Path(__file__).parent / "models")))
    voice_profiles_dir: Path = storage_dir / "voices" / "profiles"
    temp_dir: Path = Path(os.getenv("TEMP_PATH", "/tmp/qwen_tts"))

    # Model settings
    model_name: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    hf_cache_dir: Path = models_dir / "huggingface"
    supported_languages: List[str] = ["ja", "en", "zh", "ko", "de", "fr", "es", "it", "pt", "ru"]
    default_language: str = "ja"

    # PyTorch settings (dynamically set)
    device: str = "cpu"

    # Audio processing settings
    sample_rate: int = 22050  # Qwen3-TTS uses 22050Hz
    max_audio_length: int = 30  # seconds
    min_audio_length: int = 3   # seconds (minimum reference audio length)

    # VRAM management
    lazy_load: bool = True  # Load model only when needed
    unload_after_idle: int = 300  # Seconds of idle before unloading model (0 = never)

    # Synthesis settings
    default_speed: float = 1.0
    default_pitch: float = 0.0
    default_volume: float = 1.0

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.hf_cache_dir.mkdir(parents=True, exist_ok=True)
        # Setup device
        self._setup_device()

    def _setup_device(self):
        """Dynamically configure PyTorch device"""
        # Check environment variable first
        env_device = os.getenv("DEVICE", "").lower()
        if env_device in ["cuda", "cpu", "mps"]:
            self.device = env_device
            return

        try:
            import torch

            if torch.cuda.is_available():
                self.device = "cuda"
                # Set CUDA device explicitly
                torch.cuda.set_device(0)
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                print(f"CUDA available: {gpu_name} ({gpu_memory:.1f}GB)")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"
                print("MPS (Apple Silicon) available")
            else:
                self.device = "cpu"
                print("Using CPU (no GPU available)")
        except ImportError:
            self.device = "cpu"
            print("PyTorch not installed, using CPU")

    def get_profile_dir(self, profile_id: str) -> Path:
        """Get profile directory path"""
        return self.voice_profiles_dir / profile_id

    def get_reference_audio_path(self, profile_id: str) -> Path:
        """Get reference audio path for a profile"""
        return self.get_profile_dir(profile_id) / "reference.wav"

    def get_profile_metadata_path(self, profile_id: str) -> Path:
        """Get profile metadata path"""
        return self.get_profile_dir(profile_id) / "profile.json"


# Global configuration instance
config = Qwen3TTSConfig()
