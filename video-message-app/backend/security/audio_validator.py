"""
Audio File Validator - オーディオボム検出とファイル検証
"""

import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from mutagen import File as MutagenFile
import wave

logger = logging.getLogger(__name__)


class AudioValidator:
    """
    音声ファイルの包括的な検証
    オーディオボム攻撃の検出と安全性確保
    """

    # === 制限値定義 ===

    # ファイルサイズ制限（バイト）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB（CRITICAL制限）
    RECOMMENDED_FILE_SIZE = 10 * 1024 * 1024  # 10MB（推奨）
    MIN_FILE_SIZE = 100  # 100バイト（最小）

    # 音声長制限（秒）
    MAX_DURATION = 300.0  # 5分（CRITICAL制限）
    RECOMMENDED_DURATION = 30.0  # 30秒（音声クローン推奨）
    MIN_DURATION = 0.1  # 0.1秒（最小）

    # サンプルレート制限（Hz）
    MIN_SAMPLE_RATE = 8000  # 8kHz
    MAX_SAMPLE_RATE = 48000  # 48kHz
    RECOMMENDED_SAMPLE_RATE = [16000, 22050, 44100, 48000]

    # ビットレート制限（bps）
    MAX_BITRATE = 320000  # 320kbps

    # チャンネル数制限
    VALID_CHANNELS = [1, 2]  # モノラル、ステレオのみ

    # サポートする音声形式
    SUPPORTED_FORMATS = {
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/wave': '.wav',
        'audio/flac': '.flac',
        'audio/mp4': '.m4a',
        'audio/m4a': '.m4a',
        'audio/x-m4a': '.m4a',
        'audio/aac': '.aac'
    }

    SUPPORTED_EXTENSIONS = ['.mp3', '.wav', '.flac', '.m4a', '.mp4', '.aac']

    # === 検証メソッド ===

    @classmethod
    def validate_file_size(cls, file_size: int, strict: bool = False) -> Tuple[bool, str]:
        """
        ファイルサイズ検証

        Args:
            file_size: ファイルサイズ（バイト）
            strict: Trueの場合、推奨サイズを超えたら警告

        Returns:
            (is_valid, error_message)
        """
        if file_size < cls.MIN_FILE_SIZE:
            return False, f"ファイルサイズが小さすぎます（最小{cls.MIN_FILE_SIZE}バイト）"

        if file_size > cls.MAX_FILE_SIZE:
            return False, f"ファイルサイズが大きすぎます（最大{cls.MAX_FILE_SIZE // (1024*1024)}MB）"

        if strict and file_size > cls.RECOMMENDED_FILE_SIZE:
            logger.warning(f"ファイルサイズが推奨値を超過: {file_size / (1024*1024):.2f}MB > {cls.RECOMMENDED_FILE_SIZE / (1024*1024)}MB")

        return True, ""

    @classmethod
    def validate_duration(cls, duration: float, use_case: str = "general") -> Tuple[bool, str]:
        """
        音声長検証

        Args:
            duration: 音声長（秒）
            use_case: "voice_clone" | "synthesis" | "general"

        Returns:
            (is_valid, error_message)
        """
        if duration < cls.MIN_DURATION:
            return False, f"音声が短すぎます（最小{cls.MIN_DURATION}秒）"

        # ユースケース別の最大長
        max_duration = cls.MAX_DURATION
        if use_case == "voice_clone":
            max_duration = cls.RECOMMENDED_DURATION  # 30秒

        if duration > max_duration:
            return False, f"音声が長すぎます（最大{max_duration}秒）"

        return True, ""

    @classmethod
    def validate_sample_rate(cls, sample_rate: int) -> Tuple[bool, str]:
        """
        サンプルレート検証（オーディオボム検出）

        Args:
            sample_rate: サンプルレート（Hz）

        Returns:
            (is_valid, error_message)
        """
        if not (cls.MIN_SAMPLE_RATE <= sample_rate <= cls.MAX_SAMPLE_RATE):
            return False, f"異常なサンプルレート: {sample_rate} Hz（正常範囲: {cls.MIN_SAMPLE_RATE}-{cls.MAX_SAMPLE_RATE} Hz）⚠️ オーディオボムの可能性"

        if sample_rate not in cls.RECOMMENDED_SAMPLE_RATE:
            logger.warning(f"非推奨のサンプルレート: {sample_rate} Hz（推奨: {cls.RECOMMENDED_SAMPLE_RATE}）")

        return True, ""

    @classmethod
    def validate_bitrate(cls, bitrate: int) -> Tuple[bool, str]:
        """
        ビットレート検証（オーディオボム検出）

        Args:
            bitrate: ビットレート（bps）

        Returns:
            (is_valid, error_message)
        """
        if bitrate > cls.MAX_BITRATE:
            return False, f"異常なビットレート: {bitrate} bps（最大: {cls.MAX_BITRATE // 1000} kbps）⚠️ オーディオボムの可能性"

        return True, ""

    @classmethod
    def validate_channels(cls, channels: int) -> Tuple[bool, str]:
        """
        チャンネル数検証（オーディオボム検出）

        Args:
            channels: チャンネル数

        Returns:
            (is_valid, error_message)
        """
        if channels not in cls.VALID_CHANNELS:
            return False, f"異常なチャンネル数: {channels}（許可: モノラル(1) または ステレオ(2)）⚠️ オーディオボムの可能性"

        return True, ""

    @classmethod
    def validate_format(cls, content_type: Optional[str], filename: Optional[str]) -> Tuple[bool, str]:
        """
        ファイル形式検証

        Args:
            content_type: MIMEタイプ
            filename: ファイル名

        Returns:
            (is_valid, error_message)
        """
        # MIMEタイプでの検証
        is_valid_mime = content_type in cls.SUPPORTED_FORMATS if content_type else False

        # ファイル拡張子での補完検証
        is_valid_extension = False
        if filename:
            file_extension = Path(filename).suffix.lower()
            is_valid_extension = file_extension in cls.SUPPORTED_EXTENSIONS

        if not is_valid_mime and not is_valid_extension:
            return False, f"サポートされていないファイル形式です。対応形式: {', '.join(cls.SUPPORTED_EXTENSIONS)}"

        return True, ""

    @classmethod
    def detect_audio_bomb(cls, file_path: Path) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        オーディオボム総合検出
        異常なサンプルレート、ビットレート、チャンネル数を検出

        Args:
            file_path: 音声ファイルパス

        Returns:
            (is_safe, error_message, audio_info)
        """
        try:
            audio = MutagenFile(file_path)
            if audio is None:
                return False, "音声ファイルの解析に失敗しました", None

            # 音声情報抽出
            audio_info = {
                "duration": getattr(audio.info, 'length', 0),
                "sample_rate": getattr(audio.info, 'sample_rate', 0),
                "bitrate": getattr(audio.info, 'bitrate', 0),
                "channels": getattr(audio.info, 'channels', 0)
            }

            # サンプルレート検証
            is_valid, error_msg = cls.validate_sample_rate(audio_info["sample_rate"])
            if not is_valid:
                return False, error_msg, audio_info

            # ビットレート検証（MP3の場合）
            if audio_info["bitrate"] > 0:
                is_valid, error_msg = cls.validate_bitrate(audio_info["bitrate"])
                if not is_valid:
                    return False, error_msg, audio_info

            # チャンネル数検証
            is_valid, error_msg = cls.validate_channels(audio_info["channels"])
            if not is_valid:
                return False, error_msg, audio_info

            return True, "", audio_info

        except Exception as e:
            logger.error(f"オーディオボム検出中にエラー: {e}", exc_info=True)
            return False, f"音声ファイルの検証に失敗しました", None

    @classmethod
    def validate_audio_file_comprehensive(
        cls,
        file_path: Path,
        file_size: int,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        use_case: str = "general",
        strict: bool = False
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        音声ファイルの包括的な検証

        Args:
            file_path: 音声ファイルパス
            file_size: ファイルサイズ（バイト）
            content_type: MIMEタイプ
            filename: ファイル名
            use_case: "voice_clone" | "synthesis" | "general"
            strict: 厳格モード（推奨値も検証）

        Returns:
            (is_valid, error_message, audio_info)
        """
        # 1. ファイルサイズ検証
        is_valid, error_msg = cls.validate_file_size(file_size, strict=strict)
        if not is_valid:
            return False, error_msg, None

        # 2. ファイル形式検証
        is_valid, error_msg = cls.validate_format(content_type, filename)
        if not is_valid:
            return False, error_msg, None

        # 3. オーディオボム検出
        is_safe, error_msg, audio_info = cls.detect_audio_bomb(file_path)
        if not is_safe:
            return False, error_msg, audio_info

        # 4. 音声長検証
        if audio_info:
            duration = audio_info.get("duration", 0)
            is_valid, error_msg = cls.validate_duration(duration, use_case=use_case)
            if not is_valid:
                return False, error_msg, audio_info

        logger.info(f"音声ファイル検証成功: {file_path.name} ({file_size / (1024*1024):.2f}MB, {audio_info.get('duration', 0):.2f}s)")
        return True, "", audio_info

    @classmethod
    def validate_wav_header(cls, file_path: Path) -> Tuple[bool, str]:
        """
        WAVファイルヘッダーの検証（低レベル検証）
        悪意のあるヘッダー改ざんを検出

        Args:
            file_path: WAVファイルパス

        Returns:
            (is_valid, error_message)
        """
        try:
            with wave.open(str(file_path), 'rb') as wav:
                # 基本情報取得
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frame_rate = wav.getframerate()
                num_frames = wav.getnframes()

                # チャンネル数検証
                is_valid, error_msg = cls.validate_channels(channels)
                if not is_valid:
                    return False, error_msg

                # サンプルレート検証
                is_valid, error_msg = cls.validate_sample_rate(frame_rate)
                if not is_valid:
                    return False, error_msg

                # サンプル幅検証（8bit, 16bit, 24bit, 32bitのみ）
                if sample_width not in [1, 2, 3, 4]:
                    return False, f"異常なサンプル幅: {sample_width * 8}bit（許可: 8, 16, 24, 32bit）"

                # 計算上のファイルサイズと実際のサイズの比較
                expected_size = num_frames * channels * sample_width + 44  # WAVヘッダー44バイト
                actual_size = file_path.stat().st_size
                size_diff = abs(actual_size - expected_size)

                # 10%以上の差異がある場合は異常
                if size_diff > expected_size * 0.1:
                    logger.warning(f"WAVファイルサイズの不整合: expected={expected_size}, actual={actual_size}")

            return True, ""

        except wave.Error as e:
            return False, f"WAVファイルの解析に失敗: {str(e)}"
        except Exception as e:
            logger.error(f"WAVヘッダー検証エラー: {e}", exc_info=True)
            return False, "WAVファイルの検証に失敗しました"

    @classmethod
    def check_silence(cls, file_path: Path, max_silence_ratio: float = 0.9) -> Tuple[bool, str]:
        """
        無音区間の検出（悪意のある無音ファイル攻撃）

        Args:
            file_path: 音声ファイルパス
            max_silence_ratio: 許容する無音区間の割合（0.0-1.0）

        Returns:
            (is_valid, error_message)
        """
        # TODO: librosaを使用した無音区間検出実装
        # 現在はスキップ（libraosaの依存関係を追加する必要がある）
        logger.debug(f"無音区間チェック（未実装）: {file_path.name}")
        return True, ""

    @classmethod
    def get_audio_info_summary(cls, audio_info: Optional[Dict[str, Any]]) -> str:
        """
        音声情報の要約文字列を生成

        Args:
            audio_info: 音声情報辞書

        Returns:
            要約文字列
        """
        if not audio_info:
            return "音声情報なし"

        return (
            f"Duration: {audio_info.get('duration', 0):.2f}s, "
            f"Sample Rate: {audio_info.get('sample_rate', 0)}Hz, "
            f"Channels: {audio_info.get('channels', 0)}, "
            f"Bitrate: {audio_info.get('bitrate', 0) // 1000}kbps"
        )
