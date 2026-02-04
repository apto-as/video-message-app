# DEPRECATED: D-ID cloud API code - to be removed
# This validator was used for D-ID cloud API interactions.
# The current system uses MuseTalk for local lip-sync video generation instead.
"""
D-ID API セキュリティバリデーター

CRITICAL SECURITY RULES:
1. API Keyはログに出力しない
2. すべての入力を検証する
3. URLは許可リストで検証
4. ファイルサイズ制限を厳守
5. Content-Typeを検証
"""

import re
import os
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from pathlib import Path

# ログにAPI keyが含まれないように専用ロガーを作成
logger = logging.getLogger(__name__)

class DIdValidator:
    """D-ID API用のセキュリティバリデーター"""

    # D-IDのドメイン（許可リスト）
    ALLOWED_D_ID_DOMAINS = [
        "d-id.com",
        "api.d-id.com",
        "static-assets.d-id.com",
        "create-images-results.d-id.com"
    ]

    # サポートされる画像形式
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp'
    }

    # サポートされる音声形式
    ALLOWED_AUDIO_TYPES = {
        'audio/wav',
        'audio/mp3',
        'audio/mpeg',
        'audio/mp4',
        'audio/flac',
        'audio/m4a',
        'audio/x-wav',
        'audio/x-m4a'
    }

    # ファイルサイズ制限（バイト）
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB

    # テキスト長制限
    MAX_TEXT_LENGTH = 10000  # 10,000文字

    # API Key形式（Base64エンコード済み）
    API_KEY_PATTERN = re.compile(r'^[A-Za-z0-9+/=]{20,}$')

    @staticmethod
    def validate_api_key(api_key: Optional[str]) -> bool:
        """
        API Keyの検証（形式のみ、実際の値は検証しない）

        Args:
            api_key: D-ID API Key

        Returns:
            有効な形式の場合True
        """
        if not api_key:
            logger.error("API Key is not configured")
            return False

        if not isinstance(api_key, str):
            logger.error("API Key must be a string")
            return False

        if len(api_key) < 20:
            logger.error("API Key is too short")
            return False

        if not DIdValidator.API_KEY_PATTERN.match(api_key):
            logger.error("API Key format is invalid")
            return False

        return True

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        URL文字列をサニタイズ（ログ出力用）

        Args:
            url: 元のURL

        Returns:
            サニタイズされたURL（末尾部分のみ表示）
        """
        if not url:
            return "[empty]"

        parsed = urlparse(url)
        if parsed.path:
            filename = os.path.basename(parsed.path)
            return f"[.../{filename}]"

        return "[URL]"

    @staticmethod
    def validate_d_id_url(url: str) -> bool:
        """
        D-IDのURLを検証（許可リストベース）

        Args:
            url: 検証するURL

        Returns:
            D-IDの有効なURLの場合True
        """
        if not url:
            logger.error("URL is empty")
            return False

        try:
            parsed = urlparse(url)

            # HTTPSを強制
            if parsed.scheme != 'https':
                logger.error(f"URL must use HTTPS: {DIdValidator.sanitize_url(url)}")
                return False

            # ドメインを許可リストで検証
            domain = parsed.netloc.lower()

            # サブドメインを含む検証
            is_allowed = any(
                domain == allowed or domain.endswith(f".{allowed}")
                for allowed in DIdValidator.ALLOWED_D_ID_DOMAINS
            )

            if not is_allowed:
                logger.error(f"Domain not allowed: {domain}")
                return False

            return True

        except Exception as e:
            logger.error(f"URL validation error: {str(e)}")
            return False

    @staticmethod
    def validate_image_upload(
        content_type: Optional[str],
        file_size: int,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        画像アップロードの検証

        Args:
            content_type: Content-Type
            file_size: ファイルサイズ（バイト）
            filename: ファイル名（オプション）

        Returns:
            検証結果
        """
        result = {
            "valid": True,
            "errors": []
        }

        # Content-Type検証
        if not content_type:
            result["valid"] = False
            result["errors"].append("Content-Type is missing")
        elif content_type.lower() not in DIdValidator.ALLOWED_IMAGE_TYPES:
            result["valid"] = False
            result["errors"].append(f"Invalid image type: {content_type}")

        # ファイルサイズ検証
        if file_size <= 0:
            result["valid"] = False
            result["errors"].append("File is empty")
        elif file_size > DIdValidator.MAX_IMAGE_SIZE:
            result["valid"] = False
            result["errors"].append(
                f"Image too large: {file_size} bytes (max: {DIdValidator.MAX_IMAGE_SIZE})"
            )

        # ファイル名検証（オプション）
        if filename:
            # パストラバーサル対策
            if ".." in filename or "/" in filename or "\\" in filename:
                result["valid"] = False
                result["errors"].append("Invalid filename: path traversal detected")

            # 許可される拡張子
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
            ext = os.path.splitext(filename)[1].lower()
            if ext not in allowed_extensions:
                result["valid"] = False
                result["errors"].append(f"Invalid file extension: {ext}")

        if result["errors"]:
            logger.warning(f"Image validation failed: {', '.join(result['errors'])}")

        return result

    @staticmethod
    def validate_audio_upload(
        content_type: Optional[str],
        file_size: int,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        音声アップロードの検証

        Args:
            content_type: Content-Type
            file_size: ファイルサイズ（バイト）
            filename: ファイル名（オプション）

        Returns:
            検証結果
        """
        result = {
            "valid": True,
            "errors": []
        }

        # Content-Type検証
        if not content_type:
            result["valid"] = False
            result["errors"].append("Content-Type is missing")
        elif content_type.lower() not in DIdValidator.ALLOWED_AUDIO_TYPES:
            result["valid"] = False
            result["errors"].append(f"Invalid audio type: {content_type}")

        # ファイルサイズ検証
        if file_size <= 0:
            result["valid"] = False
            result["errors"].append("File is empty")
        elif file_size > DIdValidator.MAX_AUDIO_SIZE:
            result["valid"] = False
            result["errors"].append(
                f"Audio too large: {file_size} bytes (max: {DIdValidator.MAX_AUDIO_SIZE})"
            )

        # ファイル名検証（オプション）
        if filename:
            # パストラバーサル対策
            if ".." in filename or "/" in filename or "\\" in filename:
                result["valid"] = False
                result["errors"].append("Invalid filename: path traversal detected")

            # 許可される拡張子
            allowed_extensions = {'.wav', '.mp3', '.mp4', '.flac', '.m4a'}
            ext = os.path.splitext(filename)[1].lower()
            if ext not in allowed_extensions:
                result["valid"] = False
                result["errors"].append(f"Invalid file extension: {ext}")

        if result["errors"]:
            logger.warning(f"Audio validation failed: {', '.join(result['errors'])}")

        return result

    @staticmethod
    def validate_text_input(text: str, field_name: str = "text") -> Dict[str, Any]:
        """
        テキスト入力の検証（SQLインジェクション・XSS対策）

        Args:
            text: 検証するテキスト
            field_name: フィールド名（エラーメッセージ用）

        Returns:
            検証結果
        """
        result = {
            "valid": True,
            "errors": []
        }

        if not text:
            result["valid"] = False
            result["errors"].append(f"{field_name} is empty")
            return result

        if not isinstance(text, str):
            result["valid"] = False
            result["errors"].append(f"{field_name} must be a string")
            return result

        # 長さ制限
        if len(text) > DIdValidator.MAX_TEXT_LENGTH:
            result["valid"] = False
            result["errors"].append(
                f"{field_name} too long: {len(text)} chars (max: {DIdValidator.MAX_TEXT_LENGTH})"
            )

        # 危険な文字パターン検出（XSS対策）
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe',
            r'eval\(',
            r'expression\(',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result["valid"] = False
                result["errors"].append(f"{field_name} contains potentially dangerous content")
                logger.warning(f"Dangerous pattern detected in {field_name}: {pattern}")
                break

        if result["errors"]:
            logger.warning(f"Text validation failed: {', '.join(result['errors'])}")

        return result

    @staticmethod
    def validate_talk_id(talk_id: str) -> bool:
        """
        D-ID Talk IDの検証

        Args:
            talk_id: 検証するTalk ID

        Returns:
            有効なフォーマットの場合True
        """
        if not talk_id:
            logger.error("Talk ID is empty")
            return False

        # Talk IDの形式: 英数字とハイフン（UUIDスタイル）
        talk_id_pattern = re.compile(r'^[a-zA-Z0-9\-]{10,100}$')

        if not talk_id_pattern.match(talk_id):
            logger.error(f"Invalid Talk ID format: {talk_id}")
            return False

        return True

    @staticmethod
    def sanitize_error_message(error_message: str) -> str:
        """
        エラーメッセージをサニタイズ（機密情報漏洩防止）

        Args:
            error_message: 元のエラーメッセージ

        Returns:
            サニタイズされたエラーメッセージ
        """
        # API Keyのパターンを削除
        sanitized = re.sub(
            r'[A-Za-z0-9+/=]{20,}',
            '[REDACTED]',
            error_message
        )

        # URLのクエリパラメータを削除
        sanitized = re.sub(
            r'\?[^\s]+',
            '?[params]',
            sanitized
        )

        # 絶対パスを削除
        sanitized = re.sub(
            r'/[^\s]+?/([^/\s]+)$',
            r'[...]/\1',
            sanitized
        )

        return sanitized


# デフォルトバリデーターインスタンス
validator = DIdValidator()
