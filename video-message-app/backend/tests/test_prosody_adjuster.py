"""
Prosody調整エンジンのユニットテスト
"""

import pytest
import numpy as np
import soundfile as sf
import io
from pathlib import Path

from services.prosody_adjuster import (
    ProsodyAdjuster,
    ProsodyConfig,
    get_prosody_adjuster
)


@pytest.fixture
def sample_audio_data():
    """
    テスト用サンプル音声データ生成（1秒のサイン波）
    """
    sample_rate = 24000
    duration = 1.0  # 1秒
    frequency = 440.0  # A4音（ラ）

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)

    # WAV形式でエンコード
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format='WAV', subtype='PCM_16')
    buffer.seek(0)

    return buffer.read()


@pytest.fixture
def adjuster():
    """Prosody調整サービスのインスタンス"""
    return get_prosody_adjuster()


class TestProsodyConfig:
    """ProsodyConfig モデルのテスト"""

    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = ProsodyConfig()
        assert config.pitch_shift == 0.0
        assert config.speed_rate == 1.0
        assert config.volume_db == 0.0
        assert config.pause_duration == 0.0
        assert config.preserve_formants is True

    def test_valid_config(self):
        """有効な設定のテスト"""
        config = ProsodyConfig(
            pitch_shift=3.0,
            speed_rate=1.5,
            volume_db=5.0,
            pause_duration=0.5
        )
        assert config.pitch_shift == 3.0
        assert config.speed_rate == 1.5
        assert config.volume_db == 5.0
        assert config.pause_duration == 0.5

    def test_invalid_pitch_shift(self):
        """無効なピッチシフトのテスト"""
        with pytest.raises(ValueError):
            ProsodyConfig(pitch_shift=15.0)  # 範囲外

        with pytest.raises(ValueError):
            ProsodyConfig(pitch_shift=-15.0)  # 範囲外

    def test_invalid_speed_rate(self):
        """無効な速度倍率のテスト"""
        with pytest.raises(ValueError):
            ProsodyConfig(speed_rate=0.3)  # 範囲外

        with pytest.raises(ValueError):
            ProsodyConfig(speed_rate=2.5)  # 範囲外


class TestProsodyAdjuster:
    """ProsodyAdjuster の基本機能テスト"""

    def test_singleton_instance(self):
        """シングルトンインスタンスのテスト"""
        adjuster1 = get_prosody_adjuster()
        adjuster2 = get_prosody_adjuster()
        assert adjuster1 is adjuster2

    def test_load_audio(self, adjuster, sample_audio_data):
        """音声データ読み込みのテスト"""
        audio, sr = adjuster._load_audio(sample_audio_data)
        assert isinstance(audio, np.ndarray)
        assert sr > 0
        assert len(audio) > 0

    def test_validate_audio(self, adjuster, sample_audio_data):
        """音声検証のテスト"""
        result = adjuster.validate_audio(sample_audio_data)
        assert result['valid'] is True
        assert result['sample_rate'] == 24000
        assert result['duration'] > 0.9  # 約1秒
        assert result['channels'] == 1  # モノラル

    def test_no_adjustment(self, adjuster, sample_audio_data):
        """調整なし（デフォルト設定）のテスト"""
        config = ProsodyConfig()
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.audio_data is not None
        assert result.sample_rate == 24000
        assert abs(result.duration_original - result.duration_adjusted) < 0.1  # ほぼ同じ長さ
        assert len(result.adjustments_applied) == 0  # 調整なし

    def test_pitch_shift_positive(self, adjuster, sample_audio_data):
        """正のピッチシフトのテスト"""
        config = ProsodyConfig(pitch_shift=3.0)  # +3 semitones
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.audio_data is not None
        assert 'pitch_shift' in result.adjustments_applied
        assert '+3.0 semitones' in result.adjustments_applied['pitch_shift']

    def test_pitch_shift_negative(self, adjuster, sample_audio_data):
        """負のピッチシフトのテスト"""
        config = ProsodyConfig(pitch_shift=-2.0)  # -2 semitones
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert 'pitch_shift' in result.adjustments_applied
        assert '-2.0 semitones' in result.adjustments_applied['pitch_shift']

    def test_speed_rate_faster(self, adjuster, sample_audio_data):
        """速度アップのテスト"""
        config = ProsodyConfig(speed_rate=1.5)  # 1.5倍速
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.duration_adjusted < result.duration_original  # 短くなる
        assert 'speed_rate' in result.adjustments_applied

    def test_speed_rate_slower(self, adjuster, sample_audio_data):
        """速度ダウンのテスト"""
        config = ProsodyConfig(speed_rate=0.75)  # 0.75倍速
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.duration_adjusted > result.duration_original  # 長くなる
        assert 'speed_rate' in result.adjustments_applied

    def test_volume_adjustment_up(self, adjuster, sample_audio_data):
        """音量アップのテスト"""
        config = ProsodyConfig(volume_db=6.0)  # +6dB
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert 'volume_db' in result.adjustments_applied
        assert '+6.0 dB' in result.adjustments_applied['volume_db']

    def test_volume_adjustment_down(self, adjuster, sample_audio_data):
        """音量ダウンのテスト"""
        config = ProsodyConfig(volume_db=-3.0)  # -3dB
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert 'volume_db' in result.adjustments_applied

    def test_pause_insertion(self, adjuster, sample_audio_data):
        """ポーズ挿入のテスト"""
        config = ProsodyConfig(pause_duration=0.5)  # +0.5秒
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.duration_adjusted > result.duration_original  # 長くなる
        assert abs(
            (result.duration_adjusted - result.duration_original) - 0.5
        ) < 0.05  # 約0.5秒追加

    def test_combined_adjustments(self, adjuster, sample_audio_data):
        """複合調整のテスト"""
        config = ProsodyConfig(
            pitch_shift=2.0,
            speed_rate=1.2,
            volume_db=3.0,
            pause_duration=0.3
        )
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert len(result.adjustments_applied) == 4
        assert 'pitch_shift' in result.adjustments_applied
        assert 'speed_rate' in result.adjustments_applied
        assert 'volume_db' in result.adjustments_applied
        assert 'pause_duration' in result.adjustments_applied

    def test_processing_time(self, adjuster, sample_audio_data):
        """処理時間のテスト（<3秒）"""
        config = ProsodyConfig(
            pitch_shift=5.0,
            speed_rate=1.5,
            volume_db=5.0,
            pause_duration=1.0
        )
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert result.processing_time < 3.0  # 1秒音声なら3秒以内

    def test_invalid_audio_data(self, adjuster):
        """無効な音声データのテスト"""
        invalid_data = b"this is not audio data"
        config = ProsodyConfig()
        result = adjuster.adjust_prosody(invalid_data, config)

        assert result.success is False
        assert result.error_message is not None


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_extreme_pitch_shift(self, adjuster, sample_audio_data):
        """極端なピッチシフト（±12 semitones）のテスト"""
        # +12 semitones (1オクターブ上)
        config_up = ProsodyConfig(pitch_shift=12.0)
        result_up = adjuster.adjust_prosody(sample_audio_data, config_up)
        assert result_up.success is True

        # -12 semitones (1オクターブ下)
        config_down = ProsodyConfig(pitch_shift=-12.0)
        result_down = adjuster.adjust_prosody(sample_audio_data, config_down)
        assert result_down.success is True

    def test_extreme_speed_rate(self, adjuster, sample_audio_data):
        """極端な速度倍率（0.5x, 2.0x）のテスト"""
        # 0.5x (半分の速度)
        config_slow = ProsodyConfig(speed_rate=0.5)
        result_slow = adjuster.adjust_prosody(sample_audio_data, config_slow)
        assert result_slow.success is True
        assert result_slow.duration_adjusted > result_slow.duration_original * 1.8

        # 2.0x (2倍速)
        config_fast = ProsodyConfig(speed_rate=2.0)
        result_fast = adjuster.adjust_prosody(sample_audio_data, config_fast)
        assert result_fast.success is True
        assert result_fast.duration_adjusted < result_fast.duration_original * 0.6

    def test_max_pause_duration(self, adjuster, sample_audio_data):
        """最大ポーズ長（2秒）のテスト"""
        config = ProsodyConfig(pause_duration=2.0)
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert abs(
            (result.duration_adjusted - result.duration_original) - 2.0
        ) < 0.1  # 約2秒追加

    def test_zero_length_pause(self, adjuster, sample_audio_data):
        """ポーズなし（0秒）のテスト"""
        config = ProsodyConfig(pause_duration=0.0)
        result = adjuster.adjust_prosody(sample_audio_data, config)

        assert result.success is True
        assert 'pause_duration' not in result.adjustments_applied


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
