#!/usr/bin/env python3
"""
Prosody調整エンジンのパフォーマンスベンチマーク

目標:
- 処理時間: <3秒 (10秒音声の場合)
- メモリ使用: <500MB
- バッチ処理: 5並列処理可能
"""

import sys
import time
import psutil
import numpy as np
import soundfile as sf
import io
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from services.prosody_adjuster import ProsodyAdjuster, ProsodyConfig


def generate_test_audio(duration: float = 10.0, sample_rate: int = 24000) -> bytes:
    """
    テスト用音声データ生成

    Args:
        duration: 音声長 (秒)
        sample_rate: サンプルレート

    Returns:
        WAV形式の音声データ (bytes)
    """
    # 複数周波数のサイン波を合成（より自然な音声に近い）
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = (
        0.3 * np.sin(2 * np.pi * 220 * t) +  # A3
        0.2 * np.sin(2 * np.pi * 330 * t) +  # E4
        0.15 * np.sin(2 * np.pi * 440 * t) +  # A4
        0.1 * np.sin(2 * np.pi * 550 * t)    # C#5
    )

    # WAV形式でエンコード
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format='WAV', subtype='PCM_16')
    buffer.seek(0)
    return buffer.read()


def benchmark_single_processing(
    adjuster: ProsodyAdjuster,
    audio_data: bytes,
    config: ProsodyConfig
) -> Dict[str, Any]:
    """
    単一処理のベンチマーク

    Returns:
        処理時間、メモリ使用量などのメトリクス
    """
    process = psutil.Process()

    # 初期メモリ使用量
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    # 処理実行
    start_time = time.perf_counter()
    result = adjuster.adjust_prosody(audio_data, config)
    processing_time = time.perf_counter() - start_time

    # 処理後メモリ使用量
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_used = mem_after - mem_before

    return {
        'success': result.success,
        'processing_time': processing_time,
        'duration_original': result.duration_original,
        'duration_adjusted': result.duration_adjusted,
        'memory_used_mb': mem_used,
        'memory_total_mb': mem_after,
        'throughput': result.duration_original / processing_time if processing_time > 0 else 0
    }


def benchmark_batch_processing(
    adjuster: ProsodyAdjuster,
    audio_data_list: List[bytes],
    config: ProsodyConfig,
    num_workers: int = 5
) -> Dict[str, Any]:
    """
    バッチ並列処理のベンチマーク

    Args:
        audio_data_list: 音声データリスト
        num_workers: 並列ワーカー数

    Returns:
        バッチ処理のメトリクス
    """
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024

    start_time = time.perf_counter()

    # 並列処理実行
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(adjuster.adjust_prosody, audio_data, config)
            for audio_data in audio_data_list
        ]
        results = [future.result() for future in futures]

    total_time = time.perf_counter() - start_time

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before

    # 結果集計
    success_count = sum(1 for r in results if r.success)
    avg_processing_time = np.mean([r.processing_time for r in results])
    total_audio_duration = sum(r.duration_original for r in results)

    return {
        'total_tasks': len(audio_data_list),
        'success_count': success_count,
        'total_time': total_time,
        'avg_processing_time': avg_processing_time,
        'total_audio_duration': total_audio_duration,
        'throughput': total_audio_duration / total_time if total_time > 0 else 0,
        'memory_used_mb': mem_used,
        'memory_peak_mb': mem_after,
        'parallelization_efficiency': (total_audio_duration / num_workers) / total_time if total_time > 0 else 0
    }


def print_benchmark_results(title: str, results: Dict[str, Any]):
    """ベンチマーク結果の表示"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

    for key, value in results.items():
        if isinstance(value, float):
            print(f"  {key:30s}: {value:>10.3f}")
        else:
            print(f"  {key:30s}: {value:>10}")

    print(f"{'='*60}\n")


def main():
    """メインベンチマーク実行"""
    print("\n" + "="*60)
    print("Prosody調整エンジン パフォーマンスベンチマーク")
    print("="*60)

    adjuster = ProsodyAdjuster()

    # テスト設定
    test_configs = {
        "ニュートラル（調整なし）": ProsodyConfig(),
        "ピッチシフトのみ": ProsodyConfig(pitch_shift=3.0),
        "速度調整のみ": ProsodyConfig(speed_rate=1.5),
        "音量調整のみ": ProsodyConfig(volume_db=5.0),
        "複合調整": ProsodyConfig(
            pitch_shift=2.0,
            speed_rate=1.2,
            volume_db=3.0,
            pause_duration=0.5
        )
    }

    # 1. 単一処理ベンチマーク (10秒音声)
    print("\n[1] 単一処理ベンチマーク (10秒音声)")
    audio_10s = generate_test_audio(duration=10.0)

    for config_name, config in test_configs.items():
        result = benchmark_single_processing(adjuster, audio_10s, config)
        print_benchmark_results(f"設定: {config_name}", result)

        # 目標チェック
        if result['processing_time'] > 3.0:
            print(f"⚠️  警告: 処理時間が目標を超過しました ({result['processing_time']:.2f}秒 > 3.0秒)")

    # 2. 異なる音声長でのスケーラビリティテスト
    print("\n[2] スケーラビリティテスト")
    config = ProsodyConfig(pitch_shift=2.0, speed_rate=1.2)

    for duration in [1.0, 5.0, 10.0, 30.0]:
        audio_data = generate_test_audio(duration=duration)
        result = benchmark_single_processing(adjuster, audio_data, config)

        print(f"音声長: {duration:5.1f}秒 → "
              f"処理時間: {result['processing_time']:6.3f}秒, "
              f"スループット: {result['throughput']:6.2f}x, "
              f"メモリ使用: {result['memory_used_mb']:6.1f}MB")

    # 3. バッチ並列処理ベンチマーク
    print("\n[3] バッチ並列処理ベンチマーク (5タスク同時)")
    audio_5s_list = [generate_test_audio(duration=5.0) for _ in range(5)]
    config = ProsodyConfig(pitch_shift=2.0, speed_rate=1.2, volume_db=3.0)

    batch_result = benchmark_batch_processing(
        adjuster,
        audio_5s_list,
        config,
        num_workers=5
    )
    print_benchmark_results("バッチ並列処理結果", batch_result)

    # 目標チェック
    if batch_result['memory_peak_mb'] > 500:
        print(f"⚠️  警告: メモリ使用量が目標を超過しました ({batch_result['memory_peak_mb']:.1f}MB > 500MB)")

    # 4. 最終評価
    print("\n" + "="*60)
    print("最終評価")
    print("="*60)

    # 10秒音声の複合調整処理時間チェック
    audio_10s = generate_test_audio(duration=10.0)
    config_complex = ProsodyConfig(
        pitch_shift=5.0,
        speed_rate=1.5,
        volume_db=5.0,
        pause_duration=1.0
    )
    result_complex = benchmark_single_processing(adjuster, audio_10s, config_complex)

    print(f"✓ 処理時間目標 (<3秒, 10秒音声): ", end="")
    if result_complex['processing_time'] < 3.0:
        print(f"✅ PASS ({result_complex['processing_time']:.2f}秒)")
    else:
        print(f"❌ FAIL ({result_complex['processing_time']:.2f}秒)")

    print(f"✓ メモリ使用目標 (<500MB): ", end="")
    if batch_result['memory_peak_mb'] < 500:
        print(f"✅ PASS ({batch_result['memory_peak_mb']:.1f}MB)")
    else:
        print(f"❌ FAIL ({batch_result['memory_peak_mb']:.1f}MB)")

    print(f"✓ バッチ処理目標 (5並列): ", end="")
    if batch_result['success_count'] == 5:
        print(f"✅ PASS (全{batch_result['success_count']}タスク成功)")
    else:
        print(f"❌ FAIL ({batch_result['success_count']}/5 成功)")

    print("\n" + "="*60)
    print("ベンチマーク完了")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
