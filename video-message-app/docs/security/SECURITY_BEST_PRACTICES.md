# セキュリティベストプラクティスガイド

**対象**: Video Message App - Audio Processing & Prosody Adjustment
**作成日**: 2025-11-07
**対象者**: 開発者、デプロイ担当者

---

## 📋 目次

1. [音声ファイルアップロード時のセキュリティ](#音声ファイルアップロード時のセキュリティ)
2. [Prosody調整機能のセキュリティ](#prosody調整機能のセキュリティ)
3. [リソース管理とDoS対策](#リソース管理とdos対策)
4. [エラーハンドリングとロギング](#エラーハンドリングとロギング)
5. [デプロイ時のセキュリティチェックリスト](#デプロイ時のセキュリティチェックリスト)
6. [セキュリティモニタリング](#セキュリティモニタリング)

---

## 音声ファイルアップロード時のセキュリティ

### 必須チェック項目

#### 1. ファイルサイズ制限

```python
from security.audio_validator import AudioValidator

# ファイルサイズチェック
is_valid, error_msg = AudioValidator.validate_file_size(
    file_size=file.size,
    strict=True  # 推奨サイズ(10MB)を超えたら警告
)

if not is_valid:
    raise HTTPException(400, error_msg)
```

**推奨設定**:
- **最大サイズ**: 50MB（CRITICAL制限）
- **推奨サイズ**: 10MB（ほとんどのユースケースで十分）
- **最小サイズ**: 100バイト

#### 2. 音声長制限

```python
# 音声長チェック（ユースケース別）
is_valid, error_msg = AudioValidator.validate_duration(
    duration=audio_info["duration"],
    use_case="voice_clone"  # "voice_clone" | "synthesis" | "general"
)

if not is_valid:
    raise HTTPException(400, error_msg)
```

**推奨設定**:
- **音声クローン用**: 10秒〜30秒（推奨）
- **音声合成用**: 最大5分
- **一般用途**: 最大5分

#### 3. オーディオボム検出

```python
# 包括的な音声ファイル検証
is_valid, error_msg, audio_info = AudioValidator.validate_audio_file_comprehensive(
    file_path=temp_file_path,
    file_size=file.size,
    content_type=file.content_type,
    filename=file.filename,
    use_case="voice_clone",
    strict=True
)

if not is_valid:
    # セキュリティイベントログ
    SecureErrorHandler.log_security_event(
        event_type="audio_validation_failed",
        severity="medium",
        details={"file": file.filename, "error": error_msg}
    )
    raise HTTPException(400, error_msg)
```

**検出項目**:
- ✅ 異常なサンプルレート（8kHz〜48kHz範囲外）
- ✅ 異常なビットレート（320kbps超過）
- ✅ 異常なチャンネル数（モノラル/ステレオ以外）
- ✅ WAVヘッダー改ざん

---

## Prosody調整機能のセキュリティ

### 必須チェック項目

#### 1. パラメータ範囲検証

```python
from security.prosody_validator import ProsodyValidator

# すべてのProsodyパラメータを一括検証
is_valid, error_msg = ProsodyValidator.validate_all(
    pitch=request.pitch,
    speed=request.speed,
    volume_linear=request.volume,
    pause=request.pause,
    strict=True  # 推奨範囲も検証
)

if not is_valid:
    raise SecureErrorHandler.handle_validation_error("prosody_params", error_msg)
```

**推奨範囲**:
- **ピッチシフト**: ±3 semitones（自然な音程変化）
- **速度**: 0.8x 〜 1.2x（自然な速度変化）
- **音量**: ±6dB（安全な音量変化）
- **ポーズ**: 0 〜 0.5秒（自然なポーズ）

#### 2. NaN/Inf値の検出

```python
# NaN/Inf値を含むリクエストを拒否
if not math.isfinite(request.pitch):
    raise HTTPException(400, "ピッチに無効な値が含まれています")

# または、サニタイズ（安全な値にリセット）
sanitized = ProsodyValidator.sanitize_prosody_params(
    pitch=request.pitch,
    speed=request.speed,
    volume_linear=request.volume,
    pause=request.pause
)
```

#### 3. 実装状態チェック

```python
# 未実装の機能を使用しようとした場合はエラー
is_valid, error_msg = ProsodyValidator.validate_with_implementation_check(
    pitch=request.pitch,
    speed=request.speed,
    volume_linear=request.volume,
    pause=request.pause
)

if not is_valid:
    raise HTTPException(501, error_msg)  # 501 Not Implemented
```

---

## リソース管理とDoS対策

### 必須実装項目

#### 1. 並列処理制限

```python
from security.resource_limiter import voice_clone_limiter

# 音声クローン処理（重い処理）
@router.post("/clone")
async def clone_voice(...):
    try:
        async with voice_clone_limiter.acquire(timeout=60.0):
            # 保護された処理
            result = await perform_voice_cloning(audio_data)
            return result

    except asyncio.TimeoutError:
        raise SecureErrorHandler.handle_resource_error("timeout")

    except MemoryError:
        raise SecureErrorHandler.handle_resource_error("memory")
```

**推奨設定**:
- **音声クローン**: 最大3並列、タイムアウト60秒
- **音声合成**: 最大5並列、タイムアウト30秒
- **Prosody調整**: 最大10並列、タイムアウト15秒

#### 2. メモリ監視

```python
# ResourceLimiterが自動的にメモリをチェック
# 設定値を超えた場合はMemoryErrorを発生
limiter = ResourceLimiter(
    max_concurrent=5,
    default_timeout=30.0,
    max_memory_mb=500.0,  # 500MB制限
    max_cpu_percent=80.0,
    name="voice_synthesis"
)
```

#### 3. タイムアウト処理

```python
# タイムアウト付きで処理実行
try:
    result = await limiter.execute_with_timeout(
        expensive_operation(),
        timeout=30.0
    )
except asyncio.TimeoutError:
    logger.error("Processing timeout")
    raise HTTPException(408, "処理がタイムアウトしました")
```

---

## エラーハンドリングとロギング

### 必須実装項目

#### 1. セキュアなエラーメッセージ

```python
from security.error_handler import SecureErrorHandler

# 本番環境では詳細を隠す
SecureErrorHandler.set_debug_mode(debug=False)  # 本番環境

try:
    result = process_audio(file)
except Exception as e:
    # 詳細はサーバーログにのみ記録
    exc = SecureErrorHandler.handle_audio_processing_error(
        e,
        context="voice_clone"
    )
    raise exc
```

**NG例**（情報漏洩）:
```python
# ❌ Bad
except Exception as e:
    raise HTTPException(500, f"Error: {str(e)}")
    # → スタックトレース、パス情報が露出

# ✅ Good
except Exception as e:
    logger.error(f"Detailed error: {e}", exc_info=True)
    raise HTTPException(500, "音声処理中にエラーが発生しました")
```

#### 2. セキュリティイベントログ

```python
# オーディオボム検出時
if not is_safe:
    SecureErrorHandler.log_security_event(
        event_type="audio_bomb_detected",
        severity="high",
        details={
            "file": file.filename,
            "sample_rate": audio_info["sample_rate"],
            "channels": audio_info["channels"]
        }
    )
    raise HTTPException(400, "異常な音声ファイルが検出されました")
```

**セキュリティイベントの重要度**:
- **critical**: 即座に対応が必要（例: 認証情報漏洩）
- **high**: 24時間以内に対応（例: オーディオボム検出）
- **medium**: 3日以内に対応（例: レート制限超過）
- **low**: 記録のみ（例: 推奨範囲外のパラメータ）

#### 3. ログレベルの適切な使用

```python
import logging

logger = logging.getLogger(__name__)

# ❌ Bad: 機密情報をINFOレベルでログ
logger.info(f"User API key: {api_key}")

# ✅ Good: 適切なレベルと情報のマスキング
logger.debug(f"User API key: {mask_api_key(api_key)}")  # DEBUGレベル
logger.info(f"User authentication successful: user_id={user_id}")  # IDのみ
```

---

## デプロイ時のセキュリティチェックリスト

### Phase 1: 開発環境

- [ ] すべてのセキュリティモジュールがインポート可能か確認
- [ ] セキュリティテストが成功するか確認
- [ ] デバッグモードが有効になっているか確認（`DEBUG=True`）
- [ ] ファイルサイズ制限が適切に設定されているか確認

### Phase 2: ステージング環境

- [ ] デバッグモードが無効になっているか確認（`DEBUG=False`）
- [ ] リソース制限が本番相当に設定されているか確認
- [ ] エラーメッセージに機密情報が含まれていないか確認
- [ ] セキュリティイベントログが正しく記録されているか確認
- [ ] 負荷テストを実施してリソース枯渇攻撃を確認

### Phase 3: 本番環境

- [ ] HTTPS強制が有効になっているか確認
- [ ] セキュリティヘッダーが設定されているか確認
- [ ] レート制限が有効になっているか確認
- [ ] メモリ/CPU監視が有効になっているか確認
- [ ] セキュリティアラートの通知先が設定されているか確認

### デプロイ後の確認

```bash
# 1. セキュリティモジュールの動作確認
curl -X POST http://localhost:55433/api/health/security

# 2. リソース制限の確認
curl http://localhost:55433/api/metrics/limiters

# 3. エラーハンドリングの確認（意図的にエラー発生）
curl -X POST http://localhost:55433/api/test/validation-error

# 4. ログの確認
tail -f /var/log/video-message-app/security.log | grep "SECURITY EVENT"
```

---

## セキュリティモニタリング

### メトリクス監視

#### 1. リソース使用状況

```python
from security.resource_limiter import get_system_metrics

# システム全体のメトリクスを取得
metrics = get_system_metrics()

# Prometheus形式でエクスポート（推奨）
"""
# HELP video_app_active_tasks Number of active tasks
# TYPE video_app_active_tasks gauge
video_app_active_tasks{limiter="voice_clone"} 2
video_app_active_tasks{limiter="voice_synthesis"} 5

# HELP video_app_memory_usage Memory usage in MB
# TYPE video_app_memory_usage gauge
video_app_memory_usage{process="main"} 450.2

# HELP video_app_cpu_percent CPU usage percentage
# TYPE video_app_cpu_percent gauge
video_app_cpu_percent{process="main"} 65.3
"""
```

#### 2. セキュリティイベント統計

```python
# セキュリティイベントの集計
security_events = {
    "audio_bomb_detected": 3,
    "rate_limit_exceeded": 15,
    "validation_failed": 42,
    "timeout": 8
}

# アラート条件
if security_events["audio_bomb_detected"] > 10:
    send_alert("High number of audio bomb attacks detected")

if security_events["timeout"] > 20:
    send_alert("High number of timeouts - possible DoS attack")
```

### アラート設定（推奨）

| メトリクス | 警告閾値 | 緊急閾値 | アクション |
|-----------|---------|---------|-----------|
| オーディオボム検出 | 10件/時間 | 50件/時間 | IP制限検討 |
| タイムアウト | 20件/時間 | 100件/時間 | リソース増強 |
| メモリ使用率 | 80% | 95% | 即座にスケールアウト |
| CPU使用率 | 80% | 95% | 即座にスケールアウト |
| 並列処理キュー | 10件待機 | 50件待機 | リソース増強 |

---

## 定期的なセキュリティレビュー

### 週次チェック

- [ ] セキュリティイベントログの確認
- [ ] リソース使用状況の確認
- [ ] エラー率の確認
- [ ] タイムアウト率の確認

### 月次チェック

- [ ] セキュリティテストの実行
- [ ] 依存関係の脆弱性スキャン（`pip-audit`）
- [ ] ペネトレーションテストの実施
- [ ] セキュリティメトリクスのレビュー

### 四半期チェック

- [ ] セキュリティポリシーの見直し
- [ ] インシデント対応計画の見直し
- [ ] セキュリティトレーニングの実施
- [ ] 外部セキュリティ監査（推奨）

---

## 緊急時の対応

### オーディオボム攻撃検出時

1. **即座の対応**（5分以内）:
   ```bash
   # 攻撃元IPのブロック
   iptables -A INPUT -s <攻撃元IP> -j DROP

   # リクエストレート制限の強化
   nginx -s reload  # rate_limit設定を厳格化
   ```

2. **短期対応**（1時間以内）:
   - セキュリティイベントログの詳細分析
   - 攻撃パターンの特定
   - 追加のIP制限

3. **中期対応**（24時間以内）:
   - 検証ロジックの強化
   - モニタリングの改善
   - インシデントレポート作成

### DoS攻撃検出時

1. **即座の対応**:
   ```python
   # リソース制限の即座の引き下げ
   voice_clone_limiter.max_concurrent = 1  # 3 → 1
   voice_synthesis_limiter.max_concurrent = 2  # 5 → 2
   ```

2. **短期対応**:
   - 攻撃元の特定とブロック
   - CDN/WAFの設定強化
   - スケールアウト検討

3. **中期対応**:
   - レート制限の見直し
   - リソース配分の最適化
   - インシデントレポート作成

---

## 参考資料

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [CWE-400: Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Next Review**: 2025-12-07
