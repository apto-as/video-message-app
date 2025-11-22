"""
Example Unit Test - Image Validator

This file demonstrates best practices for writing unit tests:
- Clear test names
- Arrange-Act-Assert pattern
- Edge case coverage
- Parametrized tests
"""

import pytest
from pathlib import Path
from backend.security.validators import ImageValidator, ValidationError


class TestImageValidator:
    """Test suite for ImageValidator"""

    @pytest.fixture
    def validator(self):
        """Create ImageValidator instance for tests"""
        return ImageValidator(max_size_mb=10)

    # ======================================================================
    # Happy Path Tests
    # ======================================================================

    @pytest.mark.parametrize("filename", [
        "test.jpg",
        "image.jpeg",
        "photo.png",
        "avatar.webp",
        "picture.JPG",  # Case insensitive
    ])
    def test_accept_valid_image_formats(self, validator, filename):
        """Test that validator accepts standard image formats"""
        # Arrange
        # (validator fixture already created)

        # Act
        result = validator.validate_filename(filename)

        # Assert
        assert result is True

    def test_validate_real_image_file(self, validator, tmp_path):
        """Test validation of actual image file"""
        # Arrange
        image_path = tmp_path / "test.jpg"
        # Create minimal valid JPEG
        image_path.write_bytes(
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        )

        # Act
        result = validator.validate_file(image_path)

        # Assert
        assert result.is_valid is True
        assert result.error is None

    # ======================================================================
    # Error Cases
    # ======================================================================

    @pytest.mark.parametrize("filename,expected_error", [
        ("test.exe", "Invalid file extension"),
        ("malware.sh", "Invalid file extension"),
        ("document.pdf", "Invalid file extension"),
        ("", "Empty filename"),
        (" ", "Empty filename"),
    ])
    def test_reject_invalid_formats(self, validator, filename, expected_error):
        """Test that validator rejects invalid file formats"""
        # Arrange
        # (validator fixture)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_filename(filename, raise_error=True)

        assert expected_error in str(exc_info.value)

    def test_reject_path_traversal_attack(self, validator):
        """Test protection against path traversal attacks"""
        # Arrange
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "./../../secret.txt"
        ]

        # Act & Assert
        for path in malicious_paths:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate_filename(path, raise_error=True)

            assert "path traversal" in str(exc_info.value).lower()

    def test_reject_file_exceeding_size_limit(self, validator, tmp_path):
        """Test rejection of files larger than max_size_mb"""
        # Arrange
        large_file = tmp_path / "large.jpg"
        # Create 11MB file (exceeds 10MB limit)
        large_file.write_bytes(b'\x00' * (11 * 1024 * 1024))

        # Act
        result = validator.validate_file(large_file)

        # Assert
        assert result.is_valid is False
        assert "exceeds maximum size" in result.error.lower()

    # ======================================================================
    # Magic Byte Validation
    # ======================================================================

    def test_reject_executable_disguised_as_image(self, validator, tmp_path):
        """Test detection of executable with .jpg extension"""
        # Arrange
        fake_image = tmp_path / "malware.jpg"
        # Write EXE magic bytes (MZ header)
        fake_image.write_bytes(b'MZ\x90\x00\x03\x00\x00\x00')

        # Act
        result = validator.validate_file(fake_image)

        # Assert
        assert result.is_valid is False
        assert "magic bytes" in result.error.lower()

    @pytest.mark.parametrize("magic_bytes,extension,should_pass", [
        (b'\xff\xd8\xff', "jpg", True),   # JPEG
        (b'\x89PNG\r\n\x1a\n', "png", True),  # PNG
        (b'RIFF', "webp", True),  # WebP
        (b'MZ', "jpg", False),    # EXE disguised as JPG
        (b'PK\x03\x04', "png", False),  # ZIP disguised as PNG
    ])
    def test_magic_byte_validation(
        self, validator, tmp_path, magic_bytes, extension, should_pass
    ):
        """Test magic byte validation for various file types"""
        # Arrange
        test_file = tmp_path / f"test.{extension}"
        test_file.write_bytes(magic_bytes + b'\x00' * 100)

        # Act
        result = validator.validate_file(test_file)

        # Assert
        if should_pass:
            assert result.is_valid is True
        else:
            assert result.is_valid is False
            assert "mismatch" in result.error.lower()

    # ======================================================================
    # Edge Cases
    # ======================================================================

    def test_validate_empty_file(self, validator, tmp_path):
        """Test handling of empty file"""
        # Arrange
        empty_file = tmp_path / "empty.jpg"
        empty_file.touch()  # Create empty file

        # Act
        result = validator.validate_file(empty_file)

        # Assert
        assert result.is_valid is False
        assert "empty" in result.error.lower()

    def test_validate_nonexistent_file(self, validator):
        """Test handling of non-existent file"""
        # Arrange
        fake_path = Path("/nonexistent/file.jpg")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            validator.validate_file(fake_path)

    def test_validate_directory_instead_of_file(self, validator, tmp_path):
        """Test handling when directory is passed instead of file"""
        # Arrange
        directory = tmp_path / "test_dir"
        directory.mkdir()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_file(directory, raise_error=True)

        assert "not a file" in str(exc_info.value).lower()

    # ======================================================================
    # Configuration Tests
    # ======================================================================

    def test_custom_max_size(self, tmp_path):
        """Test validator with custom max_size_mb"""
        # Arrange
        validator = ImageValidator(max_size_mb=5)
        test_file = tmp_path / "test.jpg"
        # Create 6MB file
        test_file.write_bytes(b'\xff\xd8\xff' + b'\x00' * (6 * 1024 * 1024))

        # Act
        result = validator.validate_file(test_file)

        # Assert
        assert result.is_valid is False
        assert "5 MB" in result.error

    def test_custom_allowed_extensions(self, tmp_path):
        """Test validator with custom allowed extensions"""
        # Arrange
        validator = ImageValidator(allowed_extensions=[".jpg", ".png"])

        # Act & Assert
        assert validator.validate_filename("test.jpg") is True
        assert validator.validate_filename("test.png") is True

        with pytest.raises(ValidationError):
            validator.validate_filename("test.webp", raise_error=True)

    # ======================================================================
    # Performance Tests
    # ======================================================================

    def test_validation_performance(self, validator, tmp_path, benchmark):
        """Benchmark validation performance"""
        # Arrange
        test_file = tmp_path / "benchmark.jpg"
        test_file.write_bytes(b'\xff\xd8\xff' + b'\x00' * 1024)

        # Act & Assert
        result = benchmark(validator.validate_file, test_file)

        # Validation should be fast (<10ms)
        assert result.is_valid is True


# ======================================================================
# Additional Test Utilities
# ======================================================================

def create_test_image(path: Path, size_mb: int = 1) -> Path:
    """
    Helper function to create test image file

    Args:
        path: Path where to create the file
        size_mb: Size in megabytes

    Returns:
        Path to created file
    """
    # Write JPEG magic bytes + filler
    path.write_bytes(
        b'\xff\xd8\xff\xe0\x00\x10JFIF' +
        b'\x00' * (size_mb * 1024 * 1024)
    )
    return path


@pytest.fixture
def sample_images(tmp_path):
    """Fixture providing multiple test images"""
    images = {
        "small": create_test_image(tmp_path / "small.jpg", size_mb=1),
        "medium": create_test_image(tmp_path / "medium.jpg", size_mb=5),
        "large": create_test_image(tmp_path / "large.jpg", size_mb=10),
    }
    return images


def test_batch_validation(validator, sample_images):
    """Test validation of multiple images"""
    # Arrange
    images = sample_images.values()

    # Act
    results = [validator.validate_file(img) for img in images]

    # Assert
    assert all(r.is_valid for r in results)
