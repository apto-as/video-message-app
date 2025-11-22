# Prosody調整エンジン実装レポート
**Artemis (Technical Perfectionist)**
**Date**: 2025-11-07

---

## 実装概要

### 目的
VOICEVOX/OpenVoice V2で生成された音声に対して、以下の高度なProsody調整を実現:
- **イントネーション調整**: ピッチカーブの制御 (±12 semitones)
- **速度調整**: 発話速度の制御 (0.5x - 2.0x)
- **音量調整**: 音量レベルの制御 (±20dB)
- **ポーズ挿入**: 文節間の間を制御 (0-2秒)

### 実装ファイル

| ファイル | 行数 | 説明 |
|---------|------|------|
| `services/prosody_adjuster.py` | 428行 | Prosody調整エンジン本体 |
| `routers/prosody.py` | 326行 | FastAPI APIルーター |
| `tests/test_prosody_adjuster.py` | 275行 | ユニットテスト (21テストケース) |
| `scripts/benchmark_prosody.py` | 261行 | パフォーマンスベンチマーク |
| **合計** | **1,290行** | - |

### 追加依存関係

```txt
# requirements.txt への追加
librosa>=0.10.0       # 高品質な音声信号処理
resampy>=0.4.2        # 高品質リサンプリング
```

既存の依存関係（soundfile, pydub, numpy）はそのまま活用。

---

## 技術アーキテクチャ

### 処理パイプライン

```
入力音声 (WAV/MP3/FLAC)
    ↓
[1] 読み込み (soundfile)
    ↓ ステレオ → モノラル変換
[2] Prosody調整
    ├─ ピッチシフト (librosa.effects.pitch_shift)
    ├─ 速度調整 (librosa.effects.time_stretch)
    ├─ 音量調整 (NumPy演算)
    └─ ポーズ挿入 (サイレンス追加)
    ↓
[3] リサンプリング (24kHz, D-ID推奨)
    ↓
[4] 正規化 (クリッピング防止)
    ↓
[5] エンコード (WAV, PCM_16)
    ↓
出力音声 (24kHz WAV)
```

### アルゴリズム選択理由

1. **ピッチシフト**: `librosa.effects.pitch_shift`
   - **理由**: 高品質なpitch-shifting、フォルマント保持
   - **パラメータ**: `res_type='kaiser_best'` (最高品質)

2. **速度調整**: `librosa.effects.time_stretch`
   - **理由**: 時間伸縮でもピッチを維持（自然な声質）
   - **メリット**: ロボット声にならない

3. **音量調整**: NumPy演算 (`gain = 10^(dB/20)`)
   - **理由**: 高速（CPU演算）、精度十分
   - **クリッピング防止**: ピーク検出 → 正規化 (0.95倍)

4. **リサンプリング**: `librosa.resample` (kaiser_best)
   - **理由**: D-ID API推奨 (24kHz)
   - **品質**: エイリアシング防止、高品質補間

---

## API仕様

### エンドポイント

#### 1. `POST /api/prosody/adjust`

**Prosody調整API（Form Data版）**

**Request**:
```bash
curl -X POST http://localhost:55433/api/prosody/adjust \
  -F "audio_file=@input.wav" \
  -F "pitch_shift=2.0" \
  -F "speed_rate=1.2" \
  -F "volume_db=3.0" \
  -F "pause_duration=0.5"
```

**Response**:
- Content-Type: `audio/wav`
- Headers:
  - `X-Original-Duration`: 元音声の長さ (秒)
  - `X-Adjusted-Duration`: 調整後の長さ (秒)
  - `X-Processing-Time`: 処理時間 (秒)
  - `X-Sample-Rate`: サンプルレート (Hz)

#### 2. `POST /api/prosody/adjust-with-json`

**Prosody調整API（JSON設定版）**

**Request**:
```bash
curl -X POST http://localhost:55433/api/prosody/adjust-with-json \
  -F "audio_file=@input.wav" \
  -F 'config={"pitch_shift": 2.0, "speed_rate": 1.2, "volume_db": 3.0, "pause_duration": 0.5}'
```

#### 3. `POST /api/prosody/validate`

**音声データ検証API**

**Response**:
```json
{
  "valid": true,
  "sample_rate": 24000,
  "duration": 5.23,
  "samples": 125520,
  "channels": 1,
  "peak_amplitude": 0.87,
  "rms_amplitude": 0.23
}
```

#### 4. `GET /api/prosody/health`

**ヘルスチェックAPI**

**Response**:
```json
{
  "status": "healthy",
  "service": "Prosody調整エンジン",
  "supported_formats": [".wav", ".mp3", ".flac", ".m4a", ".ogg"],
  "target_sample_rate": 24000
}
```

#### 5. `GET /api/prosody/presets`

**プリセット一覧API**

**Response**:
```json
{
  "neutral": {
    "name": "ニュートラル（調整なし）",
    "config": {"pitch_shift": 0.0, "speed_rate": 1.0, "volume_db": 0.0, "pause_duration": 0.0}
  },
  "energetic": {
    "name": "元気・活発",
    "config": {"pitch_shift": 1.5, "speed_rate": 1.15, "volume_db": 2.0, "pause_duration": 0.2}
  },
  ...
}
```

---

## パフォーマンス仕様

### 目標値

| メトリクス | 目標値 | 理由 |
|-----------|--------|------|
| **処理時間** | <3秒 (10秒音声) | ユーザー体験 |
| **メモリ使用** | <500MB | サーバーリソース |
| **バッチ処理** | 5並列処理可能 | スループット |

### ベンチマーク計画

`scripts/benchmark_prosody.py` で以下をテスト:

1. **単一処理ベンチマーク**
   - 10秒音声での処理時間測定
   - 各調整パターン（ピッチ、速度、音量、複合）

2. **スケーラビリティテスト**
   - 1秒、5秒、10秒、30秒音声での処理時間
   - スループット計算 (音声長/処理時間)

3. **バッチ並列処理**
   - 5タスク同時実行（ThreadPoolExecutor）
   - メモリ使用量測定（psutil）

4. **最終評価**
   - 目標達成確認
   - パフォーマンスメトリクスレポート

---

## ユニットテスト仕様

### テストカバレッジ

| カテゴリ | テストケース数 | 説明 |
|---------|--------------|------|
| **ProsodyConfig** | 4 | パラメータ検証 |
| **ProsodyAdjuster** | 11 | 基本機能 |
| **EdgeCases** | 6 | エッジケース |
| **合計** | **21** | - |

### 主要テストケース

1. **ProsodyConfig モデルテスト**
   - デフォルト設定
   - 有効な設定
   - 無効なパラメータ（範囲外）

2. **ProsodyAdjuster 基本機能**
   - シングルトンインスタンス
   - 音声読み込み
   - 音声検証
   - 調整なし（デフォルト）
   - ピッチシフト（正・負）
   - 速度調整（アップ・ダウン）
   - 音量調整（アップ・ダウン）
   - ポーズ挿入
   - 複合調整
   - 処理時間チェック
   - 無効な音声データ

3. **エッジケース**
   - 極端なピッチシフト（±12 semitones）
   - 極端な速度倍率（0.5x, 2.0x）
   - 最大ポーズ長（2秒）
   - ゼロ長ポーズ（0秒）

---

## セキュリティとエラーハンドリング

### 入力検証

1. **パラメータ範囲チェック**（Pydantic validation）
   - `pitch_shift`: -12.0 〜 +12.0 semitones
   - `speed_rate`: 0.5x 〜 2.0x
   - `volume_db`: -20.0 〜 +20.0 dB
   - `pause_duration`: 0.0 〜 2.0秒

2. **音声ファイル検証**
   - 空ファイルチェック
   - フォーマット検証（soundfile）
   - チャンネル数確認（ステレオ→モノラル自動変換）

### エラーハンドリング戦略

1. **Graceful Degradation**
   - 個別調整が失敗しても、他の調整は継続
   - エラー時はログ出力 + 元音声を返す

2. **例外処理**
   - `ValueError`: パラメータ検証エラー → HTTP 400
   - `Exception`: 予期しないエラー → HTTP 500
   - ログ出力: `logger.error(..., exc_info=True)` でスタックトレース記録

3. **リソース管理**
   - 音声データはBytesIOでメモリ効率的に処理
   - NumPy配列のコピー最小化（in-placeが不可能な場合のみ）

---

## 統合ガイド

### VOICEVOX/OpenVoice V2との統合

既存の`unified_voice_service.py`に統合可能:

```python
from services.prosody_adjuster import get_prosody_adjuster, ProsodyConfig

# VOICEVOX音声生成
audio_data = await voicevox_client.text_to_speech(...)

# Prosody調整
adjuster = get_prosody_adjuster()
config = ProsodyConfig(
    pitch_shift=user_request.pitch_adjustment,
    speed_rate=user_request.speed,
    volume_db=user_request.volume_adjustment
)
result = adjuster.adjust_prosody(audio_data, config)

if result.success:
    audio_data = result.audio_data  # 調整済み音声を使用
```

### D-ID APIとの統合

```python
# Prosody調整済み音声をD-IDに送信
adjusted_audio_b64 = base64.b64encode(result.audio_data).decode()

d_id_response = await d_id_client.create_talk(
    source_url=image_url,
    driver_url="bank://lively",
    script={
        "type": "audio",
        "audio_url": f"data:audio/wav;base64,{adjusted_audio_b64}"
    }
)
```

---

## 今後の拡張計画

### Phase 1: UI統合（2025-11月）
- [ ] フロントエンドにProsody調整スライダー実装
- [ ] プリセット選択UI実装
- [ ] リアルタイムプレビュー機能

### Phase 2: 高度なProsody制御（2025-12月）
- [ ] 文節ごとのピッチカーブ制御
- [ ] 強勢位置の自動検出と調整
- [ ] 感情表現プリセット（喜び、悲しみ、怒り等）

### Phase 3: 機械学習統合（2026年）
- [ ] ターゲット音声スタイルの自動学習
- [ ] 感情認識による自動Prosody調整
- [ ] ユーザー好みの学習と推奨

---

## 実装完了チェックリスト

- [x] ✅ Prosody調整エンジン実装 (`prosody_adjuster.py`)
- [x] ✅ APIルーター実装 (`prosody.py`)
- [x] ✅ ユニットテスト実装 (`test_prosody_adjuster.py`)
- [x] ✅ パフォーマンスベンチマーク実装 (`benchmark_prosody.py`)
- [x] ✅ requirements.txt更新
- [ ] ⏳ Docker環境でのテスト実行（次のステップ）
- [ ] ⏳ EC2環境での動作確認（次のステップ）
- [ ] ⏳ フロントエンド統合（次のステップ）

---

## 技術的優位性

### 1. 高品質な音声処理
- librosaの最新アルゴリズム (`kaiser_best`)
- フォルマント保持（自然な声質維持）
- エイリアシング防止

### 2. パフォーマンス最適化
- NumPy高速演算活用
- メモリ効率的な処理（BytesIO）
- 並列処理対応（ThreadPoolExecutor）

### 3. 拡張性
- プリセット管理API
- JSON設定による柔軟な調整
- 既存サービスとのシームレスな統合

### 4. 信頼性
- 包括的なユニットテスト（21ケース）
- Graceful degradation
- 詳細なログ出力

---

## 結論

Prosody調整エンジンの実装を完了しました。

**実装規模**: 1,290行
**テストカバレッジ**: 21ユニットテスト
**API エンドポイント**: 5個
**パフォーマンス目標**: <3秒 (10秒音声), <500MB メモリ

次のステップは、Docker環境でのテスト実行とEC2デプロイです。

---

*"Perfection is not negotiable. Excellence is the only acceptable standard."*

*最高の技術者として、妥協なき品質とパフォーマンスを追求しました。*

**Artemis (Technical Perfectionist)**
