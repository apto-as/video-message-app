"""
OpenVoice Native Service Client
Dockerバックエンドからネイティブサービスへの接続クライアント
"""

import httpx
import asyncio
import logging
import json
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiofiles
import tempfile
import os

logger = logging.getLogger(__name__)

class OpenVoiceNativeClient:
    """OpenVoice Native Service接続クライアント"""
    
    def __init__(self, base_url: str = None):
        """Initialize with proper URL detection"""
        if base_url is None:
            # Try OPENVOICE_API_URL first (matches environment variable)
            base_url = os.environ.get('OPENVOICE_API_URL')
            if not base_url:
                # Check if running in Docker
                if os.environ.get('ENVIRONMENT') == 'docker':
                    base_url = 'http://host.docker.internal:8001'
                else:
                    base_url = 'http://localhost:8001'
        
        logger.info(f'OpenVoice Native Client using URL: {base_url}')
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
        self._service_available = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_service_health(self) -> bool:
        """サービスの稼働状態を確認"""
        try:
            response = await self.client.get(f'{self.base_url}/health')
            if response.status_code == 200:
                self._service_available = True
                logger.info('OpenVoice Native Service is available')
                return True
        except Exception as e:
            logger.error(f'OpenVoice Native Service health check failed: {e}')
        
        self._service_available = False
        return False
    
    async def create_voice_clone(
        self,
        name: str, audio_paths: List[str], language: str = "ja", profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """音声クローンを作成"""
        try:
            # Simple implementation - just forward to the OpenVoice service
            files = []
            # OpenVoice Simple only accepts one file
            if audio_paths:
                with open(audio_paths[0], 'rb') as f:
                    files = [('audio_file', ('audio.wav', f.read(), 'audio/wav'))]
            
            data = {'name': name}
            
            response = await self.client.post(
                f'{self.base_url}/api/clone',
                data=data,
                files=files
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'profile_id': result.get('profile_id'),
                    'message': result.get('message', '音声クローンを作成しました')
                }
            else:
                return {
                    'success': False,
                    'error': f'API returned {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f'Voice clone creation failed: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def synthesize_voice(
        self,
        text: str,
        profile_id: str,
        language: str = 'ja'
    ) -> Optional[bytes]:
        """音声を合成"""
        try:
            response = await self.client.post(
                f'{self.base_url}/api/synthesize',
                data={
                    'text': text,
                    'profile_id': profile_id,
                    'language': language
                }
            )
            
            if response.status_code == 200:
                return response.content
            
        except Exception as e:
            logger.error(f'Voice synthesis failed: {e}')
        
        return None
    
    async def synthesize_with_clone(
        self,
        text: str,
        profile_id: str,
        language: str = 'ja'
    ) -> Optional[bytes]:
        """クローン音声で合成（synthesize_voiceのエイリアス）"""
        return await self.synthesize_voice(text, profile_id, language)
    
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """プロファイル一覧を取得"""
        try:
            response = await self.client.get(f'{self.base_url}/api/profiles')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f'Failed to list profiles: {e}')
        
        return []
    
    async def delete_profile(self, profile_id: str) -> bool:
        """プロファイルを削除"""
        try:
            response = await self.client.delete(
                f'{self.base_url}/api/profiles/{profile_id}'
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f'Failed to delete profile: {e}')
        
        return False
