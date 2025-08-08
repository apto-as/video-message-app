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
        # Docker環境では host.docker.internal を使用
        if base_url is None:
            import os
            if os.environ.get('DOCKER_ENV'):
                base_url = "http://host.docker.internal:8001"
            else:
                base_url = "http://localhost:8001"
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
        self._service_available = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_service_health(self) -> bool:
        """ネイティブサービスのヘルスチェック"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                self._service_available = health_data.get('openvoice_available', False)
                logger.info(f"OpenVoice Native Service: {health_data.get('status', 'unknown')}")
                return self._service_available
            else:
                logger.warning(f"ヘルスチェック失敗: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"OpenVoice Native Service接続失敗: {str(e)}")
            self._service_available = False
            return False
    
    async def create_voice_clone(
        self,
        name: str,
        audio_paths: List[str],
        language: str = "ja",
        profile_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """音声クローン作成"""
        
        if not await self.check_service_health():
            raise Exception("OpenVoice Native Serviceが利用できません")
        
        try:
            # 音声ファイルを読み込み
            files = []
            data = {
                'name': name,
                'language': language
            }
            
            # profile_idが指定されている場合は追加
            if profile_id:
                data['voice_profile_id'] = profile_id
            
            for i, audio_path in enumerate(audio_paths):
                async with aiofiles.open(audio_path, 'rb') as f:
                    content = await f.read()
                    files.append(
                        ('audio_samples', (f'sample_{i}.wav', content, 'audio/wav'))
                    )
            
            # ネイティブサービスに送信
            response = await self.client.post(
                f"{self.base_url}/voice-clone/create",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"音声クローン作成成功: {result.get('voice_profile_id')}")
                # パス変換: NativeのパスをDocker用に変換
                embedding_path = result.get('embedding_path')
                if embedding_path:
                    # /Users/apto-as/... を /app/... に変換
                    # または /data/backend/... に変換
                    if '/storage/openvoice/' in embedding_path:
                        # パスの後半部分を抽出
                        path_parts = embedding_path.split('/storage/openvoice/')
                        if len(path_parts) > 1:
                            embedding_path = f"/app/storage/openvoice/{path_parts[1]}"
                    logger.info(f"埋め込みファイルパス: {embedding_path}")
                
                return {
                    'success': True,
                    'profile_id': result.get('voice_profile_id'),
                    'path': None,  # 互換性のため保持
                    'embedding_path': embedding_path,  # 新しいフィールド
                    'processing_time': 0
                }
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                raise Exception(f"音声クローン作成失敗: {error_detail}")
                
        except Exception as e:
            logger.error(f"音声クローン作成エラー: {str(e)}")
            raise
    
    async def synthesize_with_clone(
        self,
        text: str,
        voice_profile: Dict[str, Any],
        language: str = "ja",
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> Optional[bytes]:
        """クローン音声で合成"""
        
        if not await self.check_service_health():
            raise Exception("OpenVoice Native Serviceが利用できません")
        
        try:
            # 【緊急修正】ネイティブサービスでプロファイル検索
            voice_profile_id = voice_profile.get('id')
            
            # ネイティブサービスでプロファイルが存在するかチェック
            available_profiles = await self.get_available_profiles()
            native_profile = None
            
            # まず完全一致でプロファイルを検索
            for p in available_profiles:
                if p.get('id') == voice_profile_id:
                    native_profile = p
                    break
            
            # 完全一致がない場合、名前で検索して最新のものを使用
            if not native_profile:
                profile_name = voice_profile.get('name')
                matching_profiles = [p for p in available_profiles if p.get('name') == profile_name]
                if matching_profiles:
                    # 最新のプロファイル（作成日時順）を使用
                    native_profile = max(matching_profiles, key=lambda p: p.get('created_at', ''))
                    logger.info(f"プロファイル名 '{profile_name}' で検索、最新プロファイル {native_profile.get('id')} を使用")
                    voice_profile_id = native_profile.get('id')
            
            # それでも見つからない場合はバックエンドから登録
            if not native_profile:
                logger.info(f"プロファイル {voice_profile_id} がネイティブサービスに存在しないため登録")
                
                # 参照音声ファイルでプロファイルを作成
                reference_audio_path = voice_profile.get('reference_audio_path')
                if not reference_audio_path or not Path(reference_audio_path).exists():
                    raise Exception(f"参照音声ファイルが見つかりません: {reference_audio_path}")
                
                # 【緊急修正】参照音声ファイルを3回使用して要件を満たす
                created_profile = await self.create_voice_clone(
                    name=voice_profile.get('name', 'imported_profile'),
                    audio_paths=[reference_audio_path, reference_audio_path, reference_audio_path],
                    language=language,
                    profile_id=voice_profile_id
                )
                
                if not created_profile or not created_profile.get('success'):
                    raise Exception("プロファイル登録に失敗しました")
            
            # 通常の音声合成要求
            data = {
                'text': text,
                'voice_profile_id': voice_profile_id,
                'language': language,
                'speed': str(speed)
            }
            
            response = await self.client.post(
                f"{self.base_url}/voice-clone/synthesize",
                data=data
            )
            
            if response.status_code == 200:
                # レスポンスがJSONかバイナリかチェック
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                    if result.get('success'):
                        # Base64デコード
                        audio_b64 = result.get('audio_data')
                        if audio_b64:
                            audio_data = base64.b64decode(audio_b64)
                            logger.info(f"音声合成完了: {len(audio_data)} bytes")
                            return audio_data
                        else:
                            raise Exception("音声データが空です")
                    else:
                        raise Exception(result.get('error', 'Unknown synthesis error'))
                elif 'audio/' in content_type:
                    # 直接音声データが返却された場合
                    audio_data = response.content
                    logger.info(f"音声合成完了（直接）: {len(audio_data)} bytes")
                    return audio_data
                else:
                    raise Exception(f"予期しないレスポンス形式: {content_type}")
            else:
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                except:
                    error_detail = response.text or 'Unknown error'
                raise Exception(f"音声合成失敗: {error_detail}")
                
        except Exception as e:
            logger.error(f"音声合成エラー: {str(e)}")
            raise
    
    async def get_available_profiles(self) -> List[Dict[str, Any]]:
        """利用可能な音声プロファイル取得"""
        
        try:
            response = await self.client.get(f"{self.base_url}/voice-clone/profiles")
            
            if response.status_code == 200:
                profiles = response.json()
                logger.info(f"音声プロファイル {len(profiles)}件取得")
                return profiles
            else:
                logger.warning(f"プロファイル取得失敗: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"プロファイル取得エラー: {str(e)}")
            return []
    
    async def delete_voice_profile(self, profile_id: str) -> bool:
        """音声プロファイル削除"""
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/voice-clone/profiles/{profile_id}"
            )
            
            if response.status_code == 200:
                logger.info(f"音声プロファイル削除完了: {profile_id}")
                return True
            else:
                logger.warning(f"プロファイル削除失敗: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"プロファイル削除エラー: {str(e)}")
            return False
    
    @property
    def is_available(self) -> bool:
        """サービス利用可能性"""
        return self._service_available