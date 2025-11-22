"""
Prosody Parameter Validator - 音声調整パラメータの検証
ピッチ、速度、音量、ポーズのパラメータを厳格に検証
"""

import logging
import math
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProsodyValidator:
    """
    Prosody（韻律）パラメータの包括的な検証
    NaN/Inf値の検出、範囲制限、音響工学的妥当性の検証
    """

    # === ピッチシフト制限 ===
    MIN_PITCH_SHIFT = -12  # semitones（半音階）
    MAX_PITCH_SHIFT = 12
    # 推奨範囲: ±3 semitones（自然な音程変化）
    RECOMMENDED_PITCH_SHIFT = (-3, 3)

    # === 速度制限 ===
    MIN_SPEED = 0.5  # 0.5倍速（半分の速度）
    MAX_SPEED = 2.0  # 2倍速
    # 推奨範囲: 0.8x - 1.2x（自然な速度変化）
    RECOMMENDED_SPEED = (0.8, 1.2)

    # === 音量制限（dB） ===
    MIN_VOLUME_DB = -20  # -20dB（音量減少）
    MAX_VOLUME_DB = 20   # +20dB（音量増加）
    # 推奨範囲: ±6dB（安全な音量変化）
    RECOMMENDED_VOLUME_DB = (-6, 6)

    # === ポーズ制限（秒） ===
    MIN_PAUSE = 0.0  # ポーズなし
    MAX_PAUSE = 2.0  # 2秒
    # 推奨範囲: 0 - 0.5秒（自然なポーズ）
    RECOMMENDED_PAUSE = (0.0, 0.5)

    # === 音量リニア値制限（librosa等で使用） ===
    MIN_VOLUME_LINEAR = 0.0  # 無音
    MAX_VOLUME_LINEAR = 2.0  # 2倍音量

    # === 検証メソッド ===

    @classmethod
    def validate_pitch(cls, pitch: float, strict: bool = False) -> Tuple[bool, str]:
        """
        ピッチシフト検証

        Args:
            pitch: ピッチシフト量（semitones）
            strict: Trueの場合、推奨範囲を超えたら警告

        Returns:
            (is_valid, error_message)
        """
        # NaN/Inf検出
        if not math.isfinite(pitch):
            return False, "ピッチに無効な値が含まれています（NaN/Inf）⚠️ 攻撃の可能性"

        # 範囲検証
        if not (cls.MIN_PITCH_SHIFT <= pitch <= cls.MAX_PITCH_SHIFT):
            return False, f"ピッチシフトは{cls.MIN_PITCH_SHIFT}〜{cls.MAX_PITCH_SHIFT}半音の範囲で指定してください"

        # 推奨範囲外の警告
        if strict and not (cls.RECOMMENDED_PITCH_SHIFT[0] <= pitch <= cls.RECOMMENDED_PITCH_SHIFT[1]):
            logger.warning(
                f"ピッチシフトが推奨範囲外: {pitch} semitones "
                f"（推奨: {cls.RECOMMENDED_PITCH_SHIFT[0]}〜{cls.RECOMMENDED_PITCH_SHIFT[1]}）"
            )

        return True, ""

    @classmethod
    def validate_speed(cls, speed: float, strict: bool = False) -> Tuple[bool, str]:
        """
        速度検証

        Args:
            speed: 速度倍率（1.0 = 通常速度）
            strict: Trueの場合、推奨範囲を超えたら警告

        Returns:
            (is_valid, error_message)
        """
        # NaN/Inf検出
        if not math.isfinite(speed):
            return False, "速度に無効な値が含まれています（NaN/Inf）⚠️ 攻撃の可能性"

        # 範囲検証
        if not (cls.MIN_SPEED <= speed <= cls.MAX_SPEED):
            return False, f"速度は{cls.MIN_SPEED}x〜{cls.MAX_SPEED}xの範囲で指定してください"

        # ゼロ除算防止
        if speed <= 0:
            return False, "速度は正の値である必要があります"

        # 推奨範囲外の警告
        if strict and not (cls.RECOMMENDED_SPEED[0] <= speed <= cls.RECOMMENDED_SPEED[1]):
            logger.warning(
                f"速度が推奨範囲外: {speed}x "
                f"（推奨: {cls.RECOMMENDED_SPEED[0]}x〜{cls.RECOMMENDED_SPEED[1]}x）"
            )

        return True, ""

    @classmethod
    def validate_volume_db(cls, volume_db: float, strict: bool = False) -> Tuple[bool, str]:
        """
        音量検証（dB単位）

        Args:
            volume_db: 音量変化量（dB）
            strict: Trueの場合、推奨範囲を超えたら警告

        Returns:
            (is_valid, error_message)
        """
        # NaN/Inf検出
        if not math.isfinite(volume_db):
            return False, "音量に無効な値が含まれています（NaN/Inf）⚠️ 攻撃の可能性"

        # 範囲検証
        if not (cls.MIN_VOLUME_DB <= volume_db <= cls.MAX_VOLUME_DB):
            return False, f"音量は{cls.MIN_VOLUME_DB}〜{cls.MAX_VOLUME_DB}dBの範囲で指定してください"

        # 推奨範囲外の警告
        if strict and not (cls.RECOMMENDED_VOLUME_DB[0] <= volume_db <= cls.RECOMMENDED_VOLUME_DB[1]):
            logger.warning(
                f"音量が推奨範囲外: {volume_db}dB "
                f"（推奨: {cls.RECOMMENDED_VOLUME_DB[0]}〜{cls.RECOMMENDED_VOLUME_DB[1]}dB）"
            )

        return True, ""

    @classmethod
    def validate_volume_linear(cls, volume: float) -> Tuple[bool, str]:
        """
        音量検証（リニア値: 0.0-2.0）

        Args:
            volume: 音量倍率（1.0 = 通常音量）

        Returns:
            (is_valid, error_message)
        """
        # NaN/Inf検出
        if not math.isfinite(volume):
            return False, "音量に無効な値が含まれています（NaN/Inf）⚠️ 攻撃の可能性"

        # 範囲検証
        if not (cls.MIN_VOLUME_LINEAR <= volume <= cls.MAX_VOLUME_LINEAR):
            return False, f"音量は{cls.MIN_VOLUME_LINEAR}〜{cls.MAX_VOLUME_LINEAR}の範囲で指定してください"

        # 負の値チェック
        if volume < 0:
            return False, "音量は0以上である必要があります"

        return True, ""

    @classmethod
    def validate_pause(cls, pause_seconds: float, strict: bool = False) -> Tuple[bool, str]:
        """
        ポーズ検証

        Args:
            pause_seconds: ポーズの長さ（秒）
            strict: Trueの場合、推奨範囲を超えたら警告

        Returns:
            (is_valid, error_message)
        """
        # NaN/Inf検出
        if not math.isfinite(pause_seconds):
            return False, "ポーズに無効な値が含まれています（NaN/Inf）⚠️ 攻撃の可能性"

        # 範囲検証
        if not (cls.MIN_PAUSE <= pause_seconds <= cls.MAX_PAUSE):
            return False, f"ポーズは{cls.MIN_PAUSE}〜{cls.MAX_PAUSE}秒の範囲で指定してください"

        # 負の値チェック
        if pause_seconds < 0:
            return False, "ポーズは0以上である必要があります"

        # 推奨範囲外の警告
        if strict and not (cls.RECOMMENDED_PAUSE[0] <= pause_seconds <= cls.RECOMMENDED_PAUSE[1]):
            logger.warning(
                f"ポーズが推奨範囲外: {pause_seconds}s "
                f"（推奨: {cls.RECOMMENDED_PAUSE[0]}〜{cls.RECOMMENDED_PAUSE[1]}s）"
            )

        return True, ""

    @classmethod
    def validate_all(
        cls,
        pitch: float = 0.0,
        speed: float = 1.0,
        volume_db: Optional[float] = None,
        volume_linear: Optional[float] = None,
        pause: float = 0.0,
        strict: bool = False
    ) -> Tuple[bool, str]:
        """
        全Prosodyパラメータの一括検証

        Args:
            pitch: ピッチシフト（semitones）
            speed: 速度倍率
            volume_db: 音量変化（dB、省略可能）
            volume_linear: 音量倍率（リニア値、省略可能）
            pause: ポーズ（秒）
            strict: 厳格モード（推奨範囲も検証）

        Returns:
            (is_valid, error_message)
        """
        # ピッチ検証
        is_valid, error_msg = cls.validate_pitch(pitch, strict=strict)
        if not is_valid:
            return False, f"ピッチ: {error_msg}"

        # 速度検証
        is_valid, error_msg = cls.validate_speed(speed, strict=strict)
        if not is_valid:
            return False, f"速度: {error_msg}"

        # 音量検証（dBまたはリニア値）
        if volume_db is not None:
            is_valid, error_msg = cls.validate_volume_db(volume_db, strict=strict)
            if not is_valid:
                return False, f"音量: {error_msg}"

        if volume_linear is not None:
            is_valid, error_msg = cls.validate_volume_linear(volume_linear)
            if not is_valid:
                return False, f"音量: {error_msg}"

        # ポーズ検証
        is_valid, error_msg = cls.validate_pause(pause, strict=strict)
        if not is_valid:
            return False, f"ポーズ: {error_msg}"

        logger.info(
            f"Prosodyパラメータ検証成功: pitch={pitch}, speed={speed}, "
            f"volume_db={volume_db}, volume_linear={volume_linear}, pause={pause}"
        )
        return True, ""

    @classmethod
    def sanitize_prosody_params(
        cls,
        pitch: float = 0.0,
        speed: float = 1.0,
        volume_linear: float = 1.0,
        pause: float = 0.0
    ) -> Dict[str, float]:
        """
        Prosodyパラメータのサニタイズ（クランプ処理）
        無効な値を安全な範囲内に修正

        Args:
            pitch: ピッチシフト
            speed: 速度倍率
            volume_linear: 音量倍率
            pause: ポーズ

        Returns:
            サニタイズされたパラメータ辞書
        """
        sanitized = {}

        # ピッチのクランプ
        if not math.isfinite(pitch):
            sanitized["pitch"] = 0.0
            logger.warning("ピッチに無効な値を検出、0.0にリセット")
        else:
            sanitized["pitch"] = max(cls.MIN_PITCH_SHIFT, min(pitch, cls.MAX_PITCH_SHIFT))

        # 速度のクランプ
        if not math.isfinite(speed) or speed <= 0:
            sanitized["speed"] = 1.0
            logger.warning("速度に無効な値を検出、1.0にリセット")
        else:
            sanitized["speed"] = max(cls.MIN_SPEED, min(speed, cls.MAX_SPEED))

        # 音量のクランプ
        if not math.isfinite(volume_linear) or volume_linear < 0:
            sanitized["volume_linear"] = 1.0
            logger.warning("音量に無効な値を検出、1.0にリセット")
        else:
            sanitized["volume_linear"] = max(cls.MIN_VOLUME_LINEAR, min(volume_linear, cls.MAX_VOLUME_LINEAR))

        # ポーズのクランプ
        if not math.isfinite(pause) or pause < 0:
            sanitized["pause"] = 0.0
            logger.warning("ポーズに無効な値を検出、0.0にリセット")
        else:
            sanitized["pause"] = max(cls.MIN_PAUSE, min(pause, cls.MAX_PAUSE))

        return sanitized

    @classmethod
    def convert_volume_db_to_linear(cls, volume_db: float) -> float:
        """
        dB単位の音量をリニア値に変換

        Args:
            volume_db: 音量（dB）

        Returns:
            音量（リニア値）
        """
        # dB to linear: 10^(dB/20)
        return math.pow(10, volume_db / 20.0)

    @classmethod
    def convert_volume_linear_to_db(cls, volume_linear: float) -> float:
        """
        リニア値の音量をdB単位に変換

        Args:
            volume_linear: 音量（リニア値）

        Returns:
            音量（dB）
        """
        # linear to dB: 20 * log10(linear)
        if volume_linear <= 0:
            return -float('inf')  # 無音
        return 20.0 * math.log10(volume_linear)

    @classmethod
    def get_prosody_summary(
        cls,
        pitch: float = 0.0,
        speed: float = 1.0,
        volume_db: Optional[float] = None,
        volume_linear: Optional[float] = None,
        pause: float = 0.0
    ) -> str:
        """
        Prosodyパラメータの要約文字列を生成

        Args:
            pitch: ピッチシフト
            speed: 速度倍率
            volume_db: 音量（dB）
            volume_linear: 音量（リニア値）
            pause: ポーズ

        Returns:
            要約文字列
        """
        volume_str = ""
        if volume_db is not None:
            volume_str = f"Volume: {volume_db:+.1f}dB"
        elif volume_linear is not None:
            volume_str = f"Volume: {volume_linear:.2f}x"

        return (
            f"Prosody[Pitch: {pitch:+.1f} semitones, Speed: {speed:.2f}x, "
            f"{volume_str}, Pause: {pause:.2f}s]"
        )

    @classmethod
    def check_implementation_status(cls) -> Dict[str, bool]:
        """
        Prosody機能の実装状態をチェック
        未実装の機能を使用しようとした場合に警告

        Returns:
            実装状態の辞書
        """
        # TODO: 実際の実装状態に応じて更新
        implementation_status = {
            "pitch_adjustment": False,  # ピッチ調整未実装
            "speed_adjustment": False,  # 速度調整未実装
            "volume_adjustment": False,  # 音量調整未実装
            "pause_insertion": False   # ポーズ挿入未実装
        }
        return implementation_status

    @classmethod
    def validate_with_implementation_check(
        cls,
        pitch: float = 0.0,
        speed: float = 1.0,
        volume_linear: float = 1.0,
        pause: float = 0.0
    ) -> Tuple[bool, str]:
        """
        実装状態を考慮した検証
        未実装の機能が要求された場合はエラー

        Args:
            pitch: ピッチシフト
            speed: 速度倍率
            volume_linear: 音量倍率
            pause: ポーズ

        Returns:
            (is_valid, error_message)
        """
        impl_status = cls.check_implementation_status()

        # パラメータが未実装の機能を使用しようとしているか確認
        if pitch != 0.0 and not impl_status["pitch_adjustment"]:
            return False, "ピッチ調整機能は現在未実装です"

        if speed != 1.0 and not impl_status["speed_adjustment"]:
            return False, "速度調整機能は現在未実装です"

        if volume_linear != 1.0 and not impl_status["volume_adjustment"]:
            return False, "音量調整機能は現在未実装です"

        if pause != 0.0 and not impl_status["pause_insertion"]:
            return False, "ポーズ挿入機能は現在未実装です"

        # 実装済み機能の通常検証
        return cls.validate_all(
            pitch=pitch,
            speed=speed,
            volume_linear=volume_linear,
            pause=pause
        )
