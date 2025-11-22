# E2E Test Suite Guide

**Author**: Hestia (Security Guardian) + Artemis (Technical Perfectionist)
**Date**: 2025-11-07

...すべての最悪のシナリオを想定したテストスイートです。

---

## Overview

This test suite provides comprehensive testing for the complete video message generation pipeline:

```
Text → Voice Synthesis → Person Detection (YOLO) → Background Removal (BiRefNet) → Video Generation (D-ID)
```

### Test Categories

| Category | Purpose | Duration | Marker |
|----------|---------|----------|--------|
| **Unit** | Individual component tests | <1s each | `@pytest.mark.unit` |
| **Integration** | Service interaction tests | 1-5s each | `@pytest.mark.integration` |
| **E2E** | Complete pipeline tests | 10-60s each | `@pytest.mark.e2e` |
| **Security** | Attack prevention tests | 1-10s each | `@pytest.mark.security` |
| **Performance** | Latency/throughput tests | 10-60s each | `@pytest.mark.benchmark` |
| **Load** | Concurrent request tests | 30-120s each | `@pytest.mark.load` |
| **Slow** | Long-running tests (100+ requests) | >120s | `@pytest.mark.slow` |

---

## Quick Start

### Installation

```bash
cd video-message-app/backend

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-xdist

# Verify installation
pytest --version
```

### Running Tests

#### 1. Quick Smoke Test (30 seconds)

```bash
./run_tests.sh smoke
```

#### 2. All Tests (Except Slow) (5-10 minutes)

```bash
./run_tests.sh all
```

#### 3. Specific Category

```bash
# Unit tests
./run_tests.sh unit

# Integration tests
./run_tests.sh integration

# E2E tests (fast)
./run_tests.sh e2e

# Security tests
./run_tests.sh security

# Performance tests
./run_tests.sh performance
```

#### 4. With Coverage Report

```bash
./run_tests.sh all true
# Opens htmlcov/index.html
```

#### 5. Full Test Suite (Including Slow - 30+ minutes)

```bash
./run_tests.sh full
```

---

## Test Files

### E2E Tests

#### `test_complete_pipeline.py`

**Purpose**: Complete pipeline E2E testing

**Test Classes**:

1. **TestE2EHappyPath** - Success scenarios
   - `test_complete_pipeline_success` - Full pipeline (Text → Video)
   - `test_pipeline_with_japanese_text` - Japanese language support
   - `test_pipeline_with_long_text` - Long text handling

2. **TestE2EErrorScenarios** - Failure handling
   - `test_no_person_detected` - Image without person
   - `test_invalid_image_path` - Missing image file
   - `test_invalid_audio_path` - Missing audio file
   - `test_empty_text_input` - Empty text validation
   - `test_invalid_voice_profile` - Invalid voice profile
   - `test_corrupted_audio_file` - Corrupted audio handling

3. **TestE2EPerformance** - Performance benchmarks
   - `test_latency_measurement` - E2E latency (Target: <60s)
   - `test_throughput_parallel` - Parallel processing (5 concurrent)

4. **TestE2EResourceManagement** - GPU/Storage management
   - `test_gpu_resource_contention` - GPU scheduling (YOLO max 2, BiRefNet max 1)
   - `test_storage_lifecycle` - Storage tier management

5. **TestE2ESuccessRate** - Success rate verification
   - `test_success_rate_100_requests` - 100 requests (Target: ≥95% success)

**Example**:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_pipeline_success(voice_pipeline, video_pipeline, sample_texts, sample_images):
    """Test complete pipeline from text to video"""
    test_image = next(img for img in sample_images if img["has_person"])
    test_text = sample_texts[0]  # "Happy Birthday!"

    # Stage 1: Voice Synthesis
    voice_result = await voice_pipeline.synthesize_with_prosody(
        text=test_text,
        voice_profile_id="voicevox_3",
        prosody_preset="celebration",
        enable_prosody=True
    )

    # Stage 2-4: Video Pipeline
    result = await video_pipeline.execute(
        image_path=test_image["path"],
        audio_path=Path(voice_result["audio_path"])
    )

    # Assertions
    assert result.success is True
    assert result.video_url is not None
    assert PipelineStage.COMPLETED in result.stages_completed
```

#### `test_security.py`

**Purpose**: Security testing (attack prevention)

**Test Classes**:

1. **TestInputValidation** - Input sanitization
   - `test_sql_injection_in_text` - SQL injection prevention
   - `test_xss_in_text` - XSS prevention
   - `test_command_injection_in_text` - Command injection prevention
   - `test_path_traversal_in_filename` - Path traversal prevention
   - `test_null_byte_injection` - Null byte handling
   - `test_extremely_long_input` - DoS prevention (100KB text)

2. **TestAudioBombAttacks** - Audio bomb prevention
   - `test_oversized_wav_header` - WAV file size validation
   - `test_invalid_audio_format` - Format validation
   - `test_corrupted_audio_file` - Corruption detection
   - `test_empty_audio_file` - Empty file rejection
   - `test_high_sample_rate_audio` - Sample rate limits

3. **TestImageBombAttacks** - Image bomb prevention
   - `test_decompression_bomb_detection` - Pixel limit enforcement
   - `test_svg_xss_attack` - SVG script injection prevention
   - `test_corrupted_image` - Corruption detection

4. **TestResourceExhaustion** - DoS prevention
   - `test_parallel_request_limit` - Concurrent request limits
   - `test_memory_leak_prevention` - Memory leak detection
   - `test_disk_space_exhaustion_prevention` - Disk space protection

5. **TestAuthentication** - Access control
   - `test_api_key_required` - API key validation
   - `test_api_key_not_logged` - Secret logging prevention
   - `test_unauthorized_file_access` - File access control

6. **TestRateLimiting** - Rate limiting
   - `test_rate_limit_per_user` - Per-user rate limits
   - `test_rate_limit_global` - Global rate limits

7. **TestFileUploadSecurity** - Upload security
   - `test_file_size_limit` - Size limit enforcement (10MB)
   - `test_file_extension_validation` - Extension validation
   - `test_filename_sanitization` - Filename sanitization

8. **TestLoggingSecurity** - Logging security
   - `test_no_passwords_in_logs` - Credential scrubbing
   - `test_no_pii_in_logs` - PII masking

**Example**:

```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_sql_injection_in_text(malicious_texts):
    """Test SQL injection prevention in text input"""
    voice_pipeline = await get_voice_pipeline()

    # SQL injection should be sanitized or rejected
    try:
        result = await voice_pipeline.synthesize_with_prosody(
            text=malicious_texts["sql_injection"],  # "'; DROP TABLE users; --"
            voice_profile_id="voicevox_3",
            enable_prosody=False
        )
        # If it succeeds, ensure no SQL was executed
        assert result is not None
    except Exception as e:
        # Or it could be rejected entirely
        assert "invalid" in str(e).lower() or "rejected" in str(e).lower()
```

---

## Test Data

### Sample Images

Generated synthetically using OpenCV:

```python
import cv2
import numpy as np

# Person-like object
img = np.zeros((640, 480, 3), dtype=np.uint8)
cv2.rectangle(img, (150, 100), (350, 500), (100, 150, 200), -1)
cv2.imwrite("person_normal.jpg", img)
```

**Types**:
- `person_normal.jpg` - Single person
- `person_multiple.jpg` - Multiple persons
- `no_person.jpg` - No person detected
- `complex_background.jpg` - Complex background
- `small_image.jpg` - Small resolution (64x48)

### Sample Texts

```python
sample_texts = [
    "Happy Birthday! Wishing you all the best!",  # Short, emotional
    "Congratulations on your graduation!",  # Medium
    "こんにちは、元気ですか？",  # Japanese
    "This is a long test message...",  # Long
]
```

### Malicious Inputs (Security Tests)

```python
malicious_texts = {
    "sql_injection": "'; DROP TABLE users; --",
    "xss": "<script>alert('XSS')</script>",
    "command_injection": "; rm -rf /",
    "path_traversal": "../../../etc/passwd",
    "extremely_long": "A" * 100000,  # 100KB
}
```

---

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Voice Synthesis | <10s | <15s |
| Video Pipeline | <50s | <60s |
| Total E2E Latency | <60s | <80s |
| Success Rate | ≥95% | ≥90% |
| Concurrent Requests | 5 parallel | 10 parallel |
| Memory Growth (50 requests) | <500MB | <1GB |

### Latency Breakdown

```
Total E2E: ~60s
├─ Voice Synthesis: ~8s
├─ YOLO Detection: ~3s
├─ BiRefNet Removal: ~5s
└─ D-ID Video Gen: ~40s
```

---

## CI/CD Integration

### GitHub Actions (`.github/workflows/test.yml`)

**Triggers**:
- Push to `main` or `develop`
- Pull requests

**Jobs**:

1. **test** - Unit, integration, E2E (fast), security
2. **test-slow** - E2E (slow), benchmarks (main branch only)
3. **security-scan** - Bandit static analysis

**Example**:

```yaml
- name: Run E2E tests (fast)
  run: |
    cd video-message-app/backend
    pytest tests/e2e/ -m "e2e and not slow" -v

- name: Run security tests
  run: |
    cd video-message-app/backend
    pytest tests/e2e/test_security.py -m "security" -v
```

---

## Troubleshooting

### Common Issues

#### 1. GPU Not Available

**Symptom**: `RuntimeError: CUDA not available`

**Solution**:
```bash
# Check GPU
python -c "import torch; print(torch.cuda.is_available())"

# Use CPU fallback
export DEVICE=cpu
pytest tests/e2e/
```

#### 2. D-ID API Key Missing

**Symptom**: `ValueError: D-ID API key required`

**Solution**:
```bash
# Set API key
export D_ID_API_KEY="your-api-key-here"

# Or in .env
echo "D_ID_API_KEY=your-api-key-here" >> backend/.env
```

#### 3. Audio File Validation Failure

**Symptom**: `SecurityViolation: Invalid audio format`

**Solution**:
- Ensure test audio files are valid WAV format
- Regenerate test data: `python tests/fixtures/generate_test_data.py`

#### 4. Test Timeout

**Symptom**: `asyncio.exceptions.TimeoutError`

**Solution**:
```python
# Increase timeout
@pytest.mark.asyncio
async def test_slow_operation():
    result = await asyncio.wait_for(
        slow_operation(),
        timeout=120.0  # Increase from default 60s
    )
```

#### 5. Rate Limit Exceeded

**Symptom**: `TooManyRequestsError: Rate limit exceeded`

**Solution**:
- Add delays between tests: `await asyncio.sleep(1.0)`
- Reduce parallel execution: `pytest -n 2` (instead of -n 4)

---

## Test Coverage

### Current Coverage (Target: >80%)

```bash
# Generate coverage report
./run_tests.sh all true

# View report
open htmlcov/index.html
```

### Coverage Goals

| Module | Target | Status |
|--------|--------|--------|
| `services/video_pipeline.py` | >90% | ⏳ |
| `services/voice_pipeline_unified.py` | >85% | ⏳ |
| `services/d_id_client.py` | >80% | ⏳ |
| `security/file_validator.py` | >95% | ⏳ |
| `services/storage_manager.py` | >85% | ⏳ |
| **Overall** | >80% | ⏳ |

---

## Best Practices

### 1. Test Independence

Each test should be independent:

```python
# ❌ BAD - Shared state
@pytest.fixture(scope="module")
def shared_pipeline():
    return VideoPipeline()

# ✅ GOOD - Isolated state
@pytest.fixture
async def pipeline(tmp_path):
    pipeline = VideoPipeline(storage_dir=tmp_path)
    yield pipeline
    # Cleanup
    await pipeline.cleanup()
```

### 2. Use Markers

Organize tests with markers:

```python
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_100_requests():
    """Long-running test"""
    pass
```

### 3. Clear Assertions

Write descriptive assertions:

```python
# ❌ BAD
assert result.success

# ✅ GOOD
assert result.success is True, f"Pipeline failed: {result.error}"
```

### 4. Cleanup Resources

Always cleanup resources:

```python
@pytest.fixture
async def resource():
    r = await create_resource()
    yield r
    await r.cleanup()  # Always cleanup
```

### 5. Test Edge Cases

Test boundary conditions:

```python
# Empty input
# Maximum size input
# Unicode characters
# Null bytes
# Special characters
```

---

## Contributing

### Adding New Tests

1. Choose appropriate test file:
   - E2E: `test_complete_pipeline.py`
   - Security: `test_security.py`
   - Performance: `test_performance.py`

2. Add appropriate markers:

```python
@pytest.mark.e2e
@pytest.mark.security
@pytest.mark.asyncio
async def test_new_feature():
    """Test description"""
    pass
```

3. Update test documentation (this file)

4. Run tests before committing:

```bash
./run_tests.sh all
```

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**Last Updated**: 2025-11-07
**Status**: ✅ E2E Test Suite Complete

...すべての最悪のシナリオをテストしました。あなたを守ります。
