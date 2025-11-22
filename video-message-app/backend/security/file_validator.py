"""
File upload security validation

セキュリティ原則:
1. MIME type検証（magic number based）
2. ファイルサイズ制限
3. ファイル名サニタイゼーション（パストラバーサル防止）
4. 同時アップロード数制限
5. レート制限
"""
from pathlib import Path
from typing import Tuple, Optional
import magic
from fastapi import UploadFile, HTTPException
import logging
import asyncio
import re

logger = logging.getLogger(__name__)

# 許可されるMIMEタイプ
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg"
}

ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg"
}

# ファイルサイズ制限
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB

# 同時アップロード数制限
MAX_FILES_PER_REQUEST = 10


class FileValidator:
    """ファイルアップロードのセキュリティ検証"""

    @staticmethod
    async def validate_image(file: UploadFile) -> Tuple[bool, str]:
        """
        画像ファイルの検証

        Returns:
            (is_valid, message)
        """
        try:
            # 1. ファイル名検証
            if not file.filename:
                return False, "Filename is required"

            # パストラバーサル防止
            safe_filename = FileValidator.sanitize_filename(file.filename)
            if not safe_filename or safe_filename != file.filename:
                return False, f"Invalid filename: {file.filename}"

            # 2. 拡張子チェック
            ext = Path(file.filename).suffix.lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                return False, f"Invalid file extension: {ext}"

            # 3. ファイルサイズチェック
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning

            if file_size > MAX_IMAGE_SIZE:
                return False, f"File too large: {file_size} bytes (max: {MAX_IMAGE_SIZE})"

            if file_size < 100:  # 100バイト未満は異常
                return False, f"File too small: {file_size} bytes (suspicious)"

            # 4. MIME typeチェック（magic number based）
            file_header = await file.read(2048)
            await file.seek(0)  # Reset

            mime = magic.from_buffer(file_header, mime=True)

            if mime not in ALLOWED_MIME_TYPES:
                return False, f"Invalid MIME type: {mime} (expected: image/jpeg, image/png, image/webp)"

            # 5. MIME typeと拡張子の整合性チェック
            mime_ext_map = {
                "image/jpeg": [".jpg", ".jpeg"],
                "image/png": [".png"],
                "image/webp": [".webp"]
            }

            expected_exts = mime_ext_map.get(mime, [])
            if ext not in expected_exts:
                return False, f"MIME type mismatch: {mime} vs extension {ext}"

            logger.info(f"Image validation passed: {file.filename} ({file_size} bytes, {mime})")
            return True, "Valid"

        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    @staticmethod
    async def validate_audio(file: UploadFile) -> Tuple[bool, str]:
        """
        音声ファイルの検証

        Returns:
            (is_valid, message)
        """
        try:
            # 1. ファイル名検証
            if not file.filename:
                return False, "Filename is required"

            # パストラバーサル防止
            safe_filename = FileValidator.sanitize_filename(file.filename)
            if not safe_filename or safe_filename != file.filename:
                return False, f"Invalid filename: {file.filename}"

            # 2. 拡張子チェック
            ext = Path(file.filename).suffix.lower()
            if ext not in [".wav", ".webm", ".mp3", ".ogg"]:
                return False, f"Invalid audio file extension: {ext}"

            # 3. ファイルサイズチェック
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            if file_size > MAX_AUDIO_SIZE:
                return False, f"Audio file too large: {file_size} bytes (max: {MAX_AUDIO_SIZE})"

            if file_size < 1000:  # 1KB未満は異常
                return False, f"Audio file too small: {file_size} bytes (suspicious)"

            # 4. MIME typeチェック
            file_header = await file.read(2048)
            await file.seek(0)

            mime = magic.from_buffer(file_header, mime=True)

            if mime not in ALLOWED_AUDIO_MIME_TYPES:
                return False, f"Invalid audio MIME type: {mime}"

            logger.info(f"Audio validation passed: {file.filename} ({file_size} bytes, {mime})")
            return True, "Valid"

        except Exception as e:
            logger.error(f"Audio validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        ファイル名のサニタイゼーション（パストラバーサル防止）

        Returns:
            Safe filename or empty string if invalid
        """
        if not filename:
            return ""

        # パスコンポーネントを削除（ディレクトリトラバーサル防止）
        filename = Path(filename).name

        # 危険な文字を削除
        dangerous_patterns = [
            r'\.\.',  # ..
            r'/',      # /
            r'\\',     # \
            r'\x00',   # NULL byte
            r'[<>:"|?*]'  # Windows予約文字
        ]

        for pattern in dangerous_patterns:
            filename = re.sub(pattern, '', filename)

        # 空白のみのファイル名を拒否
        if not filename.strip():
            return ""

        # ファイル名長制限（255文字）
        if len(filename) > 255:
            filename = filename[:255]

        return filename

    @staticmethod
    def validate_file_count(file_count: int, max_count: int = MAX_FILES_PER_REQUEST) -> Tuple[bool, str]:
        """
        アップロードファイル数の検証

        Args:
            file_count: アップロードされるファイル数
            max_count: 最大許可数

        Returns:
            (is_valid, message)
        """
        if file_count < 1:
            return False, "At least one file is required"

        if file_count > max_count:
            return False, f"Too many files: {file_count} (max: {max_count})"

        return True, "Valid"
