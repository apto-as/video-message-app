"""
EchoMimic Service Client
Audio-driven portrait animation with natural blink and expressions.

Design Notes:
- Similar pattern to MuseTalkClient for consistency
- Async HTTP client with httpx
- Polling-based status checking for long-running tasks
- Environment-based URL configuration
- File upload support for images and audio
- Additional parameters: pose_weight, face_weight, lip_weight, cfg_scale, num_inference_steps
"""

import httpx
import asyncio
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class EchoMimicClient:
    """
    Client for EchoMimic audio-driven portrait animation service.

    Features:
    - Audio and image upload via multipart
    - Video generation with natural blink and expressions
    - Status polling for async operations
    - Health monitoring
    - Model loading/unloading control

    Environment Variables:
    - ECHOMIMIC_SERVICE_URL: Service base URL (default: http://echomimic:8005)
    """

    DEFAULT_TIMEOUT = 30.0  # For quick operations
    UPLOAD_TIMEOUT = 120.0  # For file uploads
    GENERATION_TIMEOUT = 600.0  # 10 minutes for video generation
    HEALTH_CHECK_TIMEOUT = 10.0

    # Polling configuration
    POLL_INTERVAL_SECONDS = 3.0
    MAX_POLL_ATTEMPTS = 120  # 6 minutes with 3s interval

    # Default generation parameters
    DEFAULT_POSE_WEIGHT = 1.0
    DEFAULT_FACE_WEIGHT = 1.0
    DEFAULT_LIP_WEIGHT = 1.0
    DEFAULT_CFG_SCALE = 2.5
    DEFAULT_NUM_INFERENCE_STEPS = 20

    def __init__(self, base_url: str = None):
        """
        Initialize EchoMimic client with automatic URL detection.

        Args:
            base_url: Optional explicit service URL. If not provided,
                     will auto-detect from environment variables.
        """
        if base_url is None:
            # Priority: ECHOMIMIC_SERVICE_URL > environment detection
            base_url = os.environ.get('ECHOMIMIC_SERVICE_URL')
            if not base_url:
                # Check if running in Docker
                if os.environ.get('ENVIRONMENT') == 'docker':
                    base_url = 'http://echomimic:8005'  # Docker network
                else:
                    base_url = 'http://localhost:8005'  # Local development

        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        self._service_available = False

        logger.info(f'EchoMimic Client initialized: {self.base_url}')

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def check_service_health(self) -> bool:
        """
        Check if the EchoMimic service is available.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            response = await self.client.get(
                f'{self.base_url}/health',
                timeout=self.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                health_data = response.json()
                # Accept both 'healthy' and 'degraded' (lazy loading mode)
                status = health_data.get('status')
                self._service_available = status in ('healthy', 'degraded')
                if self._service_available:
                    logger.info(f'EchoMimic Service is available (status: {status})')
                    # Log GPU info if available
                    if 'gpu' in health_data:
                        logger.info(f'EchoMimic GPU: {health_data["gpu"]}')
                    # Log model status if available
                    if 'models_loaded' in health_data:
                        logger.info(f'EchoMimic Models loaded: {health_data["models_loaded"]}')
                return self._service_available
        except httpx.ConnectError as e:
            logger.warning(f'EchoMimic Service connection failed: {e}')
        except httpx.TimeoutException:
            logger.warning('EchoMimic Service health check timed out')
        except Exception as e:
            logger.error(f'EchoMimic Service health check error: {e}')

        self._service_available = False
        return False

    @property
    def is_available(self) -> bool:
        """Check if service was last known to be available."""
        return self._service_available

    async def load_models(self) -> Dict[str, Any]:
        """
        Load EchoMimic models into GPU memory.

        Returns:
            dict: Status of model loading operation

        Raises:
            Exception: If model loading fails
        """
        try:
            logger.info('Loading EchoMimic models...')
            response = await self.client.post(
                f'{self.base_url}/models/load',
                timeout=self.GENERATION_TIMEOUT  # Model loading can take a while
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f'EchoMimic models loaded: {result}')
                return result
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Model loading failed: {response.status_code} - {error_detail}')
                raise Exception(f'Model loading failed: {error_detail}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during model loading: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Model loading failed: {e}', exc_info=True)
            raise

    async def unload_models(self) -> Dict[str, Any]:
        """
        Unload EchoMimic models from GPU memory.

        Returns:
            dict: Status of model unloading operation

        Raises:
            Exception: If model unloading fails
        """
        try:
            logger.info('Unloading EchoMimic models...')
            response = await self.client.post(
                f'{self.base_url}/models/unload',
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f'EchoMimic models unloaded: {result}')
                return result
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Model unloading failed: {response.status_code} - {error_detail}')
                raise Exception(f'Model unloading failed: {error_detail}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during model unloading: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Model unloading failed: {e}', exc_info=True)
            raise

    async def create_video(
        self,
        audio_data: bytes,
        image_data: bytes,
        audio_filename: str = "audio.wav",
        image_filename: str = "source.jpg",
        pose_weight: float = None,
        face_weight: float = None,
        lip_weight: float = None,
        cfg_scale: float = None,
        num_inference_steps: int = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Create an audio-driven portrait animation video.

        Args:
            audio_data: Raw audio bytes to upload
            image_data: Raw image bytes to upload
            audio_filename: Filename for the audio upload (used for content type detection)
            image_filename: Filename for the image upload (used for content type detection)
            pose_weight: Weight for pose control (default: 1.0)
            face_weight: Weight for face control (default: 1.0)
            lip_weight: Weight for lip sync control (default: 1.0)
            cfg_scale: Classifier-free guidance scale (default: 2.5)
            num_inference_steps: Number of diffusion steps (default: 20)
            wait_for_completion: If True, wait for video generation to complete

        Returns:
            dict: {
                'id': str,           # Job ID
                'status': str,       # 'DONE', 'PROCESSING', 'QUEUED', 'ERROR'
                'result_url': str,   # URL of generated video (when done)
                'created_at': str    # ISO timestamp
            }

        Raises:
            Exception: If video generation fails
        """
        try:
            # Use defaults if not specified
            if pose_weight is None:
                pose_weight = self.DEFAULT_POSE_WEIGHT
            if face_weight is None:
                face_weight = self.DEFAULT_FACE_WEIGHT
            if lip_weight is None:
                lip_weight = self.DEFAULT_LIP_WEIGHT
            if cfg_scale is None:
                cfg_scale = self.DEFAULT_CFG_SCALE
            if num_inference_steps is None:
                num_inference_steps = self.DEFAULT_NUM_INFERENCE_STEPS

            logger.info(
                f'Creating EchoMimic video: '
                f'audio={audio_filename} ({len(audio_data)} bytes), '
                f'image={image_filename} ({len(image_data)} bytes), '
                f'pose_weight={pose_weight}, face_weight={face_weight}, '
                f'lip_weight={lip_weight}, cfg_scale={cfg_scale}, '
                f'num_inference_steps={num_inference_steps}'
            )

            # Detect content types from filename extensions
            audio_suffix = Path(audio_filename).suffix.lower()
            audio_content_type_map = {
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.flac': 'audio/flac',
                '.m4a': 'audio/mp4',
            }
            audio_content_type = audio_content_type_map.get(audio_suffix, 'audio/wav')

            image_suffix = Path(image_filename).suffix.lower()
            image_content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
            }
            image_content_type = image_content_type_map.get(image_suffix, 'image/jpeg')

            # Build multipart form data
            files = {
                'audio_data': (audio_filename, audio_data, audio_content_type),
                'source_image': (image_filename, image_data, image_content_type),
            }

            # Build form data for parameters
            data = {
                'pose_weight': str(pose_weight),
                'face_weight': str(face_weight),
                'lip_weight': str(lip_weight),
                'cfg_scale': str(cfg_scale),
                'num_inference_steps': str(num_inference_steps),
            }

            response = await self.client.post(
                f'{self.base_url}/generate-video',
                files=files,
                data=data,
                timeout=self.UPLOAD_TIMEOUT
            )

            if response.status_code != 200:
                error_detail = self._extract_error(response)
                logger.error(f'Video generation request failed: {response.status_code} - {error_detail}')
                raise Exception(f'Video generation failed: {error_detail}')

            result = response.json()
            job_id = result.get('id') or result.get('job_id')
            created_at = result.get('created_at', datetime.utcnow().isoformat())

            if not job_id:
                raise ValueError('Video generation started but no job ID returned')

            logger.info(f'EchoMimic video generation started: job_id={job_id}')

            if wait_for_completion:
                # Poll until completion
                final_result = await self._wait_for_video(job_id)
                final_result['created_at'] = created_at
                return final_result
            else:
                # Return immediately with pending status
                return {
                    'id': job_id,
                    'status': result.get('status', 'QUEUED'),
                    'result_url': None,
                    'created_at': created_at
                }

        except httpx.ConnectError as e:
            logger.error(f'Connection error during video generation: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Video generation failed: {e}', exc_info=True)
            raise

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the current status of a video generation job.

        Args:
            job_id: The video generation job ID

        Returns:
            dict: {
                'id': str,
                'status': str,       # 'DONE', 'PROCESSING', 'QUEUED', 'ERROR'
                'result_url': str,   # Available when status='DONE'
                'error': str         # Available when status='ERROR'
            }
        """
        try:
            response = await self.client.get(
                f'{self.base_url}/job-status/{job_id}',
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {
                    'id': job_id,
                    'status': 'ERROR',
                    'error': 'Job not found'
                }
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Status check failed: {response.status_code} - {error_detail}')
                return {
                    'id': job_id,
                    'status': 'ERROR',
                    'error': f'Status check failed: {error_detail}'
                }

        except httpx.ConnectError as e:
            logger.error(f'Connection error during status check: {e}')
            return {
                'id': job_id,
                'status': 'ERROR',
                'error': f'Service connection failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f'Status check failed: {e}')
            return {
                'id': job_id,
                'status': 'ERROR',
                'error': str(e)
            }

    async def get_result(self, job_id: str) -> bytes:
        """
        Download the generated video for a completed job.

        Args:
            job_id: The video generation job ID

        Returns:
            bytes: Raw video data

        Raises:
            Exception: If download fails or job not found
        """
        try:
            logger.info(f'Downloading EchoMimic result: job_id={job_id}')

            response = await self.client.get(
                f'{self.base_url}/result/{job_id}',
                timeout=self.GENERATION_TIMEOUT
            )

            if response.status_code == 200:
                video_data = response.content
                logger.info(f'Video downloaded: {len(video_data)} bytes')
                return video_data
            elif response.status_code == 404:
                raise FileNotFoundError(f'Video not found for job: {job_id}')
            else:
                error_detail = self._extract_error(response)
                raise Exception(f'Video download failed: {error_detail}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during video download: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Video download failed: {e}', exc_info=True)
            raise

    async def _wait_for_video(
        self,
        job_id: str,
        max_attempts: int = None
    ) -> Dict[str, Any]:
        """
        Poll until video generation is complete.

        Args:
            job_id: The video generation job ID
            max_attempts: Maximum polling attempts (default: MAX_POLL_ATTEMPTS)

        Returns:
            Final status dictionary with result_url

        Raises:
            TimeoutError: If max attempts exceeded
            Exception: If video generation fails
        """
        if max_attempts is None:
            max_attempts = self.MAX_POLL_ATTEMPTS

        logger.info(f'Waiting for EchoMimic video completion: job_id={job_id}')

        for attempt in range(max_attempts):
            status = await self.get_job_status(job_id)

            current_status = status.get('status', 'unknown').upper()

            if current_status == 'DONE':
                result_url = status.get('result_url')
                logger.info(f'EchoMimic video generation complete: {job_id} -> {result_url}')
                return {
                    'id': job_id,
                    'status': 'done',  # Normalize to lowercase for consistency
                    'result_url': result_url
                }

            elif current_status == 'ERROR':
                error_msg = status.get('error', 'Unknown error')
                logger.error(f'EchoMimic video generation failed: {job_id} - {error_msg}')
                raise Exception(f'Video generation failed: {error_msg}')

            # Still processing (QUEUED or PROCESSING), wait and retry
            if (attempt + 1) % 10 == 0:
                logger.info(f'EchoMimic video generation in progress... ({attempt + 1}/{max_attempts})')

            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        # Timeout
        raise TimeoutError(f'Video generation timed out after {max_attempts * self.POLL_INTERVAL_SECONDS}s')

    def _extract_error(self, response: httpx.Response) -> str:
        """Extract error message from HTTP response."""
        try:
            error_json = response.json()
            if 'detail' in error_json:
                return str(error_json['detail'])
            if 'error' in error_json:
                return str(error_json['error'])
            if 'message' in error_json:
                return str(error_json['message'])
            return str(error_json)
        except (ValueError, KeyError):
            return response.text or f'HTTP {response.status_code}'


# Singleton instance for global use
_echomimic_client: Optional[EchoMimicClient] = None


def get_echomimic_client() -> EchoMimicClient:
    """
    Get or create the global EchoMimic client instance.

    Returns:
        EchoMimicClient singleton instance
    """
    global _echomimic_client

    if _echomimic_client is None:
        _echomimic_client = EchoMimicClient()

    return _echomimic_client


async def check_echomimic_available() -> bool:
    """
    Quick check if EchoMimic service is available.

    Returns:
        True if service is healthy
    """
    client = get_echomimic_client()
    return await client.check_service_health()
