"""
Qwen3-TTS Service Client
Replaces OpenVoice for voice cloning and synthesis with local inference.

Design Notes:
- Drop-in replacement for OpenVoice Native Client
- Async HTTP client with httpx
- Graceful error handling with fallback support
- Environment-based URL configuration
"""

import httpx
import asyncio
import logging
import base64
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class Qwen3TTSClient:
    """
    Client for Qwen3-TTS service (replaces OpenVoice).

    Features:
    - Voice cloning from audio samples
    - Text-to-speech synthesis with cloned voices
    - Profile management
    - Health monitoring

    Environment Variables:
    - QWEN_TTS_SERVICE_URL: Service base URL (default: http://qwen-tts:8002)
    - USE_LOCAL_TTS: Enable/disable local TTS (default: true)
    """

    DEFAULT_TIMEOUT = 300.0  # 5 minutes for synthesis operations
    HEALTH_CHECK_TIMEOUT = 10.0

    def __init__(self, base_url: str = None):
        """
        Initialize Qwen3-TTS client with automatic URL detection.

        Args:
            base_url: Optional explicit service URL. If not provided,
                     will auto-detect from environment variables.
        """
        if base_url is None:
            # Priority: QWEN_TTS_SERVICE_URL > environment detection
            base_url = os.environ.get('QWEN_TTS_SERVICE_URL')
            if not base_url:
                # Check if running in Docker
                if os.environ.get('ENVIRONMENT') == 'docker':
                    base_url = 'http://qwen-tts:8002'  # Docker network
                else:
                    base_url = 'http://localhost:8002'  # Local development

        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        self._service_available = False

        logger.info(f'Qwen3-TTS Client initialized: {self.base_url}')

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def check_service_health(self) -> bool:
        """
        Check if the Qwen3-TTS service is available.

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
                    logger.info('Qwen3-TTS Service is available')
                    logger.debug(f'Service info: {health_data}')
                return self._service_available
        except httpx.ConnectError as e:
            logger.warning(f'Qwen3-TTS Service connection failed: {e}')
        except httpx.TimeoutException:
            logger.warning('Qwen3-TTS Service health check timed out')
        except Exception as e:
            logger.error(f'Qwen3-TTS Service health check error: {e}')

        self._service_available = False
        return False

    @property
    def is_available(self) -> bool:
        """Check if service was last known to be available."""
        return self._service_available

    async def create_voice_clone(
        self,
        name: str,
        audio_paths: List[str],
        language: str = "ja",
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a voice clone profile from audio samples.

        Args:
            name: Display name for the voice profile
            audio_paths: List of paths to reference audio files
            language: Target language code (ja, en, zh, etc.)
            profile_id: Optional specific profile ID (auto-generated if None)

        Returns:
            dict: {
                'success': bool,
                'profile_id': str,
                'message': str,
                'error': str (only if success=False)
            }
        """
        try:
            # Prepare multipart files
            files = []
            for idx, audio_path in enumerate(audio_paths):
                path = Path(audio_path)
                if not path.exists():
                    return {
                        'success': False,
                        'error': f'Audio file not found: {audio_path}'
                    }

                with open(path, 'rb') as f:
                    audio_data = f.read()
                    # Determine content type
                    suffix = path.suffix.lower()
                    content_type = {
                        '.wav': 'audio/wav',
                        '.mp3': 'audio/mpeg',
                        '.flac': 'audio/flac',
                        '.m4a': 'audio/mp4'
                    }.get(suffix, 'audio/wav')

                    files.append(('audio_samples', (path.name, audio_data, content_type)))

            # Prepare form data
            data = {
                'name': name,
                'language': language
            }
            if profile_id:
                data['voice_profile_id'] = profile_id

            logger.info(f'Creating voice clone: name={name}, language={language}, samples={len(audio_paths)}')

            response = await self.client.post(
                f'{self.base_url}/voice-clone/create',
                data=data,
                files=files
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f'Voice clone created: profile_id={result.get("profile_id")}')
                return {
                    'success': True,
                    'profile_id': result.get('profile_id'),
                    'message': result.get('message', 'Voice clone created successfully')
                }
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_detail)
                except:
                    pass
                logger.error(f'Voice clone creation failed: {response.status_code} - {error_detail}')
                return {
                    'success': False,
                    'error': f'API returned {response.status_code}: {error_detail}'
                }

        except httpx.ConnectError as e:
            logger.error(f'Connection error during voice clone creation: {e}')
            return {
                'success': False,
                'error': f'Service connection failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f'Voice clone creation failed: {e}', exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    async def synthesize_voice(
        self,
        text: str,
        profile_id: str,
        language: str = 'ja',
        speed: float = 1.0,
        pitch: float = 0.0,
        volume: float = 1.0,
        pause_duration: float = 0.0
    ) -> bytes:
        """
        Synthesize speech using a cloned voice profile.

        Args:
            text: Text to synthesize
            profile_id: Voice profile ID to use
            language: Language code
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Pitch adjustment (-0.15 to 0.15)
            volume: Volume multiplier (0.0-2.0)
            pause_duration: End-of-sentence pause in seconds

        Returns:
            bytes: WAV audio data

        Raises:
            Exception: If synthesis fails
        """
        try:
            logger.info(f'Synthesizing voice: profile={profile_id}, text_len={len(text)}, lang={language}')

            response = await self.client.post(
                f'{self.base_url}/voice-clone/synthesize',
                data={
                    'text': text,
                    'voice_profile_id': profile_id,
                    'language': language,
                    'speed': str(speed),
                    'pitch': str(pitch),
                    'volume': str(volume),
                    'pause_duration': str(pause_duration)
                }
            )

            if response.status_code == 200:
                # Qwen3-TTS returns JSON with base64-encoded audio
                result = response.json()

                if result.get('success') and result.get('audio_data'):
                    audio_data = base64.b64decode(result['audio_data'])
                    logger.info(f'Voice synthesis successful: {len(audio_data)} bytes')
                    return audio_data
                else:
                    error_msg = result.get('error', 'Unknown synthesis error')
                    logger.error(f'Voice synthesis failed: {error_msg}')
                    raise Exception(f'Voice synthesis failed: {error_msg}')
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_detail)
                except:
                    pass
                logger.error(f'Voice synthesis API error: {response.status_code} - {error_detail}')
                raise Exception(f'Voice synthesis API error: {response.status_code}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error during voice synthesis: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Voice synthesis failed: {e}', exc_info=True)
            raise

    async def synthesize_with_clone(
        self,
        text: str,
        profile_id: str,
        language: str = 'ja',
        speed: float = 1.0,
        pitch: float = 0.0,
        volume: float = 1.0,
        pause_duration: float = 0.0
    ) -> bytes:
        """
        Alias for synthesize_voice for API compatibility with OpenVoice client.
        """
        return await self.synthesize_voice(
            text=text,
            profile_id=profile_id,
            language=language,
            speed=speed,
            pitch=pitch,
            volume=volume,
            pause_duration=pause_duration
        )

    async def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all available voice profiles.

        Returns:
            List of profile dictionaries with id, name, language, etc.

        Raises:
            Exception: If API call fails
        """
        try:
            response = await self.client.get(f'{self.base_url}/voice-clone/profiles')

            if response.status_code == 200:
                profiles = response.json()
                logger.info(f'Retrieved {len(profiles)} voice profiles')
                return profiles
            else:
                logger.error(f'Failed to list profiles: {response.status_code}')
                raise Exception(f'Profile list API error: {response.status_code}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error listing profiles: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Failed to list profiles: {e}', exc_info=True)
            raise

    async def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a voice profile.

        Args:
            profile_id: Profile ID to delete

        Returns:
            True if deletion successful

        Raises:
            Exception: If deletion fails
        """
        try:
            response = await self.client.delete(
                f'{self.base_url}/voice-clone/profiles/{profile_id}'
            )

            if response.status_code == 200:
                logger.info(f'Profile deleted: {profile_id}')
                return True
            elif response.status_code == 404:
                logger.warning(f'Profile not found for deletion: {profile_id}')
                # Return True anyway - profile doesn't exist which is the goal
                return True
            else:
                logger.error(f'Failed to delete profile {profile_id}: {response.status_code}')
                raise Exception(f'Profile delete API error: {response.status_code}')

        except httpx.ConnectError as e:
            logger.error(f'Connection error deleting profile: {e}')
            raise Exception(f'Service connection failed: {str(e)}')
        except Exception as e:
            logger.error(f'Failed to delete profile {profile_id}: {e}', exc_info=True)
            raise

    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific voice profile.

        Args:
            profile_id: Profile ID to retrieve

        Returns:
            Profile dictionary or None if not found
        """
        try:
            response = await self.client.get(
                f'{self.base_url}/voice-clone/profiles/{profile_id}'
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f'Failed to get profile {profile_id}: {response.status_code}')
                return None

        except Exception as e:
            logger.error(f'Failed to get profile {profile_id}: {e}')
            return None


# Singleton instance for global use
_qwen_tts_client: Optional[Qwen3TTSClient] = None


def get_qwen_tts_client() -> Qwen3TTSClient:
    """
    Get or create the global Qwen3-TTS client instance.

    Returns:
        Qwen3TTSClient singleton instance
    """
    global _qwen_tts_client

    if _qwen_tts_client is None:
        _qwen_tts_client = Qwen3TTSClient()

    return _qwen_tts_client


async def check_qwen_tts_available() -> bool:
    """
    Quick check if Qwen3-TTS service is available.

    Returns:
        True if service is healthy
    """
    client = get_qwen_tts_client()
    return await client.check_service_health()
