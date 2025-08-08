"""
統合音声サービス
VOICEVOX、OpenVoice V2、D-IDを統一インターフェースで管理
"""

import asyncio
import tempfile
import os
from typing import Dict, List, Optional, Union, Tuple, Any
from enum import Enum
from pathlib import Path
import aiofiles
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

from .voicevox_client import VOICEVOXClient, get_voicevox_client
from .openvoice_hybrid_client import OpenVoiceHybridClient

class VoiceProvider(str, Enum):
    """音声プロバイダー"""
    VOICEVOX = "voicevox"
    OPENVOICE = "openvoice"

class VoiceType(str, Enum):
    """音声種別"""
    PRESET = "preset"        # プリセット音声
    CLONED = "cloned"        # クローン音声
    CUSTOM = "custom"        # カスタム音声

class VoiceProfile(BaseModel):
    """音声プロファイル"""
    id: str
    name: str
    provider: VoiceProvider
    voice_type: VoiceType
    language: str = "ja"
    speaker_id: Optional[int] = None
    voice_file_path: Optional[str] = None
    metadata: Dict[str, Any] = {}

class VoiceSynthesisRequest(BaseModel):
    """音声合成リクエスト"""
    text: str = Field(..., min_length=1, max_length=1000)
    voice_profile: VoiceProfile
    speed: float = Field(default=1.0, ge=0.1, le=3.0)
    pitch: float = Field(default=0.0, ge=-0.15, le=0.15)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    emotion: str = "neutral"

class UnifiedVoiceService:
    """統合音声サービス"""
    
    def __init__(self):
        self.voicevox_client: Optional[VOICEVOXClient] = None
        self.openvoice_client: Optional[OpenVoiceHybridClient] = None
        self._voice_profiles: Dict[str, VoiceProfile] = {}
        
    async def initialize(self):
        """サービス初期化"""
        try:
            # VOICEVOXクライアント初期化
            try:
                self.voicevox_client = await get_voicevox_client()
                await self._load_voicevox_profiles()
            except Exception as e:
                print(f"VOICEVOX初期化警告: {str(e)}")
                
            # OpenVoiceクライアント初期化
            try:
                self.openvoice_client = OpenVoiceHybridClient()
                await self._load_openvoice_profiles()
            except Exception as e:
                print(f"OpenVoice初期化警告: {str(e)}")
                
                
        except Exception as e:
            raise Exception(f"統合音声サービス初期化エラー: {str(e)}")
    
    async def _load_voicevox_profiles(self):
        """VOICEVOXプロファイル読み込み"""
        if not self.voicevox_client:
            return
            
        try:
            speakers = await self.voicevox_client.get_popular_speakers()
            
            for speaker in speakers:
                profile_id = f"voicevox_{speaker['style_id']}"
                profile = VoiceProfile(
                    id=profile_id,
                    name=f"{speaker['speaker_name']} ({speaker['style_name']})",
                    provider=VoiceProvider.VOICEVOX,
                    voice_type=VoiceType.PRESET,
                    language="ja",
                    speaker_id=speaker['style_id'],
                    metadata={
                        "speaker_uuid": speaker['speaker_uuid'],
                        "order": speaker.get('order', 999)
                    }
                )
                self._voice_profiles[profile_id] = profile
                
        except Exception as e:
            print(f"VOICEVOXプロファイル読み込みエラー: {str(e)}")
    
    async def _load_openvoice_profiles(self):
        """OpenVoiceプロファイル読み込み"""
        if not self.openvoice_client:
            return
            
        try:
            # 登録済みOpenVoice音声クローンプロファイルを読み込み
            from .voice_storage_service import VoiceStorageService
            storage_service = VoiceStorageService()
            
            # OpenVoiceプロバイダーのプロファイルを取得
            openvoice_profiles = await storage_service.get_all_voice_profiles(provider="openvoice")
            
            for profile_data in openvoice_profiles:
                if profile_data.get("status") == "ready":
                    profile_id = profile_data["id"]
                    
                    # クローン音声の参照音声ファイルパスを構築
                    voice_file_path = None
                    if profile_data.get("reference_audio_path"):
                        voice_file_path = profile_data["reference_audio_path"]
                    else:
                        # ストレージパスから参照音声ファイルを探す
                        storage_path = profile_data.get("storage_path")
                        if storage_path:
                            from pathlib import Path
                            storage_dir = Path(storage_path)
                            # 一般的な音声ファイル拡張子で検索
                            for ext in ['.wav', '.mp3', '.m4a', '.flac']:
                                potential_file = storage_dir / f"reference{ext}"
                                if potential_file.exists():
                                    voice_file_path = str(potential_file)
                                    break
                    
                    profile = VoiceProfile(
                        id=profile_id,
                        name=profile_data["name"],
                        provider=VoiceProvider.OPENVOICE,
                        voice_type=VoiceType.CLONED,
                        language=profile_data.get("language", "ja"),
                        voice_file_path=voice_file_path,
                        metadata={
                            "description": profile_data.get("description"),
                            "sample_count": profile_data.get("sample_count", 0),
                            "created_at": profile_data.get("created_at"),
                            "embedding_path": profile_data.get("embedding_path"),
                            "storage_path": profile_data.get("storage_path"),
                            "requires_reference": False  # クローン音声はファイルパスが設定されていれば参照音声不要
                        }
                    )
                    self._voice_profiles[profile_id] = profile
            
            # デフォルトプロファイルも追加（後方互換性）
            # OpenVoiceHybridClientには get_supported_languages メソッドがないため、直接定義
            default_languages = [
                {'code': 'ja', 'native': '日本語'},
                {'code': 'en', 'native': 'English'},
                {'code': 'zh', 'native': '中文'}
            ]
            
            for lang in default_languages:
                if lang['code'] == 'ja':  # 日本語のみ追加
                    profile_id = f"openvoice_{lang['code']}"
                    # 既存のクローンプロファイルと重複しないようにチェック
                    if profile_id not in self._voice_profiles:
                        profile = VoiceProfile(
                            id=profile_id,
                            name=f"OpenVoice ({lang['native']})",
                            provider=VoiceProvider.OPENVOICE,
                            voice_type=VoiceType.PRESET,
                            language=lang['code'],
                            metadata={
                                "native_name": lang['native'],
                                "requires_reference": True
                            }
                        )
                        self._voice_profiles[profile_id] = profile
                    
        except Exception as e:
            print(f"OpenVoiceプロファイル読み込みエラー: {str(e)}")
    
    
    async def get_available_voices(
        self, 
        provider: Optional[VoiceProvider] = None,
        voice_type: Optional[VoiceType] = None,
        language: Optional[str] = None
    ) -> List[VoiceProfile]:
        """利用可能な音声一覧を取得"""
        
        voices = list(self._voice_profiles.values())
        
        # フィルタリング
        if provider:
            voices = [v for v in voices if v.provider == provider]
        if voice_type:
            voices = [v for v in voices if v.voice_type == voice_type]
        if language:
            voices = [v for v in voices if v.language == language]
        
        # ソート（プロバイダー順、そして順序）
        def sort_key(voice):
            provider_order = {
                VoiceProvider.VOICEVOX: 0,
                VoiceProvider.OPENVOICE: 1
            }
            return (
                provider_order.get(voice.provider, 999),
                voice.metadata.get('order', 999),
                voice.name
            )
        
        return sorted(voices, key=sort_key)
    
    async def synthesize_speech(
        self, 
        request: VoiceSynthesisRequest
    ) -> bytes:
        """音声合成実行"""
        
        profile = request.voice_profile
        
        try:
            if profile.provider == VoiceProvider.VOICEVOX:
                return await self._synthesize_voicevox(request)
            elif profile.provider == VoiceProvider.OPENVOICE:
                return await self._synthesize_openvoice(request)
            else:
                raise ValueError(f"サポートされていないプロバイダー: {profile.provider}")
                
        except Exception as e:
            raise Exception(f"音声合成エラー ({profile.provider}): {str(e)}")
    
    async def _synthesize_voicevox(self, request: VoiceSynthesisRequest) -> bytes:
        """VOICEVOX音声合成"""
        if not self.voicevox_client:
            raise Exception("VOICEVOXクライアントが初期化されていません")
        
        profile = request.voice_profile
        speaker_id = profile.speaker_id
        
        if speaker_id is None:
            raise ValueError("VOICEVOX話者IDが指定されていません")
        
        return await self.voicevox_client.text_to_speech(
            text=request.text,
            speaker_id=speaker_id,
            speed_scale=request.speed,
            pitch_scale=request.pitch,
            volume_scale=request.volume
        )
    
    async def _synthesize_openvoice(self, request: VoiceSynthesisRequest) -> bytes:
        """OpenVoice音声合成"""
        if not self.openvoice_client:
            raise Exception("OpenVoiceクライアントが初期化されていません")
        
        profile = request.voice_profile
        
        # クローン音声の場合は既存のプロファイルを使用、プリセット音声の場合は参照音声ファイルが必要
        if profile.voice_type == VoiceType.CLONED:
            # クローン音声の場合はプロファイルデータを使って合成
            try:
                # プロファイルメタデータから必要な情報を取得
                embedding_path = profile.metadata.get("embedding_path")
                storage_path = profile.metadata.get("storage_path")
                
                logger.info(f"クローン音声合成: プロファイル={profile.id}, embedding_path={embedding_path}")
                
                profile_dict = {
                    "id": profile.id,
                    "name": profile.name,
                    "language": profile.language,
                    "embedding_path": embedding_path,
                    "storage_path": storage_path,
                    "status": "ready"
                }
                
                return await self.openvoice_client.synthesize_with_clone(
                    text=request.text,
                    voice_profile=profile_dict,
                    language=profile.language,
                    speed=request.speed,
                    emotion=request.emotion
                )
            except Exception as e:
                raise ValueError(f"OpenVoiceクローン音声での合成に失敗しました: {str(e)}")
        else:
            # プリセット音声の場合は参照音声ファイルが必要
            if not profile.voice_file_path or not os.path.exists(profile.voice_file_path):
                raise ValueError("OpenVoice音声合成には参照音声ファイルが必要です")
        
        # 参照音声読み込み
        async with aiofiles.open(profile.voice_file_path, 'rb') as f:
            reference_audio = await f.read()
        
        return await self.openvoice_client.clone_voice(
            reference_audio=reference_audio,
            target_text=request.text,
            voice_name=profile.name,
            target_language=profile.language,
            speed=request.speed
        )
    
    
    async def clone_voice(
        self, 
        voice_name: str,
        reference_audio: bytes,
        provider: VoiceProvider = VoiceProvider.OPENVOICE,
        language: str = "ja"
    ) -> VoiceProfile:
        """音声クローン実行"""
        
        if provider == VoiceProvider.OPENVOICE:
            if not self.openvoice_client:
                raise Exception("OpenVoiceクライアントが初期化されていません")
            
            # 音声ファイル検証
            validation = await self.openvoice_client.validate_audio_file(reference_audio)
            if not validation['valid']:
                raise ValueError(f"音声ファイルが無効です: {validation.get('error', 'Unknown error')}")
            
            # 参照音声を保存
            storage_dir = Path("/app/storage/voice_clones")
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            audio_file_path = storage_dir / f"{voice_name}_reference.wav"
            async with aiofiles.open(audio_file_path, 'wb') as f:
                await f.write(reference_audio)
            
            # プロファイル作成
            profile_id = f"openvoice_cloned_{voice_name}"
            profile = VoiceProfile(
                id=profile_id,
                name=f"Cloned: {voice_name}",
                provider=VoiceProvider.OPENVOICE,
                voice_type=VoiceType.CLONED,
                language=language,
                voice_file_path=str(audio_file_path),
                metadata={
                    "clone_date": "now",
                    "validation": validation,
                    "custom_clone": True
                }
            )
            
            self._voice_profiles[profile_id] = profile
            return profile
            
        
        else:
            raise ValueError(f"サポートされていないクローンプロバイダー: {provider}")
    
    async def get_voice_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """音声プロファイルを取得"""
        return self._voice_profiles.get(profile_id)
    
    async def reload_profiles(self) -> Dict[str, Any]:
        """音声プロファイルを再読み込み"""
        result = {"status": "success", "reloaded": {}}
        
        try:
            # プロファイルキャッシュをクリア
            self._voice_profiles.clear()
            
            # 各プロバイダーのプロファイルを再読み込み
            await self._load_voicevox_profiles()
            voicevox_count = len([p for p in self._voice_profiles.values() 
                                if p.provider == VoiceProvider.VOICEVOX])
            result["reloaded"]["voicevox"] = voicevox_count
            
            await self._load_openvoice_profiles()
            openvoice_count = len([p for p in self._voice_profiles.values() 
                                 if p.provider == VoiceProvider.OPENVOICE])
            result["reloaded"]["openvoice"] = openvoice_count
            
            
            result["total_profiles"] = len(self._voice_profiles)
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        health = {
            "service": "healthy",
            "providers": {}
        }
        
        # VOICEVOX
        if self.voicevox_client:
            try:
                vx_health = await self.voicevox_client.health_check()
                health["providers"]["voicevox"] = vx_health
            except Exception as e:
                health["providers"]["voicevox"] = {"status": "error", "error": str(e)}
        
        # OpenVoice
        if self.openvoice_client:
            try:
                ov_health = await self.openvoice_client.health_check()
                health["providers"]["openvoice"] = ov_health
            except Exception as e:
                health["providers"]["openvoice"] = {"status": "error", "error": str(e)}
        
        
        # 全体ステータス
        provider_statuses = [p.get('status') for p in health["providers"].values()]
        if not provider_statuses or all(s in ['error', 'unhealthy'] for s in provider_statuses):
            health["service"] = "degraded"
        
        return health


# グローバルサービスインスタンス
_unified_service: Optional[UnifiedVoiceService] = None

async def get_unified_voice_service() -> UnifiedVoiceService:
    """統合音声サービスを取得"""
    global _unified_service
    
    if _unified_service is None:
        _unified_service = UnifiedVoiceService()
        await _unified_service.initialize()
    
    return _unified_service