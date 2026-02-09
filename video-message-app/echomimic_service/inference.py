"""
EchoMimic Inference Engine

This module provides the core inference logic for EchoMimic audio-driven
portrait animation. It handles model loading, video generation, and VRAM management.

Reference: https://github.com/BadToBest/EchoMimic
"""
import asyncio
import logging
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Callable

import cv2
import numpy as np
import torch
from PIL import Image
from diffusers import AutoencoderKL, DDIMScheduler
from facenet_pytorch import MTCNN
from moviepy.editor import VideoFileClip, AudioFileClip

from config import Config
from models import AnimationParams, JobData, JobStatus

# EchoMimic imports
from src.models.unet_2d_condition import UNet2DConditionModel
from src.models.unet_3d_echo import EchoUNet3DConditionModel
from src.models.whisper.audio2feature import load_audio_model
from src.models.face_locator import FaceLocator
from src.pipelines.pipeline_echo_mimic import Audio2VideoPipeline
from src.utils.util import save_videos_grid, crop_and_pad

logger = logging.getLogger(__name__)

# Inference configuration (from configs/inference/inference_v2.yaml)
INFER_CONFIG = {
    "unet_additional_kwargs": {
        "use_inflated_groupnorm": True,
        "unet_use_cross_frame_attention": False,
        "unet_use_temporal_attention": False,
        "use_motion_module": True,
        "cross_attention_dim": 384,
        "motion_module_resolutions": [1, 2, 4, 8],
        "motion_module_mid_block": True,
        "motion_module_decoder_only": False,
        "motion_module_type": "Vanilla",
        "motion_module_kwargs": {
            "num_attention_heads": 8,
            "num_transformer_block": 1,
            "attention_block_types": ["Temporal_Self", "Temporal_Self"],
            "temporal_position_encoding": True,
            "temporal_position_encoding_max_len": 32,
            "temporal_attention_dim_div": 1,
        }
    },
    "noise_scheduler_kwargs": {
        "beta_start": 0.00085,
        "beta_end": 0.012,
        "beta_schedule": "linear",
        "clip_sample": False,
        "steps_offset": 1,
        "prediction_type": "v_prediction",
        "rescale_betas_zero_snr": True,
        "timestep_spacing": "trailing",
    }
}


def select_face(det_bboxes, probs):
    """Select the largest face with probability above 0.8"""
    if det_bboxes is None or probs is None:
        return None
    filtered_bboxes = []
    for bbox_i in range(len(det_bboxes)):
        if probs[bbox_i] > 0.8:
            filtered_bboxes.append(det_bboxes[bbox_i])
    if len(filtered_bboxes) == 0:
        return None
    sorted_bboxes = sorted(
        filtered_bboxes,
        key=lambda x: (x[3] - x[1]) * (x[2] - x[0]),
        reverse=True
    )
    return sorted_bboxes[0]


class EchoMimicInference:
    """EchoMimic model wrapper for audio-driven portrait animation"""

    def __init__(self, preloaded_models: Optional[Dict] = None):
        """
        Initialize EchoMimic inference engine.

        Args:
            preloaded_models: Optional dict of pre-loaded model components
                             to avoid CUDA/asyncio segfault issues
        """
        self.device = Config.get_device()
        self.last_used = time.time()
        self._lock = threading.Lock()

        # Determine weight dtype
        if Config.MODEL_PRECISION == "fp16":
            self.weight_dtype = torch.float16
        else:
            self.weight_dtype = torch.float32

        # Model components
        self.vae = None
        self.reference_unet = None
        self.denoising_unet = None
        self.face_locator = None
        self.audio_processor = None
        self.face_detector = None
        self.scheduler = None
        self.pipeline = None
        self.model_loaded = False

        # Use pre-loaded models if provided
        if preloaded_models is not None:
            self._initialize_from_preloaded(preloaded_models)
        else:
            logger.info(f"EchoMimic inference initialized (lazy loading) on device: {self.device}")

    def _initialize_from_preloaded(self, models: Dict):
        """
        Initialize from pre-loaded model components.

        Args:
            models: Dict containing pre-loaded model components
        """
        logger.info("Using pre-loaded models")

        self.vae = models.get('vae')
        self.reference_unet = models.get('reference_unet')
        self.denoising_unet = models.get('denoising_unet')
        self.face_locator = models.get('face_locator')
        self.audio_processor = models.get('audio_processor')
        self.face_detector = models.get('face_detector')
        self.scheduler = models.get('scheduler')
        self.pipeline = models.get('pipeline')

        if self.pipeline is not None:
            self.model_loaded = True
            logger.info("Pre-loaded models ready for inference")
            self._log_vram_usage()

    def load_models(self) -> bool:
        """
        Load all EchoMimic models.

        Returns:
            bool: True if models loaded successfully
        """
        if self.model_loaded:
            logger.info("Models already loaded")
            return True

        with self._lock:
            if self.model_loaded:
                return True

            try:
                logger.info("Loading EchoMimic models...")
                device = self.device
                weight_dtype = self.weight_dtype

                # Check if model files exist
                file_status = Config.check_model_files()
                missing = [k for k, v in file_status.items() if not v]
                if missing:
                    logger.error(f"Missing model files: {missing}")
                    return False

                # 1. Load VAE
                logger.info("Loading VAE...")
                self.vae = AutoencoderKL.from_pretrained(
                    str(Config.SD_VAE_DIR),
                ).to(device, dtype=weight_dtype)

                # 2. Load Reference UNet (2D)
                logger.info("Loading Reference UNet...")
                self.reference_unet = UNet2DConditionModel.from_pretrained(
                    str(Config.IMAGE_ENCODER_DIR),
                    subfolder="unet",
                ).to(dtype=weight_dtype, device=device)
                self.reference_unet.load_state_dict(
                    torch.load(str(Config.REFERENCE_UNET), map_location="cpu"),
                )

                # 3. Load Denoising UNet (3D with Motion Module)
                logger.info("Loading Denoising UNet with Motion Module...")
                motion_module_path = str(Config.MOTION_MODULE)
                if Config.MOTION_MODULE.exists():
                    self.denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
                        str(Config.IMAGE_ENCODER_DIR),
                        motion_module_path,
                        subfolder="unet",
                        unet_additional_kwargs=INFER_CONFIG["unet_additional_kwargs"],
                    ).to(dtype=weight_dtype, device=device)
                else:
                    logger.warning("Motion module not found, using stage1 only")
                    self.denoising_unet = EchoUNet3DConditionModel.from_pretrained_2d(
                        str(Config.IMAGE_ENCODER_DIR),
                        "",
                        subfolder="unet",
                        unet_additional_kwargs={
                            "use_motion_module": False,
                            "unet_use_temporal_attention": False,
                            "cross_attention_dim": INFER_CONFIG["unet_additional_kwargs"]["cross_attention_dim"]
                        }
                    ).to(dtype=weight_dtype, device=device)

                self.denoising_unet.load_state_dict(
                    torch.load(str(Config.DENOISING_UNET), map_location="cpu"),
                    strict=False
                )

                # 4. Load Face Locator
                logger.info("Loading Face Locator...")
                self.face_locator = FaceLocator(
                    320,
                    conditioning_channels=1,
                    block_out_channels=(16, 32, 96, 256)
                ).to(dtype=weight_dtype, device=device)
                self.face_locator.load_state_dict(
                    torch.load(str(Config.FACE_LOCATOR), map_location="cpu")
                )

                # 5. Load Audio Processor (Whisper)
                logger.info("Loading Audio Processor...")
                self.audio_processor = load_audio_model(
                    model_path=str(Config.WHISPER_MODEL),
                    device=device
                )

                # 6. Load Face Detector (MTCNN)
                logger.info("Loading Face Detector...")
                self.face_detector = MTCNN(
                    image_size=320,
                    margin=0,
                    min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7],
                    factor=0.709,
                    post_process=True,
                    device=device
                )

                # 7. Create Scheduler
                logger.info("Creating Scheduler...")
                self.scheduler = DDIMScheduler(**INFER_CONFIG["noise_scheduler_kwargs"])

                # 8. Create Pipeline
                logger.info("Creating Pipeline...")
                self.pipeline = Audio2VideoPipeline(
                    vae=self.vae,
                    reference_unet=self.reference_unet,
                    denoising_unet=self.denoising_unet,
                    audio_guider=self.audio_processor,
                    face_locator=self.face_locator,
                    scheduler=self.scheduler,
                )
                self.pipeline = self.pipeline.to(device, dtype=weight_dtype)

                self.model_loaded = True
                self.last_used = time.time()

                logger.info("EchoMimic models loaded successfully!")
                self._log_vram_usage()
                return True

            except Exception as e:
                logger.error(f"Failed to load EchoMimic models: {e}")
                import traceback
                traceback.print_exc()
                return False

    def unload_models(self):
        """Unload models to free VRAM"""
        if not self.model_loaded:
            return

        with self._lock:
            logger.info("Unloading EchoMimic models...")

            self.vae = None
            self.reference_unet = None
            self.denoising_unet = None
            self.face_locator = None
            self.audio_processor = None
            self.face_detector = None
            self.scheduler = None
            self.pipeline = None

            if self.device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            self.model_loaded = False
            logger.info("Models unloaded, VRAM freed")

    def _log_vram_usage(self):
        """Log current VRAM usage"""
        if self.device == "cuda" and torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info(f"VRAM: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved, {total:.2f}GB total")

    def get_vram_info(self) -> Tuple[Optional[float], Optional[float]]:
        """Get VRAM usage info"""
        if self.device == "cuda" and torch.cuda.is_available():
            used = torch.cuda.memory_allocated() / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            return used, total
        return None, None

    def get_model_status(self) -> Dict[str, bool]:
        """Get status of each model component"""
        return {
            "vae": self.vae is not None,
            "reference_unet": self.reference_unet is not None,
            "denoising_unet": self.denoising_unet is not None,
            "face_locator": self.face_locator is not None,
            "audio_processor": self.audio_processor is not None,
            "face_detector": self.face_detector is not None,
            "scheduler": self.scheduler is not None,
            "pipeline": self.pipeline is not None,
            "fully_loaded": self.model_loaded,
        }

    async def generate_video(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        animation_params: Optional[AnimationParams] = None,
        cfg_scale: float = 2.5,
        num_inference_steps: int = 30,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Generate animated video from image and audio.

        Args:
            image_path: Path to source face image
            audio_path: Path to audio file
            output_path: Path for output video
            animation_params: Animation weight parameters
            cfg_scale: Classifier-free guidance scale
            num_inference_steps: Number of diffusion steps
            progress_callback: Optional callback for progress updates

        Returns:
            Path to generated video
        """
        self.last_used = time.time()

        # Ensure models are loaded
        if not self.load_models():
            raise RuntimeError("Failed to load EchoMimic models")

        # Default animation parameters
        if animation_params is None:
            animation_params = AnimationParams()

        try:
            # Run inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._generate_video_sync,
                image_path,
                audio_path,
                output_path,
                animation_params,
                cfg_scale,
                num_inference_steps,
                progress_callback
            )
            return result
        finally:
            if Config.CLEAR_CACHE_AFTER_GENERATION and self.device == "cuda":
                torch.cuda.empty_cache()

    def _generate_video_sync(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        animation_params: AnimationParams,
        cfg_scale: float,
        num_inference_steps: int,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Synchronous video generation using EchoMimic pipeline.
        """
        temp_dir = Path(tempfile.mkdtemp(dir=Config.TEMP_DIR))
        try:
            logger.info(f"Starting video generation: image={image_path}, audio={audio_path}")
            logger.info(f"Parameters: cfg={cfg_scale}, steps={num_inference_steps}")

            if progress_callback:
                progress_callback(0.05, "Loading source image")

            # Configuration
            width = Config.OUTPUT_WIDTH
            height = Config.OUTPUT_HEIGHT
            fps = Config.OUTPUT_FPS
            context_frames = Config.CONTEXT_FRAMES
            context_overlap = Config.CONTEXT_OVERLAP
            facemusk_dilation_ratio = 0.1
            facecrop_dilation_ratio = 0.5
            seed = 420
            sample_rate = 16000
            max_frames = 1200  # Max frames per generation

            if progress_callback:
                progress_callback(0.1, "Detecting face")

            # Read source image
            face_img = cv2.imread(image_path)
            if face_img is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Detect face
            det_bboxes, probs = self.face_detector.detect(face_img)
            select_bbox = select_face(det_bboxes, probs)

            # Create face mask
            face_mask = np.zeros((face_img.shape[0], face_img.shape[1])).astype('uint8')

            if select_bbox is None:
                logger.warning("No face detected, using full image")
                face_mask[:, :] = 255
                # Resize to output dimensions
                face_img = cv2.resize(face_img, (width, height))
                face_mask = cv2.resize(face_mask, (width, height))
            else:
                xyxy = select_bbox[:4]
                xyxy = np.round(xyxy).astype('int')
                rb, re, cb, ce = xyxy[1], xyxy[3], xyxy[0], xyxy[2]

                # Face mask dilation
                r_pad = int((re - rb) * facemusk_dilation_ratio)
                c_pad = int((ce - cb) * facecrop_dilation_ratio)
                face_mask[rb - r_pad : re + r_pad, cb - c_pad : ce + c_pad] = 255

                # Face crop
                r_pad_crop = int((re - rb) * facecrop_dilation_ratio)
                c_pad_crop = int((ce - cb) * facecrop_dilation_ratio)
                crop_rect = [
                    max(0, cb - c_pad_crop),
                    max(0, rb - r_pad_crop),
                    min(ce + c_pad_crop, face_img.shape[1]),
                    min(re + r_pad_crop, face_img.shape[0])
                ]
                logger.info(f"Face crop rect: {crop_rect}")

                face_img, _ = crop_and_pad(face_img, crop_rect)
                face_mask, _ = crop_and_pad(face_mask, crop_rect)
                face_img = cv2.resize(face_img, (width, height))
                face_mask = cv2.resize(face_mask, (width, height))

            if progress_callback:
                progress_callback(0.2, "Preparing tensors")

            # Convert to PIL and tensor
            ref_image_pil = Image.fromarray(face_img[:, :, [2, 1, 0]])  # BGR to RGB
            face_mask_tensor = torch.Tensor(face_mask).to(
                dtype=self.weight_dtype,
                device=self.device
            ).unsqueeze(0).unsqueeze(0).unsqueeze(0) / 255.0

            # Set random seed
            generator = torch.manual_seed(seed)

            if progress_callback:
                progress_callback(0.3, "Running diffusion pipeline")

            # Run pipeline
            logger.info("Starting diffusion pipeline...")
            video = self.pipeline(
                ref_image_pil,
                audio_path,
                face_mask_tensor,
                width,
                height,
                max_frames,
                num_inference_steps,
                cfg_scale,
                generator=generator,
                audio_sample_rate=sample_rate,
                context_frames=context_frames,
                fps=fps,
                context_overlap=context_overlap
            ).videos

            if progress_callback:
                progress_callback(0.8, "Saving video")

            # Save video (without audio first)
            temp_video_path = str(temp_dir / "temp_video.mp4")
            save_videos_grid(
                video,
                temp_video_path,
                n_rows=1,
                fps=fps,
            )

            if progress_callback:
                progress_callback(0.9, "Adding audio")

            # Merge with audio
            video_clip = VideoFileClip(temp_video_path)
            audio_clip = AudioFileClip(audio_path)
            video_clip = video_clip.set_audio(audio_clip)
            video_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )
            video_clip.close()
            audio_clip.close()

            if progress_callback:
                progress_callback(1.0, "Complete")

            logger.info(f"Video generated: {output_path}")
            return output_path

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)


class JobQueue:
    """Thread-safe job queue manager"""

    def __init__(self, max_concurrent: int = Config.MAX_CONCURRENT_JOBS):
        self.jobs: Dict[str, JobData] = {}
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=Config.MAX_QUEUE_SIZE)
        self.max_concurrent = max_concurrent
        self.active_count = 0
        self._lock = asyncio.Lock()
        self._workers_started = False

    async def add_job(self, job: JobData) -> bool:
        """Add job to queue"""
        async with self._lock:
            if len(self.jobs) >= Config.MAX_QUEUE_SIZE:
                return False

            self.jobs[job.id] = job
            await self.queue.put(job.id)
            return True

    def get_job(self, job_id: str) -> Optional[JobData]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def remove_job(self, job_id: str):
        """Remove job from storage"""
        self.jobs.pop(job_id, None)

    def get_stats(self) -> Tuple[int, int]:
        """Get queue stats (queued, processing)"""
        queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
        processing = sum(1 for j in self.jobs.values() if j.status == JobStatus.PROCESSING)
        return queued, processing

    async def start_workers(self, inference: EchoMimicInference):
        """Start background workers"""
        if self._workers_started:
            return

        self._workers_started = True
        for i in range(self.max_concurrent):
            asyncio.create_task(self._worker(inference, worker_id=i))
        logger.info(f"Started {self.max_concurrent} job workers")

    async def _worker(self, inference: EchoMimicInference, worker_id: int):
        """Background worker for processing jobs"""
        logger.info(f"Worker {worker_id} started")

        while True:
            try:
                job_id = await self.queue.get()
                job = self.jobs.get(job_id)

                if not job:
                    continue

                job.start_processing()
                logger.info(f"Worker {worker_id} processing job {job_id}")

                try:
                    # Progress callback
                    def update_progress(progress: float, message: str):
                        job.update_stage(message, progress)
                        logger.debug(f"Job {job_id}: {progress:.0%} - {message}")

                    # Generate video
                    output_path = str(Config.VIDEOS_DIR / f"{job_id}.mp4")
                    await inference.generate_video(
                        job.image_path,
                        job.audio_path,
                        output_path,
                        animation_params=job.animation_params,
                        cfg_scale=job.cfg_scale,
                        num_inference_steps=job.num_inference_steps,
                        progress_callback=update_progress
                    )

                    # Mark complete
                    result_url = f"/storage/videos/{job_id}.mp4"
                    job.complete(result_url)
                    logger.info(f"Job {job_id} completed: {result_url}")

                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    job.fail(str(e))

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)


# Global instances - initialized by main.py
inference_engine: Optional[EchoMimicInference] = None
job_queue: Optional[JobQueue] = None


def init_globals(preloaded_models: Optional[Dict] = None) -> Tuple[EchoMimicInference, JobQueue]:
    """
    Initialize global instances with optional pre-loaded models.

    IMPORTANT: For CUDA environments, preloaded_models SHOULD be provided
    to avoid segfault caused by CUDA/asyncio interaction.

    Args:
        preloaded_models: Optional dict of pre-loaded model components

    Returns:
        Tuple of (inference_engine, job_queue)
    """
    global inference_engine, job_queue
    inference_engine = EchoMimicInference(preloaded_models=preloaded_models)
    job_queue = JobQueue()
    return inference_engine, job_queue
