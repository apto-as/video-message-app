"""
D-ID セキュリティテスト

Tests:
1. API Key検証
2. URL検証
3. 入力検証
4. ファイルアップロード検証
5. レート制限
6. Webhook検証
"""

import pytest
import time
from unittest.mock import Mock, patch
from security.d_id_validator import DIdValidator, validator
from security.webhook_verifier import WebhookVerifier, WebhookRateLimiter
from security.rate_limiter import UserRateLimiter, TokenBucket


class TestDIdValidator:
    """D-ID Validatorのテスト"""

    def test_valid_api_key(self):
        """有効なAPI Key形式"""
        # Base64エンコード済みの形式
        valid_keys = [
            "YmlsbEBuZXVyb2F4aXMuYWk6dXp1NzhGYUo=",
            "dGVzdDp0ZXN0a2V5MTIzNDU2Nzg5MA==",
            "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXowMTIzNDU2Nzg5"
        ]
        for key in valid_keys:
            assert DIdValidator.validate_api_key(key) is True

    def test_invalid_api_key(self):
        """無効なAPI Key形式"""
        invalid_keys = [
            None,
            "",
            "short",
            "invalid-format",
            "contains spaces",
            123,  # 数値
            []    # リスト
        ]
        for key in invalid_keys:
            assert DIdValidator.validate_api_key(key) is False

    def test_valid_d_id_urls(self):
        """有効なD-ID URL"""
        valid_urls = [
            "https://api.d-id.com/talks",
            "https://static-assets.d-id.com/image.jpg",
            "https://create-images-results.d-id.com/video.mp4",
            "https://subdomain.d-id.com/path/to/resource"
        ]
        for url in valid_urls:
            assert DIdValidator.validate_d_id_url(url) is True

    def test_invalid_d_id_urls(self):
        """無効なD-ID URL"""
        invalid_urls = [
            "",
            "http://api.d-id.com/talks",  # HTTPは不可
            "https://malicious.com/phishing",
            "https://d-id.com.evil.com/fake",
            "javascript:alert('xss')",
            "file:///etc/passwd"
        ]
        for url in invalid_urls:
            assert DIdValidator.validate_d_id_url(url) is False

    def test_image_upload_validation(self):
        """画像アップロードの検証"""
        # 有効な画像
        result = DIdValidator.validate_image_upload(
            content_type="image/jpeg",
            file_size=1024 * 1024,  # 1MB
            filename="photo.jpg"
        )
        assert result["valid"] is True

        # ファイルサイズ超過
        result = DIdValidator.validate_image_upload(
            content_type="image/jpeg",
            file_size=20 * 1024 * 1024,  # 20MB (MAX: 10MB)
            filename="large.jpg"
        )
        assert result["valid"] is False
        assert "too large" in result["errors"][0].lower()

        # 無効なContent-Type
        result = DIdValidator.validate_image_upload(
            content_type="application/pdf",
            file_size=1024,
            filename="not_image.pdf"
        )
        assert result["valid"] is False

        # パストラバーサル攻撃
        result = DIdValidator.validate_image_upload(
            content_type="image/jpeg",
            file_size=1024,
            filename="../../../etc/passwd"
        )
        assert result["valid"] is False
        assert "path traversal" in result["errors"][0].lower()

    def test_audio_upload_validation(self):
        """音声アップロードの検証"""
        # 有効な音声
        result = DIdValidator.validate_audio_upload(
            content_type="audio/wav",
            file_size=5 * 1024 * 1024,  # 5MB
            filename="voice.wav"
        )
        assert result["valid"] is True

        # ファイルサイズ超過
        result = DIdValidator.validate_audio_upload(
            content_type="audio/wav",
            file_size=60 * 1024 * 1024,  # 60MB (MAX: 50MB)
            filename="large.wav"
        )
        assert result["valid"] is False

    def test_text_input_validation(self):
        """テキスト入力の検証"""
        # 正常なテキスト
        result = DIdValidator.validate_text_input("こんにちは、世界！", "greeting")
        assert result["valid"] is True

        # XSS攻撃
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "eval('malicious code')"
        ]
        for payload in xss_payloads:
            result = DIdValidator.validate_text_input(payload, "text")
            assert result["valid"] is False

        # 長さ超過
        long_text = "A" * 20000  # MAX: 10,000
        result = DIdValidator.validate_text_input(long_text, "text")
        assert result["valid"] is False

    def test_talk_id_validation(self):
        """Talk ID検証"""
        # 有効なTalk ID
        valid_ids = [
            "tlk_123456789abcdef",
            "abcd-1234-efgh-5678",
            "TalkID12345"
        ]
        for talk_id in valid_ids:
            assert DIdValidator.validate_talk_id(talk_id) is True

        # 無効なTalk ID
        invalid_ids = [
            "",
            "short",
            "contains spaces",
            "../../etc/passwd",
            "<script>alert(1)</script>"
        ]
        for talk_id in invalid_ids:
            assert DIdValidator.validate_talk_id(talk_id) is False

    def test_sanitize_error_message(self):
        """エラーメッセージのサニタイズ"""
        # API Key漏洩防止
        error_with_key = "Authentication failed: YmlsbEBuZXVyb2F4aXMuYWk6dXp1NzhGYUo="
        sanitized = DIdValidator.sanitize_error_message(error_with_key)
        assert "YmlsbEBuZXVyb2F4aXMuYWk6dXp1NzhGYUo=" not in sanitized
        assert "[REDACTED]" in sanitized

        # URL漏洩防止
        error_with_url = "Failed to upload: https://api.d-id.com/upload?token=secret123"
        sanitized = DIdValidator.sanitize_error_message(error_with_url)
        assert "secret123" not in sanitized


class TestWebhookVerifier:
    """Webhook検証のテスト"""

    def setup_method(self):
        """各テストの前に実行"""
        self.secret = "test_webhook_secret_12345"
        self.verifier = WebhookVerifier(self.secret)

    def test_valid_signature(self):
        """有効な署名の検証"""
        payload = b'{"id":"talk_123","status":"done"}'
        signature = self.verifier._compute_signature(payload)

        is_valid, error = self.verifier.verify_signature(payload, signature)
        assert is_valid is True
        assert error is None

    def test_invalid_signature(self):
        """無効な署名の検証"""
        payload = b'{"id":"talk_123","status":"done"}'
        wrong_signature = "0000000000000000000000000000000000000000"

        is_valid, error = self.verifier.verify_signature(payload, wrong_signature)
        assert is_valid is False
        assert "Invalid signature" in error

    def test_missing_signature(self):
        """署名ヘッダーなし"""
        payload = b'{"id":"talk_123","status":"done"}'

        is_valid, error = self.verifier.verify_signature(payload, "")
        assert is_valid is False
        assert "missing" in error.lower()

    def test_timestamp_validation(self):
        """タイムスタンプ検証"""
        # 現在時刻
        current_timestamp = str(int(time.time()))
        assert self.verifier._verify_timestamp(current_timestamp) is True

        # 古すぎるタイムスタンプ（6分前）
        old_timestamp = str(int(time.time()) - 360)
        assert self.verifier._verify_timestamp(old_timestamp) is False

    def test_payload_validation(self):
        """ペイロード検証"""
        # 有効なペイロード
        valid_payload = {
            "id": "talk_123456",
            "status": "done",
            "created_at": "2025-01-01T00:00:00Z"
        }
        is_valid, error = self.verifier.verify_webhook_payload(valid_payload)
        assert is_valid is True

        # 必須フィールド欠如
        invalid_payload = {
            "status": "done"
        }
        is_valid, error = self.verifier.verify_webhook_payload(invalid_payload)
        assert is_valid is False
        assert "Missing required field" in error

        # 無効なステータス
        invalid_status = {
            "id": "talk_123",
            "status": "unknown_status",
            "created_at": "2025-01-01T00:00:00Z"
        }
        is_valid, error = self.verifier.verify_webhook_payload(invalid_status)
        assert is_valid is False


class TestWebhookRateLimiter:
    """Webhookレート制限のテスト"""

    def setup_method(self):
        """各テストの前に実行"""
        self.limiter = WebhookRateLimiter(max_requests=5, time_window=10)

    def test_rate_limit_allow(self):
        """レート制限内のリクエスト"""
        identifier = "192.168.1.100"

        # 最初の5リクエストは許可
        for i in range(5):
            assert self.limiter.is_allowed(identifier) is True

    def test_rate_limit_exceed(self):
        """レート制限超過"""
        identifier = "192.168.1.100"

        # 5リクエスト許可
        for i in range(5):
            self.limiter.is_allowed(identifier)

        # 6番目は拒否
        assert self.limiter.is_allowed(identifier) is False

    def test_rate_limit_recovery(self):
        """レート制限の回復"""
        identifier = "192.168.1.100"

        # 5リクエスト
        for i in range(5):
            self.limiter.is_allowed(identifier)

        # 6番目は拒否
        assert self.limiter.is_allowed(identifier) is False

        # 10秒待機（time_window）
        time.sleep(10)

        # 回復して許可されるはず
        assert self.limiter.is_allowed(identifier) is True


class TestUserRateLimiter:
    """ユーザーレート制限のテスト"""

    def setup_method(self):
        """各テストの前に実行"""
        self.limiter = UserRateLimiter()

    def test_token_bucket(self):
        """トークンバケットアルゴリズム"""
        bucket = TokenBucket(rate=1.0, capacity=5)  # 毎秒1トークン、容量5

        # 5トークン消費（成功）
        for i in range(5):
            assert bucket.consume(1) is True

        # 6トークン目は失敗（容量超過）
        assert bucket.consume(1) is False

        # 1秒待機
        time.sleep(1)

        # トークンが補充されて1トークン消費可能
        assert bucket.consume(1) is True

    def test_rate_limit_per_endpoint(self):
        """エンドポイント別のレート制限"""
        identifier = "test_user_001"
        endpoint = "/api/d-id/generate-video"

        # 初回リクエストは許可
        allowed, error, retry_after = self.limiter.check_rate_limit(identifier, endpoint)
        assert allowed is True

    def test_anomaly_detection(self):
        """異常検出"""
        identifier = "attacker_001"

        # 短時間に大量のリクエスト（10リクエスト/10秒未満）
        for i in range(10):
            self.limiter.request_history[identifier].append(time.time())

        # 異常検出
        is_anomaly = self.limiter._detect_anomaly(identifier)
        assert is_anomaly is True

    def test_block_user(self):
        """ユーザーブロック"""
        identifier = "blocked_user_001"

        # ブロック
        self.limiter.block_user(identifier, duration_seconds=1)

        # ブロック中
        assert self.limiter.is_blocked(identifier) is True

        # 1秒待機
        time.sleep(1)

        # ブロック解除
        assert self.limiter.is_blocked(identifier) is False


class TestIntegration:
    """統合テスト"""

    def test_end_to_end_video_generation_security(self):
        """動画生成のエンドツーエンドセキュリティ"""
        # 1. API Key検証
        api_key = "YmlsbEBuZXVyb2F4aXMuYWk6dXp1NzhGYUo="
        assert DIdValidator.validate_api_key(api_key) is True

        # 2. 画像URL検証
        image_url = "https://static-assets.d-id.com/test.jpg"
        assert DIdValidator.validate_d_id_url(image_url) is True

        # 3. 音声URL検証
        audio_url = "https://api.d-id.com/audio/test.wav"
        assert DIdValidator.validate_d_id_url(audio_url) is True

        # 4. レート制限チェック
        limiter = UserRateLimiter()
        identifier = "test_user_integration"
        endpoint = "/api/d-id/generate-video"

        allowed, error, retry_after = limiter.check_rate_limit(identifier, endpoint)
        assert allowed is True

    def test_webhook_security_flow(self):
        """Webhookセキュリティフロー"""
        secret = "webhook_secret_test"
        verifier = WebhookVerifier(secret)

        # 1. ペイロード作成
        payload = b'{"id":"talk_test_123","status":"done","created_at":"2025-01-01T00:00:00Z"}'

        # 2. 署名生成
        signature = verifier._compute_signature(payload)

        # 3. タイムスタンプ検証
        timestamp = str(int(time.time()))
        assert verifier._verify_timestamp(timestamp) is True

        # 4. 署名検証
        is_valid, error = verifier.verify_signature(payload, signature, timestamp)
        assert is_valid is True

        # 5. ペイロード検証
        import json
        payload_dict = json.loads(payload)
        is_valid, error = verifier.verify_webhook_payload(payload_dict)
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
