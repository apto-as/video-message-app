"""
Qwen3-TTS Service Wrapper
Uses the official qwen-tts package for model loading and inference
"""

import asyncio
import base64
import gc
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import numpy as np
import torch
import soundfile as sf

from config import config
from models import (
    VoiceProfile,
    VoiceCloneResponse,
    VoiceSynthesisResponse,
    ProfileStatus,
    ModelStatus,
)

logger = logging.getLogger(__name__)

# Language code mapping: internal code -> Qwen3-TTS language name
LANGUAGE_MAP = {
    "ja": "Japanese",
    "en": "English",
    "zh": "Chinese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}


class Qwen3TTSService:
    """Qwen3-TTS Service using official qwen-tts package"""

    def __init__(self):
        self.model = None
        self._model_lock = asyncio.Lock()
        self._status = ModelStatus()
        self._last_synthesis_time: Optional[float] = None
        self._unload_task: Optional[asyncio.Task] = None
        # Cache for voice clone prompts (profile_id -> prompt_items)
        self._prompt_cache: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the service (does not load model if lazy_load is True)"""
        logger.info(f"Initializing Qwen3-TTS Service on device: {config.device}")

        config.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        config.temp_dir.mkdir(parents=True, exist_ok=True)

        if not config.lazy_load:
            return await self._load_model()

        logger.info("Lazy loading enabled - model will be loaded on first use")
        return True

    async def _load_model(self) -> bool:
        """Load the Qwen3-TTS model using official qwen-tts package"""
        async with self._model_lock:
            if self._status.loaded:
                return True

            if self._status.loading:
                while self._status.loading:
                    await asyncio.sleep(0.1)
                return self._status.loaded

            self._status.loading = True

            try:
                logger.info(f"Loading Qwen3-TTS model: {config.model_name}")
                start_time = time.time()

                os.environ["HF_HOME"] = str(config.hf_cache_dir)
                os.environ["TRANSFORMERS_CACHE"] = str(config.hf_cache_dir)

                from qwen_tts import Qwen3TTSModel

                # Tesla T4 does not support bfloat16, use float16
                dtype = torch.float16 if config.device == "cuda" else torch.float32

                self.model = Qwen3TTSModel.from_pretrained(
                    config.model_name,
                    device_map=f"{config.device}:0" if config.device == "cuda" else config.device,
                    dtype=dtype,
                )

                # Log VRAM usage
                if config.device == "cuda":
                    vram_used = torch.cuda.memory_allocated() / (1024 ** 2)
                    self._status.vram_usage_mb = vram_used
                    logger.info(f"VRAM usage: {vram_used:.1f}MB")

                load_time = time.time() - start_time
                logger.info(f"Model loaded successfully in {load_time:.1f}s")

                self._status.loaded = True
                self._status.loading = False
                self._status.last_used = datetime.now()
                return True

            except Exception as e:
                logger.error(f"Failed to load model: {e}", exc_info=True)
                self._status.loading = False
                self._status.loaded = False
                return False

    async def _ensure_model_loaded(self) -> bool:
        """Ensure model is loaded, loading it if necessary"""
        if not self._status.loaded:
            return await self._load_model()

        self._status.last_used = datetime.now()
        if self._unload_task:
            self._unload_task.cancel()
            self._unload_task = None

        if config.unload_after_idle > 0:
            self._unload_task = asyncio.create_task(self._schedule_unload())

        return True

    async def _schedule_unload(self):
        """Schedule model unload after idle period"""
        try:
            await asyncio.sleep(config.unload_after_idle)
            await self._unload_model()
        except asyncio.CancelledError:
            pass

    async def _unload_model(self):
        """Unload model to free VRAM"""
        async with self._model_lock:
            if not self._status.loaded:
                return

            logger.info("Unloading model to free VRAM...")
            try:
                del self.model
                self.model = None
                self._prompt_cache.clear()

                if config.device == "cuda":
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()

                gc.collect()

                self._status.loaded = False
                self._status.vram_usage_mb = None
                logger.info("Model unloaded successfully")

            except Exception as e:
                logger.error(f"Error unloading model: {e}")

    async def get_health_status(self) -> dict:
        """Get service health status"""
        status = {
            "status": "healthy" if self._status.loaded or config.lazy_load else "degraded",
            "service": "Qwen3-TTS Service",
            "version": "1.0.0",
            "model_loaded": self._status.loaded,
            "pytorch_device": config.device,
            "model_name": config.model_name,
            "model_files_status": {
                "profiles_dir": config.voice_profiles_dir.exists(),
                "temp_dir": config.temp_dir.exists(),
                "hf_cache_dir": config.hf_cache_dir.exists(),
            },
        }

        if self._status.vram_usage_mb:
            status["vram_usage_mb"] = self._status.vram_usage_mb

        if config.device == "cuda" and torch.cuda.is_available():
            status["model_files_status"]["cuda_available"] = True
            status["gpu_name"] = torch.cuda.get_device_name(0)

        return status

    async def create_voice_clone(
        self,
        name: str,
        audio_files: List[bytes],
        language: str = "ja",
        profile_id: Optional[str] = None,
    ) -> VoiceCloneResponse:
        """Create a voice clone profile from audio samples"""
        try:
            if not profile_id:
                profile_id = f"qwen3tts_{uuid.uuid4().hex[:8]}"

            profile_dir = config.get_profile_dir(profile_id)
            profile_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Creating voice clone profile: {profile_id} with {len(audio_files)} samples")

            # Save the best reference audio
            reference_path = config.get_reference_audio_path(profile_id)
            best_audio, best_sr = self._select_best_reference(audio_files)

            if best_audio is None:
                return VoiceCloneResponse(
                    success=False,
                    message="Failed to process audio samples",
                    error="Audio processing failed - ensure samples are at least 3 seconds each"
                )

            sf.write(str(reference_path), best_audio, best_sr)

            # Create profile metadata
            profile = VoiceProfile(
                id=profile_id,
                name=name,
                language=language,
                description=f"Qwen3-TTS voice clone - {len(audio_files)} samples",
                created_at=datetime.now(),
                status=ProfileStatus.READY,
                sample_count=len(audio_files),
                reference_audio_path=str(reference_path),
                engine="qwen3-tts",
            )

            metadata_path = config.get_profile_metadata_path(profile_id)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(profile.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)

            # Invalidate prompt cache for this profile
            self._prompt_cache.pop(profile_id, None)

            logger.info(f"Voice clone profile created: {profile_id}")

            return VoiceCloneResponse(
                success=True,
                voice_profile_id=profile_id,
                message=f"Voice clone profile '{name}' created successfully",
            )

        except Exception as e:
            logger.error(f"Failed to create voice clone: {e}")
            return VoiceCloneResponse(
                success=False,
                message="Failed to create voice clone",
                error=str(e)
            )

    def _select_best_reference(self, audio_files: List[bytes]) -> Tuple[Optional[np.ndarray], int]:
        """Select the best reference audio from the provided samples"""
        import torchaudio

        best_audio = None
        best_sr = config.sample_rate
        best_duration = 0.0

        for i, audio_data in enumerate(audio_files):
            try:
                audio_tensor, sr = torchaudio.load(BytesIO(audio_data))

                # Convert to mono
                if audio_tensor.shape[0] > 1:
                    audio_tensor = audio_tensor.mean(dim=0, keepdim=True)

                audio_np = audio_tensor.squeeze().numpy()
                duration = len(audio_np) / sr

                if duration < config.min_audio_length:
                    logger.warning(f"Audio sample {i} too short ({duration:.1f}s)")
                    continue

                # Keep the longest sample as reference
                if duration > best_duration:
                    best_audio = audio_np
                    best_sr = sr
                    best_duration = duration

                logger.info(f"Processed audio sample {i}: {duration:.1f}s")

            except Exception as e:
                logger.warning(f"Failed to process audio sample {i}: {e}")
                continue

        return best_audio, best_sr

    async def synthesize_voice(
        self,
        text: str,
        voice_profile_id: str,
        language: str = "ja",
        speed: float = 1.0,
        pitch: float = 0.0,
        volume: float = 1.0,
        pause_duration: float = 0.0,
    ) -> VoiceSynthesisResponse:
        """Synthesize speech using Qwen3-TTS voice cloning"""
        try:
            if not await self._ensure_model_loaded():
                return VoiceSynthesisResponse(
                    success=False,
                    message="Model not loaded",
                    error="Failed to load Qwen3-TTS model"
                )

            # Load profile
            profile = await self._load_profile(voice_profile_id)
            if not profile:
                return VoiceSynthesisResponse(
                    success=False,
                    message="Profile not found",
                    error=f"Voice profile '{voice_profile_id}' not found"
                )

            reference_audio_path = Path(profile.reference_audio_path) if profile.reference_audio_path else None
            if not reference_audio_path or not reference_audio_path.exists():
                return VoiceSynthesisResponse(
                    success=False,
                    message="Reference audio not found",
                    error=f"Reference audio for profile '{voice_profile_id}' not found"
                )

            logger.info(f"Synthesizing: '{text[:50]}...' with profile {voice_profile_id}")

            # Perform synthesis
            audio_data, sample_rate, duration = await self._synthesize(
                text=text,
                reference_audio_path=reference_audio_path,
                profile_id=voice_profile_id,
                language=language,
                speed=speed,
            )

            if audio_data is None:
                return VoiceSynthesisResponse(
                    success=False,
                    message="Synthesis failed",
                    error="Failed to generate audio"
                )

            # Apply volume adjustment
            if volume != 1.0:
                audio_data = (audio_data * volume).clip(-1.0, 1.0)

            # Add pause at the end
            if pause_duration > 0:
                silence_samples = int(pause_duration * sample_rate)
                audio_data = np.concatenate([audio_data, np.zeros(silence_samples, dtype=audio_data.dtype)])
                duration += pause_duration

            # Encode to base64 WAV
            audio_base64 = self._encode_audio(audio_data, sample_rate)

            if config.device == "cuda":
                torch.cuda.empty_cache()

            return VoiceSynthesisResponse(
                success=True,
                audio_data=audio_base64,
                duration=duration,
                message="Synthesis completed successfully"
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}", exc_info=True)
            return VoiceSynthesisResponse(
                success=False,
                message="Synthesis failed",
                error=str(e)
            )

    async def _synthesize(
        self,
        text: str,
        reference_audio_path: Path,
        profile_id: str,
        language: str,
        speed: float,
    ) -> Tuple[Optional[np.ndarray], int, float]:
        """Perform TTS synthesis using Qwen3-TTS generate_voice_clone"""
        try:
            qwen_language = LANGUAGE_MAP.get(language, "Japanese")

            # Use cached voice clone prompt if available, otherwise create one
            # x_vector_only_mode=True avoids needing ref_text
            if profile_id not in self._prompt_cache:
                logger.info(f"Creating voice clone prompt for profile {profile_id}")
                prompt_items = self.model.create_voice_clone_prompt(
                    ref_audio=str(reference_audio_path),
                    x_vector_only_mode=True,
                )
                self._prompt_cache[profile_id] = prompt_items
            else:
                prompt_items = self._prompt_cache[profile_id]
                logger.info(f"Using cached voice clone prompt for profile {profile_id}")

            # Generate speech with voice cloning
            with torch.no_grad():
                wavs, sr = self.model.generate_voice_clone(
                    text=text,
                    language=qwen_language,
                    voice_clone_prompt=prompt_items,
                )

            audio_np = wavs[0]  # First (and only) output
            duration = len(audio_np) / sr

            # Apply speed adjustment via resampling
            if speed != 1.0:
                import scipy.signal as signal
                new_length = int(len(audio_np) / speed)
                audio_np = signal.resample(audio_np, new_length).astype(audio_np.dtype)
                duration = len(audio_np) / sr

            logger.info(f"Synthesis complete: {duration:.1f}s at {sr}Hz")
            return audio_np, sr, duration

        except Exception as e:
            logger.error(f"Synthesis error: {e}", exc_info=True)
            return None, 0, 0.0

    def _encode_audio(self, audio: np.ndarray, sample_rate: int) -> str:
        """Encode audio to base64 WAV"""
        buffer = BytesIO()
        sf.write(buffer, audio, sample_rate, format='WAV')
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')

    async def _load_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Load voice profile from storage"""
        try:
            metadata_path = config.get_profile_metadata_path(profile_id)

            if not metadata_path.exists():
                return None

            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return VoiceProfile(**data)

        except Exception as e:
            logger.error(f"Error loading profile {profile_id}: {e}")
            return None

    async def list_profiles(self) -> List[VoiceProfile]:
        """List all voice profiles"""
        profiles = []

        try:
            if not config.voice_profiles_dir.exists():
                return profiles

            for profile_dir in config.voice_profiles_dir.iterdir():
                if profile_dir.is_dir():
                    profile = await self._load_profile(profile_dir.name)
                    if profile and profile.status == ProfileStatus.READY:
                        profiles.append(profile)

        except Exception as e:
            logger.error(f"Error listing profiles: {e}")

        return profiles

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a voice profile"""
        try:
            profile_dir = config.get_profile_dir(profile_id)

            if not profile_dir.exists():
                return False

            shutil.rmtree(profile_dir)
            self._prompt_cache.pop(profile_id, None)
            logger.info(f"Deleted profile: {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {e}")
            return False
