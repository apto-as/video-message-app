"""
OpenVoice Native Service Configuration
"""

import os
from pathlib import Path
from pydantic import BaseModel
from typing import List

class OpenVoiceNativeConfig(BaseModel):
    """OpenVoice Native Service設定"""
    
    # サービス設定
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False  # Production環境ではreloadを無効化
    
    # ファイルパス設定
    base_dir: Path = Path(__file__).parent.parent
    models_dir: Path = base_dir / "data" / "openvoice" / "checkpoints_v2"
    converter_dir: Path = models_dir / "converter"
    speakers_dir: Path = models_dir / "base_speakers" / "ses"
    storage_dir: Path = base_dir / "data" / "backend" / "storage"
    voice_profiles_dir: Path = storage_dir / "voices" / "profiles"
    temp_dir: Path = base_dir / "openvoice_native" / "temp"
    
    # モデル設定
    supported_languages: List[str] = ["ja", "en", "zh", "es", "fr", "ko"]
    default_language: str = "ja"
    
    # PyTorch設定 (動的に設定)
    device: str = "cpu"  # 初期化時に動的設定
    
    # 音声処理設定
    sample_rate: int = 24000
    max_audio_length: int = 30  # seconds
    min_audio_length: int = 5   # seconds
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ディレクトリ作成
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # デバイス設定
        self._setup_device()
    
    def _setup_device(self):
        """PyTorchデバイスを動的に設定"""
        try:
            import torch
            # EC2環境かどうかを確認
            import platform
            is_ec2 = os.path.exists('/home/ec2-user')
            
            if is_ec2 and torch.cuda.is_available():
                # EC2環境では必ずCUDAを使用
                self.device = "cuda"
                torch.cuda.set_device(0)  # 明示的にGPU 0を選択
                print(f"EC2環境: CUDA device {torch.cuda.current_device()} を使用")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        except ImportError:
            self.device = "cpu"
        
    @property
    def checkpoint_path(self) -> str:
        return str(self.converter_dir / "checkpoint.pth")
    
    @property
    def config_path(self) -> str:
        return str(self.converter_dir / "config.json")
    
    @property
    def japanese_speaker_path(self) -> str:
        return str(self.speakers_dir / "jp.pth")
    
    @property
    def english_speaker_path(self) -> str:
        return str(self.speakers_dir / "en-default.pth")

# グローバル設定インスタンス
config = OpenVoiceNativeConfig()