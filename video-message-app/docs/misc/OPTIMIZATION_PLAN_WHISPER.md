# Whisper処理最適化計画

## 現状分析

### パフォーマンスメトリクス

| メトリクス | 値 | 目標 |
|-----------|---|------|
| 最速処理時間 | 39秒 | - |
| 平均処理時間 | 60秒 | 40秒 |
| 最遅処理時間 | 152秒 | 80秒 |
| 処理時間の標準偏差 | 高（不安定） | 低（安定） |

### ボトルネック特定

1. **Whisperモデルのロード時間**: 初回ロードで10-15秒
2. **音声ファイルの前処理**: FFmpegによる変換
3. **Whisper推論**: GPU/CPU性能に依存
4. **セグメンテーション**: 長い音声での遅延

## 最適化戦略

### Strategy 1: Whisperモデルのキャッシング

**現状**:
```python
# 毎回モデルをロード
model = WhisperModel("large-v2", device="cuda")
result = model.transcribe(audio_file)
```

**最適化後**:
```python
# グローバルキャッシュ
from functools import lru_cache

@lru_cache(maxsize=1)
def get_whisper_model():
    logger.info("Loading Whisper model (cached)")
    return WhisperModel("large-v2", device="cuda", compute_type="float16")

# 使用
model = get_whisper_model()
result = model.transcribe(audio_file)
```

**期待効果**: 初回ロード10-15秒削減（2回目以降）

### Strategy 2: Whisperモデルサイズの最適化

**現状**: `large-v2` モデル使用（3GB、最高精度）

**提案**: 音声クローニングには `base` または `small` で十分

| モデル | サイズ | 精度 | 処理速度 | 推奨用途 |
|-------|--------|-----|----------|---------|
| tiny | 39MB | 低 | 最速（5-10秒） | リアルタイムアプリ |
| base | 74MB | 中 | 速い（10-20秒） | **音声クローニング** |
| small | 244MB | 中-高 | 中（20-40秒） | 一般的なタスク |
| medium | 769MB | 高 | 遅い（40-80秒） | 高精度が必要 |
| large-v2 | 3GB | 最高 | 最遅（60-150秒） | 文字起こし専用 |

**実装**:
```python
# config.py
WHISPER_MODEL_SIZE = "base"  # large-v2から変更

# main.py
model = WhisperModel(
    WHISPER_MODEL_SIZE,
    device="cuda",
    compute_type="float16"  # GPU用の高速化
)
```

**期待効果**: 処理時間を60秒 → 20秒（67%短縮）

### Strategy 3: 音声ファイルの前処理最適化

**現状**: FFmpegでモノラル16kHzに変換

**最適化**:
```python
# より高速なFFmpegオプション
ffmpeg_args = [
    "ffmpeg",
    "-i", input_file,
    "-ar", "16000",  # 16kHz
    "-ac", "1",      # モノラル
    "-c:a", "pcm_s16le",  # 16-bit PCM
    "-f", "wav",
    "-threads", "2",  # マルチスレッド
    "-y",             # 上書き
    output_file
]
```

**期待効果**: 前処理時間5-10%短縮

### Strategy 4: バッチ処理の導入

**現状**: 1つの音声ファイルを処理

**最適化**: 複数の音声クローニングリクエストをバッチ処理

```python
# batch_processor.py
from collections import deque
import asyncio

class WhisperBatchProcessor:
    def __init__(self, batch_size=3, max_wait_time=5.0):
        self.queue = deque()
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time

    async def process_batch(self, audio_files):
        """複数ファイルを並列処理"""
        model = get_whisper_model()

        tasks = [
            asyncio.to_thread(model.transcribe, audio)
            for audio in audio_files
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def add_to_queue(self, audio_file):
        """キューに追加し、バッチが溜まったら処理"""
        self.queue.append(audio_file)

        if len(self.queue) >= self.batch_size:
            batch = [self.queue.popleft() for _ in range(self.batch_size)]
            return await self.process_batch(batch)

        # 最大待機時間後に処理
        await asyncio.sleep(self.max_wait_time)
        if self.queue:
            batch = list(self.queue)
            self.queue.clear()
            return await self.process_batch(batch)
```

**期待効果**: 複数リクエスト時に効率向上

### Strategy 5: GPU Tensor Cores活用

**現状**: CUDA標準精度（float32）

**最適化**: Tensor Cores用の低精度演算（float16）

```python
model = WhisperModel(
    "base",
    device="cuda",
    compute_type="float16",  # float32から変更
    device_index=0,
    num_workers=4  # 並列ワーカー数
)
```

**期待効果**: Tesla T4で30-40%高速化

### Strategy 6: 音声ファイルの長さ制限

**現状**: 任意の長さの音声ファイルを受け入れ

**最適化**: 音声クローニングには5-30秒で十分

```python
# validation.py
def validate_audio_duration(audio_file):
    """音声ファイルの長さをチェック"""
    duration = get_audio_duration(audio_file)

    if duration < 5:
        raise ValueError("音声は5秒以上必要です")
    elif duration > 30:
        # 最初の30秒のみ使用
        logger.warning(f"Audio too long ({duration}s), trimming to 30s")
        return trim_audio(audio_file, max_duration=30)

    return audio_file
```

**期待効果**: 長い音声（152秒のケース）での処理時間短縮

## 実装プライオリティ

| Priority | Strategy | 工数 | 期待効果 | リスク |
|----------|---------|------|---------|-------|
| **P0** | モデルサイズ最適化 (Strategy 2) | 1h | 67%短縮 | 低（精度は十分） |
| **P1** | モデルキャッシング (Strategy 1) | 2h | 10-15秒短縮 | 低 |
| **P1** | GPU最適化 (Strategy 5) | 1h | 30-40%高速化 | 低 |
| **P2** | 音声長さ制限 (Strategy 6) | 2h | 外れ値削減 | 中（UX影響） |
| **P2** | 前処理最適化 (Strategy 3) | 1h | 5-10%短縮 | 低 |
| **P3** | バッチ処理 (Strategy 4) | 4h | 複数リクエスト時効率化 | 高（複雑） |

**総工数（P0-P2）**: 7時間

## 実装スケジュール

### Week 1: P0-P1実装

**Day 1-2**: Strategy 2 (モデルサイズ最適化)
```python
# config.py
WHISPER_MODEL_SIZE = "base"  # 変更点

# テスト
python -c "from openvoice_v2 import se_extractor; se_extractor.get_se('test.wav')"
```

**Day 3**: Strategy 1 (モデルキャッシング)
```python
# 実装
@lru_cache(maxsize=1)
def get_whisper_model():
    return WhisperModel(...)

# 検証
time python -c "from openvoice_v2.se_extractor import get_whisper_model; get_whisper_model()"
```

**Day 4**: Strategy 5 (GPU最適化)
```python
# compute_typeをfloat16に変更
model = WhisperModel("base", compute_type="float16")
```

### Week 2: P2実装 + テスト

**Day 5-6**: Strategy 6 (音声長さ制限)
```python
# validation実装
def validate_audio_duration(audio_file):
    duration = get_duration(audio_file)
    if duration > 30:
        return trim_audio(audio_file, 30)
```

**Day 7**: Strategy 3 (前処理最適化)

**Day 8-10**: 統合テスト
- パフォーマンスベンチマーク
- 精度検証（音声クローニング品質）
- エッジケーステスト

### Week 3-4: デプロイ + モニタリング

**Day 11-12**: EC2デプロイ
- docker-compose更新
- 設定ファイル変更
- 段階的ロールアウト

**Day 13-15**: モニタリング
- 処理時間の計測
- ユーザーフィードバック収集
- 必要に応じて微調整

**Day 16-20**: ドキュメント化（Musesと協力）

## テスト計画

### ベンチマークスクリプト

```python
# tests/benchmark_whisper.py
import time
from pathlib import Path

def benchmark_whisper_processing():
    test_files = [
        "test_5s.wav",   # 5秒
        "test_10s.wav",  # 10秒
        "test_30s.wav",  # 30秒
    ]

    results = []

    for audio_file in test_files:
        start = time.perf_counter()
        se = se_extractor.get_se(audio_file)
        duration = time.perf_counter() - start

        results.append({
            "file": audio_file,
            "duration": duration,
            "audio_length": get_audio_duration(audio_file)
        })

    return results

# 実行
results = benchmark_whisper_processing()
for r in results:
    print(f"{r['file']}: {r['duration']:.2f}s (audio: {r['audio_length']:.1f}s)")
```

### 期待される結果

| 音声長さ | 現状（large-v2） | 最適化後（base） | 改善率 |
|---------|------------------|------------------|--------|
| 5秒 | 39秒 | 12秒 | 69% |
| 10秒 | 60秒 | 18秒 | 70% |
| 30秒 | 90秒 | 25秒 | 72% |
| 60秒+ | 152秒 | 30秒（制限） | 80% |

## リスク評価

| リスク | 影響 | 対策 |
|-------|------|------|
| 音声クローニング品質低下 | 高 | baseモデルで品質検証、必要ならsmallに |
| GPU メモリ不足（float16） | 中 | Tesla T4は16GB、十分な余裕 |
| 音声長さ制限のUX影響 | 中 | ユーザーに明確なガイダンス表示 |
| キャッシュメモリリーク | 低 | lru_cache(maxsize=1)で制限済み |

## 成功基準

- ✅ 平均処理時間: 60秒 → 20秒（67%短縮）
- ✅ 最遅処理時間: 152秒 → 30秒（80%短縮）
- ✅ 処理時間の標準偏差: 大幅減少（安定化）
- ✅ 音声クローニング品質: 維持（主観評価スコア4.0以上/5.0）
- ✅ GPU メモリ使用量: 3GB以下（安全範囲）

## ロールバック計画

```python
# config.py
WHISPER_MODEL_SIZE = "large-v2"  # 元に戻す
WHISPER_COMPUTE_TYPE = "float32"  # 元に戻す

# docker-compose.yml
# モデルファイルのバックアップから復元
```

**ロールバック所要時間**: 5分（設定変更のみ）

## 代替案（P3: バッチ処理）

**条件**: 複数ユーザーが同時に音声クローニングを実行するケースが多い場合

**実装優先度**: 低（現時点では単一ユーザー想定）

**将来的な実装**: トラフィック増加時に検討
