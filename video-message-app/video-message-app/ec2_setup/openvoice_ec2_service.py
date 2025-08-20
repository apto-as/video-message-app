#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenVoice Service for EC2 with uv environment
Based on working Mac implementation
"""

import os
import sys
import locale
import logging
import json
import pickle
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

# エンコーディング設定（最優先）
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# CUDAを完全に無効化（EC2 CPU環境）
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_HOME'] = ''

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'openvoice_{datetime.now():%Y%m%d}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI imports
from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import aiofiles
import numpy as np
import soundfile as sf
import librosa

# OpenVoiceパスの追加
OPENVOICE_PATH = Path.home() / "video-message-app" / "OpenVoice"
if OPENVOICE_PATH.exists():
    sys.path.insert(0, str(OPENVOICE_PATH))
    logger.info(f"Added OpenVoice path: {OPENVOICE_PATH}")

import torch
# PyTorchをCPUモードに強制
torch.cuda.is_available = lambda: False
torch.cuda.device_count = lambda: 0
device = "cpu"
logger.info(f"Using device: {device}")

# Mac環境と同じWhisperパッチを適用
import platform
def patch_whisper_for_cpu():
    """WhisperモデルをCPU専用にパッチ"""
    try:
        from faster_whisper import WhisperModel as OriginalWhisperModel
        
        class PatchedWhisperModel(OriginalWhisperModel):
            def __init__(self, model_size, device="auto", compute_type="auto", **kwargs):
                # 常にCPUを使用
                if device == "cuda" or device == "auto":
                    logger.info("Forcing WhisperModel to use CPU")
                    device = "cpu"
                    compute_type = "int8"  # CPUでの高速化
                super().__init__(model_size, device=device, compute_type=compute_type, **kwargs)
        
        # モジュールレベルでパッチを適用
        sys.modules['faster_whisper'].WhisperModel = PatchedWhisperModel
        logger.info("Whisper model patched for CPU")
        
    except Exception as e:
        logger.warning(f"Failed to patch Whisper model: {str(e)}")

# パッチ適用
patch_whisper_for_cpu()

# Configuration class (based on Mac config)
class OpenVoiceConfig:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = 8001
        self.debug = True
        
        # パス設定（EC2環境用に調整）
        self.base_dir = Path.home() / "video-message-app" / "video-message-app"
        self.models_dir = self.base_dir / "data" / "openvoice" / "checkpoints_v2"
        self.converter_dir = self.models_dir / "converter"
        self.speakers_dir = self.models_dir / "base_speakers" / "ses"
        self.storage_dir = self.base_dir / "data" / "backend" / "storage"
        self.voice_profiles_dir = self.storage_dir / "openvoice"
        self.temp_dir = self.base_dir / "openvoice_ec2" / "temp"
        
        # モデル設定
        self.supported_languages = ["ja", "en", "zh", "es", "fr", "ko"]
        self.default_language = "ja"
        self.device = device
        
        # 音声処理設定
        self.sample_rate = 24000
        self.max_audio_length = 30  # seconds
        self.min_audio_length = 5   # seconds
        
        # ディレクトリ作成
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        
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

config = OpenVoiceConfig()

# OpenVoice Service Class (based on Mac implementation)
class OpenVoiceService:
    def __init__(self):
        self.config = config
        self._initialized = False
        self._tone_color_converter = None
        self._models = {}
        self.profiles = {}
        self.metadata_file = config.voice_profiles_dir / "metadata.json"
        
    async def initialize(self) -> bool:
        """サービス初期化"""
        try:
            logger.info("OpenVoice Service initialization starting...")
            
            # モデルファイル確認
            if not await self._check_model_files():
                logger.error("Required model files not found")
                return False
            
            # OpenVoiceライブラリのインポート
            if not await self._import_openvoice():
                logger.error("Failed to import OpenVoice libraries")
                return False
            
            # モデル初期化
            if not await self._initialize_models():
                logger.error("Failed to initialize models")
                return False
            
            # メタデータ読み込み
            self._load_metadata()
            
            self._initialized = True
            logger.info("OpenVoice Service initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return False
    
    async def _check_model_files(self) -> bool:
        """必要なモデルファイルの存在確認"""
        required_files = [
            self.config.checkpoint_path,
            self.config.config_path,
            self.config.japanese_speaker_path,
            self.config.english_speaker_path
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing model files: {missing_files}")
            return False
        
        logger.info("All required model files confirmed")
        return True
    
    async def _import_openvoice(self) -> bool:
        """OpenVoiceライブラリのインポート"""
        try:
            global ToneColorConverter, se_extractor, TTS
            from openvoice.api import ToneColorConverter
            from openvoice import se_extractor
            # MeloTTSはオプショナル（なければ基本TTSを使用）
            try:
                from melo.api import TTS
                logger.info("MeloTTS imported successfully")
            except ImportError:
                logger.warning("MeloTTS not available, using fallback")
                TTS = None
            
            logger.info("OpenVoice libraries imported successfully")
            return True
            
        except ImportError as e:
            logger.error(f"OpenVoice import error: {str(e)}")
            return False
    
    async def _initialize_models(self) -> bool:
        """OpenVoiceモデルの初期化"""
        try:
            # ToneColorConverter初期化
            self._tone_color_converter = ToneColorConverter(
                self.config.config_path, 
                device=self.config.device
            )
            self._tone_color_converter.load_ckpt(self.config.checkpoint_path)
            logger.info("ToneColorConverter initialized")
            
            # TTS初期化（利用可能な場合）
            if TTS:
                try:
                    self._models['ja'] = TTS(language='JP', device=self.config.device)
                    self._models['en'] = TTS(language='EN', device=self.config.device)
                    logger.info("TTS models initialized")
                except Exception as e:
                    logger.warning(f"TTS initialization failed: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Model initialization error: {str(e)}")
            return False
    
    def _load_metadata(self):
        """メタデータの読み込み"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.profiles = data.get('profiles', {})
                    logger.info(f"Loaded {len(self.profiles)} profiles from metadata")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self.profiles = {}
        else:
            self.profiles = {}
    
    def _save_metadata(self):
        """メタデータの保存"""
        try:
            data = {
                'profiles': self.profiles,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Metadata saved successfully")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def normalize_audio(self, audio_path: str) -> tuple:
        """音声ファイルの正規化（16kHz, mono, float32）"""
        try:
            # 音声読み込み（24kHzに統一）
            audio, sr = librosa.load(audio_path, sr=24000, mono=True)
            
            # 振幅正規化
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))
            
            # クリッピング防止
            audio = np.clip(audio, -0.99, 0.99)
            
            return audio, 24000
            
        except Exception as e:
            logger.error(f"Failed to normalize audio: {e}")
            raise
    
    async def create_voice_clone(
        self, 
        profile_id: str,
        name: str,
        audio_files: List[UploadFile],
        language: str = "ja",
        description: Optional[str] = None
    ) -> Dict:
        """音声クローンプロファイルの作成"""
        temp_files = []
        try:
            # 音声ファイルを一時保存
            for i, audio_file in audio_files:
                temp_path = self.config.temp_dir / f"{profile_id}_{i}.wav"
                content = await audio_file.read()
                with open(temp_path, 'wb') as f:
                    f.write(content)
                temp_files.append(temp_path)
            
            # 最初のファイルを使用（複数ファイルの場合は後で平均化）
            primary_audio = temp_files[0]
            
            # 音声の正規化
            audio, sr = self.normalize_audio(str(primary_audio))
            
            # 保存先パス
            audio_path = self.config.voice_profiles_dir / f"{profile_id}.wav"
            feature_path = self.config.voice_profiles_dir / f"{profile_id}.npy"
            
            # 正規化された音声を保存
            sf.write(str(audio_path), audio, sr, subtype='PCM_16')
            logger.info(f"Audio saved to {audio_path}")
            
            # 音声特徴の抽出
            if self._tone_color_converter:
                try:
                    # se_extractorを使用した特徴抽出
                    target_se, audio_name = se_extractor.get_se(
                        str(audio_path),
                        self._tone_color_converter,
                        vad=False,  # CPUでは無効化
                        device=self.config.device
                    )
                    
                    # 特徴量を保存
                    np.save(str(feature_path), target_se)
                    logger.info(f"Voice features extracted for {profile_id}")
                    
                except Exception as e:
                    logger.error(f"Feature extraction error: {e}")
                    raise
            
            # メタデータ更新
            self.profiles[profile_id] = {
                'id': profile_id,
                'name': name,
                'language': language,
                'description': description,
                'audio_path': str(audio_path),
                'feature_path': str(feature_path),
                'created_at': datetime.now().isoformat()
            }
            self._save_metadata()
            
            return {
                "profile_id": profile_id,
                "name": name,
                "status": "created",
                "message": "Voice clone profile created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating voice clone: {e}")
            raise
        finally:
            # 一時ファイルのクリーンアップ
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()
    
    async def synthesize_voice(
        self,
        text: str,
        profile_id: str,
        language: str = "ja"
    ) -> bytes:
        """クローン音声での合成"""
        try:
            # UTF-8エンコーディング確認
            text = text.encode('utf-8').decode('utf-8')
            
            # プロファイル確認
            if profile_id not in self.profiles:
                raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
            
            profile = self.profiles[profile_id]
            feature_path = Path(profile['feature_path'])
            
            if not feature_path.exists():
                raise HTTPException(status_code=404, detail="Voice features not found")
            
            # 音声特徴の読み込み
            target_se = np.load(str(feature_path))
            
            # TTSで基本音声を生成
            if language in self._models:
                tts_model = self._models[language]
                temp_tts_path = self.config.temp_dir / f"tts_{uuid.uuid4()}.wav"
                
                # TTSモデルで音声生成
                tts_model.tts_to_file(
                    text,
                    speaker_id=0,
                    output_path=str(temp_tts_path),
                    speed=1.0
                )
                
                # ToneColorConverterで音声変換
                output_path = self.config.temp_dir / f"output_{uuid.uuid4()}.wav"
                
                # 基本話者の特徴を取得
                source_se = self._tone_color_converter.extract_se(
                    str(temp_tts_path),
                    vad=False
                )
                
                # 音声変換実行
                encode_message = "@MyShell"
                self._tone_color_converter.convert(
                    audio_src_path=str(temp_tts_path),
                    src_se=source_se,
                    tgt_se=target_se,
                    output_path=str(output_path),
                    message=encode_message
                )
                
                # 結果を読み込み
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                
                # クリーンアップ
                temp_tts_path.unlink()
                output_path.unlink()
                
                return audio_data
                
            else:
                # TTSモデルがない場合のフォールバック
                # （実際には実装が必要）
                raise HTTPException(status_code=501, detail="TTS model not available")
                
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            raise

# FastAPI app
app = FastAPI(
    title="OpenVoice Service (EC2 uv environment)",
    version="2.0.0",
    description="Complete OpenVoice implementation based on working Mac version"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# サービスインスタンス
service = OpenVoiceService()

@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    logger.info("🚀 OpenVoice Service (EC2 uv) starting...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"Default encoding: {sys.getdefaultencoding()}")
    
    # サービス初期化
    success = await service.initialize()
    if not success:
        logger.error("Service initialization failed")
    else:
        logger.info(f"Service initialized with {len(service.profiles)} profiles")

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy" if service._initialized else "initializing",
        "service": "OpenVoice EC2 uv",
        "device": device,
        "initialized": service._initialized,
        "profiles_count": len(service.profiles),
        "encoding": sys.getdefaultencoding()
    }

@app.post("/api/clone")
async def create_clone(
    name: str = Form(...),
    profile_id: str = Form(...),
    language: str = Form("ja"),
    description: Optional[str] = Form(None),
    audio_file: UploadFile = File(...)
):
    """音声クローンプロファイルの作成"""
    try:
        result = await service.create_voice_clone(
            profile_id=profile_id,
            name=name,
            audio_files=[audio_file],
            language=language,
            description=description
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Clone creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profiles")
async def list_profiles():
    """プロファイル一覧"""
    return list(service.profiles.values())

@app.post("/api/synthesize")
async def synthesize(
    text: str = Form(...),
    profile_id: str = Form(...),
    language: str = Form("ja")
):
    """音声合成"""
    try:
        audio_data = await service.synthesize_voice(text, profile_id, language)
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Type": "audio/wav; charset=utf-8",
                "Content-Disposition": f'attachment; filename="{profile_id}_synthesis.wav"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True
    )