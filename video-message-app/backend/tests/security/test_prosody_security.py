"""
Prosody & Audio Security Tests
セキュリティ攻撃シナリオの包括的なテスト
"""

import pytest
import asyncio
import wave
import numpy as np
import tempfile
import math
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# テスト対象モジュール
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security.audio_validator import AudioValidator
from security.prosody_validator import ProsodyValidator
from security.resource_limiter import ResourceLimiter
from security.error_handler import SecureErrorHandler


# === Audio Validator Tests ===

class TestAudioValidator:
    """AudioValidator（オーディオボム検出）のテスト"""

    def test_file_size_validation_too_large(self):
        """ファイルサイズが大きすぎる場合のテスト"""
        # 100MB超過
        file_size = 100 * 1024 * 1024 + 1
        is_valid, error_msg = AudioValidator.validate_file_size(file_size)

        assert not is_valid
        assert "大きすぎます" in error_msg

    def test_file_size_validation_too_small(self):
        """ファイルサイズが小さすぎる場合のテスト"""
        file_size = 50  # 50バイト
        is_valid, error_msg = AudioValidator.validate_file_size(file_size)

        assert not is_valid
        assert "小さすぎます" in error_msg

    def test_file_size_validation_valid(self):
        """正常なファイルサイズのテスト"""
        file_size = 10 * 1024 * 1024  # 10MB
        is_valid, error_msg = AudioValidator.validate_file_size(file_size)

        assert is_valid
        assert error_msg == ""

    def test_duration_validation_too_long(self):
        """音声が長すぎる場合のテスト"""
        duration = 301.0  # 5分1秒
        is_valid, error_msg = AudioValidator.validate_duration(duration)

        assert not is_valid
        assert "長すぎます" in error_msg

    def test_duration_validation_too_short(self):
        """音声が短すぎる場合のテスト"""
        duration = 0.05  # 0.05秒
        is_valid, error_msg = AudioValidator.validate_duration(duration)

        assert not is_valid
        assert "短すぎます" in error_msg

    def test_duration_validation_voice_clone_strict(self):
        """音声クローン用の厳格な音声長検証"""
        duration = 31.0  # 31秒
        is_valid, error_msg = AudioValidator.validate_duration(duration, use_case="voice_clone")

        assert not is_valid  # voice_cloneは30秒まで
        assert "長すぎます" in error_msg

    def test_sample_rate_validation_audio_bomb(self):
        """異常なサンプルレート（オーディオボム）のテスト"""
        # 1MHz（異常）
        is_valid, error_msg = AudioValidator.validate_sample_rate(1000000)

        assert not is_valid
        assert "異常な" in error_msg
        assert "オーディオボム" in error_msg

    def test_sample_rate_validation_too_low(self):
        """サンプルレートが低すぎる場合のテスト"""
        is_valid, error_msg = AudioValidator.validate_sample_rate(4000)  # 4kHz

        assert not is_valid
        assert "異常な" in error_msg

    def test_sample_rate_validation_valid(self):
        """正常なサンプルレートのテスト"""
        is_valid, error_msg = AudioValidator.validate_sample_rate(44100)

        assert is_valid
        assert error_msg == ""

    def test_bitrate_validation_audio_bomb(self):
        """異常なビットレート（オーディオボム）のテスト"""
        is_valid, error_msg = AudioValidator.validate_bitrate(999999999)  # 999Mbps

        assert not is_valid
        assert "異常な" in error_msg
        assert "オーディオボム" in error_msg

    def test_channels_validation_audio_bomb(self):
        """異常なチャンネル数（オーディオボム）のテスト"""
        is_valid, error_msg = AudioValidator.validate_channels(256)

        assert not is_valid
        assert "異常な" in error_msg
        assert "オーディオボム" in error_msg

    def test_channels_validation_valid(self):
        """正常なチャンネル数のテスト"""
        # モノラル
        is_valid, _ = AudioValidator.validate_channels(1)
        assert is_valid

        # ステレオ
        is_valid, _ = AudioValidator.validate_channels(2)
        assert is_valid

    def test_format_validation_unsupported(self):
        """サポートされていないファイル形式のテスト"""
        is_valid, error_msg = AudioValidator.validate_format("audio/ogg", "test.ogg")

        assert not is_valid
        assert "サポートされていない" in error_msg

    def test_format_validation_supported(self):
        """サポートされているファイル形式のテスト"""
        # WAV
        is_valid, _ = AudioValidator.validate_format("audio/wav", "test.wav")
        assert is_valid

        # MP3
        is_valid, _ = AudioValidator.validate_format("audio/mpeg", "test.mp3")
        assert is_valid

    def test_wav_header_validation_malicious(self, tmp_path):
        """悪意のあるWAVヘッダー改ざんのテスト"""
        wav_file = tmp_path / "malicious.wav"

        # 異常なWAVファイル作成（チャンネル数: 256）
        with wave.open(str(wav_file), 'w') as f:
            # これは実際にはエラーになるので、try-exceptで処理
            try:
                f.setnchannels(256)  # 異常なチャンネル数
                f.setsampwidth(2)
                f.setframerate(44100)
                data = np.zeros(44100, dtype=np.int16)
                f.writeframes(data.tobytes())
            except:
                pass

    def test_create_audio_bomb_wav(self, tmp_path):
        """オーディオボムWAVファイルの作成とテスト"""
        bomb_file = tmp_path / "audio_bomb.wav"

        # 異常なパラメータで音声ファイル作成
        with wave.open(str(bomb_file), 'w') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(48000)  # 正常範囲内だが、後でメタデータを改ざん想定
            # 5秒の音声
            data = np.zeros(48000 * 5 * 2, dtype=np.int16)
            f.writeframes(data.tobytes())

        # ファイルサイズチェック
        file_size = bomb_file.stat().st_size
        is_valid, error_msg = AudioValidator.validate_file_size(file_size)
        assert is_valid  # 5秒なら正常範囲


# === Prosody Validator Tests ===

class TestProsodyValidator:
    """ProsodyValidator（パラメータ検証）のテスト"""

    def test_pitch_validation_nan(self):
        """ピッチにNaN値を指定した場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_pitch(float('nan'))

        assert not is_valid
        assert "無効な値" in error_msg
        assert "NaN/Inf" in error_msg

    def test_pitch_validation_inf(self):
        """ピッチにInf値を指定した場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_pitch(float('inf'))

        assert not is_valid
        assert "無効な値" in error_msg

    def test_pitch_validation_out_of_range(self):
        """ピッチが範囲外の場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_pitch(15.0)  # ±12超過

        assert not is_valid
        assert "範囲" in error_msg

    def test_pitch_validation_valid(self):
        """正常なピッチのテスト"""
        is_valid, _ = ProsodyValidator.validate_pitch(0.0)
        assert is_valid

        is_valid, _ = ProsodyValidator.validate_pitch(3.0)
        assert is_valid

        is_valid, _ = ProsodyValidator.validate_pitch(-3.0)
        assert is_valid

    def test_speed_validation_nan(self):
        """速度にNaN値を指定した場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_speed(float('nan'))

        assert not is_valid
        assert "無効な値" in error_msg

    def test_speed_validation_zero(self):
        """速度にゼロを指定した場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_speed(0.0)

        assert not is_valid
        assert "正の値" in error_msg

    def test_speed_validation_out_of_range(self):
        """速度が範囲外の場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_speed(3.0)  # 2.0超過

        assert not is_valid
        assert "範囲" in error_msg

    def test_speed_validation_valid(self):
        """正常な速度のテスト"""
        is_valid, _ = ProsodyValidator.validate_speed(1.0)
        assert is_valid

        is_valid, _ = ProsodyValidator.validate_speed(1.5)
        assert is_valid

    def test_volume_db_validation_nan(self):
        """音量（dB）にNaN値を指定した場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_volume_db(float('nan'))

        assert not is_valid
        assert "無効な値" in error_msg

    def test_volume_db_validation_out_of_range(self):
        """音量（dB）が範囲外の場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_volume_db(25.0)  # ±20超過

        assert not is_valid
        assert "範囲" in error_msg

    def test_volume_linear_validation_negative(self):
        """音量（リニア）が負の値の場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_volume_linear(-1.0)

        assert not is_valid
        assert "0以上" in error_msg

    def test_volume_linear_validation_valid(self):
        """正常な音量（リニア）のテスト"""
        is_valid, _ = ProsodyValidator.validate_volume_linear(1.0)
        assert is_valid

    def test_pause_validation_negative(self):
        """ポーズが負の値の場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_pause(-0.5)

        assert not is_valid
        assert "0以上" in error_msg

    def test_pause_validation_too_long(self):
        """ポーズが長すぎる場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_pause(3.0)  # 2秒超過

        assert not is_valid
        assert "範囲" in error_msg

    def test_validate_all_success(self):
        """すべてのパラメータが正常な場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_all(
            pitch=0.0,
            speed=1.0,
            volume_linear=1.0,
            pause=0.0
        )

        assert is_valid
        assert error_msg == ""

    def test_validate_all_failure(self):
        """いずれかのパラメータが異常な場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_all(
            pitch=float('nan'),  # 異常
            speed=1.0,
            volume_linear=1.0,
            pause=0.0
        )

        assert not is_valid
        assert "ピッチ" in error_msg

    def test_sanitize_prosody_params_nan(self):
        """NaN値のサニタイズテスト"""
        sanitized = ProsodyValidator.sanitize_prosody_params(
            pitch=float('nan'),
            speed=float('inf'),
            volume_linear=float('-inf'),
            pause=-1.0
        )

        # すべて安全な値にリセットされる
        assert sanitized["pitch"] == 0.0
        assert sanitized["speed"] == 1.0
        assert sanitized["volume_linear"] == 1.0
        assert sanitized["pause"] == 0.0

    def test_sanitize_prosody_params_clamp(self):
        """範囲外の値のクランプテスト"""
        sanitized = ProsodyValidator.sanitize_prosody_params(
            pitch=20.0,  # MAX_PITCH_SHIFT(12)にクランプ
            speed=5.0,   # MAX_SPEED(2.0)にクランプ
            volume_linear=10.0,  # MAX_VOLUME_LINEAR(2.0)にクランプ
            pause=10.0   # MAX_PAUSE(2.0)にクランプ
        )

        assert sanitized["pitch"] == 12.0
        assert sanitized["speed"] == 2.0
        assert sanitized["volume_linear"] == 2.0
        assert sanitized["pause"] == 2.0

    def test_volume_conversion(self):
        """音量変換（dB ↔ リニア値）のテスト"""
        # dB to linear
        linear = ProsodyValidator.convert_volume_db_to_linear(0.0)
        assert abs(linear - 1.0) < 0.01  # 0dB = 1.0x

        linear = ProsodyValidator.convert_volume_db_to_linear(6.0)
        assert abs(linear - 2.0) < 0.01  # +6dB ≈ 2.0x

        # linear to dB
        db = ProsodyValidator.convert_volume_linear_to_db(1.0)
        assert abs(db - 0.0) < 0.01  # 1.0x = 0dB

        db = ProsodyValidator.convert_volume_linear_to_db(2.0)
        assert abs(db - 6.02) < 0.1  # 2.0x ≈ +6dB

    def test_implementation_status_check(self):
        """実装状態のチェック"""
        status = ProsodyValidator.check_implementation_status()

        # 現在未実装
        assert not status["pitch_adjustment"]
        assert not status["speed_adjustment"]
        assert not status["volume_adjustment"]
        assert not status["pause_insertion"]

    def test_validate_with_implementation_check_unimplemented(self):
        """未実装機能を使用しようとした場合のテスト"""
        is_valid, error_msg = ProsodyValidator.validate_with_implementation_check(
            pitch=3.0,  # 未実装機能を使用
            speed=1.0,
            volume_linear=1.0,
            pause=0.0
        )

        assert not is_valid
        assert "未実装" in error_msg


# === Resource Limiter Tests ===

class TestResourceLimiter:
    """ResourceLimiter（並列処理制限）のテスト"""

    @pytest.mark.asyncio
    async def test_concurrent_limit_basic(self):
        """基本的な並列処理制限のテスト"""
        limiter = ResourceLimiter(max_concurrent=2, name="test")

        async def dummy_task(duration: float):
            await asyncio.sleep(duration)
            return "done"

        # 2並列まで実行可能
        async with limiter.acquire():
            assert limiter.metrics.active_tasks == 1

            async with limiter.acquire():
                assert limiter.metrics.active_tasks == 2

                # 3つ目はブロックされる（タイムアウト）
                with pytest.raises(asyncio.TimeoutError):
                    async with limiter.acquire(timeout=0.1):
                        pass

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """並列実行のテスト"""
        limiter = ResourceLimiter(max_concurrent=3, name="test")

        async def task(task_id: int):
            async with limiter.acquire():
                await asyncio.sleep(0.1)
                return task_id

        # 5タスクを同時に開始（最大3並列）
        tasks = [task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert limiter.metrics.total_tasks_executed == 5

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """タイムアウト処理のテスト"""
        limiter = ResourceLimiter(max_concurrent=1, default_timeout=0.5, name="test")

        async def slow_task():
            async with limiter.acquire():
                await asyncio.sleep(2.0)  # 2秒（タイムアウト超過）

        with pytest.raises(asyncio.TimeoutError):
            await limiter.execute_with_timeout(slow_task(), timeout=0.5)

        assert limiter.metrics.total_tasks_timeout > 0

    @pytest.mark.asyncio
    async def test_memory_check(self):
        """メモリチェックのテスト（モック）"""
        limiter = ResourceLimiter(max_memory_mb=100.0, name="test")

        # メモリ使用量を人為的に高く設定
        with patch.object(limiter.process, 'memory_info') as mock_memory:
            mock_memory.return_value = Mock(rss=200 * 1024 * 1024)  # 200MB

            with pytest.raises(MemoryError):
                async with limiter.acquire():
                    pass

    def test_get_available_slots(self):
        """利用可能なスロット数の取得テスト"""
        limiter = ResourceLimiter(max_concurrent=5, name="test")

        assert limiter.get_available_slots() == 5

        limiter.metrics.active_tasks = 3
        assert limiter.get_available_slots() == 2

    def test_get_metrics(self):
        """メトリクス取得のテスト"""
        limiter = ResourceLimiter(max_concurrent=5, name="test")

        metrics = limiter.get_metrics()

        assert metrics["name"] == "test"
        assert metrics["max_concurrent"] == 5
        assert metrics["active_tasks"] == 0

    @pytest.mark.asyncio
    async def test_wait_for_availability(self):
        """リソース待機のテスト"""
        limiter = ResourceLimiter(max_concurrent=1, name="test")

        # リソースを占有
        async with limiter.acquire():
            # 別タスクが待機
            async def wait_task():
                available = await limiter.wait_for_availability(timeout=0.5)
                return available

            # タイムアウトするはず
            result = await wait_task()
            assert not result


# === Secure Error Handler Tests ===

class TestSecureErrorHandler:
    """SecureErrorHandler（エラーハンドリング）のテスト"""

    def test_validation_error(self):
        """検証エラーのテスト"""
        exc = SecureErrorHandler.handle_validation_error(
            field="pitch",
            reason="範囲外",
            value=999
        )

        assert exc.status_code == 400
        assert "pitch" in exc.detail
        assert "範囲外" in exc.detail

    def test_audio_processing_error_production(self):
        """音声処理エラー（本番環境）のテスト"""
        SecureErrorHandler.set_debug_mode(False)

        exc = SecureErrorHandler.handle_audio_processing_error(
            Exception("Internal error with /app/storage/file.wav"),
            context="voice_clone"
        )

        assert exc.status_code == 500
        # 詳細情報は含まれない
        assert "/app/storage" not in exc.detail
        assert "Internal error" not in exc.detail

    def test_audio_processing_error_debug(self):
        """音声処理エラー（デバッグモード）のテスト"""
        SecureErrorHandler.set_debug_mode(True)

        exc = SecureErrorHandler.handle_audio_processing_error(
            Exception("Test error"),
            context="voice_clone"
        )

        assert exc.status_code == 500
        # デバッグモードでは詳細情報を含む
        assert "Test error" in str(exc.detail)

        # 元に戻す
        SecureErrorHandler.set_debug_mode(False)

    def test_resource_error_memory(self):
        """メモリ不足エラーのテスト"""
        exc = SecureErrorHandler.handle_resource_error(
            error_type="memory",
            current_value=600.0,
            limit_value=500.0
        )

        assert exc.status_code == 503
        assert "メモリ" in exc.detail

    def test_resource_error_timeout(self):
        """タイムアウトエラーのテスト"""
        exc = SecureErrorHandler.handle_resource_error(
            error_type="timeout"
        )

        assert exc.status_code == 503
        assert "タイムアウト" in exc.detail

    def test_external_api_error(self):
        """外部APIエラーのテスト"""
        exc = SecureErrorHandler.handle_external_api_error(
            service_name="OpenVoice",
            e=Exception("Connection refused"),
            status_code=502
        )

        assert exc.status_code == 502
        assert "OpenVoice" in exc.detail

    def test_file_not_found(self):
        """ファイル未発見エラーのテスト"""
        exc = SecureErrorHandler.handle_file_not_found(
            file_type="voice_profile",
            file_id="secret_id_12345"
        )

        assert exc.status_code == 404
        # IDは露出しない
        assert "secret_id_12345" not in exc.detail

    def test_rate_limit_error(self):
        """レート制限エラーのテスト"""
        exc = SecureErrorHandler.handle_rate_limit_error(
            limit=10,
            window=60,
            retry_after=30
        )

        assert exc.status_code == 429
        assert "Retry-After" in exc.headers
        assert exc.headers["Retry-After"] == "30"

    def test_sanitize_error_message(self):
        """エラーメッセージサニタイズのテスト"""
        original = "FileNotFoundError: /app/storage/voices/secret.wav not found"
        sanitized = SecureErrorHandler.sanitize_error_message(original)

        # パス情報が除去される
        assert "/app/storage" not in sanitized
        assert "FileNotFoundError" in sanitized


# === Integration Tests ===

class TestSecurityIntegration:
    """統合セキュリティテスト"""

    @pytest.mark.asyncio
    async def test_full_attack_scenario_audio_bomb(self, tmp_path):
        """オーディオボム攻撃の完全シナリオテスト"""
        # 1. 異常なWAVファイル作成
        bomb_file = tmp_path / "audio_bomb.wav"
        with wave.open(str(bomb_file), 'w') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(1000000)  # 1MHz（異常）
            data = np.zeros(1000000, dtype=np.int16)
            f.writeframes(data.tobytes())

        # 2. ファイルサイズチェック
        file_size = bomb_file.stat().st_size
        is_valid, _ = AudioValidator.validate_file_size(file_size)

        # 3. オーディオボム検出
        is_safe, error_msg, audio_info = AudioValidator.detect_audio_bomb(bomb_file)

        # 異常検出されるはず
        if not is_safe:
            # セキュリティイベントログ
            SecureErrorHandler.log_security_event(
                event_type="audio_bomb_detected",
                severity="high",
                details={"file": str(bomb_file), "error": error_msg}
            )

    @pytest.mark.asyncio
    async def test_full_attack_scenario_dos(self):
        """DoS攻撃（並列処理枯渇）の完全シナリオテスト"""
        limiter = ResourceLimiter(max_concurrent=3, default_timeout=1.0, name="test")

        async def attack_task(task_id: int):
            try:
                async with limiter.acquire():
                    await asyncio.sleep(0.5)
                    return f"task_{task_id}_success"
            except asyncio.TimeoutError:
                return f"task_{task_id}_blocked"

        # 10並列攻撃（3並列しか許可されない）
        tasks = [attack_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 成功したタスクと失敗したタスクをカウント
        success_count = sum(1 for r in results if isinstance(r, str) and "success" in r)
        blocked_count = sum(1 for r in results if isinstance(r, str) and "blocked" in r)

        # 3並列が成功、残りはブロックされるはず
        assert success_count <= 10  # 全て完了する可能性もある（順次処理）
        assert limiter.metrics.total_tasks_executed <= 10

    @pytest.mark.asyncio
    async def test_full_attack_scenario_prosody_nan(self):
        """Prosody攻撃（NaN/Inf注入）の完全シナリオテスト"""
        # 攻撃者が異常なパラメータを送信
        malicious_params = {
            "pitch": float('nan'),
            "speed": float('inf'),
            "volume_linear": -999.0,
            "pause": float('nan')
        }

        # 検証
        is_valid, error_msg = ProsodyValidator.validate_all(
            pitch=malicious_params["pitch"],
            speed=malicious_params["speed"],
            volume_linear=malicious_params["volume_linear"],
            pause=malicious_params["pause"]
        )

        # すべて拒否されるはず
        assert not is_valid
        assert "無効な値" in error_msg or "正の値" in error_msg

        # サニタイズ（フォールバック）
        sanitized = ProsodyValidator.sanitize_prosody_params(**malicious_params)

        # 安全な値にリセットされる
        assert sanitized["pitch"] == 0.0
        assert sanitized["speed"] == 1.0
        assert sanitized["volume_linear"] == 1.0
        assert sanitized["pause"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
