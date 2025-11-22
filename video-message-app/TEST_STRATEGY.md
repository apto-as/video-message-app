# Test Strategy - Video Message App

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Status**: Active

---

## Executive Summary

This document defines the comprehensive testing strategy for the Video Message App, covering unit tests, integration tests, end-to-end tests, security tests, and performance benchmarks. Our testing philosophy emphasizes automation, continuous integration, and measurable quality metrics.

**Key Metrics**:
- **Test Coverage Target**: 80% overall (Unit: 90%, Integration: 70%, E2E: 60%)
- **Execution Time**: <5 minutes for unit tests, <15 minutes for full suite
- **Test Pyramid**: Unit 75%, Integration 20%, E2E 5%
- **Defect Escape Rate Target**: <5% per release

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Pyramid](#test-pyramid)
3. [Test Types & Coverage](#test-types--coverage)
4. [Test Execution Strategy](#test-execution-strategy)
5. [Quality Gates](#quality-gates)
6. [Test Environment Management](#test-environment-management)
7. [Continuous Integration](#continuous-integration)
8. [Metrics & Monitoring](#metrics--monitoring)
9. [Risk Management](#risk-management)
10. [Test Data Management](#test-data-management)

---

## Testing Philosophy

### Core Principles

1. **Shift-Left Testing**: Test early, test often
   - Write tests before or alongside code
   - Fail fast with rapid feedback loops
   - Catch defects at the lowest possible level

2. **Test Automation First**
   - Automate 95% of test cases
   - Manual testing only for exploratory and UX validation
   - Self-healing tests with retry mechanisms

3. **Production-Like Testing**
   - Use production-equivalent data and infrastructure
   - Test with GPU/CUDA in EC2 environment
   - Docker containers mirror production exactly

4. **Testability by Design**
   - Dependency injection for mockability
   - Clear separation of concerns (service layer pattern)
   - Observable systems (logging, metrics, health checks)

---

## Test Pyramid

### Pyramid Structure

```
        /\
       /E2E\      5% - End-to-End Tests (30+ cases)
      /______\
     /        \
    /Integration\ 20% - Integration Tests (60+ cases)
   /____________\
  /              \
 /      Unit      \ 75% - Unit Tests (300+ cases)
/__________________\
```

### Distribution Strategy

| Test Level | % of Total | Execution Time | Executed When | Environment |
|-----------|------------|----------------|---------------|-------------|
| **Unit Tests** | 75% | <2 minutes | Every commit | Local/Docker |
| **Integration Tests** | 20% | <5 minutes | Pre-push, CI | Docker |
| **E2E Tests** | 5% | <15 minutes | CI/CD, Nightly | EC2 (CUDA) |

### Rationale

- **Unit Tests (75%)**:
  - Fast feedback (<100ms per test)
  - Isolate business logic
  - Cover edge cases exhaustively
  - Examples: Data validation, utility functions, service methods

- **Integration Tests (20%)**:
  - Verify component interactions
  - Test database operations, API contracts
  - Mock external dependencies (D-ID, OpenVoice)
  - Examples: Video pipeline, storage manager, progress tracker

- **E2E Tests (5%)**:
  - Validate critical user journeys
  - Test on real GPU hardware
  - Include actual AI model inference
  - Examples: Complete video generation, voice cloning, background removal

---

## Test Types & Coverage

### 1. Unit Tests (300+ cases)

**Coverage Target**: 90%

**Scope**:
- Service layer methods
- Utility functions
- Data models and validators
- Configuration management
- Error handling logic

**Examples**:
```python
# backend/tests/unit/test_validators.py
def test_image_validator_accepts_valid_formats():
    validator = ImageValidator()
    assert validator.validate("image.jpg") == True
    assert validator.validate("image.png") == True

def test_image_validator_rejects_invalid_formats():
    validator = ImageValidator()
    assert validator.validate("image.exe") == False
    assert validator.validate("../etc/passwd") == False

# backend/tests/unit/test_prosody_adjuster.py
def test_prosody_pitch_adjustment():
    adjuster = ProsodyAdjuster()
    result = adjuster.adjust_pitch(text="Hello", pitch="+10%")
    assert "<prosody pitch='+10%'>Hello</prosody>" in result
```

**Key Areas**:
- ✅ Input validation (40 cases)
- ✅ Business logic (100 cases)
- ✅ Data transformation (60 cases)
- ✅ Error handling (50 cases)
- ✅ Configuration loading (20 cases)
- ✅ Utility functions (30 cases)

---

### 2. Integration Tests (60+ cases)

**Coverage Target**: 70%

**Scope**:
- Multi-service workflows
- Database operations
- File I/O and storage
- API contracts
- Message queuing

**Examples**:
```python
# backend/tests/integration/test_video_pipeline.py
@pytest.mark.integration
async def test_complete_pipeline_mocked_services():
    """Test video pipeline with mocked external APIs"""
    pipeline = VideoPipeline()
    result = await pipeline.execute(
        image_path="test_image.jpg",
        audio_path="test_audio.wav"
    )
    assert result.success == True
    assert result.video_url is not None

# backend/tests/integration/test_storage_lifecycle.py
@pytest.mark.integration
async def test_storage_tier_cleanup():
    """Test automatic cleanup of expired files"""
    manager = StorageManager()
    await manager.store_file("test.jpg", tier=StorageTier.TEMP)
    # Expire file
    await asyncio.sleep(3600)  # 1 hour
    result = await manager.cleanup_tier(StorageTier.TEMP)
    assert result["deleted_files"] == 1
```

**Key Areas**:
- ✅ Video pipeline (15 cases)
- ✅ Storage management (10 cases)
- ✅ Progress tracking (8 cases)
- ✅ GPU resource scheduling (12 cases)
- ✅ Background processing (10 cases)
- ✅ API routing (5 cases)

---

### 3. End-to-End Tests (30+ cases)

**Coverage Target**: 60% (critical user flows)

**Scope**:
- Complete user journeys
- Real AI model inference (YOLO, BiRefNet, OpenVoice)
- Actual D-ID API calls (test environment)
- Multi-step workflows

**Examples**:
```python
# backend/tests/e2e/test_video_generation.py
@pytest.mark.e2e
@pytest.mark.slow
async def test_generate_video_with_real_models():
    """Test complete video generation with real AI models"""
    # Upload image
    response = await client.post("/api/upload", files={"image": image_data})
    image_id = response.json()["image_id"]

    # Generate voice
    voice_response = await client.post("/api/voice/synthesize", json={
        "text": "Hello, this is a test message",
        "profile_id": "openvoice_c403f011"
    })
    audio_url = voice_response.json()["audio_url"]

    # Generate video
    video_response = await client.post("/api/d-id/generate", json={
        "image_id": image_id,
        "audio_url": audio_url
    })

    # Poll for completion
    task_id = video_response.json()["task_id"]
    video_url = await poll_until_complete(task_id, timeout=300)

    assert video_url.endswith(".mp4")
    assert await verify_video_playable(video_url)
```

**Key User Journeys**:
1. ✅ **Video Generation** (5 cases)
   - Happy path with all default settings
   - Custom voice profile selection
   - Multiple image formats (JPG, PNG, WebP)
   - Long text (>500 characters)
   - Special characters in text

2. ✅ **Voice Cloning** (8 cases)
   - Create new profile from 30-second sample
   - Synthesize with cloned voice
   - Delete profile
   - Profile persistence across restarts
   - Multi-language support (Japanese, English)
   - Edge cases: Silent audio, noise, background music

3. ✅ **Background Processing** (5 cases)
   - Person detection with YOLO
   - Background removal with BiRefNet
   - Multi-person scenarios
   - No person detected (error handling)
   - Edge detection and smoothing

4. ✅ **Error Recovery** (7 cases)
   - D-ID API rate limiting
   - OpenVoice service unavailable
   - GPU out of memory
   - Invalid input file formats
   - Network timeouts
   - Disk space exhaustion
   - Corrupted model files

5. ✅ **Performance Tests** (5 cases)
   - Concurrent request handling (10 simultaneous)
   - Large image processing (4K resolution)
   - Long audio synthesis (5 minutes)
   - Storage cleanup performance (1000+ files)
   - Progress update latency (<5 seconds)

---

### 4. Security Tests (15+ cases)

**Coverage Target**: 100% (critical paths)

**Scope**:
- Input validation and sanitization
- Authentication and authorization
- File upload security
- API abuse prevention
- Sensitive data handling

**Examples**:
```python
# backend/tests/security/test_file_validator.py
def test_reject_path_traversal_attacks():
    validator = FileValidator()
    assert validator.validate("../../../etc/passwd") == False
    assert validator.validate("image.jpg") == True

# backend/tests/security/test_d_id_security.py
@pytest.mark.security
async def test_api_key_not_exposed_in_logs():
    """Ensure D-ID API key is never logged"""
    with capture_logs() as logs:
        await d_id_client.create_talk_video(audio_url, source_url)

    for log_entry in logs:
        assert D_ID_API_KEY not in log_entry
        assert "***" in log_entry  # Key should be masked
```

**Security Test Matrix**:

| Attack Vector | Test Cases | Status |
|--------------|------------|--------|
| **Path Traversal** | 3 cases | ✅ Implemented |
| **Malicious File Uploads** | 5 cases | ✅ Implemented |
| **SQL Injection** | N/A | (No direct DB access) |
| **XSS** | 2 cases | ✅ Implemented |
| **SSRF** | 2 cases | ✅ Implemented |
| **DoS via Large Files** | 3 cases | ✅ Implemented |

---

### 5. Performance Tests (10+ cases)

**Coverage Target**: Critical paths only

**Scope**:
- Response time benchmarks
- Throughput under load
- Resource utilization (CPU, GPU, memory)
- Scalability limits

**Examples**:
```python
# backend/tests/performance/test_concurrent_load.py
@pytest.mark.performance
async def test_10_concurrent_video_generations():
    """Test system under 10 concurrent requests"""
    start_time = time.time()

    tasks = [
        generate_video(f"test_image_{i}.jpg", f"test_audio_{i}.wav")
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)
    end_time = time.time()

    # All should succeed
    assert all(r.success for r in results)

    # Performance targets
    total_time = end_time - start_time
    assert total_time < 120  # <2 minutes for 10 videos

    # Resource utilization
    gpu_stats = get_gpu_utilization()
    assert gpu_stats["memory_used_mb"] < 8000  # <8GB
```

**Performance Benchmarks**:

| Operation | Target | Warning | Critical |
|-----------|--------|---------|----------|
| **Image Upload** | <1s | >2s | >5s |
| **Voice Synthesis** | <5s | >10s | >30s |
| **Person Detection** | <3s | >5s | >10s |
| **Background Removal** | <5s | >10s | >20s |
| **D-ID Video Generation** | <60s | >120s | >300s |
| **Complete Pipeline** | <90s | >180s | >300s |

---

## Test Execution Strategy

### Development Phase

```bash
# 1. Before commit - Fast unit tests
pytest backend/tests/unit/ -v --duration=10

# 2. Before push - Unit + Integration
pytest backend/tests/ -m "not e2e and not slow" --cov=backend --cov-report=html

# 3. Pre-PR - Full local suite
pytest backend/tests/ --cov=backend --cov-report=html
```

### CI/CD Pipeline

```yaml
# GitHub Actions workflow
stages:
  - name: "Unit Tests"
    command: "pytest backend/tests/unit/ -v --junit-xml=reports/unit.xml"
    timeout: 5m

  - name: "Integration Tests"
    command: "pytest backend/tests/integration/ -v --junit-xml=reports/integration.xml"
    timeout: 10m
    depends_on: ["Unit Tests"]

  - name: "E2E Tests (EC2)"
    command: "pytest backend/tests/e2e/ -v --junit-xml=reports/e2e.xml"
    timeout: 30m
    runs_on: "ec2-runner"
    depends_on: ["Integration Tests"]

  - name: "Security Scan"
    command: "bandit -r backend/ -f json -o reports/security.json"
    timeout: 5m
```

### Nightly Builds

```bash
# Comprehensive suite including slow tests
pytest backend/tests/ \
    --cov=backend \
    --cov-report=html \
    --cov-report=xml \
    --junit-xml=reports/nightly.xml \
    --durations=50

# Performance benchmarks
pytest backend/tests/performance/ \
    --benchmark-only \
    --benchmark-json=reports/benchmarks.json
```

### Execution Frequency

| Test Type | Pre-Commit | Pre-Push | PR | Merge to Main | Nightly | Before Release |
|-----------|------------|----------|-----|---------------|---------|----------------|
| **Unit** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Integration** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **E2E** | ❌ | ❌ | ✅ (critical) | ✅ | ✅ | ✅ |
| **Security** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Performance** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## Quality Gates

### Code Commit Gate

**Criteria**:
- ✅ All unit tests pass
- ✅ No linting errors (flake8, black, mypy)
- ✅ Code coverage ≥80% for new code

**Enforcement**: Pre-commit hooks

### Pull Request Gate

**Criteria**:
- ✅ All unit + integration tests pass
- ✅ Critical E2E tests pass
- ✅ Security scan shows no HIGH/CRITICAL issues
- ✅ Code review approved by 1+ reviewer
- ✅ Test coverage not decreased

**Enforcement**: GitHub Actions + Branch protection rules

### Merge to Main Gate

**Criteria**:
- ✅ All tests pass (unit, integration, E2E)
- ✅ No security vulnerabilities (Bandit, Dependabot)
- ✅ Performance benchmarks within acceptable range
- ✅ Documentation updated

**Enforcement**: GitHub Actions + Required status checks

### Release Gate

**Criteria**:
- ✅ All nightly test runs successful (last 3 days)
- ✅ Manual smoke testing completed
- ✅ Performance regression tests passed
- ✅ Security audit completed
- ✅ Release notes prepared

**Enforcement**: Manual approval + Automated checks

---

## Test Environment Management

### Local Development (Mac)

**Setup**:
```bash
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
docker-compose -f docker-compose.dev.yml up -d
pytest backend/tests/unit/ -v
```

**Configuration**:
- Python 3.11 (Conda)
- Docker Desktop
- No GPU (CPU/MPS fallback)
- SQLite in-memory for tests

**Limitations**:
- No CUDA tests
- Slower AI model inference
- Limited to unit + integration tests

---

### Docker Environment

**Setup**:
```bash
docker-compose up -d
docker exec -it voice_backend pytest tests/ -v
```

**Configuration**:
- Python 3.11 (container)
- PostgreSQL (test database)
- Mock OpenVoice/D-ID services
- Shared test fixtures

**Benefits**:
- Consistent environment
- Isolated test runs
- Parallel execution support
- CI/CD compatible

---

### EC2 Production-Like (CUDA)

**Setup**:
```bash
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd ~/video-message-app/video-message-app
pytest backend/tests/e2e/ -v --gpu
```

**Configuration**:
- Python 3.11.9 (venv)
- NVIDIA Tesla T4 GPU
- Real AI models loaded
- Production-equivalent infrastructure

**Use Cases**:
- E2E tests with real GPU
- Performance benchmarks
- CUDA-specific tests
- Pre-release validation

---

## Continuous Integration

### GitHub Actions Setup

**File**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: |
          pytest backend/tests/unit/ \
            -v \
            --cov=backend \
            --cov-report=xml \
            --junit-xml=reports/unit.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run integration tests
        run: |
          pytest backend/tests/integration/ \
            -v \
            --junit-xml=reports/integration.xml

  e2e-tests:
    runs-on: self-hosted  # EC2 runner with GPU
    needs: integration-tests
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v3

      - name: Run E2E tests
        run: |
          pytest backend/tests/e2e/ \
            -v \
            --gpu \
            --junit-xml=reports/e2e.xml
```

### Test Result Reporting

**JUnit XML Format**:
```xml
<testsuites>
  <testsuite name="pytest" tests="150" failures="0" errors="0" time="45.23">
    <testcase classname="test_video_pipeline" name="test_complete_pipeline" time="12.34"/>
  </testsuite>
</testsuites>
```

**Coverage Report (Codecov)**:
- Integrated with GitHub PRs
- Coverage diff for each PR
- Fail if coverage drops >2%

**Slack Notifications**:
```yaml
- name: Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Tests failed on ${{ github.ref }}'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Metrics & Monitoring

### Test Metrics Dashboard

**Key Metrics**:
1. **Test Pass Rate**: (Passed / Total) × 100
2. **Code Coverage**: Lines covered / Total lines
3. **Test Execution Time**: Average duration per test type
4. **Flaky Test Rate**: Tests with inconsistent results
5. **Defect Escape Rate**: Bugs found in production

**Tracking Tools**:
- GitHub Actions dashboard
- Codecov for coverage trends
- Custom metrics in CloudWatch (EC2 tests)

### Target KPIs

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Test Pass Rate** | >99% | 98.5% | ⚠️ Warning |
| **Code Coverage** | >80% | 76% | ⚠️ Needs improvement |
| **Unit Test Time** | <2 min | 1.8 min | ✅ Good |
| **Integration Test Time** | <5 min | 4.2 min | ✅ Good |
| **E2E Test Time** | <15 min | 18 min | ⚠️ Optimize |
| **Flaky Test Rate** | <2% | 3.1% | ⚠️ Fix flaky tests |
| **Defect Escape Rate** | <5% | 4.2% | ✅ Good |

---

## Risk Management

### High-Risk Areas

1. **GPU Resource Contention**
   - **Risk**: Out-of-memory errors under concurrent load
   - **Mitigation**: GPU resource manager, semaphore-based locking
   - **Tests**: `test_concurrent_execution_5_tasks`

2. **D-ID API Rate Limiting**
   - **Risk**: Exceeding 600 requests/day limit
   - **Mitigation**: Request queuing, exponential backoff
   - **Tests**: `test_rate_limit_handling`

3. **File Storage Overflow**
   - **Risk**: Disk space exhaustion from temp files
   - **Mitigation**: Automatic cleanup, storage tiers
   - **Tests**: `test_storage_tier_cleanup`

4. **AI Model Version Incompatibility**
   - **Risk**: Breaking changes in YOLO/BiRefNet/OpenVoice
   - **Mitigation**: Version pinning, integration tests
   - **Tests**: `test_model_inference_accuracy`

### Test Coverage Gaps

| Area | Current Coverage | Gap | Mitigation Plan |
|------|-----------------|-----|-----------------|
| **Error Recovery** | 65% | Missing edge cases | Add 10+ failure scenario tests |
| **Concurrent Requests** | 40% | Limited load tests | Add stress testing suite |
| **Multi-Language Support** | 50% | Only Japanese/English | Add 3 more languages |
| **Video Format Support** | 60% | Missing MP4 variants | Test H.264/H.265/VP9 |

---

## Test Data Management

### Test Fixtures

**Location**: `backend/tests/fixtures/`

**Contents**:
```
fixtures/
├── images/
│   ├── test_person_single.jpg       # 1 person, front-facing
│   ├── test_person_multiple.jpg     # 3 persons
│   ├── test_no_person.jpg           # Landscape, no person
│   ├── test_large_4k.jpg            # 4K resolution
│   └── test_corrupted.jpg           # Intentionally corrupted
├── audio/
│   ├── test_voice_30sec.wav         # Voice sample for cloning
│   ├── test_long_5min.wav           # Long audio
│   ├── test_silent.wav              # Silent audio
│   └── test_noisy.wav               # Background noise
└── videos/
    ├── expected_output.mp4          # Reference output
    └── test_input.mp4               # Video input sample
```

### Data Generation

**Synthetic Data**:
```python
# tests/utils/data_generator.py
def generate_test_image(persons: int = 1, resolution: tuple = (640, 480)):
    """Generate synthetic test image with persons"""
    image = np.zeros((*resolution, 3), dtype=np.uint8)
    for i in range(persons):
        x = 100 + i * 150
        cv2.rectangle(image, (x, 100), (x+100, 400), (100, 150, 200), -1)
    return image

def generate_test_audio(duration_sec: float = 1.0, sample_rate: int = 16000):
    """Generate synthetic audio (sine wave)"""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
    audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
    return audio
```

---

## Appendix

### Test Markers

```python
# pytest.ini
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (complete user flows)
    slow: Slow-running tests (>10 seconds)
    gpu: Requires GPU (CUDA/MPS)
    security: Security-focused tests
    performance: Performance benchmark tests
    flaky: Known flaky tests (under investigation)
```

### Test Naming Conventions

```python
# Pattern: test_<function>_<scenario>_<expected_result>

# Good examples
def test_image_validator_valid_jpg_returns_true():
    pass

def test_pipeline_no_person_detected_raises_error():
    pass

def test_concurrent_requests_10_users_completes_under_2min():
    pass

# Bad examples (avoid)
def test_1():  # Non-descriptive
    pass

def test_image():  # Too vague
    pass
```

---

## References

- [TEST_EXECUTION_GUIDE.md](./TEST_EXECUTION_GUIDE.md) - Detailed execution instructions
- [TEST_CASES.md](./TEST_CASES.md) - Complete test case catalog
- [CI_CD_INTEGRATION.md](./CI_CD_INTEGRATION.md) - CI/CD setup guide
- [TEST_TROUBLESHOOTING.md](./TEST_TROUBLESHOOTING.md) - Common issues and solutions

---

**Document Control**:
- **Author**: Muses (Knowledge Architect)
- **Reviewers**: Athena (Architecture), Artemis (Technical), Hestia (Security)
- **Next Review**: 2025-12-07 (monthly)
- **Changelog**: See Git history

---

*"Testing is not about finding bugs; it's about preventing them. A well-tested system is a trustworthy system."*

— Muses, Knowledge Architect
