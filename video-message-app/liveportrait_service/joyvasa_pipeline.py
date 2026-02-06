"""
JoyVASA Pipeline - Audio to Motion Generation

This module converts audio input to motion coefficients using:
1. HuBERT for audio feature extraction
2. JoyVASA diffusion transformer for motion generation
"""
import logging
import pickle
from pathlib import Path
from typing import Optional, Tuple, List, Callable

import numpy as np
import torch
import torch.nn.functional as F
import torchaudio

from config import Config

logger = logging.getLogger(__name__)


class JoyVASAPipeline:
    """
    Pipeline for converting audio to motion sequences using JoyVASA

    The pipeline:
    1. Loads audio and extracts features using HuBERT
    2. Uses a diffusion transformer to generate motion sequences
    3. Returns motion coefficients compatible with LivePortrait
    """

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.hubert_model = None
        self.hubert_processor = None
        self.motion_generator = None
        self.motion_template = None
        self.model_loaded = False

        # Model configuration
        self.sample_rate = 16000  # HuBERT expects 16kHz
        self.fps = Config.OUTPUT_FPS
        self.window_size = Config.JOYVASA_WINDOW_SIZE
        self.cfg_scale = Config.JOYVASA_CFG_SCALE
        self.num_inference_steps = Config.JOYVASA_NUM_INFERENCE_STEPS

        logger.info(f"JoyVASA pipeline initialized for device: {device}")

    def load_models(self) -> bool:
        """Load all required models for audio to motion conversion"""
        if self.model_loaded:
            logger.info("JoyVASA models already loaded")
            return True

        try:
            logger.info("Loading JoyVASA models...")

            # Load HuBERT model for audio feature extraction
            self._load_hubert()

            # Load motion generator
            self._load_motion_generator()

            # Load motion template
            self._load_motion_template()

            self.model_loaded = True
            logger.info("JoyVASA models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load JoyVASA models: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_hubert(self):
        """Load HuBERT model for audio feature extraction"""
        from transformers import HubertModel, Wav2Vec2FeatureExtractor

        hubert_path = str(Config.HUBERT_DIR)
        logger.info(f"Loading HuBERT from {hubert_path}")

        self.hubert_processor = Wav2Vec2FeatureExtractor.from_pretrained(hubert_path)
        self.hubert_model = HubertModel.from_pretrained(hubert_path)
        self.hubert_model = self.hubert_model.to(self.device)
        self.hubert_model.eval()
        self.hubert_model.requires_grad_(False)

        logger.info("HuBERT model loaded")

    def _load_motion_generator(self):
        """Load JoyVASA motion generator model"""
        model_path = Config.JOYVASA_MOTION_GENERATOR
        logger.info(f"Loading motion generator from {model_path}")

        if not model_path.exists():
            raise FileNotFoundError(f"Motion generator not found: {model_path}")

        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)

        # Initialize motion generator model
        # JoyVASA uses a DiT (Diffusion Transformer) architecture
        from motion_generator import MotionDiffusionTransformer

        # Model configuration from JoyVASA paper
        self.motion_generator = MotionDiffusionTransformer(
            audio_dim=768,  # HuBERT feature dimension
            motion_dim=66,  # LivePortrait motion coefficients (21 expression + rotation + translation)
            hidden_dim=512,
            num_layers=6,
            num_heads=8,
            dropout=0.1
        ).to(self.device)

        # Load weights
        if 'model' in checkpoint:
            self.motion_generator.load_state_dict(checkpoint['model'])
        else:
            self.motion_generator.load_state_dict(checkpoint)

        self.motion_generator.eval()
        self.motion_generator.requires_grad_(False)

        logger.info("Motion generator loaded")

    def _load_motion_template(self):
        """Load motion template for normalization"""
        template_path = Config.JOYVASA_MOTION_TEMPLATE
        logger.info(f"Loading motion template from {template_path}")

        if not template_path.exists():
            logger.warning(f"Motion template not found: {template_path}, using defaults")
            self.motion_template = {
                'mean': np.zeros(66, dtype=np.float32),
                'std': np.ones(66, dtype=np.float32)
            }
            return

        with open(template_path, 'rb') as f:
            self.motion_template = pickle.load(f)

        logger.info("Motion template loaded")

    def unload_models(self):
        """Unload models to free memory"""
        self.hubert_model = None
        self.hubert_processor = None
        self.motion_generator = None
        self.motion_template = None
        self.model_loaded = False

        if self.device == "cuda":
            torch.cuda.empty_cache()

        logger.info("JoyVASA models unloaded")

    def extract_audio_features(self, audio_path: str) -> torch.Tensor:
        """
        Extract audio features using HuBERT

        Args:
            audio_path: Path to audio file

        Returns:
            Audio features tensor (T, 768) where T is number of frames
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)

        # Resample if needed
        if sr != self.sample_rate:
            resampler = torchaudio.transforms.Resample(sr, self.sample_rate)
            waveform = resampler(waveform)

        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Process with HuBERT processor
        waveform_np = waveform.squeeze().numpy()
        inputs = self.hubert_processor(
            waveform_np,
            sampling_rate=self.sample_rate,
            return_tensors="pt"
        )

        # Extract features
        input_values = inputs.input_values.to(self.device)
        with torch.no_grad():
            outputs = self.hubert_model(input_values)
            hidden_states = outputs.last_hidden_state  # (1, T, 768)

        audio_features = hidden_states.squeeze(0)  # (T, 768)

        # Resample to video fps
        audio_duration = len(waveform_np) / self.sample_rate
        num_video_frames = int(audio_duration * self.fps)

        # Interpolate audio features to match video frames
        audio_features = audio_features.unsqueeze(0).permute(0, 2, 1)  # (1, 768, T)
        audio_features = F.interpolate(
            audio_features,
            size=num_video_frames,
            mode='linear',
            align_corners=True
        )
        audio_features = audio_features.permute(0, 2, 1).squeeze(0)  # (num_frames, 768)

        return audio_features

    def generate_motion(
        self,
        audio_features: torch.Tensor,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> np.ndarray:
        """
        Generate motion sequence from audio features using diffusion

        Args:
            audio_features: Audio features tensor (T, 768)
            progress_callback: Optional callback for progress updates

        Returns:
            Motion sequence (T, 66) containing expression and pose coefficients
        """
        num_frames = audio_features.shape[0]
        logger.info(f"Generating motion for {num_frames} frames")

        # Process in sliding windows for long audio
        all_motions = []
        num_windows = (num_frames + self.window_size - 1) // self.window_size

        for i in range(0, num_frames, self.window_size):
            end_idx = min(i + self.window_size, num_frames)
            window_features = audio_features[i:end_idx]

            if progress_callback:
                progress = (i / num_frames) * 0.5  # Motion generation is first half
                progress_callback(progress, f"Generating motion window {i//self.window_size + 1}/{num_windows}")

            # Pad if needed
            if window_features.shape[0] < self.window_size:
                pad_size = self.window_size - window_features.shape[0]
                window_features = F.pad(window_features, (0, 0, 0, pad_size), mode='replicate')

            # Generate motion using diffusion
            window_motion = self._diffusion_sample(window_features.unsqueeze(0))

            # Remove padding
            actual_frames = end_idx - i
            window_motion = window_motion[:actual_frames]

            all_motions.append(window_motion)

        # Concatenate all windows
        motion_sequence = np.concatenate(all_motions, axis=0)

        # Apply smoothing at window boundaries
        motion_sequence = self._smooth_motion_boundaries(motion_sequence)

        # Denormalize using motion template
        if self.motion_template is not None:
            mean = self.motion_template.get('mean', np.zeros(66))
            std = self.motion_template.get('std', np.ones(66))
            motion_sequence = motion_sequence * std + mean

        return motion_sequence

    def _diffusion_sample(self, audio_features: torch.Tensor) -> np.ndarray:
        """
        Sample motion using diffusion process

        Args:
            audio_features: Audio features (1, T, 768)

        Returns:
            Motion sequence (T, 66)
        """
        batch_size = 1
        seq_len = audio_features.shape[1]
        motion_dim = 66

        # Initialize from noise
        motion = torch.randn(
            batch_size, seq_len, motion_dim,
            device=self.device,
            dtype=audio_features.dtype
        )

        # Diffusion sampling
        timesteps = torch.linspace(1, 0, self.num_inference_steps, device=self.device)

        with torch.no_grad():
            for t in timesteps:
                t_batch = t.expand(batch_size)

                # Predict noise
                noise_pred = self.motion_generator(
                    motion,
                    audio_features,
                    t_batch
                )

                # Classifier-free guidance
                if self.cfg_scale > 1.0:
                    noise_uncond = self.motion_generator(
                        motion,
                        torch.zeros_like(audio_features),
                        t_batch
                    )
                    noise_pred = noise_uncond + self.cfg_scale * (noise_pred - noise_uncond)

                # DDIM step
                alpha = 1 - t
                alpha_prev = 1 - (t - 1/self.num_inference_steps).clamp(min=0)

                sigma = 0.0  # Deterministic sampling
                motion = (motion - (1 - alpha).sqrt() * noise_pred) / alpha.sqrt()
                motion = alpha_prev.sqrt() * motion + (1 - alpha_prev - sigma**2).sqrt() * noise_pred

        return motion.squeeze(0).cpu().numpy()

    def _smooth_motion_boundaries(self, motion: np.ndarray, overlap: int = 5) -> np.ndarray:
        """
        Smooth motion at window boundaries to avoid discontinuities

        Args:
            motion: Motion sequence (T, 66)
            overlap: Number of frames to smooth at boundaries

        Returns:
            Smoothed motion sequence
        """
        from scipy.ndimage import gaussian_filter1d

        # Apply light temporal smoothing
        for i in range(motion.shape[1]):
            motion[:, i] = gaussian_filter1d(motion[:, i], sigma=0.5)

        return motion

    def audio_to_motion(
        self,
        audio_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> np.ndarray:
        """
        Main entry point: Convert audio file to motion sequence

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Motion sequence (T, 66) compatible with LivePortrait
        """
        if not self.model_loaded:
            if not self.load_models():
                raise RuntimeError("Failed to load JoyVASA models")

        if progress_callback:
            progress_callback(0.0, "Extracting audio features")

        # Extract audio features
        audio_features = self.extract_audio_features(audio_path)

        if progress_callback:
            progress_callback(0.1, "Audio features extracted")

        # Generate motion from audio
        motion_sequence = self.generate_motion(audio_features, progress_callback)

        return motion_sequence

    def get_model_status(self) -> dict:
        """Get status of loaded models"""
        return {
            "hubert_loaded": self.hubert_model is not None,
            "motion_generator_loaded": self.motion_generator is not None,
            "motion_template_loaded": self.motion_template is not None,
            "fully_loaded": self.model_loaded
        }
