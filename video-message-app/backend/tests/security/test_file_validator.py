"""
File validator security tests

テスト項目:
1. 正常な画像ファイルのアップロード
2. 不正なファイルタイプの拒否
3. サイズ超過ファイルの拒否
4. パストラバーサル攻撃の防止
5. MIME type偽装の検出
"""
import pytest
import io
from fastapi import UploadFile
from security.file_validator import FileValidator, RateLimiter


class TestFileValidator:
    """FileValidatorのテスト"""

    @pytest.mark.asyncio
    async def test_valid_jpeg_image(self):
        """正常なJPEG画像の検証"""
        # 最小のJPEGデータ（1x1ピクセル）
        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
            b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x10\x01'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x08\x01\x01\x00\x00?\x00T\xdf\xff\xd9'
        )

        file = UploadFile(
            filename="test_image.jpg",
            file=io.BytesIO(jpeg_data)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is True, f"Valid JPEG should pass: {message}"
        assert "Valid" in message

    @pytest.mark.asyncio
    async def test_valid_png_image(self):
        """正常なPNG画像の検証"""
        # 最小のPNGデータ（1x1ピクセル）
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        file = UploadFile(
            filename="test_image.png",
            file=io.BytesIO(png_data)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is True, f"Valid PNG should pass: {message}"

    @pytest.mark.asyncio
    async def test_invalid_file_extension(self):
        """不正な拡張子の拒否"""
        jpeg_data = b'\xff\xd8\xff\xe0' + b'\x00' * 100

        file = UploadFile(
            filename="malware.exe",
            file=io.BytesIO(jpeg_data)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is False
        assert "Invalid file extension" in message

    @pytest.mark.asyncio
    async def test_oversized_file(self):
        """サイズ超過ファイルの拒否"""
        # 11MBのダミーデータ
        large_data = b'\x00' * (11 * 1024 * 1024)

        file = UploadFile(
            filename="large_image.jpg",
            file=io.BytesIO(large_data)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is False
        assert "File too large" in message

    @pytest.mark.asyncio
    async def test_mime_type_mismatch(self):
        """MIME typeと拡張子の不一致検出"""
        # PNG data but .jpg extension
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        file = UploadFile(
            filename="fake_image.jpg",  # PNG data with .jpg extension
            file=io.BytesIO(png_data)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is False
        assert "MIME type mismatch" in message

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """パストラバーサル攻撃の防止"""
        malicious_filenames = [
            "../../etc/passwd.jpg",
            "../../../root/.ssh/id_rsa.jpg",
            "..\\..\\windows\\system32\\config\\sam.jpg",
            "test/../../secret.jpg"
        ]

        for malicious_filename in malicious_filenames:
            safe_filename = FileValidator.sanitize_filename(malicious_filename)

            # パスコンポーネントが削除されていることを確認
            assert ".." not in safe_filename
            assert "/" not in safe_filename
            assert "\\" not in safe_filename

    @pytest.mark.asyncio
    async def test_null_byte_injection(self):
        """NULL byte インジェクション防止"""
        filename = "image.jpg\x00.exe"
        safe_filename = FileValidator.sanitize_filename(filename)

        assert "\x00" not in safe_filename

    @pytest.mark.asyncio
    async def test_empty_filename(self):
        """空のファイル名の拒否"""
        file = UploadFile(
            filename="",
            file=io.BytesIO(b'\x00' * 100)
        )

        is_valid, message = await FileValidator.validate_image(file)

        assert is_valid is False
        assert "Filename is required" in message

    def test_file_count_validation(self):
        """ファイル数制限の検証"""
        # 正常な範囲
        is_valid, message = FileValidator.validate_file_count(5)
        assert is_valid is True

        # 上限超過
        is_valid, message = FileValidator.validate_file_count(11)
        assert is_valid is False
        assert "Too many files" in message

        # 0個
        is_valid, message = FileValidator.validate_file_count(0)
        assert is_valid is False


class TestRateLimiter:
    """レート制限のテスト"""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_requests(self):
        """通常のリクエストは許可される"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        for i in range(5):
            is_allowed, message = await limiter.check_rate_limit("client_1")
            assert is_allowed is True, f"Request {i+1} should be allowed"

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self):
        """過剰なリクエストは拒否される"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # 最初の3リクエストは成功
        for i in range(3):
            is_allowed, message = await limiter.check_rate_limit("client_2")
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # 4つ目は拒否
        is_allowed, message = await limiter.check_rate_limit("client_2")
        assert is_allowed is False
        assert "Rate limit exceeded" in message

    @pytest.mark.asyncio
    async def test_rate_limit_per_client(self):
        """クライアント毎に独立したレート制限"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Client 1: 2リクエスト
        await limiter.check_rate_limit("client_1")
        await limiter.check_rate_limit("client_1")

        # Client 2: 最初のリクエストは成功（独立している）
        is_allowed, message = await limiter.check_rate_limit("client_2")
        assert is_allowed is True


class TestAudioFileValidator:
    """音声ファイル検証のテスト"""

    @pytest.mark.asyncio
    async def test_valid_wav_audio(self):
        """正常なWAVファイルの検証"""
        # 最小のWAVデータ
        wav_data = (
            b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00'
        )

        file = UploadFile(
            filename="test_audio.wav",
            file=io.BytesIO(wav_data)
        )

        is_valid, message = await FileValidator.validate_audio(file)

        assert is_valid is True, f"Valid WAV should pass: {message}"

    @pytest.mark.asyncio
    async def test_invalid_audio_extension(self):
        """不正な音声拡張子の拒否"""
        wav_data = b'RIFF' + b'\x00' * 100

        file = UploadFile(
            filename="audio.txt",
            file=io.BytesIO(wav_data)
        )

        is_valid, message = await FileValidator.validate_audio(file)

        assert is_valid is False
        assert "Invalid audio file extension" in message
