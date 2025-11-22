"""
Image processing security validation

画像処理特有のセキュリティリスク対策:
1. Image bomb attacks (decompression bomb)
2. Memory exhaustion attacks
3. Malicious metadata injection
4. Processing timeout enforcement
5. Per-user resource limiting
"""
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import logging
import io
import time
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

# Security thresholds
MAX_IMAGE_PIXELS = 50_000_000  # 50 megapixels
MAX_DECOMPRESSION_RATIO = 1000  # Suspicious if > 1000x
MIN_FILE_SIZE = 100  # Bytes
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Processing limits
MAX_PROCESSING_TIME_SECONDS = 30
MAX_CONCURRENT_REQUESTS_PER_USER = 3


class ImageSecurityValidator:
    """
    Image processing security validation

    Detects and prevents:
    - Image bomb attacks (zip bomb style)
    - Memory exhaustion
    - Malicious metadata
    - DoS via slow processing
    """

    @staticmethod
    def detect_image_bomb(image_bytes: bytes) -> Tuple[bool, str]:
        """
        Detect image bomb attacks before full decompression

        Image bombs are small compressed files that expand to huge sizes,
        causing memory exhaustion and DoS.

        Args:
            image_bytes: Image file binary data

        Returns:
            (is_safe, message)
        """
        try:
            file_size = len(image_bytes)

            # Basic size checks
            if file_size < MIN_FILE_SIZE:
                return False, f"File too small: {file_size} bytes (suspicious)"

            if file_size > MAX_FILE_SIZE:
                return False, f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"

            # Open image without loading pixel data
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                total_pixels = width * height

                # Check pixel count
                if total_pixels > MAX_IMAGE_PIXELS:
                    return False, f"Image too large: {total_pixels} pixels (max: {MAX_IMAGE_PIXELS})"

                # Calculate decompression ratio
                # Assume 3 bytes per pixel (RGB) for worst case
                uncompressed_size = total_pixels * 3
                decompression_ratio = uncompressed_size / file_size

                # Suspicious compression ratio indicates potential bomb
                if decompression_ratio > MAX_DECOMPRESSION_RATIO:
                    return False, (
                        f"Suspicious compression ratio: {decompression_ratio:.1f}x "
                        f"({file_size} bytes -> {uncompressed_size} bytes)"
                    )

                logger.info(
                    f"Image bomb check passed: {width}x{height} pixels, "
                    f"ratio: {decompression_ratio:.1f}x"
                )

                return True, "Image is safe"

        except Exception as e:
            logger.error(f"Image bomb detection failed: {e}")
            return False, f"Image validation failed: {e}"

    @staticmethod
    def validate_image_metadata(image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate image metadata for malicious content

        Checks for:
        - Path traversal strings in EXIF
        - Suspicious command injection attempts
        - Overly large metadata

        Args:
            image_bytes: Image file binary data

        Returns:
            (is_safe, message)
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Check for EXIF data
                exif = img.getexif()

                if exif:
                    metadata_size = 0

                    for tag, value in exif.items():
                        # Convert value to string for analysis
                        value_str = str(value)
                        metadata_size += len(value_str)

                        # Check for path traversal attempts
                        dangerous_patterns = ['..', '/', '\\', '\x00', '<', '>', '|', '&', ';']

                        for pattern in dangerous_patterns:
                            if pattern in value_str:
                                return False, (
                                    f"Suspicious metadata in tag {tag}: "
                                    f"contains '{pattern}'"
                                )

                    # Check for suspiciously large metadata
                    if metadata_size > 100_000:  # 100KB
                        return False, f"Metadata too large: {metadata_size} bytes"

                logger.info("Metadata validation passed")
                return True, "Metadata is safe"

        except Exception as e:
            logger.error(f"Metadata validation failed: {e}")
            return False, f"Metadata validation error: {e}"

    @staticmethod
    def comprehensive_validation(image_bytes: bytes) -> Tuple[bool, str]:
        """
        Run all security checks

        Args:
            image_bytes: Image file binary data

        Returns:
            (is_safe, message)
        """
        # 1. Image bomb detection
        is_safe, msg = ImageSecurityValidator.detect_image_bomb(image_bytes)
        if not is_safe:
            return False, f"Image bomb: {msg}"

        # 2. Metadata validation
        is_safe, msg = ImageSecurityValidator.validate_image_metadata(image_bytes)
        if not is_safe:
            return False, f"Metadata: {msg}"

        return True, "All validations passed"


class ProcessingTimeoutError(Exception):
    """Raised when image processing exceeds timeout"""
    pass


class ProcessingTimeoutManager:
    """
    Timeout enforcement for image processing

    Prevents DoS via slow processing (e.g., malicious images that cause
    infinite loops in processing libraries)
    """

    def __init__(self, timeout_seconds: int = MAX_PROCESSING_TIME_SECONDS):
        self.timeout_seconds = timeout_seconds
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def check_timeout(self):
        """
        Check if processing has exceeded timeout

        Raises:
            ProcessingTimeoutError: If timeout exceeded
        """
        if self.start_time is None:
            return

        elapsed = time.time() - self.start_time
        if elapsed > self.timeout_seconds:
            raise ProcessingTimeoutError(
                f"Processing timeout: {elapsed:.1f}s > {self.timeout_seconds}s"
            )


class ResourceLimiter:
    """
    Per-user resource limiting

    Prevents DoS via concurrent requests from single user
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_REQUESTS_PER_USER):
        self.max_concurrent = max_concurrent
        self.active_requests = defaultdict(int)
        self.lock = threading.Lock()

    def acquire(self, client_id: str) -> bool:
        """
        Try to acquire resource slot

        Args:
            client_id: Unique client identifier (IP address)

        Returns:
            True if acquired, False if limit reached
        """
        with self.lock:
            if self.active_requests[client_id] >= self.max_concurrent:
                logger.warning(
                    f"Resource limit reached for {client_id}: "
                    f"{self.active_requests[client_id]} active requests"
                )
                return False

            self.active_requests[client_id] += 1
            return True

    def release(self, client_id: str):
        """Release resource slot"""
        with self.lock:
            if self.active_requests[client_id] > 0:
                self.active_requests[client_id] -= 1


# Global resource limiter
resource_limiter = ResourceLimiter(max_concurrent=MAX_CONCURRENT_REQUESTS_PER_USER)
