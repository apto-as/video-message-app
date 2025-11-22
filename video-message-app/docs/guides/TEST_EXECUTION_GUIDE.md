# Test Execution Guide - Video Message App

**Version**: 1.0.0
**Last Updated**: 2025-11-07

---

## Quick Start

```bash
# Local development (Mac)
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
pytest backend/tests/unit/ -v

# Docker environment
docker-compose up -d
docker exec -it voice_backend pytest tests/ -v --cov=backend

# EC2 production-like (with GPU)
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd ~/video-message-app/video-message-app
pytest backend/tests/e2e/ -v --gpu
```

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Running Tests Locally](#running-tests-locally)
3. [Running Tests in Docker](#running-tests-in-docker)
4. [Running Tests on EC2](#running-tests-on-ec2)
5. [Test Filtering & Selection](#test-filtering--selection)
6. [Coverage Reports](#coverage-reports)
7. [Debugging Failed Tests](#debugging-failed-tests)
8. [Performance Profiling](#performance-profiling)
9. [CI/CD Integration](#cicd-integration)

---

## Environment Setup

### Prerequisites

**All Environments**:
- Python 3.11+
- Git
- pytest, pytest-cov, pytest-asyncio

**Local (Mac)**:
```bash
# Install Conda (if not already)
brew install --cask miniconda

# Create environment
conda create -n video-message-app python=3.11
conda activate video-message-app

# Install dependencies
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

**Docker**:
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker
open -a Docker

# Build images
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
docker-compose build
```

**EC2**:
```bash
# SSH access
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166

# Python environment
cd ~/video-message-app/video-message-app/openvoice_native
source venv_py311/bin/activate

# Verify CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# Expected: CUDA: True
```

---

### Installing Test Dependencies

```bash
# Core testing libraries
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
pip install pytest-cov==4.1.0
pip install pytest-xdist==3.5.0  # Parallel execution
pip install pytest-timeout==2.2.0  # Timeout control
pip install pytest-mock==3.12.0  # Mocking support

# Optional performance tools
pip install pytest-benchmark==4.0.0
pip install pytest-profiling==1.7.0

# Security scanning
pip install bandit==1.7.5
pip install safety==2.3.5

# Linting (pre-commit checks)
pip install flake8==6.1.0
pip install black==23.12.0
pip install mypy==1.7.1
```

**Save to `requirements-dev.txt`**:
```txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-xdist==3.5.0
pytest-timeout==2.2.0
pytest-mock==3.12.0
bandit==1.7.5
flake8==6.1.0
black==23.12.0
mypy==1.7.1
```

---

## Running Tests Locally

### Basic Execution

```bash
# Run all tests
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/unit/test_validators.py -v

# Run specific test function
pytest backend/tests/unit/test_validators.py::test_image_validator_accepts_valid_formats -v

# Run specific test class
pytest backend/tests/integration/test_video_pipeline.py::TestGPUResourceManager -v
```

### Output Verbosity

```bash
# Minimal output (default)
pytest backend/tests/

# Verbose (-v)
pytest backend/tests/ -v

# Extra verbose (-vv) - shows diffs
pytest backend/tests/ -vv

# Show print statements (-s)
pytest backend/tests/ -s

# Show local variables on failure (--showlocals)
pytest backend/tests/ --showlocals

# Short traceback (--tb=short)
pytest backend/tests/ --tb=short

# Long traceback (--tb=long)
pytest backend/tests/ --tb=long

# No traceback (--tb=no)
pytest backend/tests/ --tb=no
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest backend/tests/ -n 4

# Auto-detect CPU count
pytest backend/tests/ -n auto

# Parallel with verbose output
pytest backend/tests/ -n 4 -v

# Note: Some tests (GPU tests) must run sequentially
pytest backend/tests/e2e/ -n 1  # Sequential for E2E
```

### Test Selection by Marker

```bash
# Run only unit tests
pytest backend/tests/ -m unit

# Run only integration tests
pytest backend/tests/ -m integration

# Run only E2E tests
pytest backend/tests/ -m e2e

# Exclude slow tests
pytest backend/tests/ -m "not slow"

# Combine markers (unit OR integration)
pytest backend/tests/ -m "unit or integration"

# Exclude GPU tests (local Mac)
pytest backend/tests/ -m "not gpu"
```

### Timeout Control

```bash
# Set global timeout (30 seconds)
pytest backend/tests/ --timeout=30

# Skip timeout for specific tests
# (Add @pytest.mark.timeout(0) decorator)

# Timeout with output
pytest backend/tests/ --timeout=30 --timeout-method=thread
```

---

## Running Tests in Docker

### Start Test Environment

```bash
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME               STATUS    PORTS
# voice_backend      Up        0.0.0.0:55433->55433/tcp
# voice_frontend     Up        0.0.0.0:55434->55434/tcp
# openvoice_native   Up        0.0.0.0:8001->8001/tcp
# voicevox_engine    Up        0.0.0.0:50021->50021/tcp
```

### Execute Tests in Container

```bash
# Run all tests
docker exec -it voice_backend pytest tests/ -v

# Run with coverage
docker exec -it voice_backend pytest tests/ --cov=backend --cov-report=html

# Run specific test file
docker exec -it voice_backend pytest tests/unit/test_validators.py -v

# Interactive shell (for debugging)
docker exec -it voice_backend bash
# Inside container:
pytest tests/ -v --pdb  # Drop to debugger on failure
```

### View Coverage Report

```bash
# Generate HTML report
docker exec -it voice_backend pytest tests/ --cov=backend --cov-report=html

# Copy report to local machine
docker cp voice_backend:/app/htmlcov ./htmlcov

# Open in browser
open htmlcov/index.html
```

### Docker Test Best Practices

1. **Isolated Runs**: Stop and restart containers between test runs to ensure clean state
   ```bash
   docker-compose down
   docker-compose up -d
   docker exec -it voice_backend pytest tests/ -v
   ```

2. **Volume Mounts**: Test data persists in `./data/` directory
   ```bash
   # Clear test data
   rm -rf ./data/backend/storage/test_*
   ```

3. **Logs**: Check container logs for debugging
   ```bash
   docker logs voice_backend --tail 100 -f
   ```

---

## Running Tests on EC2

### Connect to EC2

```bash
# Start EC2 instance (if stopped)
aws ec2 start-instances --instance-ids i-0267e9e09093fd8b7 \
    --profile aws-mcp-admin-agents --region ap-northeast-1

# Wait for instance to start (30 seconds)
sleep 30

# Connect via SSH
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166
```

### Activate Environment

```bash
# Navigate to project
cd ~/video-message-app/video-message-app/openvoice_native

# Activate Python environment
source venv_py311/bin/activate

# Verify CUDA availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"

# Expected output:
# CUDA available: True
# GPU: Tesla T4
```

### Run E2E Tests with GPU

```bash
cd ~/video-message-app/video-message-app

# Run all E2E tests
pytest backend/tests/e2e/ -v --gpu

# Run specific E2E test
pytest backend/tests/e2e/test_video_generation.py::test_generate_video_with_real_models -v

# Run with GPU monitoring
nvidia-smi -l 1 &  # Monitor GPU in background
pytest backend/tests/e2e/ -v --gpu
```

### Performance Benchmarks

```bash
# Run performance tests
pytest backend/tests/performance/ -v --benchmark-only

# Save benchmark results
pytest backend/tests/performance/ \
    --benchmark-only \
    --benchmark-json=benchmark_results.json

# Compare with baseline
pytest backend/tests/performance/ \
    --benchmark-only \
    --benchmark-compare=0001 \
    --benchmark-compare-fail=mean:10%
```

### GPU Memory Monitoring

```bash
# Monitor GPU memory during tests
watch -n 1 nvidia-smi

# Run tests with memory tracking
pytest backend/tests/e2e/ -v --gpu --capture=no 2>&1 | tee test_gpu.log

# Check for out-of-memory errors
grep -i "out of memory" test_gpu.log
```

---

## Test Filtering & Selection

### By Test Name Pattern

```bash
# Run tests matching "validator"
pytest backend/tests/ -k "validator" -v

# Run tests matching "pipeline" but not "slow"
pytest backend/tests/ -k "pipeline and not slow" -v

# Run tests matching "create" or "delete"
pytest backend/tests/ -k "create or delete" -v
```

### By Test Path

```bash
# Run all tests in directory
pytest backend/tests/unit/ -v

# Run multiple directories
pytest backend/tests/unit/ backend/tests/integration/ -v

# Run specific test files
pytest backend/tests/unit/test_validators.py backend/tests/unit/test_prosody.py -v
```

### By Custom Markers

```python
# In test file (test_example.py)
import pytest

@pytest.mark.unit
def test_fast_unit():
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration():
    pass

@pytest.mark.e2e
@pytest.mark.gpu
def test_gpu_inference():
    pass
```

```bash
# Run by marker
pytest backend/tests/ -m "unit" -v
pytest backend/tests/ -m "integration and not slow" -v
pytest backend/tests/ -m "e2e and gpu" -v
```

### Last Failed Tests

```bash
# Run only tests that failed in last run
pytest backend/tests/ --lf

# Run failed first, then others
pytest backend/tests/ --ff

# Show cache info
pytest backend/tests/ --cache-show
```

### Collecting Tests (Dry Run)

```bash
# Show which tests would be run (don't execute)
pytest backend/tests/ --collect-only

# Count tests
pytest backend/tests/ --collect-only -q | tail -1

# Show test IDs (for selective execution)
pytest backend/tests/ --collect-only -q
```

---

## Coverage Reports

### Generate Coverage

```bash
# Basic coverage
pytest backend/tests/ --cov=backend

# With branch coverage
pytest backend/tests/ --cov=backend --cov-branch

# HTML report
pytest backend/tests/ --cov=backend --cov-report=html

# XML report (for CI/CD)
pytest backend/tests/ --cov=backend --cov-report=xml

# Terminal report with missing lines
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

### Coverage Reports Example

```bash
# Generate comprehensive report
pytest backend/tests/ \
    --cov=backend \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml

# Output:
# ---------- coverage: platform darwin, python 3.11.12 -----------
# Name                                 Stmts   Miss  Cover   Missing
# ------------------------------------------------------------------
# backend/services/video_pipeline.py    150      15    90%   45-48, 67-70
# backend/services/storage_manager.py   120       8    93%   102-105
# backend/security/validators.py         80       2    98%   75, 81
# ------------------------------------------------------------------
# TOTAL                                 1500    125    92%

# Open HTML report
open htmlcov/index.html
```

### Coverage Configuration

**File**: `backend/.coveragerc`

```ini
[run]
source = backend
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*
    */config.py

[report]
precision = 2
show_missing = True
skip_covered = False

exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

### Minimum Coverage Enforcement

```bash
# Fail if coverage below 80%
pytest backend/tests/ --cov=backend --cov-fail-under=80

# Fail if coverage decreased
pytest backend/tests/ --cov=backend --cov-fail-under=80 --cov-report=term-missing
```

---

## Debugging Failed Tests

### Interactive Debugging

```bash
# Drop to debugger on failure
pytest backend/tests/ --pdb

# Drop to debugger on first failure
pytest backend/tests/ --pdb -x

# Drop to debugger at start of test
pytest backend/tests/ --trace
```

**Debugger Commands**:
```python
# Inside pdb debugger
(Pdb) l         # List code
(Pdb) p var     # Print variable
(Pdb) pp var    # Pretty-print variable
(Pdb) n         # Next line
(Pdb) s         # Step into function
(Pdb) c         # Continue
(Pdb) q         # Quit
(Pdb) bt        # Backtrace
(Pdb) up        # Move up stack
(Pdb) down      # Move down stack
```

### Verbose Output

```bash
# Show all print statements
pytest backend/tests/ -s

# Show local variables on failure
pytest backend/tests/ --showlocals

# Show full traceback
pytest backend/tests/ --tb=long

# Show pytest internals (very verbose)
pytest backend/tests/ -vv --debug
```

### Capture Logs

```bash
# Show log output
pytest backend/tests/ --log-cli-level=INFO

# Save logs to file
pytest backend/tests/ --log-file=test_logs.txt --log-file-level=DEBUG

# Show warnings
pytest backend/tests/ -W all
```

### Reproduce Specific Failure

```bash
# Run single failing test
pytest backend/tests/integration/test_video_pipeline.py::TestVideoPipelineMocked::test_pipeline_no_person_detected -vv

# With debugger
pytest backend/tests/integration/test_video_pipeline.py::TestVideoPipelineMocked::test_pipeline_no_person_detected --pdb

# With full output
pytest backend/tests/integration/test_video_pipeline.py::TestVideoPipelineMocked::test_pipeline_no_person_detected -s --tb=long
```

### Common Failure Patterns

#### 1. Async Test Timeout

```bash
# Symptom: Test hangs indefinitely
# Solution: Add timeout
pytest backend/tests/integration/ --timeout=30

# Or in test file:
@pytest.mark.timeout(30)
async def test_long_running():
    pass
```

#### 2. GPU Out of Memory

```bash
# Symptom: CUDA out of memory
# Solution: Run tests sequentially
pytest backend/tests/e2e/ -n 1  # No parallel

# Or reduce batch size in test
@pytest.fixture
def pipeline():
    return VideoPipeline(batch_size=1)
```

#### 3. File Not Found

```bash
# Symptom: FileNotFoundError in tests
# Solution: Check test fixtures exist
ls -la backend/tests/fixtures/

# Or create missing fixtures
mkdir -p backend/tests/fixtures/images
cp test_image.jpg backend/tests/fixtures/images/
```

#### 4. Mock Not Applied

```bash
# Symptom: Test calls real external API
# Solution: Verify mock setup
pytest backend/tests/integration/test_video_pipeline.py -vv --capture=no

# Check mock is applied:
# Inside test, add:
assert isinstance(pipeline._d_id_client, MockDIdClient)
```

---

## Performance Profiling

### Execution Time Profiling

```bash
# Show slowest 10 tests
pytest backend/tests/ --durations=10

# Show all test durations
pytest backend/tests/ --durations=0

# Example output:
# ======================== slowest 10 durations =========================
# 15.23s call     backend/tests/e2e/test_video_generation.py::test_generate_video_with_real_models
# 8.45s call      backend/tests/integration/test_video_pipeline.py::test_pipeline_success_path
# 3.12s call      backend/tests/performance/test_concurrent_load.py::test_10_concurrent_video_generations
```

### CPU/Memory Profiling

```bash
# Install profiling tools
pip install pytest-profiling
pip install memory-profiler

# Profile CPU
pytest backend/tests/ --profile

# Profile memory
pytest backend/tests/ --memory-profile

# Generate flame graph
pytest backend/tests/ --profile --profile-svg

# Open flame graph
open prof/combined.svg
```

### Benchmarking

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
pytest backend/tests/performance/ --benchmark-only

# Save results
pytest backend/tests/performance/ --benchmark-only --benchmark-save=baseline

# Compare with baseline
pytest backend/tests/performance/ --benchmark-only --benchmark-compare=baseline

# Auto-calibrate runs
pytest backend/tests/performance/ --benchmark-only --benchmark-autosave
```

**Example Benchmark Test**:
```python
def test_video_pipeline_benchmark(benchmark, sample_image, sample_audio):
    """Benchmark video pipeline execution"""
    pipeline = VideoPipeline()

    result = benchmark(
        pipeline.execute,
        image_path=sample_image,
        audio_path=sample_audio
    )

    assert result.success == True

# Output:
# ---------------------- benchmark: 1 tests ---------------------
# Name (time in s)                   Min     Max    Mean  Median
# ---------------------------------------------------------------
# test_video_pipeline_benchmark    12.34   13.45   12.89   12.80
# ---------------------------------------------------------------
```

---

## CI/CD Integration

### GitHub Actions

**File**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
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
          pip install -r backend/requirements-dev.txt

      - name: Run unit tests
        run: |
          pytest backend/tests/unit/ -v --junit-xml=reports/unit.xml

      - name: Run integration tests
        run: |
          pytest backend/tests/integration/ -v --junit-xml=reports/integration.xml

      - name: Generate coverage report
        run: |
          pytest backend/tests/ --cov=backend --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          fail_ci_if_error: true

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: reports/*.xml
```

### Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest backend/tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
```

**Install pre-commit**:
```bash
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Appendix

### Useful Pytest Plugins

```bash
# Parallel execution
pip install pytest-xdist

# Retry flaky tests
pip install pytest-rerunfailures

# HTML report
pip install pytest-html

# BDD-style tests
pip install pytest-bdd

# Database fixtures
pip install pytest-postgresql

# Mock HTTP requests
pip install pytest-httpx
```

### Pytest Configuration

**File**: `backend/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

asyncio_mode = auto

addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --maxfail=5

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (complete user flows)
    slow: Slow-running tests (>10 seconds)
    gpu: Requires GPU (CUDA/MPS)
    security: Security-focused tests
    performance: Performance benchmark tests
    flaky: Known flaky tests (under investigation)

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## Quick Reference

### Common Commands

| Task | Command |
|------|---------|
| Run all tests | `pytest backend/tests/ -v` |
| Run with coverage | `pytest backend/tests/ --cov=backend --cov-report=html` |
| Run specific test | `pytest backend/tests/unit/test_validators.py::test_image_validator -v` |
| Run failed tests only | `pytest backend/tests/ --lf` |
| Run in parallel | `pytest backend/tests/ -n auto` |
| Show slowest tests | `pytest backend/tests/ --durations=10` |
| Debug on failure | `pytest backend/tests/ --pdb` |
| Exclude slow tests | `pytest backend/tests/ -m "not slow"` |
| Docker execution | `docker exec -it voice_backend pytest tests/ -v` |
| EC2 with GPU | `pytest backend/tests/e2e/ -v --gpu` |

---

**Document Control**:
- **Author**: Muses (Knowledge Architect)
- **Version**: 1.0.0
- **Next Review**: 2025-12-07

---

*"A well-executed test suite is the heartbeat of a healthy codebase."*

— Muses, Knowledge Architect
