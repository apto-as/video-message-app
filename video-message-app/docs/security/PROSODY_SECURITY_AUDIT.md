# Prosody調整機能 セキュリティ監査レポート

**監査日**: 2025-11-07
**監査者**: Hestia (Security Guardian)
**対象システム**: Video Message App - Audio Processing & Prosody Adjustment
**重要度**: 🔥 **CRITICAL**

---

## ⚠️ Executive Summary（要約）

Prosody調整機能（音声のピッチ、速度、音量調整）は**まだ完全実装されていない**が、既存の音声処理システムに**Critical級の脆弱性**を複数発見しました。音声処理は計算コストが高いため、DoS攻撃のリスクが極めて高いです。

**総合リスク評価**: 🔴 **HIGH RISK**

### 発見された Critical脆弱性（即時対応必須）

| ID | 脆弱性 | 影響 | CVSS Score |
|----|--------|------|------------|
| V-1 | ファイルサイズ制限が緩い（100MB） | リソース枯渇 | 7.5 (HIGH) |
| V-2 | 音声長チェックなし | CPU占有、DoS | 8.2 (HIGH) |
| V-3 | 並列処理制限なし | メモリ枯渇、サーバーダウン | 8.6 (HIGH) |
| V-4 | オーディオボム検出なし | 異常データによる処理停止 | 7.8 (HIGH) |
| V-5 | Prosodyパラメータ検証なし | 不正なパラメータによる異常音声 | 6.5 (MEDIUM) |
| V-6 | エラーメッセージの情報漏洩 | サーバーパス、スタックトレース露出 | 5.3 (MEDIUM) |

---

## 🚨 Critical脆弱性の詳細

### V-1: ファイルサイズ制限が緩い（100MB）

**場所**: `backend/routers/unified_voice.py:196`

```python
# ファイルサイズチェック（100MB制限）
if len(audio_data) > 100 * 1024 * 1024:
    raise HTTPException(status_code=400, detail="ファイルサイズが大きすぎます（100MB以下）")
```

**問題点**:
- 100MBは大きすぎる。攻撃者が10並列で送信すれば1GBのメモリを消費
- WAVファイル（非圧縮）の場合、100MB = 約10分の音声 → 処理時間が長すぎる

**攻撃シナリオ**:
```bash
# 攻撃者が100MBファイルを10並列でアップロード
for i in {1..10}; do
  curl -X POST http://target/api/clone \
    -F "audio_file=@malicious_100mb.wav" &
done

# 結果:
# - メモリ: 1GB消費（10 * 100MB）
# - CPU: 10分間 * 10並列 = 100分の処理時間
# - サーバーが応答不能に
```

**推奨対策**:
- **最大ファイルサイズ: 50MB** (5分の非圧縮WAV)
- **推奨サイズ: 10MB** (MP3なら約10分の音声)
- 段階的制限:
  - ゲストユーザー: 5MB
  - 通常ユーザー: 20MB
  - プレミアムユーザー: 50MB

---

### V-2: 音声長チェックなし

**場所**: `backend/services/voice_manager.py:126-139`

**問題点**:
- 音声ファイルの**実際の再生時間**をチェックしていない
- `duration`を取得しているが、検証に使用していない
- 攻撃者が1時間の音声をアップロードしても拒否されない

**攻撃シナリオ**:
```python
# 攻撃者が1時間の音声ファイルを生成
import wave
import numpy as np

# 1時間 = 3600秒の無音WAV生成
sample_rate = 44100
duration = 3600  # 1時間
data = np.zeros(sample_rate * duration, dtype=np.int16)

with wave.open('1hour_silence.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(data.tobytes())

# このファイルは60MBだがアップロード可能
# OpenVoice処理に1時間以上かかる可能性
```

**推奨対策**:
- **最大音声長: 5分（300秒）**
- 段階的制限:
  - 音声クローン用リファレンス: 10秒〜30秒（推奨）
  - TTS合成用テキスト: 最大5分相当
  - バックグラウンド処理: 最大10分

**実装例**:
```python
# backend/security/audio_validator.py (新規作成)
def validate_audio_duration(file_path: Path, max_duration: float = 300.0) -> Tuple[bool, str]:
    """音声長の検証"""
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return False, "音声ファイルの解析に失敗しました"

        duration = getattr(audio.info, 'length', 0)

        if duration > max_duration:
            return False, f"音声が長すぎます（最大{max_duration}秒）"

        if duration < 0.1:
            return False, "音声が短すぎます（最低0.1秒）"

        return True, ""
    except Exception as e:
        return False, f"音声長の検証に失敗: {str(e)}"
```

---

### V-3: 並列処理制限なし

**場所**: `backend/routers/unified_voice.py:298-348`

**問題点**:
- `clone_voice_background`で無制限にBackgroundTasksを作成可能
- メモリ監視なし、CPU制限なし、タイムアウトなし
- 攻撃者が1000並列リクエストを送れば確実にサーバーダウン

**攻撃シナリオ**:
```bash
# 攻撃者が1000並列リクエスト送信
for i in {1..1000}; do
  curl -X POST http://target/api/unified-voice/clone/background \
    -F "audio_file=@ref.wav" \
    -F "voice_name=voice_$i" &
done

# 結果:
# - 1000個のBackgroundTaskが同時実行
# - メモリ: 1000 * 500MB（OpenVoice処理メモリ）= 500GB
# - CPU: 100%で固定、他のリクエストが処理不能に
# - サーバーが完全停止
```

**推奨対策**:
- **同時処理数: 最大5並列**
- **処理タイムアウト: 30秒**
- **メモリ制限: 500MB/プロセス**
- **キュー方式**: 5並列超過分はキューイング

**実装例**:
```python
# backend/security/resource_limiter.py (新規作成)
import asyncio
from asyncio import Semaphore

class ResourceLimiter:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)
        self.active_tasks = 0
        self.max_concurrent = max_concurrent

    async def acquire(self, timeout: float = 30.0):
        """リソース取得（タイムアウト付き）"""
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
            self.active_tasks += 1
            return True
        except asyncio.TimeoutError:
            return False

    def release(self):
        """リソース解放"""
        self.semaphore.release()
        self.active_tasks -= 1

    def get_available_slots(self) -> int:
        """利用可能なスロット数"""
        return self.max_concurrent - self.active_tasks

# グローバルインスタンス
voice_clone_limiter = ResourceLimiter(max_concurrent=5)
```

---

### V-4: オーディオボム検出なし

**場所**: `backend/services/voice_manager.py:126-139`

**問題点**:
- 異常なサンプルレート（例: 1,000,000 Hz）を検出していない
- 異常なビットレート（例: 9999 kbps）を検出していない
- 異常なチャンネル数（例: 256チャンネル）を検出していない
- これらの異常データはlibrosa、ffmpegでの処理時に**メモリ爆発**を引き起こす

**攻撃シナリオ**:
```python
# 攻撃者がオーディオボムを生成
import wave

# 異常なサンプルレート: 1,000,000 Hz
with wave.open('audio_bomb.wav', 'w') as f:
    f.setnchannels(256)  # 256チャンネル（異常）
    f.setsampwidth(4)    # 32bit（異常）
    f.setframerate(1000000)  # 1MHz（異常）
    # 1秒の音声データ（実際は空）
    f.writeframes(b'\x00' * 1000000)

# このファイルをアップロード
# librosaでの読み込み時に:
# - メモリ: 1,000,000 * 256 * 4 = 1GB/秒
# - 10秒の音声なら10GBのメモリを瞬時に消費
# - サーバーがOOM (Out of Memory) でクラッシュ
```

**推奨対策**:
- **サンプルレート範囲: 8,000 Hz 〜 48,000 Hz**
- **チャンネル数: 1 (モノラル) または 2 (ステレオ)**
- **ビット深度: 16bit または 24bit**
- **ビットレート: 32 kbps 〜 320 kbps**

**実装例**:
```python
# backend/security/audio_validator.py
def detect_audio_bomb(file_path: Path) -> Tuple[bool, str]:
    """オーディオボム検出"""
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return False, "音声ファイルの解析に失敗しました"

        # サンプルレート検証
        sample_rate = getattr(audio.info, 'sample_rate', 0)
        if not (8000 <= sample_rate <= 48000):
            return False, f"異常なサンプルレート: {sample_rate} Hz（正常範囲: 8000-48000 Hz）"

        # ビットレート検証（MP3の場合）
        bitrate = getattr(audio.info, 'bitrate', 0)
        if bitrate > 320000:  # 320 kbps
            return False, f"異常なビットレート: {bitrate} bps（最大: 320 kbps）"

        # チャンネル数検証
        channels = getattr(audio.info, 'channels', 0)
        if channels not in [1, 2]:
            return False, f"異常なチャンネル数: {channels}（許可: 1 or 2）"

        return True, ""
    except Exception as e:
        return False, f"オーディオボム検出失敗: {str(e)}"
```

---

### V-5: Prosodyパラメータ検証なし

**場所**: `backend/routers/unified_voice.py:43-46`

```python
speed: float = Field(default=1.0, ge=0.1, le=3.0)
pitch: float = Field(default=0.0, ge=-0.15, le=0.15)
volume: float = Field(default=1.0, ge=0.0, le=2.0)
emotion: str = Field(default="neutral")
```

**問題点**:
- Pydanticの範囲検証は存在するが、**実装が存在しない**
- パラメータは受け取っているが、実際の音声処理に反映されていない
- `NaN`, `Inf` などの異常値を検出していない

**攻撃シナリオ**:
```python
# 攻撃者が異常なパラメータを送信
import requests
import json

payload = {
    "text": "テスト",
    "voice_profile_id": "test_id",
    "speed": float('inf'),   # 無限大
    "pitch": float('nan'),   # NaN
    "volume": 999999999.0    # 極端な大音量
}

response = requests.post('http://target/api/unified-voice/synthesize', json=payload)

# 現在の実装では:
# - Pydanticの検証をパスしてしまう可能性
# - バックエンド処理でクラッシュ
# - または極端に歪んだ音声が生成される
```

**推奨対策**:
- **Prosodyパラメータの厳格検証**:
  - ピッチシフト: ±12 semitones (半音階)
  - 速度: 0.5x 〜 2.0x
  - 音量: ±20dB
  - ポーズ: 0 〜 2.0秒
- **NaN/Inf値の明示的拒否**
- **実装前のパラメータ使用禁止**

**実装例**:
```python
# backend/security/prosody_validator.py (新規作成)
import math
from typing import Tuple

class ProsodyValidator:
    # 範囲定義
    MIN_PITCH_SHIFT = -12  # semitones
    MAX_PITCH_SHIFT = 12
    MIN_SPEED = 0.5
    MAX_SPEED = 2.0
    MIN_VOLUME = -20  # dB
    MAX_VOLUME = 20
    MAX_PAUSE = 2.0  # seconds

    @staticmethod
    def validate_pitch(pitch: float) -> Tuple[bool, str]:
        """ピッチシフト検証"""
        if not math.isfinite(pitch):
            return False, "ピッチに無効な値が含まれています（NaN/Inf）"

        if not (ProsodyValidator.MIN_PITCH_SHIFT <= pitch <= ProsodyValidator.MAX_PITCH_SHIFT):
            return False, f"ピッチシフトは{ProsodyValidator.MIN_PITCH_SHIFT}〜{ProsodyValidator.MAX_PITCH_SHIFT}半音の範囲で指定してください"

        return True, ""

    @staticmethod
    def validate_speed(speed: float) -> Tuple[bool, str]:
        """速度検証"""
        if not math.isfinite(speed):
            return False, "速度に無効な値が含まれています（NaN/Inf）"

        if not (ProsodyValidator.MIN_SPEED <= speed <= ProsodyValidator.MAX_SPEED):
            return False, f"速度は{ProsodyValidator.MIN_SPEED}x〜{ProsodyValidator.MAX_SPEED}xの範囲で指定してください"

        return True, ""

    @staticmethod
    def validate_volume(volume_db: float) -> Tuple[bool, str]:
        """音量検証"""
        if not math.isfinite(volume_db):
            return False, "音量に無効な値が含まれています（NaN/Inf）"

        if not (ProsodyValidator.MIN_VOLUME <= volume_db <= ProsodyValidator.MAX_VOLUME):
            return False, f"音量は{ProsodyValidator.MIN_VOLUME}〜{ProsodyValidator.MAX_VOLUME}dBの範囲で指定してください"

        return True, ""

    @staticmethod
    def validate_pause(pause_seconds: float) -> Tuple[bool, str]:
        """ポーズ検証"""
        if not math.isfinite(pause_seconds):
            return False, "ポーズに無効な値が含まれています（NaN/Inf）"

        if not (0 <= pause_seconds <= ProsodyValidator.MAX_PAUSE):
            return False, f"ポーズは0〜{ProsodyValidator.MAX_PAUSE}秒の範囲で指定してください"

        return True, ""

    @classmethod
    def validate_all(cls, pitch: float, speed: float, volume_db: float, pause: float = 0.0) -> Tuple[bool, str]:
        """全Prosodyパラメータの一括検証"""
        validations = [
            cls.validate_pitch(pitch),
            cls.validate_speed(speed),
            cls.validate_volume(volume_db),
            cls.validate_pause(pause)
        ]

        for is_valid, error_msg in validations:
            if not is_valid:
                return False, error_msg

        return True, ""
```

---

### V-6: エラーメッセージの情報漏洩

**場所**: 複数箇所（例: `unified_voice.py:172`）

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"音声合成エラー: {str(e)}")
```

**問題点**:
- スタックトレース、サーバーパス、内部エラーメッセージがそのまま露出
- 攻撃者が内部構造を推測可能

**攻撃シナリオ**:
```python
# 攻撃者が意図的に異常なリクエストを送信
response = requests.post('http://target/api/unified-voice/synthesize', json={
    "text": "test",
    "voice_profile_id": "../../../etc/passwd"  # パストラバーサル
})

# エラーメッセージに以下が含まれる可能性:
# "音声合成エラー: [Errno 2] No such file or directory: '/app/storage/voices/../../../etc/passwd'"
# → サーバーのパス構造が露出
```

**推奨対策**:
- **一般的なエラーメッセージのみ返す**
- **詳細はサーバーログに記録**
- **本番環境ではdebug=Falseを徹底**

**実装例**:
```python
# backend/security/error_handler.py (新規作成)
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class SecureErrorHandler:
    @staticmethod
    def handle_audio_processing_error(e: Exception, context: str) -> HTTPException:
        """音声処理エラーの安全なハンドリング"""
        # 詳細ログ（サーバーのみ）
        logger.error(f"Audio processing error in {context}: {str(e)}", exc_info=True)

        # ユーザーには一般的なエラーメッセージのみ
        return HTTPException(
            status_code=500,
            detail="音声処理中にエラーが発生しました。しばらく時間をおいてから再度お試しください。"
        )

    @staticmethod
    def handle_validation_error(field: str, reason: str) -> HTTPException:
        """検証エラーのハンドリング"""
        # 検証エラーは安全なのでユーザーに詳細を返す
        return HTTPException(
            status_code=400,
            detail=f"{field}の検証に失敗しました: {reason}"
        )
```

---

## 🛡️ 推奨セキュリティ対策（優先順位順）

### Phase 1: 即時対応（24時間以内）

1. **ファイルサイズ制限の厳格化**
   - 100MB → 50MB（最大）、推奨10MB
   - `backend/routers/unified_voice.py:196` 修正

2. **音声長チェックの追加**
   - 最大5分（300秒）
   - `backend/services/voice_manager.py` に検証追加

3. **並列処理制限の実装**
   - 最大5並列、タイムアウト30秒
   - `backend/security/resource_limiter.py` 新規作成

### Phase 2: 短期対応（3日以内）

4. **オーディオボム検出の実装**
   - サンプルレート、ビットレート、チャンネル数検証
   - `backend/security/audio_validator.py` 新規作成

5. **Prosodyパラメータ検証の実装**
   - NaN/Inf検出、範囲制限
   - `backend/security/prosody_validator.py` 新規作成

### Phase 3: 中期対応（1週間以内）

6. **エラーハンドリングの強化**
   - 情報漏洩防止
   - `backend/security/error_handler.py` 新規作成

7. **セキュリティテストの作成**
   - 攻撃シナリオテスト
   - `backend/tests/security/test_prosody_security.py` 新規作成

8. **メトリクス監視の実装**
   - CPU、メモリ、処理時間の監視
   - Prometheus、Grafana統合

---

## 📊 セキュリティメトリクス（目標値）

| メトリクス | 現状 | 目標 | 期限 |
|-----------|------|------|------|
| ファイルサイズ制限 | 100MB | 50MB | 24時間 |
| 音声長制限 | なし | 5分 | 24時間 |
| 並列処理制限 | なし | 5並列 | 24時間 |
| オーディオボム検出 | なし | 100% | 3日 |
| Prosodyパラメータ検証 | 部分的 | 100% | 3日 |
| エラー情報漏洩 | あり | なし | 1週間 |

---

## 🧪 セキュリティテスト計画

### 1. ファイルサイズ攻撃テスト
```python
def test_file_size_attack():
    # 50MB超過ファイルをアップロード
    large_file = generate_audio(size=51 * 1024 * 1024)
    response = client.post("/api/clone", files={"audio_file": large_file})
    assert response.status_code == 400
    assert "ファイルサイズ" in response.json()["detail"]
```

### 2. オーディオボム攻撃テスト
```python
def test_audio_bomb():
    # 異常なサンプルレートのファイル
    audio_bomb = generate_audio_bomb(sample_rate=1000000, channels=256)
    response = client.post("/api/clone", files={"audio_file": audio_bomb})
    assert response.status_code == 400
    assert "異常な" in response.json()["detail"]
```

### 3. 並列処理攻撃テスト
```python
def test_concurrent_limit():
    # 10並列リクエスト送信
    tasks = [client.post("/api/clone/background", ...) for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 5件は成功、5件は429 (Too Many Requests)
    success = sum(1 for r in results if r.status_code == 200)
    rate_limited = sum(1 for r in results if r.status_code == 429)
    assert success == 5
    assert rate_limited == 5
```

### 4. Prosodyパラメータ攻撃テスト
```python
def test_prosody_nan_inf():
    # NaN/Inf値を送信
    response = client.post("/api/unified-voice/synthesize", json={
        "text": "test",
        "pitch": float('nan'),
        "speed": float('inf')
    })
    assert response.status_code == 400
    assert "無効な値" in response.json()["detail"]
```

---

## 📖 セキュリティベストプラクティス

### 開発時の注意事項

1. **音声処理は必ずタイムアウト付きで実行**
   ```python
   async def process_audio_with_timeout(audio_data, timeout=30.0):
       try:
           return await asyncio.wait_for(process_audio(audio_data), timeout=timeout)
       except asyncio.TimeoutError:
           raise HTTPException(408, "音声処理がタイムアウトしました")
   ```

2. **メモリ使用量を監視**
   ```python
   import psutil

   def check_memory_usage():
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024
       if memory_mb > 500:  # 500MB制限
           raise MemoryError(f"メモリ使用量超過: {memory_mb:.2f}MB")
   ```

3. **エラーメッセージは一般的に**
   ```python
   # ❌ Bad
   raise HTTPException(500, f"Error: {e}")

   # ✅ Good
   logger.error(f"Detailed error: {e}", exc_info=True)
   raise HTTPException(500, "音声処理中にエラーが発生しました")
   ```

4. **入力検証は複数レイヤーで**
   ```python
   # Layer 1: Pydantic (型、範囲)
   class SynthesisRequest(BaseModel):
       speed: float = Field(ge=0.5, le=2.0)

   # Layer 2: Custom validator (NaN/Inf)
   if not math.isfinite(request.speed):
       raise ValueError("Invalid speed value")

   # Layer 3: Business logic (実装状態確認)
   if prosody_not_implemented():
       raise NotImplementedError("Prosody adjustment not available")
   ```

---

## 🎯 Next Steps（次のアクション）

### 即時対応（今日中）
1. ✅ セキュリティ監査レポート作成（このドキュメント）
2. ⏳ `AudioValidator`実装
3. ⏳ `ProsodyValidator`実装
4. ⏳ `ResourceLimiter`実装

### 短期対応（今週中）
5. ⏳ セキュリティテスト作成
6. ⏳ エラーハンドリング強化
7. ⏳ 既存コードへの統合

### 中期対応（来週）
8. ⏳ メトリクス監視実装
9. ⏳ ドキュメント更新
10. ⏳ ペネトレーションテスト実施

---

## 📚 参考資料

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE-400: Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html)
- [Audio Bomb Detection Techniques](https://research.checkpoint.com/2019/reverse-engineering-audio-files/)

---

**Report Status**: 🟡 DRAFT
**Last Updated**: 2025-11-07
**Next Review**: Phase 1完了後（24時間後）

