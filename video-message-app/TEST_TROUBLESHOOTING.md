# Test Troubleshooting Guide - Video Message App

**Version**: 1.0.0
**Last Updated**: 2025-11-07

---

## Table of Contents

1. [Common Test Failures](#common-test-failures)
2. [Environment Issues](#environment-issues)
3. [GPU-Related Problems](#gpu-related-problems)
4. [Dependency Issues](#dependency-issues)
5. [Network & Timeout Problems](#network--timeout-problems)
6. [File System Issues](#file-system-issues)
7. [Mock & Fixture Problems](#mock--fixture-problems)
8. [Coverage Issues](#coverage-issues)
9. [CI/CD Failures](#cicd-failures)
10. [Performance Problems](#performance-problems)

---

## Common Test Failures

### 1. Import Errors

#### Symptom
```
ImportError: cannot import name 'VideoPipeline' from 'services.video_pipeline'
```

#### Causes
- Module not in Python path
- Circular import
- Typo in import statement
- Missing `__init__.py`

#### Solutions

**Solution 1: Add project root to PYTHONPATH**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
pytest backend/tests/ -v
```

**Solution 2: Install package in editable mode**
```bash
cd backend
pip install -e .
pytest tests/ -v
```

**Solution 3: Use `conftest.py` to modify sys.path**
```python
# backend/tests/conftest.py
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
```

---

### 2. Async Test Failures

#### Symptom
```
RuntimeWarning: coroutine 'test_async_function' was never awaited
```

#### Cause
Missing `@pytest.mark.asyncio` decorator

#### Solution
```python
import pytest

# ❌ WRONG
def test_async_pipeline():
    result = await pipeline.execute()

# ✅ CORRECT
@pytest.mark.asyncio
async def test_async_pipeline():
    result = await pipeline.execute()
    assert result.success == True
```

**Alternative: Configure pytest-asyncio mode in pytest.ini**
```ini
[pytest]
asyncio_mode = auto  # Automatically detect async tests
```

---

### 3. Fixture Not Found

#### Symptom
```
fixture 'video_pipeline' not found
```

#### Causes
- Fixture defined in wrong file
- Fixture scope mismatch
- Typo in fixture name

#### Solutions

**Solution 1: Move fixture to conftest.py**
```python
# backend/tests/conftest.py (shared fixtures)
import pytest

@pytest.fixture
async def video_pipeline(tmp_path):
    """Shared video pipeline fixture"""
    pipeline = VideoPipeline(storage_dir=tmp_path)
    yield pipeline
    # Cleanup
    await pipeline.cleanup()
```

**Solution 2: Check fixture scope**
```python
# If using session scope, declare it properly
@pytest.fixture(scope="session")
async def video_pipeline():
    pipeline = VideoPipeline()
    yield pipeline
    await pipeline.cleanup()
```

---

### 4. Assertion Failures with Floating Point

#### Symptom
```
AssertionError: 0.8999999999999999 != 0.9
```

#### Cause
Floating point precision issues

#### Solution
```python
import pytest

# ❌ WRONG
assert result == 0.9

# ✅ CORRECT
assert result == pytest.approx(0.9, rel=1e-2)  # 1% tolerance

# Or use math.isclose()
import math
assert math.isclose(result, 0.9, rel_tol=1e-2)
```

---

### 5. Test Timeout

#### Symptom
```
TimeoutError: Test exceeded 120 seconds
```

#### Causes
- Infinite loop
- Blocking I/O operation
- GPU resource deadlock

#### Solutions

**Solution 1: Increase timeout for specific test**
```python
@pytest.mark.timeout(300)  # 5 minutes
async def test_long_running():
    result = await slow_operation()
```

**Solution 2: Disable timeout for debugging**
```python
@pytest.mark.timeout(0)  # No timeout
async def test_debug():
    result = await problematic_function()
```

**Solution 3: Use asyncio.wait_for with timeout**
```python
import asyncio

@pytest.mark.asyncio
async def test_with_internal_timeout():
    try:
        result = await asyncio.wait_for(
            slow_operation(),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        pytest.fail("Operation timed out")
```

---

## Environment Issues

### 6. Missing Environment Variables

#### Symptom
```
KeyError: 'D_ID_API_KEY'
```

#### Cause
Environment variable not set

#### Solutions

**Solution 1: Create .env file for tests**
```bash
# backend/tests/.env.test
D_ID_API_KEY=test_key_123
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
OPENVOICE_URL=http://localhost:8001
```

**Solution 2: Use pytest-env plugin**
```ini
# pytest.ini
[pytest]
env =
    D_ID_API_KEY=test_key
    DATABASE_URL=sqlite:///:memory:
```

**Solution 3: Set in conftest.py**
```python
# backend/tests/conftest.py
import os

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    os.environ["D_ID_API_KEY"] = "test_key"
    os.environ["ENVIRONMENT"] = "test"
```

---

### 7. Docker vs Local Path Differences

#### Symptom
```
FileNotFoundError: /app/storage/test.jpg not found
```

#### Cause
Different paths in Docker vs local environment

#### Solution
```python
from pathlib import Path
import os

def get_storage_path():
    """Get storage path based on environment"""
    if os.getenv("ENVIRONMENT") == "docker":
        return Path("/app/storage")
    else:
        return Path.cwd() / "data" / "backend" / "storage"

# In test
@pytest.fixture
def storage_dir(tmp_path):
    """Use temp directory for tests (environment-agnostic)"""
    return tmp_path / "test_storage"
```

---

## GPU-Related Problems

### 8. CUDA Out of Memory

#### Symptom
```
torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB
```

#### Causes
- Too many concurrent GPU tests
- Large batch sizes
- Memory leaks from previous tests

#### Solutions

**Solution 1: Run GPU tests sequentially**
```bash
pytest backend/tests/e2e/ -n 1  # No parallel execution
```

**Solution 2: Clear GPU cache between tests**
```python
import torch
import pytest

@pytest.fixture(autouse=True)
def clear_gpu_cache():
    """Clear GPU cache before each test"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    yield
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

**Solution 3: Reduce batch size in tests**
```python
@pytest.fixture
def detector():
    return PersonDetector(batch_size=1)  # Smaller batch
```

**Solution 4: Use GPU resource manager**
```python
@pytest.mark.asyncio
async def test_with_gpu_lock():
    async with gpu_manager.acquire_yolo("test_task"):
        result = await detector.detect(image)
```

---

### 9. CUDA Not Available

#### Symptom
```
AssertionError: CUDA is not available
```

#### Causes
- Running on CPU-only machine
- CUDA drivers not installed
- PyTorch CPU version installed

#### Solutions

**Solution 1: Skip GPU tests on CPU machines**
```python
import torch
import pytest

@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA not available"
)
def test_gpu_inference():
    assert torch.cuda.is_available()
```

**Solution 2: Fallback to CPU**
```python
def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")  # Mac
    else:
        return torch.device("cpu")

# In test
@pytest.fixture
def detector():
    device = get_device()
    return PersonDetector(device=device)
```

**Solution 3: Verify CUDA installation (EC2)**
```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA version
nvcc --version

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.version.cuda)"
```

---

### 10. MPS Device Not Available (Mac)

#### Symptom
```
RuntimeError: MPS device not available
```

#### Cause
Mac without M1/M2 chip, or PyTorch version too old

#### Solution
```python
import torch
import pytest

@pytest.fixture
def device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")

# Skip MPS-specific tests
@pytest.mark.skipif(
    not torch.backends.mps.is_available(),
    reason="MPS not available"
)
def test_mps_inference():
    pass
```

---

## Dependency Issues

### 11. Version Conflicts

#### Symptom
```
ImportError: cannot import name 'WhisperModel' from 'faster_whisper'
```

#### Cause
Dependency version mismatch

#### Solutions

**Solution 1: Pin exact versions**
```txt
# backend/requirements.txt
faster-whisper==1.2.1
whisper-timestamped==1.15.9
torch==2.0.1
```

**Solution 2: Use virtual environment**
```bash
# Create isolated environment
python3.11 -m venv venv_test
source venv_test/bin/activate
pip install -r requirements.txt
pytest backend/tests/ -v
```

**Solution 3: Check installed versions**
```bash
pip list | grep -E "torch|whisper|faster"

# Output should match requirements.txt
torch==2.0.1
faster-whisper==1.2.1
whisper-timestamped==1.15.9
```

---

### 12. Missing Dependencies

#### Symptom
```
ModuleNotFoundError: No module named 'pytest_asyncio'
```

#### Solution
```bash
# Install test dependencies
pip install -r backend/requirements-dev.txt

# Or install missing package
pip install pytest-asyncio==0.21.1
```

---

## Network & Timeout Problems

### 13. External API Timeouts

#### Symptom
```
httpx.ReadTimeout: Read timeout after 30 seconds
```

#### Causes
- D-ID API slow response
- OpenVoice service not running
- Network issues

#### Solutions

**Solution 1: Increase timeout**
```python
import httpx

client = httpx.AsyncClient(timeout=120.0)  # 2 minutes
```

**Solution 2: Mock external APIs in tests**
```python
@pytest.fixture
def mock_d_id_client(monkeypatch):
    """Mock D-ID API calls"""
    class MockDIdClient:
        async def create_talk_video(self, audio_url, source_url):
            return {
                "id": "tlk_test123",
                "status": "done",
                "result_url": "https://example.com/video.mp4"
            }

    monkeypatch.setattr("services.d_id_client.DIdClient", MockDIdClient)
```

**Solution 3: Verify services are running**
```bash
# Check OpenVoice
curl http://localhost:8001/health

# Check Backend
curl http://localhost:55433/health

# If not running, start them
docker-compose up -d
```

---

### 14. Connection Refused

#### Symptom
```
ConnectionError: [Errno 111] Connection refused to http://localhost:8001
```

#### Cause
Service not running or wrong port

#### Solution
```bash
# Check if service is running
docker ps | grep openvoice

# If not running, start it
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/openvoice_native
conda activate openvoice_v2
python main.py

# Or use Docker
docker-compose up -d openvoice_native
```

---

## File System Issues

### 15. Permission Denied

#### Symptom
```
PermissionError: [Errno 13] Permission denied: '/app/storage/test.jpg'
```

#### Causes
- Docker volume permissions
- File created by root
- Read-only file system

#### Solutions

**Solution 1: Fix Docker volume permissions**
```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./data/backend/storage:/app/storage:rw  # Read-write
    user: "${UID}:${GID}"  # Run as current user
```

**Solution 2: Use tmp_path fixture (recommended for tests)**
```python
@pytest.fixture
def test_storage(tmp_path):
    """Use temporary directory for tests"""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir

def test_file_operation(test_storage):
    test_file = test_storage / "test.jpg"
    test_file.write_bytes(b"test")
    assert test_file.exists()
```

**Solution 3: Change file permissions**
```bash
# Give write permissions
chmod -R 777 data/backend/storage/

# Or change ownership
sudo chown -R $(whoami):$(whoami) data/backend/storage/
```

---

### 16. File Already Exists

#### Symptom
```
FileExistsError: [Errno 17] File exists: 'test_output.jpg'
```

#### Cause
Test not cleaning up from previous run

#### Solution
```python
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up test files before and after each test"""
    test_files = [
        Path("test_output.jpg"),
        Path("test_audio.wav")
    ]

    # Cleanup before test
    for f in test_files:
        if f.exists():
            f.unlink()

    yield

    # Cleanup after test
    for f in test_files:
        if f.exists():
            f.unlink()
```

---

## Mock & Fixture Problems

### 17. Mock Not Applied

#### Symptom
Test calls real external API instead of mock

#### Cause
Mock applied to wrong import path

#### Solution
```python
# ❌ WRONG: Mocking original module
@pytest.fixture
def mock_client(monkeypatch):
    monkeypatch.setattr("d_id_client.DIdClient", MockDIdClient)

# ✅ CORRECT: Mock where it's imported
@pytest.fixture
def mock_client(monkeypatch):
    # If imported as: from services.video_pipeline import DIdClient
    monkeypatch.setattr(
        "services.video_pipeline.DIdClient",
        MockDIdClient
    )
```

---

### 18. Fixture Cleanup Not Running

#### Symptom
Resources not released after test

#### Cause
Exception in test prevents cleanup

#### Solution
```python
@pytest.fixture
async def video_pipeline():
    pipeline = VideoPipeline()

    try:
        yield pipeline
    finally:
        # Always cleanup, even if test fails
        await pipeline.cleanup()
        await pipeline.gpu_manager._lock.release()
```

---

## Coverage Issues

### 19. Low Coverage Reported

#### Symptom
```
Coverage: 45% (expected >80%)
```

#### Causes
- Not running all tests
- Excluding too many files
- Missing test files

#### Solutions

**Solution 1: Check .coveragerc configuration**
```ini
[run]
source = backend
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[report]
show_missing = True
```

**Solution 2: Run full test suite**
```bash
# Make sure to run ALL tests
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

**Solution 3: Identify uncovered code**
```bash
# Generate HTML report to see which lines are missed
pytest backend/tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

---

### 20. Coverage Report Not Generated

#### Symptom
No `htmlcov/` directory created

#### Cause
Missing `--cov-report` flag

#### Solution
```bash
# Specify report format explicitly
pytest backend/tests/ \
    --cov=backend \
    --cov-report=html \
    --cov-report=term-missing
```

---

## CI/CD Failures

### 21. Tests Pass Locally but Fail in CI

#### Symptoms
- Local: All tests pass
- CI: Some tests fail

#### Causes
- Different Python versions
- Missing environment variables
- Timing differences
- Missing system dependencies

#### Solutions

**Solution 1: Reproduce CI environment locally with Docker**
```bash
# Use same Docker image as CI
docker run -it python:3.11-slim bash

# Inside container
pip install -r requirements.txt
pytest tests/ -v
```

**Solution 2: Pin Python version**
```yaml
# .github/workflows/ci.yml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11.9'  # Exact version
```

**Solution 3: Add debug output**
```python
def test_environment_check():
    """Debug test to check CI environment"""
    import sys
    import platform

    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Environment vars: {os.environ}")
```

---

### 22. GitHub Actions Runner Out of Disk Space

#### Symptom
```
No space left on device
```

#### Solution
```yaml
# Add cleanup step before tests
- name: Free disk space
  run: |
    sudo rm -rf /usr/local/lib/android
    sudo rm -rf /usr/share/dotnet
    docker system prune -af
```

---

## Performance Problems

### 23. Slow Test Execution

#### Symptom
Tests take >10 minutes to complete

#### Causes
- Too many slow tests
- No parallelization
- Large test data

#### Solutions

**Solution 1: Run tests in parallel**
```bash
pytest backend/tests/ -n auto  # Use all CPU cores
```

**Solution 2: Identify slow tests**
```bash
pytest backend/tests/ --durations=10

# Output:
# 15.23s test_video_generation.py::test_complete_pipeline
# 8.45s test_voice_cloning.py::test_create_profile
```

**Solution 3: Skip slow tests in development**
```bash
pytest backend/tests/ -m "not slow"
```

**Solution 4: Use smaller test data**
```python
@pytest.fixture
def small_test_image():
    """Generate 64x64 test image (faster than loading large file)"""
    import numpy as np
    return np.zeros((64, 64, 3), dtype=np.uint8)
```

---

### 24. Memory Leaks in Tests

#### Symptom
Memory usage grows with each test, eventually causing OOM

#### Cause
Not releasing resources properly

#### Solution
```python
import gc
import pytest

@pytest.fixture(autouse=True)
def cleanup_memory():
    """Force garbage collection between tests"""
    yield
    gc.collect()

# For GPU tests
@pytest.fixture(autouse=True)
def cleanup_gpu():
    yield
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
```

---

## Debug Checklist

When tests fail, check these items systematically:

### Environment
- [ ] Python version matches (3.11.x)
- [ ] All dependencies installed (`pip list`)
- [ ] Environment variables set (`.env` file)
- [ ] Services running (`docker-compose ps`)

### Code
- [ ] No syntax errors (`flake8 backend/`)
- [ ] Type checks pass (`mypy backend/`)
- [ ] Imports are correct
- [ ] No circular imports

### Test Setup
- [ ] Fixtures defined in `conftest.py`
- [ ] `@pytest.mark.asyncio` for async tests
- [ ] Proper cleanup in fixtures
- [ ] Test isolation (no shared state)

### Resources
- [ ] GPU available (if GPU test)
- [ ] Disk space sufficient (`df -h`)
- [ ] Network connectivity
- [ ] External services accessible

### Data
- [ ] Test fixtures exist
- [ ] File permissions correct
- [ ] Test data not corrupted
- [ ] Paths are correct (absolute vs relative)

---

## Quick Fixes

### Reset Test Environment

```bash
# Stop all services
docker-compose down

# Clean Docker
docker system prune -af

# Remove test artifacts
rm -rf htmlcov/ .pytest_cache/ reports/
find . -name "__pycache__" -exec rm -rf {} +

# Reinstall dependencies
pip uninstall -y -r backend/requirements.txt
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt

# Restart services
docker-compose up -d

# Run tests
pytest backend/tests/ -v
```

---

## Get Help

### Diagnostic Commands

```bash
# System info
python --version
pip list | grep pytest
docker --version
nvidia-smi  # GPU info

# Service status
docker-compose ps
curl http://localhost:8001/health
curl http://localhost:55433/health

# Test discovery
pytest backend/tests/ --collect-only

# Verbose test run
pytest backend/tests/test_specific.py -vv --tb=long --capture=no
```

### Log Analysis

```bash
# View test logs
pytest backend/tests/ -v --log-cli-level=DEBUG

# View service logs
docker logs voice_backend --tail 100 -f
docker logs openvoice_native --tail 100 -f

# Search for errors
grep -r "ERROR" backend/logs/
```

---

**Document Control**:
- **Author**: Muses (Knowledge Architect)
- **Version**: 1.0.0
- **Next Review**: 2025-12-07

---

*"Debugging is not about finding the bug; it's about understanding why the system behaves unexpectedly."*

— Muses, Knowledge Architect
