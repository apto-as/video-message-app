"""
MuseTalk Lip-Sync Service - Core inference logic
"""
import asyncio
import logging
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import torch

from config import Config
from models import JobData, JobStatus

logger = logging.getLogger(__name__)


class MuseTalkInference:
    """MuseTalk model wrapper for lip-sync video generation"""

    def __init__(self, preloaded_models=None, preloaded_audio_processor=None):
        self.device = Config.get_device()
        self.last_used = time.time()
        self._lock = threading.Lock()

        # Model components
        self.audio_processor = None
        self.vae = None
        self.unet = None
        self.pe = None
        self.timesteps = None
        self.musetalk_loaded = False
        self.model_loaded = False

        # If pre-loaded models are available, use them immediately
        # This avoids CUDA/asyncio segfault by not importing modules later
        if preloaded_models is not None and preloaded_audio_processor is not None:
            logger.info("Using pre-loaded models - skipping lazy loading")
            self.vae, self.unet, self.pe = preloaded_models
            self.audio_processor = preloaded_audio_processor

            # Move models to device
            if self.device == "cuda":
                self.vae.vae = self.vae.vae.half().to(self.device)
                self.unet.model = self.unet.model.half().to(self.device)
                self.pe = self.pe.half().to(self.device)
            else:
                self.vae.vae = self.vae.vae.to(self.device)
                self.unet.model = self.unet.model.to(self.device)
                self.pe = self.pe.to(self.device)

            # Set timesteps
            self.timesteps = torch.tensor([0], device=self.device)

            self.model_loaded = True
            self.musetalk_loaded = True
            logger.info("Pre-loaded models ready for inference")
            self._log_vram_usage()

        logger.info(f"MuseTalk inference initialized with device: {self.device}")

    def _add_musetalk_to_path(self):
        """Add MuseTalk directory to Python path"""
        musetalk_path = str(Config.MUSETALK_DIR)
        if musetalk_path not in sys.path:
            sys.path.insert(0, musetalk_path)
            logger.info(f"Added MuseTalk to path: {musetalk_path}")

    def load_models(self) -> bool:
        """Load all MuseTalk models"""
        # If already loaded (either pre-loaded or dynamically), return success
        if self.model_loaded:
            logger.info("Models already loaded")
            return True

        with self._lock:
            if self.model_loaded:
                return True

            # WARNING: Dynamic loading can cause CUDA/asyncio segfault
            # Models should be pre-loaded before uvicorn starts
            logger.warning("Dynamic model loading - this may cause segfault under uvicorn!")

            try:
                logger.info("Loading MuseTalk models dynamically...")
                self._add_musetalk_to_path()

                # Import MuseTalk modules
                from musetalk.utils.utils import load_all_model
                from musetalk.utils.preprocessing import get_landmark_and_bbox
                from musetalk.utils.audio_processor import AudioProcessor

                # Load models - load_all_model returns (vae, unet, pe)
                self.vae, self.unet, self.pe = load_all_model(device=self.device)

                # Load audio processor
                whisper_model_dir = str(Config.MODELS_DIR / "whisper")
                self.audio_processor = AudioProcessor(feature_extractor_path=whisper_model_dir)
                logger.info(f"Audio processor loaded from {whisper_model_dir}")

                # Move models to device (MuseTalk wraps models in container classes)
                if self.device == "cuda":
                    self.vae.vae = self.vae.vae.half().to(self.device)
                    self.unet.model = self.unet.model.half().to(self.device)
                    self.pe = self.pe.half().to(self.device)
                else:
                    self.vae.vae = self.vae.vae.to(self.device)
                    self.unet.model = self.unet.model.to(self.device)
                    self.pe = self.pe.to(self.device)

                # Set timesteps
                self.timesteps = torch.tensor([0], device=self.device)

                self.model_loaded = True
                self.musetalk_loaded = True
                self.last_used = time.time()

                logger.info("MuseTalk models loaded successfully")
                self._log_vram_usage()
                return True

            except Exception as e:
                logger.error(f"Failed to load MuseTalk models: {e}")
                import traceback
                traceback.print_exc()
                return False

    def unload_models(self):
        """Unload models to free VRAM"""
        if not self.model_loaded:
            return

        with self._lock:
            logger.info("Unloading MuseTalk models...")

            self.audio_processor = None
            self.vae = None
            self.unet = None
            self.pe = None

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

    async def generate_video(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        progress_callback=None
    ) -> str:
        """
        Generate lip-sync video from image and audio

        Args:
            image_path: Path to source face image
            audio_path: Path to audio file
            output_path: Path for output video
            progress_callback: Optional callback for progress updates

        Returns:
            Path to generated video
        """
        self.last_used = time.time()

        # Ensure models are loaded
        if not self.load_models():
            raise RuntimeError("Failed to load MuseTalk models")

        try:
            # Run inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._generate_video_sync,
                image_path,
                audio_path,
                output_path,
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
        progress_callback=None
    ) -> str:
        """Synchronous video generation"""
        self._add_musetalk_to_path()

        from musetalk.utils.utils import get_file_type, datagen
        from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs, coord_placeholder
        from musetalk.utils.blending import get_image_prepare_material, get_image_blending

        temp_dir = Path(tempfile.mkdtemp(dir=Config.TEMP_DIR))
        try:
            logger.info(f"Starting video generation: image={image_path}, audio={audio_path}")

            if progress_callback:
                progress_callback(0.1, "Preprocessing image")

            # Read and preprocess source image
            source_image = cv2.imread(image_path)
            if source_image is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Resize to target resolution
            source_image = cv2.resize(source_image, (Config.OUTPUT_RESOLUTION, Config.OUTPUT_RESOLUTION))

            # Get face landmarks and bounding box
            coord_list, frame_list = get_landmark_and_bbox([source_image], self.device)

            if not coord_list or coord_list[0] is None:
                raise ValueError("No face detected in source image")

            if progress_callback:
                progress_callback(0.2, "Processing audio")

            # Process audio
            whisper_feature = self.audio_processor.audio2feat(audio_path)
            whisper_chunks = self.audio_processor.feature2chunks(
                feature_array=whisper_feature,
                fps=Config.OUTPUT_FPS
            )

            if progress_callback:
                progress_callback(0.3, "Generating frames")

            # Prepare for blending
            input_latent_list = []
            coord = coord_list[0]
            frame = frame_list[0]

            # Get crop coordinates
            y1, y2, x1, x2 = coord
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)

            # Prepare latent for each chunk
            latent = self._get_latent(crop_frame)
            input_latent_list = [latent] * len(whisper_chunks)

            # Get masked frame for blending
            input_img_list = [crop_frame] * len(whisper_chunks)

            if progress_callback:
                progress_callback(0.4, "Running inference")

            # Generate lip-sync frames
            output_frames = []
            batch_size = 8  # Smaller batch for VRAM efficiency

            for i in range(0, len(whisper_chunks), batch_size):
                if progress_callback:
                    prog = 0.4 + (0.4 * i / len(whisper_chunks))
                    progress_callback(prog, f"Generating frames {i}/{len(whisper_chunks)}")

                batch_whisper = whisper_chunks[i:i + batch_size]
                batch_latent = input_latent_list[i:i + batch_size]

                # Prepare audio features
                audio_feat_tensor = torch.stack(
                    [torch.from_numpy(feat) for feat in batch_whisper],
                    dim=0
                ).to(self.device)

                if self.device == "cuda":
                    audio_feat_tensor = audio_feat_tensor.half()

                # Stack latents
                latent_tensor = torch.cat(batch_latent, dim=0)

                # Get position encoding
                with torch.no_grad():
                    audio_feat_pe = self.pe(audio_feat_tensor)

                    # UNet forward
                    pred_latent = self.unet(
                        latent_tensor,
                        self.timesteps.expand(len(batch_latent)),
                        encoder_hidden_states=audio_feat_pe
                    ).sample

                    # Decode
                    pred_frames = self.vae.decode(pred_latent / 0.18215).sample
                    pred_frames = (pred_frames / 2 + 0.5).clamp(0, 1)

                # Convert to numpy frames
                for j, pred_frame in enumerate(pred_frames):
                    frame_np = pred_frame.permute(1, 2, 0).cpu().numpy()
                    frame_np = (frame_np * 255).astype(np.uint8)
                    frame_np = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)

                    # Blend with original
                    blended = self._blend_frame(frame, frame_np, coord)
                    output_frames.append(blended)

            if progress_callback:
                progress_callback(0.85, "Encoding video")

            # Write video with audio
            self._write_video(output_frames, audio_path, output_path)

            if progress_callback:
                progress_callback(1.0, "Complete")

            logger.info(f"Video generated: {output_path}")
            return output_path

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _get_latent(self, image: np.ndarray) -> torch.Tensor:
        """Encode image to latent space"""
        # Normalize to [-1, 1]
        image_tensor = torch.from_numpy(image).float() / 255.0
        image_tensor = (image_tensor * 2 - 1).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.to(self.device)

        if self.device == "cuda":
            image_tensor = image_tensor.half()

        with torch.no_grad():
            latent = self.vae.encode(image_tensor).latent_dist.sample()
            latent = latent * 0.18215

        return latent

    def _blend_frame(
        self,
        original: np.ndarray,
        generated: np.ndarray,
        coord: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """Blend generated face into original frame"""
        y1, y2, x1, x2 = coord
        result = original.copy()

        # Resize generated to match crop size
        generated_resized = cv2.resize(
            generated,
            (x2 - x1, y2 - y1),
            interpolation=cv2.INTER_LANCZOS4
        )

        # Simple paste (can be improved with feathering)
        result[y1:y2, x1:x2] = generated_resized

        return result

    def _write_video(
        self,
        frames: list,
        audio_path: str,
        output_path: str
    ):
        """Write frames and audio to video file"""
        if not frames:
            raise ValueError("No frames to write")

        # Write frames to temp video
        height, width = frames[0].shape[:2]
        temp_video = Path(output_path).with_suffix('.temp.mp4')

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            str(temp_video),
            fourcc,
            Config.OUTPUT_FPS,
            (width, height)
        )

        for frame in frames:
            writer.write(frame)
        writer.release()

        # Merge with audio using ffmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', str(temp_video),
            '-i', audio_path,
            '-c:v', Config.VIDEO_CODEC,
            '-c:a', Config.AUDIO_CODEC,
            '-shortest',
            '-preset', 'fast',
            '-crf', '23',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            temp_video.unlink(missing_ok=True)


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

    async def start_workers(self, inference: MuseTalkInference):
        """Start background workers"""
        if self._workers_started:
            return

        self._workers_started = True
        for i in range(self.max_concurrent):
            asyncio.create_task(self._worker(inference, worker_id=i))
        logger.info(f"Started {self.max_concurrent} job workers")

    async def _worker(self, inference: MuseTalkInference, worker_id: int):
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
                        job.progress = progress
                        logger.debug(f"Job {job_id}: {progress:.0%} - {message}")

                    # Generate video
                    output_path = str(Config.VIDEOS_DIR / f"{job_id}.mp4")
                    await inference.generate_video(
                        job.image_path,
                        job.audio_path,
                        output_path,
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


# Global instances - initialized by main.py with pre-loaded models
inference_engine = None
job_queue = None

def init_globals(preloaded_models=None, preloaded_audio_processor=None):
    """Initialize global instances with optional pre-loaded models

    IMPORTANT: For CUDA environments, preloaded_models and preloaded_audio_processor
    MUST be provided to avoid segfault caused by CUDA/asyncio interaction.
    """
    global inference_engine, job_queue
    inference_engine = MuseTalkInference(
        preloaded_models=preloaded_models,
        preloaded_audio_processor=preloaded_audio_processor
    )
    job_queue = JobQueue()
    return inference_engine, job_queue
