"""
レート制限ミドルウェア（D-ID API保護）

CRITICAL SECURITY RULES:
1. ユーザーごとにレート制限を適用
2. 異常なリクエスト頻度を検出
3. DoS攻撃を防止
4. リソース枯渇を防止
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """レート制限設定"""

    # エンドポイント別のレート制限
    LIMITS = {
        "/api/d-id/generate-video": {
            "requests_per_minute": 5,   # 1分間に5回
            "requests_per_hour": 30,    # 1時間に30回
            "burst_size": 2             # 瞬間的に許可する最大リクエスト数
        },
        "/api/d-id/upload-source-image": {
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "burst_size": 3
        },
        "/api/d-id/upload-audio": {
            "requests_per_minute": 10,
            "requests_per_hour": 100,
            "burst_size": 3
        },
        "/api/d-id/talk-status": {
            "requests_per_minute": 30,
            "requests_per_hour": 300,
            "burst_size": 10
        },
        # デフォルト設定
        "default": {
            "requests_per_minute": 20,
            "requests_per_hour": 200,
            "burst_size": 5
        }
    }


class TokenBucket:
    """トークンバケットアルゴリズム実装"""

    def __init__(self, rate: float, capacity: int):
        """
        初期化

        Args:
            rate: トークン補充レート（トークン/秒）
            capacity: バケット容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        トークンを消費

        Args:
            tokens: 消費するトークン数

        Returns:
            消費できた場合True
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """トークンを補充"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def get_remaining(self) -> int:
        """残りトークン数を取得"""
        self._refill()
        return int(self.tokens)


class UserRateLimiter:
    """ユーザー別レート制限"""

    def __init__(self):
        # ユーザーごとのトークンバケット
        self.buckets: Dict[str, Dict[str, TokenBucket]] = defaultdict(dict)

        # リクエスト履歴（異常検出用）
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # ブロックリスト
        self.blocked_until: Dict[str, datetime] = {}

    def get_identifier(self, request: Request) -> str:
        """
        ユーザー識別子を取得

        Args:
            request: FastAPIリクエスト

        Returns:
            識別子（IP + User-Agent）
        """
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")[:50]

        # TODO: 認証実装後は user_id を使用
        # if hasattr(request.state, "user_id"):
        #     return f"user:{request.state.user_id}"

        return f"ip:{client_ip}:{hash(user_agent)}"

    def is_blocked(self, identifier: str) -> bool:
        """
        ブロックされているかチェック

        Args:
            identifier: ユーザー識別子

        Returns:
            ブロック中の場合True
        """
        if identifier in self.blocked_until:
            if datetime.now() < self.blocked_until[identifier]:
                return True
            else:
                del self.blocked_until[identifier]

        return False

    def block_user(self, identifier: str, duration_seconds: int = 3600):
        """
        ユーザーをブロック

        Args:
            identifier: ユーザー識別子
            duration_seconds: ブロック期間（秒）
        """
        self.blocked_until[identifier] = datetime.now() + timedelta(seconds=duration_seconds)
        logger.warning(f"User blocked for {duration_seconds}s: {identifier}")

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str
    ) -> Tuple[bool, Optional[str], int]:
        """
        レート制限をチェック

        Args:
            identifier: ユーザー識別子
            endpoint: エンドポイント

        Returns:
            (許可するか, エラーメッセージ, リトライまでの秒数)
        """
        # ブロックチェック
        if self.is_blocked(identifier):
            remaining = (self.blocked_until[identifier] - datetime.now()).total_seconds()
            return False, "Too many requests. You are temporarily blocked.", int(remaining)

        # エンドポイント別の設定を取得
        config = RateLimitConfig.LIMITS.get(endpoint, RateLimitConfig.LIMITS["default"])

        # 分単位のバケット
        minute_key = f"{endpoint}:minute"
        if minute_key not in self.buckets[identifier]:
            self.buckets[identifier][minute_key] = TokenBucket(
                rate=config["requests_per_minute"] / 60.0,
                capacity=config["burst_size"]
            )

        # 時間単位のバケット
        hour_key = f"{endpoint}:hour"
        if hour_key not in self.buckets[identifier]:
            self.buckets[identifier][hour_key] = TokenBucket(
                rate=config["requests_per_hour"] / 3600.0,
                capacity=config["requests_per_hour"]
            )

        # 分単位チェック
        minute_bucket = self.buckets[identifier][minute_key]
        if not minute_bucket.consume():
            retry_after = 60 / config["requests_per_minute"]
            return False, "Rate limit exceeded (per minute)", int(retry_after)

        # 時間単位チェック
        hour_bucket = self.buckets[identifier][hour_key]
        if not hour_bucket.consume():
            retry_after = 3600 / config["requests_per_hour"]
            return False, "Rate limit exceeded (per hour)", int(retry_after)

        # リクエスト履歴に記録
        self.request_history[identifier].append(time.time())

        # 異常パターン検出
        if self._detect_anomaly(identifier):
            self.block_user(identifier, duration_seconds=3600)
            return False, "Abnormal request pattern detected. You are temporarily blocked.", 3600

        return True, None, 0

    def _detect_anomaly(self, identifier: str) -> bool:
        """
        異常なリクエストパターンを検出

        Args:
            identifier: ユーザー識別子

        Returns:
            異常がある場合True
        """
        history = self.request_history[identifier]

        if len(history) < 10:
            return False

        # 最後の10リクエストが10秒以内の場合（毎秒1リクエスト以上）
        recent_requests = list(history)[-10:]
        time_span = recent_requests[-1] - recent_requests[0]

        if time_span < 10:
            logger.warning(f"Anomaly detected: 10 requests in {time_span:.2f}s for {identifier}")
            return True

        return False

    def get_remaining_quota(self, identifier: str, endpoint: str) -> Dict[str, int]:
        """
        残りクォータを取得

        Args:
            identifier: ユーザー識別子
            endpoint: エンドポイント

        Returns:
            残りクォータ情報
        """
        config = RateLimitConfig.LIMITS.get(endpoint, RateLimitConfig.LIMITS["default"])

        minute_key = f"{endpoint}:minute"
        hour_key = f"{endpoint}:hour"

        minute_remaining = 0
        hour_remaining = 0

        if minute_key in self.buckets.get(identifier, {}):
            minute_remaining = self.buckets[identifier][minute_key].get_remaining()

        if hour_key in self.buckets.get(identifier, {}):
            hour_remaining = self.buckets[identifier][hour_key].get_remaining()

        return {
            "minute_remaining": minute_remaining,
            "minute_limit": config["requests_per_minute"],
            "hour_remaining": hour_remaining,
            "hour_limit": config["requests_per_hour"]
        }


# グローバルインスタンス
rate_limiter = UserRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI用レート制限ミドルウェア"""

    async def dispatch(self, request: Request, call_next):
        # D-ID APIエンドポイントのみチェック
        if not request.url.path.startswith("/api/d-id/"):
            return await call_next(request)

        # ヘルスチェックは除外
        if request.url.path.endswith("/health"):
            return await call_next(request)

        identifier = rate_limiter.get_identifier(request)
        endpoint = request.url.path

        allowed, error_message, retry_after = rate_limiter.check_rate_limit(identifier, endpoint)

        if not allowed:
            logger.warning(f"Rate limit exceeded: {identifier} -> {endpoint}")

            # クォータ情報を取得
            quota = rate_limiter.get_remaining_quota(identifier, endpoint)

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": error_message,
                    "retry_after": retry_after,
                    "quota": quota
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Remaining-Minute": str(quota["minute_remaining"]),
                    "X-RateLimit-Remaining-Hour": str(quota["hour_remaining"])
                }
            )

        # リクエストを処理
        response = await call_next(request)

        # レスポンスヘッダーにクォータ情報を追加
        quota = rate_limiter.get_remaining_quota(identifier, endpoint)
        response.headers["X-RateLimit-Remaining-Minute"] = str(quota["minute_remaining"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(quota["hour_remaining"])

        return response
