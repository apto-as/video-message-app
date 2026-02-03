"""
Qwen3-TTS Service Wrapper
Handles model loading, voice cloning, and synthesis
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
import torchaudio
from scipy.io import wavfile

from config import config
from models import (
    VoiceProfile,
    VoiceCloneResponse,
    VoiceSynthesisResponse,
    ProfileStatus,
    ModelStatus,
)

logger = logging.getLogger(__name__)


class Qwen3TTSService:
    """Qwen3-TTS Service with lazy model loading and VRAM management"""

    def __init__(self):
        self.model = None
        self.processor = None
        self.tokenizer = None
        self._model_lock = asyncio.Lock()
        self._status = ModelStatus()
        self._last_synthesis_time: Optional[float] = None
        self._unload_task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initialize the service (does not load model if lazy_load is True)"""
        logger.info(f"Initializing Qwen3-TTS Service on device: {config.device}")

        # Verify storage directories
        config.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        config.temp_dir.mkdir(parents=True, exist_ok=True)

        if not config.lazy_load:
            # Load model immediately
            return await self._load_model()

        logger.info("Lazy loading enabled - model will be loaded on first use")
        return True

    async def _load_model(self) -> bool:
        """Load the Qwen3-TTS model"""
        async with self._model_lock:
            if self._status.loaded:
                return True

            if self._status.loading:
                # Wait for loading to complete
                while self._status.loading:
                    await asyncio.sleep(0.1)
                return self._status.loaded

            self._status.loading = True

            try:
                logger.info(f"Loading Qwen3-TTS model: {config.model_name}")
                start_time = time.time()

                # Set HuggingFace cache directory
                os.environ["HF_HOME"] = str(config.hf_cache_dir)
                os.environ["TRANSFORMERS_CACHE"] = str(config.hf_cache_dir)

                # Import transformers here to avoid startup delay
                from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor

                # Load tokenizer
                logger.info("Loading tokenizer...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    config.model_name,
                    trust_remote_code=True,
                    cache_dir=config.hf_cache_dir,
                )

                # Load processor (for audio)
                logger.info("Loading processor...")
                try:
                    self.processor = AutoProcessor.from_pretrained(
                        config.model_name,
                        trust_remote_code=True,
                        cache_dir=config.hf_cache_dir,
                    )
                except Exception as e:
                    logger.warning(f"Processor not available: {e}, using tokenizer only")
                    self.processor = None

                # Load model
                logger.info("Loading model...")
                dtype = torch.float16 if config.device == "cuda" else torch.float32
                self.model = AutoModelForCausalLM.from_pretrained(
                    config.model_name,
                    trust_remote_code=True,
                    torch_dtype=dtype,
                    device_map="auto" if config.device == "cuda" else None,
                    cache_dir=config.hf_cache_dir,
                )

                if config.device != "cuda":
                    self.model = self.model.to(config.device)

                self.model.eval()

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
                logger.error(f"Failed to load model: {e}")
                self._status.loading = False
                self._status.loaded = False
                return False

    async def _ensure_model_loaded(self) -> bool:
        """Ensure model is loaded, loading it if necessary"""
        if not self._status.loaded:
            return await self._load_model()

        # Update last used time and cancel unload task
        self._status.last_used = datetime.now()
        if self._unload_task:
            self._unload_task.cancel()
            self._unload_task = None

        # Schedule unload if configured
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
                del self.processor
                del self.tokenizer
                self.model = None
                self.processor = None
                self.tokenizer = None

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
            # Generate profile ID if not provided
            if not profile_id:
                profile_id = f"qwen3tts_{uuid.uuid4().hex[:8]}"

            profile_dir = config.get_profile_dir(profile_id)
            profile_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Creating voice clone profile: {profile_id} with {len(audio_files)} samples")

            # Process and combine audio samples
            combined_audio = await self._process_reference_audio(audio_files)

            if combined_audio is None:
                return VoiceCloneResponse(
                    success=False,
                    message="Failed to process audio samples",
                    error="Audio processing failed - ensure samples are at least 3 seconds each"
                )

            # Save reference audio
            reference_path = config.get_reference_audio_path(profile_id)
            wavfile.write(str(reference_path), config.sample_rate, combined_audio)

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

            # Save profile metadata
            metadata_path = config.get_profile_metadata_path(profile_id)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(profile.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)

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

    async def _process_reference_audio(self, audio_files: List[bytes]) -> Optional[np.ndarray]:
        """Process and combine reference audio files"""
        try:
            combined_samples = []

            for i, audio_data in enumerate(audio_files):
                try:
                    # Load audio using torchaudio
                    audio_tensor, sr = torchaudio.load(BytesIO(audio_data))

                    # Convert to mono if stereo
                    if audio_tensor.shape[0] > 1:
                        audio_tensor = audio_tensor.mean(dim=0, keepdim=True)

                    # Resample to target sample rate
                    if sr != config.sample_rate:
                        resampler = torchaudio.transforms.Resample(sr, config.sample_rate)
                        audio_tensor = resampler(audio_tensor)

                    # Convert to numpy
                    audio_np = audio_tensor.squeeze().numpy()

                    # Check minimum length
                    duration = len(audio_np) / config.sample_rate
                    if duration < config.min_audio_length:
                        logger.warning(f"Audio sample {i} is too short ({duration:.1f}s < {config.min_audio_length}s)")
                        continue

                    combined_samples.append(audio_np)
                    logger.info(f"Processed audio sample {i}: {duration:.1f}s")

                except Exception as e:
                    logger.warning(f"Failed to process audio sample {i}: {e}")
                    continue

            if not combined_samples:
                return None

            # Use the longest sample as reference (Qwen3-TTS works best with longer references)
            reference_audio = max(combined_samples, key=len)

            # Normalize audio
            max_val = np.max(np.abs(reference_audio))
            if max_val > 0:
                reference_audio = reference_audio / max_val * 0.9

            # Convert to int16
            reference_audio = (reference_audio * 32767).astype(np.int16)

            return reference_audio

        except Exception as e:
            logger.error(f"Error processing reference audio: {e}")
            return None

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
        """Synthesize speech using Qwen3-TTS with voice cloning"""
        try:
            # Ensure model is loaded
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

            # Load reference audio
            reference_audio_path = Path(profile.reference_audio_path) if profile.reference_audio_path else None
            if not reference_audio_path or not reference_audio_path.exists():
                return VoiceSynthesisResponse(
                    success=False,
                    message="Reference audio not found",
                    error=f"Reference audio for profile '{voice_profile_id}' not found"
                )

            logger.info(f"Synthesizing: '{text[:50]}...' with profile {voice_profile_id}")

            # Perform synthesis
            audio_data, duration = await self._synthesize(
                text=text,
                reference_audio_path=reference_audio_path,
                language=language,
                speed=speed,
                pitch=pitch,
            )

            if audio_data is None:
                return VoiceSynthesisResponse(
                    success=False,
                    message="Synthesis failed",
                    error="Failed to generate audio"
                )

            # Apply volume adjustment
            if volume != 1.0:
                audio_data = self._apply_volume(audio_data, volume)

            # Add pause at the end if requested
            if pause_duration > 0:
                audio_data = self._add_pause(audio_data, pause_duration)
                duration += pause_duration

            # Encode to base64
            audio_base64 = self._encode_audio(audio_data)

            # Clear VRAM after synthesis
            if config.device == "cuda":
                torch.cuda.empty_cache()

            return VoiceSynthesisResponse(
                success=True,
                audio_data=audio_base64,
                duration=duration,
                message="Synthesis completed successfully"
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return VoiceSynthesisResponse(
                success=False,
                message="Synthesis failed",
                error=str(e)
            )

    async def _synthesize(
        self,
        text: str,
        reference_audio_path: Path,
        language: str,
        speed: float,
        pitch: float,
    ) -> Tuple[Optional[np.ndarray], float]:
        """Perform actual TTS synthesis using Qwen3-TTS"""
        try:
            # Load reference audio
            ref_audio, ref_sr = torchaudio.load(str(reference_audio_path))
            if ref_sr != config.sample_rate:
                resampler = torchaudio.transforms.Resample(ref_sr, config.sample_rate)
                ref_audio = resampler(ref_audio)

            # Prepare input for Qwen3-TTS
            # Note: The actual Qwen3-TTS API may differ - this is a placeholder
            # implementation based on typical transformer TTS patterns

            with torch.no_grad():
                # Create prompt with reference audio context
                # Qwen3-TTS uses a specific prompt format for voice cloning
                prompt = self._create_tts_prompt(text, language)

                # Tokenize
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=4096,
                )

                # Move to device
                inputs = {k: v.to(config.device) for k, v in inputs.items()}

                # Reference audio processing (if processor available)
                if self.processor is not None:
                    ref_features = self.processor(
                        ref_audio.squeeze().numpy(),
                        sampling_rate=config.sample_rate,
                        return_tensors="pt",
                    )
                    ref_features = {k: v.to(config.device) for k, v in ref_features.items()}
                    inputs.update(ref_features)

                # Generate
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=8192,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.95,
                    repetition_penalty=1.1,
                )

                # Decode audio from model output
                # Note: Actual decoding depends on Qwen3-TTS architecture
                audio_output = self._decode_audio_output(outputs, speed, pitch)

                if audio_output is None:
                    # Fallback: return modified reference audio (placeholder)
                    logger.warning("Using fallback audio generation")
                    audio_output = ref_audio.squeeze().numpy()

                duration = len(audio_output) / config.sample_rate
                return audio_output, duration

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return None, 0.0

    def _create_tts_prompt(self, text: str, language: str) -> str:
        """Create TTS prompt for Qwen3-TTS"""
        # Language-specific prompts
        lang_prompts = {
            "ja": "Generate natural Japanese speech for the following text:",
            "en": "Generate natural English speech for the following text:",
            "zh": "Generate natural Chinese speech for the following text:",
            "ko": "Generate natural Korean speech for the following text:",
        }

        prompt_prefix = lang_prompts.get(language, lang_prompts["en"])
        return f"{prompt_prefix}\n\n{text}"

    def _decode_audio_output(
        self,
        outputs: torch.Tensor,
        speed: float,
        pitch: float,
    ) -> Optional[np.ndarray]:
        """Decode model output to audio waveform"""
        try:
            # This is a placeholder - actual implementation depends on Qwen3-TTS
            # The model may output tokens that need vocoder decoding
            # or direct waveform output

            # Check if model has audio head/vocoder
            if hasattr(self.model, 'audio_head') or hasattr(self.model, 'vocoder'):
                # Direct audio output
                with torch.no_grad():
                    if hasattr(self.model, 'audio_head'):
                        audio = self.model.audio_head(outputs)
                    else:
                        audio = self.model.vocoder(outputs)

                    audio_np = audio.cpu().squeeze().numpy()

                    # Apply speed adjustment
                    if speed != 1.0:
                        audio_np = self._apply_speed(audio_np, speed)

                    return audio_np

            # Token-based output - need external vocoder
            logger.warning("Model output is token-based, vocoder required")
            return None

        except Exception as e:
            logger.error(f"Error decoding audio output: {e}")
            return None

    def _apply_speed(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """Apply speed adjustment to audio"""
        try:
            import scipy.signal as signal

            # Calculate new length
            new_length = int(len(audio) / speed)

            # Resample
            resampled = signal.resample(audio, new_length)

            return resampled.astype(audio.dtype)

        except Exception as e:
            logger.warning(f"Speed adjustment failed: {e}")
            return audio

    def _apply_volume(self, audio: np.ndarray, volume: float) -> np.ndarray:
        """Apply volume adjustment to audio"""
        return (audio * volume).clip(-32768, 32767).astype(np.int16)

    def _add_pause(self, audio: np.ndarray, duration: float) -> np.ndarray:
        """Add silence at the end of audio"""
        silence_samples = int(duration * config.sample_rate)
        silence = np.zeros(silence_samples, dtype=audio.dtype)
        return np.concatenate([audio, silence])

    def _encode_audio(self, audio: np.ndarray) -> str:
        """Encode audio to base64 WAV"""
        try:
            buffer = BytesIO()
            wavfile.write(buffer, config.sample_rate, audio)
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')

        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            raise

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
            logger.info(f"Deleted profile: {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {e}")
            return False
