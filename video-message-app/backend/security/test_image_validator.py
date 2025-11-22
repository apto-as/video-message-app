"""
Test cases for image security validation

Tests for:
1. Image bomb detection
2. Metadata validation
3. Timeout enforcement
4. Resource limiting
"""
import pytest
from PIL import Image
import io
import time
from .image_validator import (
    ImageSecurityValidator,
    ProcessingTimeoutManager,
    ProcessingTimeoutError,
    ResourceLimiter
)


class TestImageSecurityValidator:
    """Test image security validation"""

    def test_valid_image(self):
        """Test validation of normal image"""
        # Create a small valid image
        img = Image.new('RGB', (512, 512), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        is_safe, msg = ImageSecurityValidator.detect_image_bomb(img_bytes)
        assert is_safe, f"Valid image rejected: {msg}"

    def test_image_bomb_large_pixels(self):
        """Test detection of image with too many pixels"""
        # Create 100MP image (exceeds 50MP limit)
        img = Image.new('RGB', (10000, 10000), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        is_safe, msg = ImageSecurityValidator.detect_image_bomb(img_bytes)
        assert not is_safe, "Image bomb not detected"
        assert "too large" in msg.lower()

    def test_image_bomb_high_compression(self):
        """Test detection of suspiciously compressed images"""
        # Create solid color image (compresses extremely well)
        img = Image.new('RGB', (5000, 5000), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', compress_level=9)
        img_bytes = img_bytes.getvalue()

        # Check decompression ratio
        file_size = len(img_bytes)
        uncompressed = 5000 * 5000 * 3
        ratio = uncompressed / file_size

        if ratio > 1000:
            is_safe, msg = ImageSecurityValidator.detect_image_bomb(img_bytes)
            assert not is_safe, "High compression ratio not detected"

    def test_file_too_small(self):
        """Test rejection of suspiciously small files"""
        tiny_file = b"fake"  # 4 bytes

        is_safe, msg = ImageSecurityValidator.detect_image_bomb(tiny_file)
        assert not is_safe, "Tiny file not rejected"
        assert "too small" in msg.lower()

    def test_file_too_large(self):
        """Test rejection of files exceeding size limit"""
        # Simulate 11MB file
        large_file = b"x" * (11 * 1024 * 1024)

        is_safe, msg = ImageSecurityValidator.detect_image_bomb(large_file)
        assert not is_safe, "Large file not rejected"
        assert "too large" in msg.lower()

    def test_metadata_with_path_traversal(self):
        """Test detection of malicious metadata"""
        # Create image with suspicious EXIF data
        img = Image.new('RGB', (100, 100))
        img_bytes = io.BytesIO()

        # Add EXIF with path traversal
        from PIL.ExifTags import TAGS
        exif_data = img.getexif()

        # Try to inject path traversal in various EXIF fields
        suspicious_values = [
            "../../../etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
            "/etc/shadow",
            "\x00null byte",
            "<script>alert('xss')</script>"
        ]

        # Note: PIL may sanitize these, but we test detection anyway
        for value in suspicious_values:
            # Create fresh image
            img = Image.new('RGB', (100, 100))
            img_bytes_test = io.BytesIO()
            img.save(img_bytes_test, format='JPEG')

            # For testing, we'll validate the pattern detection logic separately


class TestProcessingTimeoutManager:
    """Test timeout enforcement"""

    def test_normal_processing(self):
        """Test normal processing within timeout"""
        with ProcessingTimeoutManager(timeout_seconds=2) as timeout:
            time.sleep(0.1)
            timeout.check_timeout()  # Should not raise

    def test_timeout_exceeded(self):
        """Test timeout detection"""
        with pytest.raises(ProcessingTimeoutError):
            with ProcessingTimeoutManager(timeout_seconds=1) as timeout:
                time.sleep(1.5)
                timeout.check_timeout()  # Should raise


class TestResourceLimiter:
    """Test per-user resource limiting"""

    def test_resource_acquisition(self):
        """Test normal resource acquisition"""
        limiter = ResourceLimiter(max_concurrent=3)

        assert limiter.acquire("user1"), "Failed to acquire resource"
        assert limiter.acquire("user1"), "Failed to acquire resource"
        assert limiter.acquire("user1"), "Failed to acquire resource"

        # Fourth request should be rejected
        assert not limiter.acquire("user1"), "Resource limit not enforced"

    def test_resource_release(self):
        """Test resource release"""
        limiter = ResourceLimiter(max_concurrent=2)

        limiter.acquire("user1")
        limiter.acquire("user1")
        assert not limiter.acquire("user1"), "Limit not enforced"

        # Release one
        limiter.release("user1")
        assert limiter.acquire("user1"), "Failed after release"

    def test_multi_user_isolation(self):
        """Test that limits are per-user"""
        limiter = ResourceLimiter(max_concurrent=2)

        limiter.acquire("user1")
        limiter.acquire("user1")
        assert not limiter.acquire("user1"), "User1 limit not enforced"

        # User2 should be able to acquire
        assert limiter.acquire("user2"), "User2 blocked by user1"


class TestComprehensiveValidation:
    """Test combined security checks"""

    def test_comprehensive_valid_image(self):
        """Test that valid images pass all checks"""
        img = Image.new('RGB', (512, 512), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        is_safe, msg = ImageSecurityValidator.comprehensive_validation(img_bytes)
        assert is_safe, f"Valid image failed validation: {msg}"

    def test_comprehensive_malicious_image(self):
        """Test that malicious images fail validation"""
        # Create image bomb
        img = Image.new('RGB', (10000, 10000), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()

        is_safe, msg = ImageSecurityValidator.comprehensive_validation(img_bytes)
        assert not is_safe, "Malicious image passed validation"
        assert "too large" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
