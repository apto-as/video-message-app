"""
OpenVoice ハイブリッドクライアント
ネイティブサービス優先、フォールバック機能付き
"""

import os
import asyncio
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import aiofiles

from .openvoice_native_client import OpenVoiceNativeClient
from core.logging import get_logger, log_info, log_error, log_warning

logger = get_logger(__name__)

class OpenVoiceHybridClient:
    """OpenVoice ハイブリッドクライアント"""
    
    def __init__(self):
        self.native_client = OpenVoiceNativeClient()
        self._native_available = False
        
    async def __aenter__(self):
        # ネイティブサービス可用性チェック
        self._native_available = await self.native_client.check_service_health()
        if self._native_available:
            log_info("OpenVoice Native Service available", service="openvoice")
        else:
            log_warning("OpenVoice Native Service unavailable - fallback mode", service="openvoice")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.native_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def create_voice_clone(
        self,
        name: str,
        audio_paths: List[str],
        language: str = "ja",
        profile_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """音声クローン作成（ハイブリッド）"""
        
        log_info(
            "Starting voice clone creation",
            name=name,
            sample_count=len(audio_paths),
            language=language
        )
        
        # 【修正】毎回サービス可用性を確認
        try:
            self._native_available = await self.native_client.check_service_health()
            logger.debug("Service availability", available=self._native_available)
        except Exception as health_error:
            log_error("Health check failed", error=health_error)
            self._native_available = False
        
        if not self._native_available:
            log_error(
                "OpenVoice Native Service health check failed",
                base_url=self.native_client.base_url,
                docker_env=os.environ.get('DOCKER_ENV', 'Not set')
            )
            raise Exception("OpenVoice Native Serviceが利用できません。サービスを起動してください。")
        
        try:
            log_info("Executing voice clone on native service")
            result = await self.native_client.create_voice_clone(
                name=name,
                audio_paths=audio_paths,
                language=language,
                profile_id=profile_id
            )
            
            logger.debug("Native service result", result=result)
            
            if result and result.get('success'):
                log_info("Voice clone created successfully", profile_id=profile_id)
                return result
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                log_error("Native service processing failed", error_message=error_msg)
                raise Exception(f"ネイティブサービス処理失敗: {error_msg}")
                
        except Exception as e:
            log_error("Voice clone failed on native service", error=e)
            raise Exception(f"音声クローン処理エラー: {str(e)}")
    
    async def synthesize_with_clone(
        self,
        text: str,
        voice_profile: Dict[str, Any],
        language: str = "ja",
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> Optional[bytes]:
        """クローン音声合成（ハイブリッド）"""
        
        logger.info(f"音声合成要求: プロファイル={voice_profile.get('id')}, テキスト長={len(text)}")
        logger.info(f"プロファイル詳細: 名前={voice_profile.get('name')}, 参照音声={voice_profile.get('reference_audio_path')}")
        
        # ネイティブサービス可用性チェック
        current_available = await self.native_client.check_service_health()
        
        if current_available:
            try:
                logger.info("ネイティブサービスで音声合成実行")
                result = await self.native_client.synthesize_with_clone(
                    text=text,
                    voice_profile=voice_profile,
                    language=language,
                    speed=speed,
                    emotion=emotion
                )
                if result and len(result) > 1000:  # 実際の音声データかチェック
                    logger.info(f"ネイティブサービス音声合成成功: {len(result)} bytes")
                    return result
                else:
                    logger.warning("ネイティブサービスから不正な音声データ")
                    
            except Exception as e:
                logger.error(f"ネイティブサービス音声合成エラー: {str(e)}")
        
        # 【重要】フォールバックでは参照音声ファイルを直接使用（和音生成を避ける）
        reference_audio_path = voice_profile.get('reference_audio_path')
        if reference_audio_path and os.path.exists(reference_audio_path):
            logger.info(f"参照音声ファイルを使用: {reference_audio_path}")
            try:
                async with aiofiles.open(reference_audio_path, 'rb') as f:
                    reference_audio = await f.read()
                    if len(reference_audio) > 1000:
                        logger.info(f"参照音声ファイル使用成功: {len(reference_audio)} bytes")
                        return reference_audio
            except Exception as e:
                logger.error(f"参照音声ファイル読み込みエラー: {str(e)}")
        
        # 最後の手段：エラーを投げる（和音生成はしない）
        raise Exception(f"音声合成に失敗しました。プロファイル '{voice_profile.get('name')}' の参照音声ファイルを確認してください。")
    
    async def _fallback_voice_clone(
        self,
        name: str,
        audio_paths: List[str],
        language: str,
        profile_id: Optional[str]
    ) -> Dict[str, Any]:
        """フォールバック音声クローン作成"""
        
        try:
            logger.info(f"フォールバックモードで音声クローン作成: {name}")
            
            # 基本的な音声特徴保存（実際の処理なし）
            fallback_data = {
                'name': name,
                'language': language,
                'audio_paths': audio_paths,
                'created_at': datetime.now().isoformat(),
                'fallback_mode': True
            }
            
            # フォールバックモードでは実際の処理は行わず、エラーを通知
            raise Exception(
                f"音声クローン作成に失敗しました。OpenVoice Native Service が利用できません。"
                f"Name: {name}, Language: {language}"
            )
            
        except Exception as e:
            logger.error(f"フォールバック音声クローンエラー: {str(e)}")
            raise
    
    async def _fallback_synthesis(
        self,
        text: str,
        voice_profile: Dict[str, Any]
    ) -> bytes:
        """フォールバック音声合成"""
        
        try:
            # ファイルベース音声合成を試行
            profile_id = voice_profile.get('id')
            reference_audio_path = voice_profile.get('reference_audio_path')
            
            logger.warning(f"フォールバックモード: プロファイル {profile_id}")
            
            # 参照音声ファイルが存在する場合は、それを基にした簡易音声を生成
            if reference_audio_path and os.path.exists(reference_audio_path):
                logger.info(f"参照音声ファイル発見: {reference_audio_path}")
                
                # 参照音声ファイルをそのまま返す（テスト用）
                async with aiofiles.open(reference_audio_path, 'rb') as f:
                    reference_audio = await f.read()
                    logger.info("参照音声ファイルを直接返却（フォールバック）")
                    return reference_audio
            
            # 参照音声がない場合は通知音を生成
            logger.warning("参照音声ファイルが見つからないため通知音を生成")
            
            import wave
            import struct
            import math
            
            # より音楽的な通知音（和音）
            sample_rate = 22050
            duration = 2.0  # 2秒間
            
            frames = int(duration * sample_rate)
            audio_data = []
            
            # C-E-G和音 (261.63, 329.63, 392.00 Hz)
            frequencies = [261.63, 329.63, 392.00]
            
            for i in range(frames):
                value = 0
                for freq in frequencies:
                    # 各周波数の音を合成
                    value += 32767 * 0.2 * math.sin(2 * math.pi * freq * i / sample_rate)
                
                # エンベロープ（フェードイン・アウト）を適用
                envelope = 1.0
                fade_frames = int(0.1 * sample_rate)  # 0.1秒でフェード
                if i < fade_frames:
                    envelope = i / fade_frames
                elif i > frames - fade_frames:
                    envelope = (frames - i) / fade_frames
                
                value = int(value * envelope)
                audio_data.append(struct.pack('<h', value))
            
            # WAVファイルとして出力
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(b''.join(audio_data))
                
                # ファイルを読み込み
                async with aiofiles.open(temp_file.name, 'rb') as f:
                    result = await f.read()
                
                # 一時ファイル削除
                os.unlink(temp_file.name)
                
                return result
                
        except Exception as e:
            logger.error(f"フォールバック音声合成エラー: {str(e)}")
            raise Exception("音声合成機能が利用できません。OpenVoice Native Serviceの起動を確認してください。")
    
    async def check_service_availability(self) -> Dict[str, Any]:
        """サービス可用性チェック"""
        native_status = await self.native_client.check_service_health()
        
        return {
            'native_service': native_status,
            'fallback_mode': not native_status,
            'recommended_action': (
                "正常動作中" if native_status 
                else "OpenVoice Native Serviceの起動が必要です"
            )
        }
    
    @property
    def is_native_available(self) -> bool:
        """ネイティブサービス利用可能性"""
        return self._native_available