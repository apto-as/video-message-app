"""
統合音声サービス
VOICEVOXとQwen3-TTSを統一インターフェースで管理
"""

import asyncio
import os
import re
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

from .voicevox_client import VOICEVOXClient, get_voicevox_client
from .qwen_tts_client import Qwen3TTSClient, get_qwen_tts_client
from .prosody_adjuster import (
    ProsodyAdjuster,
    ProsodyConfig,
    get_prosody_adjuster,
    get_emotion_config,
)

class VoiceProvider(str, Enum):
    """音声プロバイダー"""
    VOICEVOX = "voicevox"
    QWEN_TTS = "qwen3-tts"
    VOICE_CLONE = "voice-clone"
    # Legacy alias for backward compatibility (deprecated)
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
            # "openvoice" / "voice-clone" リクエストをqwen3-ttsにマッピング（後方互換性）
            if provider in (VoiceProvider.OPENVOICE, VoiceProvider.VOICE_CLONE):
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
            elif profile.provider in (VoiceProvider.QWEN_TTS, VoiceProvider.OPENVOICE, VoiceProvider.VOICE_CLONE):
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

    @staticmethod
    def _split_sentences(text: str) -> list:
        """
        日本語テキストを文単位に分割する。

        区切り文字: 。！？\\n
        区切り文字は直前の文に含める。

        Args:
            text: 入力テキスト

        Returns:
            文のリスト（空文字列は除外）
        """
        # 区切り文字の直後で分割（区切り文字は前の文に含める）
        parts = re.split(r'(?<=[。！？\n])', text)
        # 空文字列を除去し、前後の空白をトリム
        sentences = [s.strip() for s in parts if s.strip()]
        return sentences

    async def _synthesize_qwen_tts(self, request: VoiceSynthesisRequest) -> bytes:
        """
        Qwen3-TTS音声合成

        処理フロー:
        1. テキストを文単位に分割
        2. 各文をQwen3-TTS（speed=1.0）で合成（生音声取得）
        3. 複数文の場合は無音で連結
        4. 感情プリセットをProsodyConfigにマージ
        5. ProsodyAdjusterで最終調整（pitch/speed/volume）
        """
        if not self.qwen_tts_client:
            raise Exception("Qwen3-TTSクライアントが初期化されていません")

        profile = request.voice_profile

        # --- Step 1: ProsodyConfig構築 (範囲をクランプ) ---
        clamped_speed = max(0.5, min(2.0, request.speed))
        clamped_pitch = max(-12.0, min(12.0, request.pitch))
        clamped_pause = max(0.0, min(2.0, request.pause_duration))
        prosody_config = ProsodyConfig(
            speed_rate=clamped_speed,
            pitch_shift=clamped_pitch,
            volume_db=self._volume_to_db(request.volume),
            pause_duration=clamped_pause,
        )

        # --- Step 2: 感情プリセット解決 ---
        if request.emotion and request.emotion != "neutral":
            prosody_config = get_emotion_config(request.emotion, prosody_config)
            logger.info(f"感情プリセット '{request.emotion}' を適用しました")

        # --- Step 3: 文分割 ---
        sentences = self._split_sentences(request.text)
        logger.info(f"テキスト分割: {len(sentences)}文")

        # --- Step 4: 各文をQwen3-TTSで合成（speed=1.0で生音声取得） ---
        try:
            if len(sentences) <= 1:
                # 単文: 分割オーバーヘッドなし
                raw_audio = await self.qwen_tts_client.synthesize_with_clone(
                    text=request.text,
                    profile_id=profile.id,
                    language=profile.language,
                    speed=1.0,  # 生音声（Prosodyで後から調整）
                )
            else:
                # 複数文: 各文を個別合成して連結
                audio_segments = []
                for i, sentence in enumerate(sentences):
                    logger.debug(f"文 {i + 1}/{len(sentences)} 合成中: '{sentence[:30]}...'")
                    segment = await self.qwen_tts_client.synthesize_with_clone(
                        text=sentence,
                        profile_id=profile.id,
                        language=profile.language,
                        speed=1.0,
                    )
                    audio_segments.append(segment)

                # 無音で連結（デフォルト0.3秒、pause_durationで調整可能）
                silence_sec = request.pause_duration if request.pause_duration > 0 else 0.3
                raw_audio = ProsodyAdjuster.concatenate_with_silence(
                    audio_segments=audio_segments,
                    silence_duration=silence_sec,
                    sample_rate=24000,
                )
                logger.info(
                    f"文連結完了: {len(audio_segments)}セグメント, "
                    f"無音{silence_sec:.2f}秒"
                )

        except Exception as e:
            logger.error(f"Qwen3-TTS合成エラー: {e}")
            raise

        # --- Step 5: Prosody調整（pitch/speed/volume） ---
        needs_prosody = (
            prosody_config.pitch_shift != 0.0
            or prosody_config.speed_rate != 1.0
            or prosody_config.volume_db != 0.0
            or (len(sentences) <= 1 and prosody_config.pause_duration > 0.0)
        )

        if needs_prosody:
            try:
                adjuster = get_prosody_adjuster()
                # 単文でpause_durationが設定済みの場合はProsodyAdjusterに任せる
                # 複数文の場合はconcatenate_with_silenceで既に処理済みなので
                # pause_durationは0にリセット
                config_for_adjust = ProsodyConfig(
                    speed_rate=prosody_config.speed_rate,
                    pitch_shift=prosody_config.pitch_shift,
                    volume_db=prosody_config.volume_db,
                    pause_duration=prosody_config.pause_duration if len(sentences) <= 1 else 0.0,
                    preserve_formants=prosody_config.preserve_formants,
                )
                result = adjuster.adjust_prosody(raw_audio, config_for_adjust)

                if result.success and result.audio_data:
                    logger.info(
                        f"Prosody調整適用: {result.adjustments_applied}, "
                        f"処理時間={result.processing_time:.3f}s"
                    )
                    return result.audio_data
                else:
                    logger.warning(
                        f"Prosody調整失敗（生音声を返します）: {result.error_message}"
                    )
                    return raw_audio

            except Exception as e:
                logger.warning(f"Prosody調整例外（生音声を返します）: {e}")
                return raw_audio

        return raw_audio

    @staticmethod
    def _volume_to_db(volume: float) -> float:
        """
        音量倍率 (0.0-2.0) をdB値に変換する。

        volume=1.0 -> 0.0dB (変化なし)
        volume=2.0 -> +6.02dB
        volume=0.5 -> -6.02dB
        volume=0.0 -> -20.0dB (最小値)

        Args:
            volume: 音量倍率

        Returns:
            dB値
        """
        import math
        if volume <= 0.0:
            return -20.0
        if volume == 1.0:
            return 0.0
        db = 20.0 * math.log10(volume)
        return max(-20.0, min(20.0, db))

    async def clone_voice(
        self,
        voice_name: str,
        reference_audio: bytes,
        provider: VoiceProvider = VoiceProvider.QWEN_TTS,
        language: str = "ja"
    ) -> VoiceProfile:
        """音声クローン実行"""

        if provider in (VoiceProvider.QWEN_TTS, VoiceProvider.OPENVOICE, VoiceProvider.VOICE_CLONE):
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
