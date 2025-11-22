"""
D-ID Webhook 署名検証

CRITICAL SECURITY RULES:
1. すべてのWebhookリクエストで署名を検証
2. リプレイ攻撃を防止（タイムスタンプ検証）
3. 署名シークレットはログに出力しない
4. 不正なリクエストは即座にreject

References:
- D-ID Webhook Documentation: https://docs.d-id.com/reference/webhooks
"""

import hmac
import hashlib
import time
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class WebhookVerifier:
    """D-ID Webhook署名検証クラス"""

    # タイムスタンプ許容範囲（秒）
    TIMESTAMP_TOLERANCE = 300  # 5分

    def __init__(self, webhook_secret: Optional[str] = None):
        """
        初期化

        Args:
            webhook_secret: Webhook署名用のシークレット
        """
        self.webhook_secret = webhook_secret
        if not webhook_secret:
            logger.warning("Webhook secret is not configured. Webhook verification will fail.")

    def verify_signature(
        self,
        payload: bytes,
        signature_header: str,
        timestamp_header: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Webhook署名を検証

        Args:
            payload: リクエストボディ（生のバイト列）
            signature_header: X-D-ID-Signatureヘッダーの値
            timestamp_header: X-D-ID-Timestampヘッダーの値（オプション）

        Returns:
            (検証結果, エラーメッセージ)
        """
        # シークレットが設定されていない場合
        if not self.webhook_secret:
            return False, "Webhook secret is not configured"

        # 署名ヘッダーが空の場合
        if not signature_header:
            logger.warning("Webhook signature header is missing")
            return False, "Signature header is missing"

        try:
            # タイムスタンプ検証（リプレイ攻撃防止）
            if timestamp_header:
                if not self._verify_timestamp(timestamp_header):
                    logger.warning(f"Webhook timestamp is invalid or too old: {timestamp_header}")
                    return False, "Timestamp is invalid or too old"

            # 署名を計算
            expected_signature = self._compute_signature(payload)

            # 署名を比較（タイミング攻撃対策）
            if not hmac.compare_digest(signature_header, expected_signature):
                logger.warning("Webhook signature verification failed")
                return False, "Invalid signature"

            logger.info("Webhook signature verified successfully")
            return True, None

        except Exception as e:
            logger.error(f"Webhook verification error: {str(e)}")
            return False, "Verification error"

    def _compute_signature(self, payload: bytes) -> str:
        """
        HMAC-SHA256署名を計算

        Args:
            payload: リクエストボディ

        Returns:
            署名（hexダイジェスト）
        """
        mac = hmac.new(
            self.webhook_secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        )
        return mac.hexdigest()

    def _verify_timestamp(self, timestamp_str: str) -> bool:
        """
        タイムスタンプを検証（リプレイ攻撃防止）

        Args:
            timestamp_str: ISO 8601形式のタイムスタンプ、またはUnixタイムスタンプ

        Returns:
            有効な範囲内の場合True
        """
        try:
            # Unix timestampとして解析を試みる
            try:
                timestamp = int(timestamp_str)
                webhook_time = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                # ISO 8601形式として解析
                webhook_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            current_time = datetime.now(webhook_time.tzinfo) if webhook_time.tzinfo else datetime.now()

            time_diff = abs((current_time - webhook_time).total_seconds())

            if time_diff > self.TIMESTAMP_TOLERANCE:
                logger.warning(f"Timestamp too old: {time_diff} seconds (max: {self.TIMESTAMP_TOLERANCE})")
                return False

            return True

        except Exception as e:
            logger.error(f"Timestamp parsing error: {str(e)}")
            return False

    def verify_webhook_payload(self, payload_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Webhookペイロードの内容を検証

        Args:
            payload_dict: パースされたJSONペイロード

        Returns:
            (検証結果, エラーメッセージ)
        """
        required_fields = ["id", "status", "created_at"]

        # 必須フィールドの検証
        for field in required_fields:
            if field not in payload_dict:
                logger.warning(f"Missing required field: {field}")
                return False, f"Missing required field: {field}"

        # IDの形式検証
        talk_id = payload_dict.get("id")
        if not isinstance(talk_id, str) or len(talk_id) < 10:
            logger.warning(f"Invalid talk ID format: {talk_id}")
            return False, "Invalid talk ID format"

        # ステータスの検証
        valid_statuses = {"created", "started", "done", "error", "rejected"}
        status = payload_dict.get("status")
        if status not in valid_statuses:
            logger.warning(f"Invalid status: {status}")
            return False, f"Invalid status: {status}"

        return True, None


class WebhookRateLimiter:
    """Webhook用レート制限（DoS対策）"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        初期化

        Args:
            max_requests: 時間枠内の最大リクエスト数
            time_window: 時間枠（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}  # IP別のリクエストタイムスタンプ

    def is_allowed(self, identifier: str) -> bool:
        """
        リクエストを許可するか判定

        Args:
            identifier: 識別子（通常はIPアドレス）

        Returns:
            許可する場合True
        """
        current_time = time.time()

        # 識別子ごとのリクエスト履歴を取得
        if identifier not in self.requests:
            self.requests[identifier] = []

        # 古いリクエストを削除
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.time_window
        ]

        # レート制限チェック
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{len(self.requests[identifier])} requests in {self.time_window}s"
            )
            return False

        # 新しいリクエストを記録
        self.requests[identifier].append(current_time)
        return True

    def cleanup_old_entries(self):
        """古いエントリを削除（メモリリーク防止）"""
        current_time = time.time()
        cleanup_threshold = current_time - (self.time_window * 2)

        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cleanup_threshold
            ]

            # 空のエントリを削除
            if not self.requests[identifier]:
                del self.requests[identifier]


# デフォルトインスタンス
webhook_verifier = None  # 初期化は環境変数読み込み後
webhook_rate_limiter = WebhookRateLimiter(max_requests=100, time_window=60)


def initialize_webhook_verifier(webhook_secret: str):
    """
    Webhook検証を初期化（起動時に一度だけ呼ぶ）

    Args:
        webhook_secret: Webhook署名用のシークレット
    """
    global webhook_verifier
    webhook_verifier = WebhookVerifier(webhook_secret)
    logger.info("Webhook verifier initialized")
