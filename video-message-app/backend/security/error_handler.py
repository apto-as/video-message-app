"""
Secure Error Handler - セキュアなエラーハンドリング
情報漏洩を防ぎつつ、適切なエラーメッセージをユーザーに返す
"""

import logging
import traceback
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    VALIDATION = "validation"  # 入力検証エラー
    AUTHENTICATION = "authentication"  # 認証エラー
    AUTHORIZATION = "authorization"  # 認可エラー
    RESOURCE = "resource"  # リソース不足
    PROCESSING = "processing"  # 処理エラー
    EXTERNAL = "external"  # 外部APIエラー
    SYSTEM = "system"  # システムエラー


class SecureErrorHandler:
    """
    セキュアなエラーハンドリング
    本番環境では詳細を隠し、開発環境では詳細を表示
    """

    # デバッグモード（環境変数で制御）
    DEBUG_MODE = False

    @staticmethod
    def set_debug_mode(debug: bool):
        """デバッグモードを設定"""
        SecureErrorHandler.DEBUG_MODE = debug
        logger.info(f"SecureErrorHandler debug mode: {debug}")

    @classmethod
    def handle_validation_error(
        cls,
        field: str,
        reason: str,
        value: Optional[Any] = None
    ) -> HTTPException:
        """
        入力検証エラーのハンドリング
        検証エラーは安全なのでユーザーに詳細を返す

        Args:
            field: フィールド名
            reason: エラー理由
            value: 無効な値（ログのみ）

        Returns:
            HTTPException
        """
        # 詳細ログ（サーバーのみ）
        logger.warning(f"Validation error: field={field}, reason={reason}, value={value}")

        # ユーザー向けメッセージ
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field}の検証に失敗しました: {reason}"
        )

    @classmethod
    def handle_audio_processing_error(
        cls,
        e: Exception,
        context: str,
        category: ErrorCategory = ErrorCategory.PROCESSING
    ) -> HTTPException:
        """
        音声処理エラーの安全なハンドリング

        Args:
            e: 発生した例外
            context: エラーコンテキスト（例: "voice_clone", "synthesis"）
            category: エラーカテゴリ

        Returns:
            HTTPException
        """
        # 詳細ログ（サーバーのみ）
        logger.error(
            f"Audio processing error in {context}: {str(e)}",
            exc_info=True,
            extra={"context": context, "category": category.value}
        )

        # デバッグモードの場合は詳細を返す
        if cls.DEBUG_MODE:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "音声処理中にエラーが発生しました",
                    "context": context,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                }
            )

        # 本番環境では一般的なメッセージのみ
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="音声処理中にエラーが発生しました。しばらく時間をおいてから再度お試しください。"
        )

    @classmethod
    def handle_resource_error(
        cls,
        error_type: str,
        current_value: Optional[float] = None,
        limit_value: Optional[float] = None
    ) -> HTTPException:
        """
        リソース不足エラーのハンドリング

        Args:
            error_type: "memory" | "cpu" | "concurrency" | "timeout"
            current_value: 現在の値
            limit_value: 制限値

        Returns:
            HTTPException
        """
        # 詳細ログ
        logger.error(
            f"Resource limit exceeded: type={error_type}, "
            f"current={current_value}, limit={limit_value}"
        )

        # エラータイプ別のメッセージ
        messages = {
            "memory": "メモリ使用量が制限を超えました。システム負荷が高いため、処理を実行できません。",
            "cpu": "CPU使用率が高いため、処理を実行できません。しばらく時間をおいてから再度お試しください。",
            "concurrency": "現在、多数のリクエストを処理中です。しばらく時間をおいてから再度お試しください。",
            "timeout": "処理がタイムアウトしました。ファイルサイズが大きすぎるか、サーバー負荷が高い可能性があります。"
        }

        message = messages.get(error_type, "リソース不足のため、処理を実行できません。")

        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message
        )

    @classmethod
    def handle_external_api_error(
        cls,
        service_name: str,
        e: Exception,
        status_code: Optional[int] = None
    ) -> HTTPException:
        """
        外部APIエラーのハンドリング

        Args:
            service_name: サービス名（例: "OpenVoice", "D-ID"）
            e: 発生した例外
            status_code: APIのステータスコード

        Returns:
            HTTPException
        """
        # 詳細ログ
        logger.error(
            f"External API error: service={service_name}, "
            f"status_code={status_code}, error={str(e)}",
            exc_info=True
        )

        # デバッグモードの場合は詳細を返す
        if cls.DEBUG_MODE:
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": f"{service_name}との通信中にエラーが発生しました",
                    "service": service_name,
                    "status_code": status_code,
                    "exception": str(e)
                }
            )

        # 本番環境では一般的なメッセージのみ
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service_name}との通信中にエラーが発生しました。しばらく時間をおいてから再度お試しください。"
        )

    @classmethod
    def handle_file_not_found(
        cls,
        file_type: str,
        file_id: Optional[str] = None
    ) -> HTTPException:
        """
        ファイル/リソース未発見エラーのハンドリング

        Args:
            file_type: ファイルタイプ（例: "voice_profile", "audio_file"）
            file_id: ファイルID（ログのみ）

        Returns:
            HTTPException
        """
        # 詳細ログ
        logger.warning(f"Resource not found: type={file_type}, id={file_id}")

        # IDは露出しない
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"指定された{file_type}が見つかりません"
        )

    @classmethod
    def handle_authentication_error(
        cls,
        reason: str = "認証に失敗しました"
    ) -> HTTPException:
        """
        認証エラーのハンドリング

        Args:
            reason: エラー理由

        Returns:
            HTTPException
        """
        logger.warning(f"Authentication error: {reason}")

        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=reason,
            headers={"WWW-Authenticate": "Bearer"}
        )

    @classmethod
    def handle_authorization_error(
        cls,
        resource: str,
        action: str
    ) -> HTTPException:
        """
        認可エラーのハンドリング

        Args:
            resource: リソース名
            action: アクション名

        Returns:
            HTTPException
        """
        logger.warning(f"Authorization error: resource={resource}, action={action}")

        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作を実行する権限がありません"
        )

    @classmethod
    def handle_rate_limit_error(
        cls,
        limit: int,
        window: int,
        retry_after: Optional[int] = None
    ) -> HTTPException:
        """
        レート制限エラーのハンドリング

        Args:
            limit: リクエスト制限数
            window: 時間窓（秒）
            retry_after: 再試行までの秒数

        Returns:
            HTTPException
        """
        logger.warning(f"Rate limit exceeded: {limit} requests per {window}s")

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"リクエスト制限を超えました（{limit}リクエスト / {window}秒）。しばらく時間をおいてから再度お試しください。",
            headers=headers
        )

    @classmethod
    def sanitize_error_message(cls, error_message: str) -> str:
        """
        エラーメッセージから機密情報を除去

        Args:
            error_message: 元のエラーメッセージ

        Returns:
            サニタイズされたメッセージ
        """
        # パス情報を除去
        sanitized = error_message
        sanitized = sanitized.replace("/app/", "")
        sanitized = sanitized.replace("/home/", "")
        sanitized = sanitized.replace("/Users/", "")
        sanitized = sanitized.replace("\\", "/")

        # スタックトレースを除去
        if "Traceback" in sanitized:
            sanitized = sanitized.split("Traceback")[0]

        return sanitized.strip()

    @classmethod
    def log_security_event(
        cls,
        event_type: str,
        severity: str,
        details: Dict[str, Any]
    ):
        """
        セキュリティイベントのログ記録

        Args:
            event_type: イベントタイプ（例: "audio_bomb_detected"）
            severity: 重要度（"low" | "medium" | "high" | "critical"）
            details: イベント詳細
        """
        log_message = f"SECURITY EVENT [{severity.upper()}]: {event_type}"

        if severity in ["high", "critical"]:
            logger.error(log_message, extra={"security_event": details})
        elif severity == "medium":
            logger.warning(log_message, extra={"security_event": details})
        else:
            logger.info(log_message, extra={"security_event": details})


# === ヘルパー関数 ===

def handle_generic_error(e: Exception, context: str = "unknown") -> HTTPException:
    """
    汎用エラーハンドラー（便利関数）

    Args:
        e: 発生した例外
        context: エラーコンテキスト

    Returns:
        HTTPException
    """
    # エラータイプに応じて適切なハンドラーを呼び出す
    if isinstance(e, MemoryError):
        return SecureErrorHandler.handle_resource_error("memory")

    elif isinstance(e, TimeoutError):
        return SecureErrorHandler.handle_resource_error("timeout")

    elif isinstance(e, FileNotFoundError):
        return SecureErrorHandler.handle_file_not_found("file")

    elif isinstance(e, PermissionError):
        return SecureErrorHandler.handle_authorization_error("file", "access")

    else:
        return SecureErrorHandler.handle_audio_processing_error(e, context)
