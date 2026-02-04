"""
統合音声サービス
VOICEVOXとQwen3-TTSを統一インターフェースで管理
"""

import asyncio
import os
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

from .voicevox_client import VOICEVOXClient, get_voicevox_client
from .qwen_tts_client import Qwen3TTSClient, get_qwen_tts_client

class VoiceProvider(str, Enum):
    """音声プロバイダー"""
    VOICEVOX = "voicevox"
    QWEN_TTS = "qwen3-tts"
    # Legacy alias for backward compatibility
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
    intonation: float = Field(default=1.0, ge=0.0, le=2.0)
    emotion: str = "neutral"
    pause_duration: float = Field(default=0.0, ge=0.0, le=3.0, description="文末の無音ポーズ長（秒）")

class UnifiedVoiceService:
    """統合音声サービス"""

    def __init__(self):
        self.voicevox_client: Optional[VOICEVOXClient] = None
        self.qwen_tts_client: Optional[Qwen3TTSClient] = None
        self._voice_profiles: Dict[str, VoiceProfile] = {}

    async def initialize(self):
        """サービス初期化"""
        try:
            # VOICEVOXクライアント初期化
            try:
                self.voicevox_client = await get_voicevox_client()
                await self._load_voicevox_profiles()
            except Exception as e:
                logger.warning(f"VOICEVOX初期化警告: {e}")

            # Qwen3-TTSクライアント初期化
            try:
                self.qwen_tts_client = get_qwen_tts_client()
                await self._load_qwen_tts_profiles()
            except Exception as e:
                logger.warning(f"Qwen3-TTS初期化警告: {e}")

        except Exception as e:
            raise Exception(f"統合音声サービス初期化エラー: {e}")

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
            logger.warning(f"VOICEVOXプロファイル読み込みエラー: {e}")

    async def _load_qwen_tts_profiles(self):
        """Qwen3-TTSプロファイル読み込み"""
        if not self.qwen_tts_client:
            return

        try:
            if not await self.qwen_tts_client.check_service_health():
                logger.warning("Qwen3-TTSサービスが利用不可、プロファイル読み込みスキップ")
                return

            profiles = await self.qwen_tts_client.list_profiles()

            for profile_data in profiles:
                profile_id = profile_data.get("id", "")
                if profile_data.get("status") == "ready":
                    profile = VoiceProfile(
                        id=profile_id,
                        name=profile_data.get("name", profile_id),
                        provider=VoiceProvider.QWEN_TTS,
                        voice_type=VoiceType.CLONED,
                        language=profile_data.get("language", "ja"),
                        metadata={
                            "description": profile_data.get("description"),
                            "sample_count": profile_data.get("sample_count", 0),
                            "created_at": profile_data.get("created_at"),
                            "engine": profile_data.get("engine", "qwen3-tts"),
                        }
                    )
                    self._voice_profiles[profile_id] = profile

        except Exception as e:
            logger.warning(f"Qwen3-TTSプロファイル読み込みエラー: {e}")


    async def get_available_voices(
        self,
        provider: Optional[VoiceProvider] = None,
        voice_type: Optional[VoiceType] = None,
        language: Optional[str] = None
    ) -> List[VoiceProfile]:
        """利用可能な音声一覧を取得"""

        voices = list(self._voice_profiles.values())

        if provider:
            # "openvoice" リクエストをqwen3-ttsにマッピング（後方互換性）
            if provider == VoiceProvider.OPENVOICE:
                provider = VoiceProvider.QWEN_TTS
            voices = [v for v in voices if v.provider == provider]
        if voice_type:
            voices = [v for v in voices if v.voice_type == voice_type]
        if language:
            voices = [v for v in voices if v.language == language]

        def sort_key(voice):
            provider_order = {
                VoiceProvider.VOICEVOX: 0,
                VoiceProvider.QWEN_TTS: 1
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
            elif profile.provider in (VoiceProvider.QWEN_TTS, VoiceProvider.OPENVOICE):
                return await self._synthesize_qwen_tts(request)
            else:
                raise ValueError(f"サポートされていないプロバイダー: {profile.provider}")

        except Exception as e:
            raise Exception(f"音声合成エラー ({profile.provider}): {e}")

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
            intonation_scale=request.intonation,
            volume_scale=request.volume,
            pause_length=request.pause_duration
        )

    async def _synthesize_qwen_tts(self, request: VoiceSynthesisRequest) -> bytes:
        """Qwen3-TTS音声合成"""
        if not self.qwen_tts_client:
            raise Exception("Qwen3-TTSクライアントが初期化されていません")

        profile = request.voice_profile

        return await self.qwen_tts_client.synthesize_with_clone(
            text=request.text,
            profile_id=profile.id,
            language=profile.language,
            speed=request.speed,
        )

    async def clone_voice(
        self,
        voice_name: str,
        reference_audio: bytes,
        provider: VoiceProvider = VoiceProvider.QWEN_TTS,
        language: str = "ja"
    ) -> VoiceProfile:
        """音声クローン実行"""

        if provider in (VoiceProvider.QWEN_TTS, VoiceProvider.OPENVOICE):
            if not self.qwen_tts_client:
                raise Exception("Qwen3-TTSクライアントが初期化されていません")

            result = await self.qwen_tts_client.create_voice_clone(
                name=voice_name,
                audio_files=[reference_audio],
                language=language,
            )

            if not result.get("success"):
                raise ValueError(f"音声クローン失敗: {result.get('error', 'Unknown error')}")

            profile_id = result.get("voice_profile_id", f"qwen3tts_{voice_name}")
            profile = VoiceProfile(
                id=profile_id,
                name=f"Cloned: {voice_name}",
                provider=VoiceProvider.QWEN_TTS,
                voice_type=VoiceType.CLONED,
                language=language,
                metadata={"engine": "qwen3-tts"}
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
            self._voice_profiles.clear()

            await self._load_voicevox_profiles()
            voicevox_count = len([p for p in self._voice_profiles.values()
                                if p.provider == VoiceProvider.VOICEVOX])
            result["reloaded"]["voicevox"] = voicevox_count

            await self._load_qwen_tts_profiles()
            qwen_count = len([p for p in self._voice_profiles.values()
                             if p.provider == VoiceProvider.QWEN_TTS])
            result["reloaded"]["qwen3-tts"] = qwen_count

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

        # Qwen3-TTS
        if self.qwen_tts_client:
            try:
                is_healthy = await self.qwen_tts_client.check_service_health()
                health["providers"]["qwen3-tts"] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "available": is_healthy
                }
            except Exception as e:
                health["providers"]["qwen3-tts"] = {"status": "error", "error": str(e)}

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
