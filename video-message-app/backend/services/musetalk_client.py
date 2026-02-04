"""
MuseTalk Service Client
Replaces D-ID API for lip-sync video generation with local inference.

Design Notes:
- Drop-in replacement for D-ID Client
- Async HTTP client with httpx
- Polling-based status checking for long-running tasks
- Environment-based URL configuration
- File upload support for images and audio
"""

import httpx
import asyncio
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MuseTalkClient:
    """
    Client for MuseTalk lip-sync video generation service.

    Features:
    - Image and audio upload
    - Video generation with lip-sync
    - Status polling for async operations
    - Health monitoring

    Environment Variables:
    - MUSETALK_SERVICE_URL: Service base URL (default: http://musetalk:8003)
    - USE_LOCAL_LIPSYNC: Enable/disable local lip-sync (default: true)
    """

    DEFAULT_TIMEOUT = 30.0  # For quick operations
    UPLOAD_TIMEOUT = 120.0  # For file uploads
    GENERATION_TIMEOUT = 600.0  # 10 minutes for video generation
    HEALTH_CHECK_TIMEOUT = 10.0

    # Polling configuration
    POLL_INTERVAL_SECONDS = 3.0
    MAX_POLL_ATTEMPTS = 120  # 6 minutes with 3s interval

    def __init__(self, base_url: str = None):
        """
        Initialize MuseTalk client with automatic URL detection.

        Args:
            base_url: Optional explicit service URL. If not provided,
                     will auto-detect from environment variables.
        """
        if base_url is None:
            # Priority: MUSETALK_SERVICE_URL > environment detection
            base_url = os.environ.get('MUSETALK_SERVICE_URL')
            if not base_url:
                # Check if running in Docker
                if os.environ.get('ENVIRONMENT') == 'docker':
                    base_url = 'http://musetalk:8003'  # Docker network
                else:
                    base_url = 'http://localhost:8003'  # Local development

        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        self._service_available = False

        logger.info(f'MuseTalk Client initialized: {self.base_url}')

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def check_service_health(self) -> bool:
        """
        Check if the MuseTalk service is available.

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
                self._service_available = health_data.get('status') == 'healthy'
                if self._service_available:
                    logger.info('MuseTalk Service is available')
                    # Log GPU info if available
                    if 'gpu' in health_data:
                        logger.info(f'MuseTalk GPU: {health_data["gpu"]}')
                return self._service_available
        except httpx.ConnectError as e:
            logger.warning(f'MuseTalk Service connection failed: {e}')
        except httpx.TimeoutException:
            logger.warning('MuseTalk Service health check timed out')
        except Exception as e:
            logger.error(f'MuseTalk Service health check error: {e}')

        self._service_available = False
        return False

    @property
    def is_available(self) -> bool:
        """Check if service was last known to be available."""
        return self._service_available

    async def upload_image(self, image_data: bytes, filename: str = None) -> str:
        """
        Upload source image to MuseTalk service.

        Args:
            image_data: Image binary data (JPEG, PNG)
            filename: Optional filename

        Returns:
            URL of uploaded image on the service

        Raises:
            Exception: If upload fails
        """
        try:
            if filename is None:
                filename = f"source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

            # Determine content type
            content_type = 'image/jpeg'
            if filename.lower().endswith('.png'):
                content_type = 'image/png'

            files = {
                'file': (filename, image_data, content_type)
            }

            logger.info(f'Uploading source image: {filename} ({len(image_data)} bytes)')

            response = await self.client.post(
                f'{self.base_url}/upload-source-image',
                files=files,
                timeout=self.UPLOAD_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                image_url = result.get('url')
                logger.info(f'Image uploaded successfully: {image_url}')
                return image_url
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Image upload failed: {response.status_code} - {error_detail}')
                raise Exception(f'Image upload failed: {error_detail}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during image upload: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Image upload failed: {e}', exc_info=True)
            raise

    async def upload_audio(self, audio_data: bytes, filename: str = None) -> str:
        """
        Upload audio file to MuseTalk service.

        Args:
            audio_data: Audio binary data (WAV, MP3, etc.)
            filename: Optional filename

        Returns:
            URL of uploaded audio on the service

        Raises:
            Exception: If upload fails
        """
        try:
            if filename is None:
                filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

            # Determine content type
            content_type = 'audio/wav'
            suffix = Path(filename).suffix.lower()
            content_type_map = {
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.flac': 'audio/flac',
                '.m4a': 'audio/mp4'
            }
            content_type = content_type_map.get(suffix, 'audio/wav')

            files = {
                'file': (filename, audio_data, content_type)
            }

            logger.info(f'Uploading audio: {filename} ({len(audio_data)} bytes)')

            response = await self.client.post(
                f'{self.base_url}/upload-audio',
                files=files,
                timeout=self.UPLOAD_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                audio_url = result.get('url')
                logger.info(f'Audio uploaded successfully: {audio_url}')
                return audio_url
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Audio upload failed: {response.status_code} - {error_detail}')
                raise Exception(f'Audio upload failed: {error_detail}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during audio upload: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Audio upload failed: {e}', exc_info=True)
            raise

    async def create_talk_video(
        self,
        audio_url: str,
        source_url: str,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Create a lip-sync video from audio and source image.

        Args:
            audio_url: URL of the uploaded audio file
            source_url: URL of the uploaded source image
            wait_for_completion: If True, wait for video generation to complete

        Returns:
            dict: {
                'id': str,           # Task/video ID
                'status': str,       # 'done', 'processing', 'error'
                'result_url': str,   # URL of generated video (when done)
                'created_at': str    # ISO timestamp
            }

        Raises:
            Exception: If video generation fails
        """
        try:
            logger.info(f'Creating talk video: audio={audio_url}, source={source_url}')

            # Submit video generation request (MuseTalk expects Form data, not JSON)
            response = await self.client.post(
                f'{self.base_url}/generate-video',
                data={
                    'audio_url': audio_url,
                    'source_url': source_url
                },
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                error_detail = self._extract_error(response)
                logger.error(f'Video generation request failed: {response.status_code} - {error_detail}')
                raise Exception(f'Video generation failed: {error_detail}')

            result = response.json()
            talk_id = result.get('id')
            created_at = result.get('created_at', datetime.utcnow().isoformat())

            if not talk_id:
                raise ValueError('Video generation started but no task ID returned')

            logger.info(f'Video generation started: task_id={talk_id}')

            if wait_for_completion:
                # Poll until completion
                final_result = await self._wait_for_video(talk_id)
                final_result['created_at'] = created_at
                return final_result
            else:
                # Return immediately with pending status
                return {
                    'id': talk_id,
                    'status': result.get('status', 'processing'),
                    'result_url': None,
                    'created_at': created_at
                }

        except httpx.ConnectError as e:
            logger.error(f'Connection error during video generation: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Video generation failed: {e}', exc_info=True)
            raise

    async def get_talk_status(self, talk_id: str) -> Dict[str, Any]:
        """
        Get the current status of a video generation task.

        Args:
            talk_id: The video generation task ID

        Returns:
            dict: {
                'id': str,
                'status': str,       # 'done', 'processing', 'error'
                'result_url': str,   # Available when status='done'
                'error': str         # Available when status='error'
            }
        """
        try:
            response = await self.client.get(
                f'{self.base_url}/talk-status/{talk_id}',
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {
                    'id': talk_id,
                    'status': 'error',
                    'error': 'Task not found'
                }
            else:
                error_detail = self._extract_error(response)
                logger.error(f'Status check failed: {response.status_code} - {error_detail}')
                return {
                    'id': talk_id,
                    'status': 'error',
                    'error': f'Status check failed: {error_detail}'
                }

        except httpx.ConnectError as e:
            logger.error(f'Connection error during status check: {e}')
            return {
                'id': talk_id,
                'status': 'error',
                'error': f'Service connection failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f'Status check failed: {e}')
            return {
                'id': talk_id,
                'status': 'error',
                'error': str(e)
            }

    async def _wait_for_video(
        self,
        talk_id: str,
        max_attempts: int = None
    ) -> Dict[str, Any]:
        """
        Poll until video generation is complete.

        Args:
            talk_id: The video generation task ID
            max_attempts: Maximum polling attempts (default: MAX_POLL_ATTEMPTS)

        Returns:
            Final status dictionary with result_url

        Raises:
            TimeoutError: If max attempts exceeded
            Exception: If video generation fails
        """
        if max_attempts is None:
            max_attempts = self.MAX_POLL_ATTEMPTS

        logger.info(f'Waiting for video completion: task_id={talk_id}')

        for attempt in range(max_attempts):
            status = await self.get_talk_status(talk_id)

            current_status = status.get('status', 'unknown')

            if current_status == 'done':
                result_url = status.get('result_url')
                logger.info(f'Video generation complete: {talk_id} -> {result_url}')
                return {
                    'id': talk_id,
                    'status': 'done',
                    'result_url': result_url
                }

            elif current_status == 'error':
                error_msg = status.get('error', 'Unknown error')
                logger.error(f'Video generation failed: {talk_id} - {error_msg}')
                raise Exception(f'Video generation failed: {error_msg}')

            # Still processing, wait and retry
            if (attempt + 1) % 10 == 0:
                logger.info(f'Video generation in progress... ({attempt + 1}/{max_attempts})')

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
_musetalk_client: Optional[MuseTalkClient] = None


def get_musetalk_client() -> MuseTalkClient:
    """
    Get or create the global MuseTalk client instance.

    Returns:
        MuseTalkClient singleton instance
    """
    global _musetalk_client

    if _musetalk_client is None:
        _musetalk_client = MuseTalkClient()

    return _musetalk_client


async def check_musetalk_available() -> bool:
    """
    Quick check if MuseTalk service is available.

    Returns:
        True if service is healthy
    """
    client = get_musetalk_client()
    return await client.check_service_health()
