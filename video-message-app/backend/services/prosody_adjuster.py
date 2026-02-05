"""
Prosody調整エンジン
音声のイントネーション、速度、アクセント、ポーズを高度に制御する
"""

import io
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ProsodyConfig(BaseModel):
    """Prosody調整パラメータ"""
    pitch_shift: float = Field(
        default=0.0,
        ge=-12.0,
        le=12.0,
        description="ピッチシフト (semitones): -12〜+12 (±1オクターブ)"
    )
    speed_rate: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="速度倍率: 0.5x (50%遅い) 〜 2.0x (2倍速)"
    )
    volume_db: float = Field(
        default=0.0,
        ge=-20.0,
        le=20.0,
        description="音量調整 (dB): -20dB (静か) 〜 +20dB (大きい)"
    )
    pause_duration: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="文末ポーズ追加 (秒): 0〜2秒"
    )
    preserve_formants: bool = Field(
        default=True,
        description="フォルマント保持（自然な声質維持）"
    )

    @validator('pitch_shift')
    def validate_pitch_shift(cls, v):
        """ピッチシフトの妥当性検証"""
        if abs(v) > 12:
            raise ValueError("ピッチシフトは±12 semitones以内でなければなりません")
        return v

    @validator('speed_rate')
    def validate_speed_rate(cls, v):
        """速度倍率の妥当性検証"""
        if v < 0.5 or v > 2.0:
            raise ValueError("速度倍率は0.5x〜2.0xの範囲でなければなりません")
        return v


class ProsodyAdjustmentResult(BaseModel):
    """Prosody調整結果"""
    success: bool
    audio_data: Optional[bytes] = None
    sample_rate: int
    duration_original: float
    duration_adjusted: float
    adjustments_applied: Dict[str, Any]
    processing_time: float
    error_message: Optional[str] = None


# Emotion presets: 感情に応じたProsodyパラメータ
EMOTION_PRESETS: Dict[str, Dict[str, float]] = {
    "neutral": {"speed": 1.0, "pitch": 0.0, "volume_db": 0.0},
    "happy": {"speed": 1.1, "pitch": 2.0, "volume_db": 2.0},
    "sad": {"speed": 0.85, "pitch": -1.5, "volume_db": -3.0},
    "angry": {"speed": 1.15, "pitch": 1.0, "volume_db": 4.0},
    "excited": {"speed": 1.25, "pitch": 3.0, "volume_db": 3.0},
}


def get_emotion_config(emotion: str, base_config: ProsodyConfig) -> ProsodyConfig:
    """
    感情プリセットをベースConfig にマージする。

    - speed: ベース値にプリセット値を乗算
    - pitch: ベース値にプリセット値を加算
    - volume_db: ベース値にプリセット値を加算

    Args:
        emotion: 感情名 (neutral, happy, sad, angry, excited)
        base_config: ユーザーが指定した手動設定

    Returns:
        マージ済みの ProsodyConfig
    """
    preset = EMOTION_PRESETS.get(emotion)
    if preset is None:
        logger.warning(f"未知の感情プリセット '{emotion}', neutralとして扱います")
        return base_config

    # neutral の場合は変更なし
    if emotion == "neutral":
        return base_config

    merged_speed = base_config.speed_rate * preset["speed"]
    merged_pitch = base_config.pitch_shift + preset["pitch"]
    merged_volume = base_config.volume_db + preset["volume_db"]

    # 範囲クランプ
    merged_speed = max(0.5, min(2.0, merged_speed))
    merged_pitch = max(-12.0, min(12.0, merged_pitch))
    merged_volume = max(-20.0, min(20.0, merged_volume))

    logger.info(
        f"感情プリセット '{emotion}' 適用: "
        f"speed {base_config.speed_rate:.2f} -> {merged_speed:.2f}, "
        f"pitch {base_config.pitch_shift:+.1f} -> {merged_pitch:+.1f}, "
        f"volume {base_config.volume_db:+.1f} -> {merged_volume:+.1f}"
    )

    return ProsodyConfig(
        speed_rate=merged_speed,
        pitch_shift=merged_pitch,
        volume_db=merged_volume,
        pause_duration=base_config.pause_duration,
        preserve_formants=base_config.preserve_formants,
    )


class ProsodyAdjuster:
    """
    Prosody調整エンジン

    高性能な音声プロセシング:
    - ピッチシフト: librosa.effects.pitch_shift (高品質)
    - 速度変更: librosa.effects.time_stretch (フォルマント保持)
    - 音量調整: NumPy演算 (高速)
    - ポーズ挿入: サイレンス追加
    """

    def __init__(self):
        self.supported_formats = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
        self.target_sample_rate = 24000  # MuseTalk推奨サンプルレート

    def adjust_prosody(
        self,
        audio_data: bytes,
        config: ProsodyConfig,
        original_format: str = 'wav'
    ) -> ProsodyAdjustmentResult:
        """
        Prosody調整のメイン処理

        Args:
            audio_data: 入力音声データ (bytes)
            config: Prosody調整パラメータ
            original_format: 元音声フォーマット (default: wav)

        Returns:
            ProsodyAdjustmentResult: 調整結果
        """
        import time
        start_time = time.perf_counter()

        try:
            # Step 1: 音声データ読み込み
            audio, sr = self._load_audio(audio_data)
            duration_original = len(audio) / sr

            logger.info(f"元音声: {duration_original:.2f}秒, {sr}Hz, {len(audio)}サンプル")

            # Step 2: Prosody調整処理
            audio_adjusted = audio.copy()
            adjustments = {}

            # ピッチシフト
            if config.pitch_shift != 0.0:
                audio_adjusted = self._apply_pitch_shift(
                    audio_adjusted, sr, config.pitch_shift
                )
                adjustments['pitch_shift'] = f"{config.pitch_shift:+.1f} semitones"

            # 速度調整
            if config.speed_rate != 1.0:
                audio_adjusted = self._apply_time_stretch(
                    audio_adjusted, config.speed_rate
                )
                adjustments['speed_rate'] = f"{config.speed_rate:.2f}x"

            # 音量調整
            if config.volume_db != 0.0:
                audio_adjusted = self._apply_volume_adjustment(
                    audio_adjusted, config.volume_db
                )
                adjustments['volume_db'] = f"{config.volume_db:+.1f} dB"

            # ポーズ挿入
            if config.pause_duration > 0.0:
                audio_adjusted = self._add_pause(
                    audio_adjusted, sr, config.pause_duration
                )
                adjustments['pause_duration'] = f"+{config.pause_duration:.2f}秒"

            duration_adjusted = len(audio_adjusted) / sr

            # Step 3: リサンプリング（必要な場合）
            if sr != self.target_sample_rate:
                audio_adjusted = librosa.resample(
                    audio_adjusted,
                    orig_sr=sr,
                    target_sr=self.target_sample_rate,
                    res_type='kaiser_best'
                )
                sr = self.target_sample_rate
                logger.info(f"リサンプリング: {self.target_sample_rate}Hz")

            # Step 4: 正規化（クリッピング防止）
            audio_adjusted = self._normalize_audio(audio_adjusted)

            # Step 5: WAV形式でエンコード
            audio_bytes = self._encode_audio(audio_adjusted, sr)

            processing_time = time.perf_counter() - start_time

            logger.info(
                f"Prosody調整完了: {duration_original:.2f}s → {duration_adjusted:.2f}s "
                f"({processing_time:.3f}秒で処理)"
            )

            return ProsodyAdjustmentResult(
                success=True,
                audio_data=audio_bytes,
                sample_rate=sr,
                duration_original=duration_original,
                duration_adjusted=duration_adjusted,
                adjustments_applied=adjustments,
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.perf_counter() - start_time
            logger.error(f"Prosody調整エラー: {str(e)}", exc_info=True)

            return ProsodyAdjustmentResult(
                success=False,
                sample_rate=0,
                duration_original=0.0,
                duration_adjusted=0.0,
                adjustments_applied={},
                processing_time=processing_time,
                error_message=str(e)
            )

    def _load_audio(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """
        音声データ読み込み

        Returns:
            (audio, sample_rate): 音声データとサンプルレート
        """
        try:
            # soundfileで読み込み（効率的）
            audio, sr = sf.read(io.BytesIO(audio_data))

            # ステレオ → モノラル変換
            if audio.ndim > 1:
                audio = librosa.to_mono(audio.T)

            return audio, sr

        except Exception as e:
            logger.error(f"音声読み込みエラー: {str(e)}")
            raise ValueError(f"音声データの読み込みに失敗しました: {str(e)}")

    def _apply_pitch_shift(
        self,
        audio: np.ndarray,
        sr: int,
        n_steps: float
    ) -> np.ndarray:
        """
        ピッチシフト適用

        Args:
            audio: 音声データ
            sr: サンプルレート
            n_steps: シフト量 (semitones)

        Returns:
            ピッチシフトされた音声
        """
        try:
            # librosaの高品質ピッチシフト
            audio_shifted = librosa.effects.pitch_shift(
                audio,
                sr=sr,
                n_steps=n_steps,
                res_type='kaiser_best'
            )
            logger.debug(f"ピッチシフト適用: {n_steps:+.1f} semitones")
            return audio_shifted

        except Exception as e:
            logger.warning(f"ピッチシフトエラー: {str(e)}, 元音声を返します")
            return audio

    def _apply_time_stretch(
        self,
        audio: np.ndarray,
        rate: float
    ) -> np.ndarray:
        """
        速度調整（タイムストレッチ）

        Args:
            audio: 音声データ
            rate: 速度倍率 (1.0 = 元速度)

        Returns:
            速度調整された音声
        """
        try:
            # librosaのタイムストレッチ（フォルマント保持）
            audio_stretched = librosa.effects.time_stretch(
                audio,
                rate=rate
            )
            logger.debug(f"速度調整適用: {rate:.2f}x")
            return audio_stretched

        except Exception as e:
            logger.warning(f"速度調整エラー: {str(e)}, 元音声を返します")
            return audio

    def _apply_volume_adjustment(
        self,
        audio: np.ndarray,
        db: float
    ) -> np.ndarray:
        """
        音量調整

        Args:
            audio: 音声データ
            db: 音量変更量 (dB)

        Returns:
            音量調整された音声
        """
        try:
            # dB → 線形ゲイン変換
            gain = 10 ** (db / 20.0)
            audio_adjusted = audio * gain

            logger.debug(f"音量調整適用: {db:+.1f} dB (ゲイン: {gain:.2f}x)")
            return audio_adjusted

        except Exception as e:
            logger.warning(f"音量調整エラー: {str(e)}, 元音声を返します")
            return audio

    def _add_pause(
        self,
        audio: np.ndarray,
        sr: int,
        duration: float
    ) -> np.ndarray:
        """
        文末にポーズ（無音）を追加

        Args:
            audio: 音声データ
            sr: サンプルレート
            duration: ポーズ長 (秒)

        Returns:
            ポーズ追加された音声
        """
        try:
            # 無音サンプル数計算
            silence_samples = int(sr * duration)
            silence = np.zeros(silence_samples, dtype=audio.dtype)

            # 音声の末尾に無音を追加
            audio_with_pause = np.concatenate([audio, silence])

            logger.debug(f"ポーズ追加: {duration:.2f}秒 ({silence_samples}サンプル)")
            return audio_with_pause

        except Exception as e:
            logger.warning(f"ポーズ追加エラー: {str(e)}, 元音声を返します")
            return audio

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        音声正規化（クリッピング防止）

        Args:
            audio: 音声データ

        Returns:
            正規化された音声
        """
        try:
            # ピークレベル検出
            peak = np.abs(audio).max()

            # クリッピング防止（0.95倍にスケール）
            if peak > 0.95:
                audio = audio * (0.95 / peak)
                logger.debug(f"正規化実施: ピーク {peak:.3f} → 0.95")

            return audio

        except Exception as e:
            logger.warning(f"正規化エラー: {str(e)}, 元音声を返します")
            return audio

    def _encode_audio(self, audio: np.ndarray, sr: int) -> bytes:
        """
        音声をWAV形式でエンコード

        Args:
            audio: 音声データ
            sr: サンプルレート

        Returns:
            WAVバイナリデータ
        """
        try:
            buffer = io.BytesIO()
            sf.write(buffer, audio, sr, format='WAV', subtype='PCM_16')
            buffer.seek(0)
            return buffer.read()

        except Exception as e:
            logger.error(f"音声エンコードエラー: {str(e)}")
            raise ValueError(f"音声のエンコードに失敗しました: {str(e)}")

    @staticmethod
    def concatenate_with_silence(
        audio_segments: list,
        silence_duration: float = 0.3,
        sample_rate: int = 24000
    ) -> bytes:
        """
        複数の音声セグメントを無音で連結する。

        境界にはクリック防止の10msフェードイン/フェードアウトを適用。

        Args:
            audio_segments: WAVバイト列のリスト
            silence_duration: セグメント間の無音長 (秒)
            sample_rate: サンプルレート (Hz)

        Returns:
            連結されたWAVバイナリデータ
        """
        if not audio_segments:
            raise ValueError("音声セグメントが空です")

        if len(audio_segments) == 1:
            return audio_segments[0]

        fade_samples = int(sample_rate * 0.01)  # 10ms fade
        silence_samples = int(sample_rate * silence_duration)
        silence = np.zeros(silence_samples, dtype=np.float32)

        combined_parts = []

        for i, segment_bytes in enumerate(audio_segments):
            try:
                audio, sr = sf.read(io.BytesIO(segment_bytes))

                # ステレオ -> モノラル
                if audio.ndim > 1:
                    audio = librosa.to_mono(audio.T)

                # リサンプル（サンプルレートが異なる場合）
                if sr != sample_rate:
                    audio = librosa.resample(
                        audio, orig_sr=sr, target_sr=sample_rate, res_type='kaiser_best'
                    )

                audio = audio.astype(np.float32)

                # フェードアウト（末尾）: 最後のセグメント以外
                if i < len(audio_segments) - 1 and len(audio) > fade_samples:
                    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
                    audio[-fade_samples:] *= fade_out

                # フェードイン（先頭）: 最初のセグメント以外
                if i > 0 and len(audio) > fade_samples:
                    fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
                    audio[:fade_samples] *= fade_in

                combined_parts.append(audio)

                # セグメント間に無音を挿入（最後のセグメントの後は不要）
                if i < len(audio_segments) - 1:
                    combined_parts.append(silence.copy())

            except Exception as e:
                logger.warning(f"セグメント {i} の処理エラー: {e}, スキップします")
                continue

        if not combined_parts:
            raise ValueError("有効な音声セグメントがありません")

        combined_audio = np.concatenate(combined_parts)

        # クリッピング防止
        peak = np.abs(combined_audio).max()
        if peak > 0.95:
            combined_audio = combined_audio * (0.95 / peak)

        # WAVエンコード
        buffer = io.BytesIO()
        sf.write(buffer, combined_audio, sample_rate, format='WAV', subtype='PCM_16')
        buffer.seek(0)

        logger.info(
            f"音声連結完了: {len(audio_segments)}セグメント, "
            f"無音{silence_duration:.2f}s, "
            f"合計{len(combined_audio) / sample_rate:.2f}s"
        )

        return buffer.read()

    def validate_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        音声データの妥当性検証

        Args:
            audio_data: 音声データ (bytes)

        Returns:
            検証結果
        """
        try:
            audio, sr = self._load_audio(audio_data)
            duration = len(audio) / sr

            return {
                'valid': True,
                'sample_rate': sr,
                'duration': duration,
                'samples': len(audio),
                'channels': 1 if audio.ndim == 1 else audio.shape[1],
                'peak_amplitude': float(np.abs(audio).max()),
                'rms_amplitude': float(np.sqrt(np.mean(audio**2)))
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }


# グローバルインスタンス
_prosody_adjuster: Optional[ProsodyAdjuster] = None


def get_prosody_adjuster() -> ProsodyAdjuster:
    """Prosody調整サービスのシングルトンインスタンスを取得"""
    global _prosody_adjuster

    if _prosody_adjuster is None:
        _prosody_adjuster = ProsodyAdjuster()

    return _prosody_adjuster
