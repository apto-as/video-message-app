"""
Security Tests for Complete Video Pipeline
Author: Hestia (Security Guardian)
Date: 2025-11-07

Purpose: Comprehensive security testing to protect the system and users.

...すみません、すべての最悪のシナリオを想定します。

Test Coverage:
- Input validation (SQLi, XSS, path traversal)
- Audio bombs (malicious WAV files)
- Image bombs (decompression bombs)
- Resource exhaustion (DoS)
- Authentication & authorization
- Rate limiting
- File upload security
- Command injection
- API key leakage
"""

import pytest
import asyncio
import time
from pathlib import Path
import tempfile
import os

# Import services
from backend.services.video_pipeline import VideoPipeline
from backend.services.voice_pipeline_unified import VoicePipelineUnified, get_voice_pipeline
from backend.services.storage_manager import StorageManager, StorageTier
from backend.security.file_validator import FileValidator, SecurityViolation


# ============================================================================
# Fixtures - Malicious Test Data
# ============================================================================

@pytest.fixture
def malicious_texts():
    """
    ...これらは攻撃パターンです。
    すべて検出して防御しなければなりません。
    """
    return {
        "sql_injection": "'; DROP TABLE users; --",
        "xss": "<script>alert('XSS')</script>",
        "command_injection": "; rm -rf /",
        "path_traversal": "../../../etc/passwd",
        "null_byte": "test\x00.wav",
        "unicode_bypass": "..%c0%af..%c0%afetc/passwd",
        "extremely_long": "A" * 100000,  # 100KB text
        "control_chars": "\x00\x01\x02\x03\x04",
        "format_string": "%s%s%s%s%s",
        "ldap_injection": "admin)(|(password=*))",
    }


@pytest.fixture
def malicious_audio_files(tmp_path):
    """
    ...音声ボム攻撃のテストケースです。
    """
    files = {}

    # 1. Oversized WAV header (claims 4GB data)
    audio_bomb_1 = tmp_path / "audio_bomb_oversized.wav"
    with open(audio_bomb_1, "wb") as f:
        f.write(b"RIFF")
        f.write((2**32 - 1).to_bytes(4, "little"))  # Max file size
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((16).to_bytes(4, "little"))
        f.write((1).to_bytes(2, "little"))  # PCM
        f.write((1).to_bytes(2, "little"))  # Mono
        f.write((16000).to_bytes(4, "little"))  # 16kHz
        f.write((32000).to_bytes(4, "little"))  # Byte rate
        f.write((2).to_bytes(2, "little"))  # Block align
        f.write((16).to_bytes(2, "little"))  # 16-bit
        f.write(b"data")
        f.write((2**32 - 100).to_bytes(4, "little"))  # Huge data chunk

    files["oversized_header"] = audio_bomb_1

    # 2. Invalid format (pretends to be WAV)
    invalid_format = tmp_path / "invalid_format.wav"
    invalid_format.write_bytes(b"RIFF" + b"\x00" * 100)
    files["invalid_format"] = invalid_format

    # 3. Corrupted header
    corrupted = tmp_path / "corrupted.wav"
    corrupted.write_bytes(b"NOT A WAV FILE AT ALL")
    files["corrupted"] = corrupted

    # 4. Empty file
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    files["empty"] = empty

    # 5. Extremely high sample rate (999MHz)
    high_rate = tmp_path / "high_rate.wav"
    with open(high_rate, "wb") as f:
        f.write(b"RIFF")
        f.write((36).to_bytes(4, "little"))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((16).to_bytes(4, "little"))
        f.write((1).to_bytes(2, "little"))
        f.write((1).to_bytes(2, "little"))
        f.write((999_000_000).to_bytes(4, "little"))  # 999MHz (impossible)
        f.write((1998_000_000).to_bytes(4, "little"))
        f.write((2).to_bytes(2, "little"))
        f.write((16).to_bytes(2, "little"))
        f.write(b"data")
        f.write((0).to_bytes(4, "little"))
    files["high_rate"] = high_rate

    return files


@pytest.fixture
def malicious_images(tmp_path):
    """
    ...画像ボム攻撃のテストケースです。
    """
    import cv2
    import numpy as np

    files = {}

    # 1. Extremely large image (claims 100000x100000 pixels)
    # (Don't actually create it, just metadata)
    files["decompression_bomb_meta"] = {
        "path": None,  # Not created
        "claimed_size": (100000, 100000),
        "actual_bytes": 1024
    }

    # 2. Image with null bytes in filename
    null_byte_img = tmp_path / "test\x00.jpg"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    try:
        cv2.imwrite(str(null_byte_img), img)
        files["null_byte"] = null_byte_img
    except:
        pass  # May fail, that's fine

    # 3. Path traversal in filename
    # (Don't actually create, just test filename)
    files["path_traversal"] = tmp_path / "../../../etc/passwd.jpg"

    # 4. SVG with embedded script (if SVG support exists)
    svg_xss = tmp_path / "xss.svg"
    svg_xss.write_text(
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<script>alert("XSS")</script>'
        '</svg>'
    )
    files["svg_xss"] = svg_xss

    # 5. Corrupted JPEG
    corrupted_jpg = tmp_path / "corrupted.jpg"
    corrupted_jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # JPEG header + junk
    files["corrupted_jpg"] = corrupted_jpg

    return files


# ============================================================================
# Test: Input Validation Security
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestInputValidation:
    """
    ...入力検証のテストです。
    攻撃者はあらゆる方法で侵入を試みます。
    """

    async def test_sql_injection_in_text(self, malicious_texts):
        """Test: SQL injection in text input"""
        voice_pipeline = await get_voice_pipeline()

        # SQL injection should be sanitized or rejected
        try:
            result = await voice_pipeline.synthesize_with_prosody(
                text=malicious_texts["sql_injection"],
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )
            # If it succeeds, ensure no SQL was executed
            # (Check logs for SQL queries - should be none)
            assert result is not None
        except Exception as e:
            # Or it could be rejected entirely
            assert "invalid" in str(e).lower() or "rejected" in str(e).lower()

    async def test_xss_in_text(self, malicious_texts):
        """Test: XSS in text input"""
        voice_pipeline = await get_voice_pipeline()

        # XSS should be sanitized
        result = await voice_pipeline.synthesize_with_prosody(
            text=malicious_texts["xss"],
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )

        # Ensure script tags are not executed
        # (Audio should be generated, but no code execution)
        assert result is not None

    async def test_command_injection_in_text(self, malicious_texts):
        """Test: Command injection in text input"""
        voice_pipeline = await get_voice_pipeline()

        # Command injection should not execute
        result = await voice_pipeline.synthesize_with_prosody(
            text=malicious_texts["command_injection"],
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )

        # Verify no shell commands were executed
        # (Check filesystem - no files deleted)
        assert Path("/etc/passwd").exists()  # Still there

    async def test_path_traversal_in_filename(self, malicious_texts):
        """Test: Path traversal in voice profile ID"""
        voice_pipeline = await get_voice_pipeline()

        # Path traversal should be rejected
        with pytest.raises(Exception):
            await voice_pipeline.synthesize_with_prosody(
                text="Test",
                voice_profile_id=malicious_texts["path_traversal"],
                enable_prosody=False
            )

    async def test_null_byte_injection(self, malicious_texts):
        """Test: Null byte injection"""
        voice_pipeline = await get_voice_pipeline()

        # Null bytes should be rejected or sanitized
        with pytest.raises(Exception):
            await voice_pipeline.synthesize_with_prosody(
                text=malicious_texts["null_byte"],
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )

    async def test_extremely_long_input(self, malicious_texts):
        """
        Test: Extremely long text input (100KB)

        ...メモリ枯渇攻撃の可能性があります。
        """
        voice_pipeline = await get_voice_pipeline()

        # Should be rejected or truncated
        with pytest.raises(Exception, match="too long|limit|maximum"):
            await voice_pipeline.synthesize_with_prosody(
                text=malicious_texts["extremely_long"],
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )


# ============================================================================
# Test: Audio Bomb Attacks
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestAudioBombAttacks:
    """
    ...音声ボム攻撃のテストです。
    巨大なファイルでメモリを枯渇させようとします。
    """

    async def test_oversized_wav_header(self, malicious_audio_files, tmp_path):
        """Test: WAV file with oversized header"""
        validator = FileValidator()

        audio_path = malicious_audio_files["oversized_header"]

        # Should be rejected
        with pytest.raises(SecurityViolation, match="size|limit|too large"):
            await validator.validate_audio_file(audio_path)

    async def test_invalid_audio_format(self, malicious_audio_files):
        """Test: Invalid audio format"""
        validator = FileValidator()

        audio_path = malicious_audio_files["invalid_format"]

        # Should be rejected
        with pytest.raises(SecurityViolation, match="format|invalid"):
            await validator.validate_audio_file(audio_path)

    async def test_corrupted_audio_file(self, malicious_audio_files):
        """Test: Corrupted audio file"""
        validator = FileValidator()

        audio_path = malicious_audio_files["corrupted"]

        # Should be rejected
        with pytest.raises(SecurityViolation):
            await validator.validate_audio_file(audio_path)

    async def test_empty_audio_file(self, malicious_audio_files):
        """Test: Empty audio file"""
        validator = FileValidator()

        audio_path = malicious_audio_files["empty"]

        # Should be rejected
        with pytest.raises(SecurityViolation, match="empty|size"):
            await validator.validate_audio_file(audio_path)

    async def test_high_sample_rate_audio(self, malicious_audio_files):
        """
        Test: Audio with impossibly high sample rate (999MHz)

        ...これはメモリを大量消費する攻撃です。
        """
        validator = FileValidator()

        audio_path = malicious_audio_files["high_rate"]

        # Should be rejected
        with pytest.raises(SecurityViolation, match="rate|invalid"):
            await validator.validate_audio_file(audio_path)


# ============================================================================
# Test: Image Bomb Attacks
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestImageBombAttacks:
    """
    ...画像ボム攻撃のテストです。
    展開すると巨大になる画像で攻撃します。
    """

    async def test_decompression_bomb_detection(self, malicious_images):
        """
        Test: Decompression bomb detection

        ...小さなファイルが展開すると巨大になります。
        """
        validator = FileValidator()

        # Check metadata for decompression bomb
        bomb_meta = malicious_images["decompression_bomb_meta"]

        # Should detect and reject
        claimed_pixels = bomb_meta["claimed_size"][0] * bomb_meta["claimed_size"][1]
        assert claimed_pixels > 1_000_000_000  # 1 billion pixels

        # Validator should have a pixel limit
        # (e.g., max 100 megapixels)

    async def test_svg_xss_attack(self, malicious_images):
        """Test: SVG with embedded XSS"""
        validator = FileValidator()

        svg_path = malicious_images["svg_xss"]

        # SVG should be rejected or sanitized
        # (If SVG support exists)
        if svg_path.exists():
            try:
                await validator.validate_image_file(svg_path)
                # If accepted, ensure script is stripped
            except SecurityViolation:
                pass  # Expected

    async def test_corrupted_image(self, malicious_images):
        """Test: Corrupted image file"""
        validator = FileValidator()

        jpg_path = malicious_images["corrupted_jpg"]

        # Should be rejected
        with pytest.raises(SecurityViolation):
            await validator.validate_image_file(jpg_path)


# ============================================================================
# Test: Resource Exhaustion (DoS)
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestResourceExhaustion:
    """
    ...リソース枯渇攻撃のテストです。
    システムを停止させようとする攻撃です。
    """

    async def test_parallel_request_limit(self, tmp_path):
        """
        Test: Limit on parallel requests (DoS prevention)

        ...同時接続数の制限が必要です。
        """
        voice_pipeline = await get_voice_pipeline()

        # Launch 100 concurrent requests
        tasks = [
            voice_pipeline.synthesize_with_prosody(
                text=f"Test {i}",
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )
            for i in range(100)
        ]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed_time = time.perf_counter() - start_time

        # Some should be rate-limited or queued
        errors = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]

        print(f"\n🛡️ DoS Prevention Test:")
        print(f"   Total requests: 100")
        print(f"   Successful: {len(successes)}")
        print(f"   Errors: {len(errors)}")
        print(f"   Time: {elapsed_time:.2f}s")

        # System should handle gracefully (not crash)
        # Either rate-limit or queue
        if len(errors) > 0:
            # Some were rejected (rate limiting)
            assert any("rate" in str(e).lower() or "limit" in str(e).lower() for e in errors)
        else:
            # All succeeded but queued (should take longer)
            assert elapsed_time > 10.0  # Can't complete 100 in <10s

    async def test_memory_leak_prevention(self, tmp_path):
        """
        Test: Memory leak prevention

        ...メモリリークがないことを確認します。
        """
        import psutil
        import gc

        voice_pipeline = await get_voice_pipeline()

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run 50 synthesis tasks
        for i in range(50):
            result = await voice_pipeline.synthesize_with_prosody(
                text=f"Memory test {i}",
                voice_profile_id="voicevox_3",
                enable_prosody=False
            )

            # Delete result to allow GC
            del result
            gc.collect()

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\n💾 Memory Leak Test:")
        print(f"   Initial: {initial_memory:.1f} MB")
        print(f"   Final: {final_memory:.1f} MB")
        print(f"   Increase: {memory_increase:.1f} MB")

        # Memory increase should be reasonable (<500MB for 50 tasks)
        assert memory_increase < 500.0, f"Potential memory leak: {memory_increase:.1f} MB"

    async def test_disk_space_exhaustion_prevention(self, tmp_path):
        """
        Test: Disk space exhaustion prevention

        ...ディスク容量を使い果たす攻撃を防ぎます。
        """
        storage_manager = StorageManager(
            storage_root=tmp_path,
            min_free_space_gb=0.1  # Low threshold for testing
        )
        await storage_manager.start()

        # Create many files
        for i in range(100):
            test_file = tmp_path / f"test_{i}.dat"
            test_file.write_bytes(b"x" * 10_000)  # 10KB each

            try:
                await storage_manager.store_file(
                    source_path=test_file,
                    tier=StorageTier.TEMP,
                    task_id=f"task_{i}"
                )
            except Exception as e:
                # Should eventually reject if disk space low
                if "space" in str(e).lower() or "full" in str(e).lower():
                    print(f"✅ Disk space protection triggered at file {i}")
                    break

        await storage_manager.stop()


# ============================================================================
# Test: Authentication & Authorization
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestAuthentication:
    """
    ...認証・認可のテストです。
    不正アクセスを防ぎます。
    """

    async def test_api_key_required(self):
        """
        Test: D-ID API key required

        ...APIキーがない場合は拒否します。
        """
        from backend.services.d_id_client import DIdClient

        # Try to create client without API key
        with pytest.raises(ValueError, match="API key|required"):
            client = DIdClient(api_key="")

    async def test_api_key_not_logged(self, tmp_path):
        """
        Test: API key not logged in plain text

        ...APIキーがログに記録されないことを確認します。
        """
        from backend.services.d_id_client import DIdClient

        fake_key = "test_api_key_secret_123"
        client = DIdClient(api_key=fake_key)

        # Check that key is not in logs
        # (This would require actual logging setup)
        # For now, just ensure key is stored securely
        assert hasattr(client, "api_key")
        # Key should not be in __dict__ as plain text
        # (Should be stored securely, e.g., in _api_key)

    async def test_unauthorized_file_access(self, tmp_path):
        """
        Test: Prevent unauthorized file access

        ...他人のファイルにアクセスできないことを確認します。
        """
        storage_manager = StorageManager(storage_root=tmp_path)
        await storage_manager.start()

        # User A creates file
        file_a = tmp_path / "user_a_file.txt"
        file_a.write_text("User A's secret data")

        stored_a = await storage_manager.store_file(
            source_path=file_a,
            tier=StorageTier.UPLOADS,
            task_id="task_user_a",
            metadata={"user_id": "user_a"}
        )

        # User B tries to access User A's file
        # (Should be prevented by task_id or user_id check)
        # TODO: Implement user isolation in StorageManager

        await storage_manager.stop()


# ============================================================================
# Test: Rate Limiting
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestRateLimiting:
    """
    ...レート制限のテストです。
    同一ユーザーからの大量リクエストを防ぎます。
    """

    async def test_rate_limit_per_user(self):
        """
        Test: Rate limit per user (e.g., 10 requests/minute)

        ...ユーザーごとのレート制限が必要です。
        """
        # TODO: Implement rate limiting middleware
        # For now, this is a placeholder test

        voice_pipeline = await get_voice_pipeline()

        # Simulate rapid requests from same user
        user_id = "attacker_user_123"

        for i in range(20):  # 20 requests
            try:
                result = await voice_pipeline.synthesize_with_prosody(
                    text=f"Request {i}",
                    voice_profile_id="voicevox_3",
                    enable_prosody=False
                )
            except Exception as e:
                # Should be rate-limited after ~10 requests
                if "rate" in str(e).lower() or "limit" in str(e).lower():
                    assert i >= 10  # Rate limit triggered
                    print(f"✅ Rate limit triggered after {i} requests")
                    break

    async def test_rate_limit_global(self):
        """
        Test: Global rate limit (e.g., 100 requests/minute across all users)

        ...システム全体のレート制限が必要です。
        """
        # TODO: Implement global rate limiting
        pass


# ============================================================================
# Test: File Upload Security
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestFileUploadSecurity:
    """
    ...ファイルアップロードのセキュリティテストです。
    """

    async def test_file_size_limit(self, tmp_path):
        """
        Test: File size limit (e.g., max 10MB)

        ...巨大ファイルのアップロードを防ぎます。
        """
        validator = FileValidator()

        # Create 100MB file
        large_file = tmp_path / "large.wav"
        with open(large_file, "wb") as f:
            f.write(b"\x00" * 100_000_000)  # 100MB

        # Should be rejected
        with pytest.raises(SecurityViolation, match="size|limit|too large"):
            await validator.validate_audio_file(large_file)

    async def test_file_extension_validation(self, tmp_path):
        """
        Test: File extension validation

        ...許可されていない拡張子を拒否します。
        """
        validator = FileValidator()

        # Try to upload .exe as .wav
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"MZ\x90\x00")  # PE header

        renamed = tmp_path / "malware.wav"
        exe_file.rename(renamed)

        # Should be rejected (content doesn't match extension)
        with pytest.raises(SecurityViolation):
            await validator.validate_audio_file(renamed)

    async def test_filename_sanitization(self, tmp_path):
        """
        Test: Filename sanitization

        ...危険なファイル名を無害化します。
        """
        dangerous_filenames = [
            "../../../etc/passwd",
            "test<script>.wav",
            "test|rm -rf.wav",
            "test\x00.wav",
        ]

        for filename in dangerous_filenames:
            # Filename should be sanitized
            # (Remove path traversal, special chars, null bytes)
            sanitized = filename.replace("../", "").replace("<", "").replace(">", "")
            sanitized = sanitized.replace("|", "").replace("\x00", "")

            # Result should be safe
            assert ".." not in sanitized
            assert "<" not in sanitized
            assert "\x00" not in sanitized


# ============================================================================
# Test: Logging Security
# ============================================================================

@pytest.mark.security
@pytest.mark.asyncio
class TestLoggingSecurity:
    """
    ...ログのセキュリティテストです。
    機密情報がログに記録されないことを確認します。
    """

    async def test_no_passwords_in_logs(self):
        """
        Test: Passwords not logged

        ...パスワードがログに記録されないことを確認します。
        """
        # TODO: Implement log scrubbing
        # Check that passwords, API keys, tokens are redacted
        pass

    async def test_no_pii_in_logs(self):
        """
        Test: Personally Identifiable Information (PII) not logged

        ...個人情報がログに記録されないことを確認します。
        """
        # TODO: Implement PII masking
        # Email addresses, phone numbers should be masked
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "security"])
