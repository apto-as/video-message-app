# CI/CD Integration Guide - Video Message App

**Version**: 1.0.0
**Last Updated**: 2025-11-07

---

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions Setup](#github-actions-setup)
3. [Test Automation](#test-automation)
4. [Coverage Reporting](#coverage-reporting)
5. [Security Scanning](#security-scanning)
6. [Docker Build & Push](#docker-build--push)
7. [Deployment Pipeline](#deployment-pipeline)
8. [Notifications](#notifications)
9. [Performance Monitoring](#performance-monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### CI/CD Pipeline Architecture

```
┌──────────────┐
│  Git Push    │
│  (main/dev)  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│     GitHub Actions Workflows         │
├──────────────────────────────────────┤
│  1. Lint & Format Check              │
│  2. Unit Tests (parallel)            │
│  3. Integration Tests                │
│  4. Security Scan (Bandit)           │
│  5. Coverage Report (Codecov)        │
│  6. Docker Build                     │
│  7. E2E Tests (EC2 self-hosted)      │
│  8. Deploy (if main branch)          │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  Slack       │
│  Notification│
└──────────────┘
```

### Pipeline Stages

| Stage | Duration | Runs On | Trigger |
|-------|----------|---------|---------|
| **Lint** | ~30s | ubuntu-latest | Every push |
| **Unit Tests** | ~2 min | ubuntu-latest | Every push |
| **Integration Tests** | ~5 min | ubuntu-latest | PR + main |
| **Security Scan** | ~1 min | ubuntu-latest | PR + main |
| **E2E Tests** | ~15 min | EC2 (self-hosted) | PR + main |
| **Deploy** | ~3 min | EC2 (self-hosted) | main only |

---

## GitHub Actions Setup

### Directory Structure

```
.github/
├── workflows/
│   ├── ci.yml                  # Main CI pipeline
│   ├── deploy.yml              # Deployment workflow
│   ├── nightly.yml             # Nightly comprehensive tests
│   └── security-scan.yml       # Weekly security audit
└── actions/
    ├── setup-python/           # Reusable Python setup
    └── upload-coverage/        # Reusable coverage upload
```

### Main CI Workflow

**File**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install linting tools
        run: |
          pip install flake8 black mypy

      - name: Run Black (format check)
        run: black --check backend/

      - name: Run Flake8 (linting)
        run: flake8 backend/ --max-line-length=100 --statistics

      - name: Run Mypy (type check)
        run: mypy backend/ --ignore-missing-imports --strict

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint

    strategy:
      matrix:
        test-group: [validators, services, utils]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt

      - name: Run unit tests
        run: |
          pytest backend/tests/unit/ \
            -k "${{ matrix.test-group }}" \
            -v \
            --junit-xml=reports/unit-${{ matrix.test-group }}.xml \
            --cov=backend \
            --cov-report=xml \
            --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: unittests-${{ matrix.test-group }}
          name: codecov-${{ matrix.test-group }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results-unit-${{ matrix.test-group }}
          path: reports/unit-${{ matrix.test-group }}.xml

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
        run: |
          pytest backend/tests/integration/ \
            -v \
            --junit-xml=reports/integration.xml \
            --cov=backend \
            --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: integration
          name: codecov-integration

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results-integration
          path: reports/integration.xml

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: lint

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Bandit
        run: pip install bandit[toml]

      - name: Run Bandit security scan
        run: |
          bandit -r backend/ \
            -f json \
            -o reports/security.json \
            --severity-level medium

      - name: Upload security report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: reports/security.json

      - name: Check for critical vulnerabilities
        run: |
          python -c "
          import json
          with open('reports/security.json') as f:
              data = json.load(f)
          critical = [r for r in data['results'] if r['issue_severity'] == 'HIGH']
          if critical:
              print(f'Found {len(critical)} critical vulnerabilities')
              exit(1)
          "

  e2e-tests:
    name: E2E Tests (EC2 with GPU)
    runs-on: self-hosted  # EC2 self-hosted runner
    needs: [integration-tests, security-scan]
    if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        run: |
          source ~/video-message-app/video-message-app/openvoice_native/venv_py311/bin/activate

      - name: Verify CUDA
        run: |
          python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
          nvidia-smi

      - name: Start services
        run: |
          cd ~/video-message-app/video-message-app
          docker-compose up -d
          sleep 10  # Wait for services to start

      - name: Run E2E tests
        run: |
          pytest backend/tests/e2e/ \
            -v \
            --gpu \
            --junit-xml=reports/e2e.xml \
            --timeout=300

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results-e2e
          path: reports/e2e.xml

      - name: Stop services
        if: always()
        run: |
          cd ~/video-message-app/video-message-app
          docker-compose down

  docker-build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        if: github.ref == 'refs/heads/main'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/video-message-backend:latest
            ${{ secrets.DOCKER_USERNAME }}/video-message-backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/video-message-frontend:latest
            ${{ secrets.DOCKER_USERNAME }}/video-message-frontend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  publish-results:
    name: Publish Test Results
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    if: always()

    steps:
      - name: Download all test results
        uses: actions/download-artifact@v3
        with:
          path: reports/

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: reports/**/*.xml
          check_name: Test Results
          comment_title: Test Results Summary

  notify:
    name: Slack Notification
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    if: always()

    steps:
      - name: Send Slack notification
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: |
            CI Pipeline ${{ job.status }}
            Branch: ${{ github.ref }}
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Test Automation

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
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=10240']  # 10MB limit

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.11
        args: ['--line-length=100']

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        args: ['--ignore-missing-imports', '--strict']
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest-quick
        name: pytest-quick
        entry: pytest backend/tests/unit/ -v --exitfirst --maxfail=3
        language: system
        pass_filenames: false
        always_run: false
        stages: [commit]

      - id: pytest-full
        name: pytest-full
        entry: pytest backend/tests/ -m "not e2e and not slow" -v
        language: system
        pass_filenames: false
        always_run: false
        stages: [push]
```

**Installation**:
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push

# Run manually
pre-commit run --all-files
```

---

### Makefile for Local Testing

**File**: `Makefile`

```makefile
.PHONY: help install lint test test-unit test-integration test-e2e coverage clean

help:
	@echo "Available commands:"
	@echo "  make install          Install dependencies"
	@echo "  make lint             Run linters"
	@echo "  make test             Run all tests (except E2E)"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-e2e         Run E2E tests (requires EC2)"
	@echo "  make coverage         Generate coverage report"
	@echo "  make clean            Clean temporary files"

install:
	pip install -r backend/requirements.txt
	pip install -r backend/requirements-dev.txt
	pre-commit install

lint:
	black --check backend/
	flake8 backend/ --max-line-length=100
	mypy backend/ --ignore-missing-imports --strict

test:
	pytest backend/tests/ -m "not e2e and not slow" -v

test-unit:
	pytest backend/tests/unit/ -v --durations=10

test-integration:
	pytest backend/tests/integration/ -v

test-e2e:
	pytest backend/tests/e2e/ -v --gpu

coverage:
	pytest backend/tests/ \
		--cov=backend \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml
	@echo "Coverage report: htmlcov/index.html"

clean:
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf reports/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
```

**Usage**:
```bash
# Install dependencies
make install

# Run tests locally (before push)
make test

# Check coverage
make coverage
open htmlcov/index.html
```

---

## Coverage Reporting

### Codecov Integration

**File**: `.codecov.yml`

```yaml
codecov:
  require_ci_to_pass: yes
  notify:
    wait_for_ci: yes

coverage:
  precision: 2
  round: down
  range: "70...100"

  status:
    project:
      default:
        target: 80%
        threshold: 2%
        if_not_found: success

    patch:
      default:
        target: 70%
        threshold: 5%

  changes:
    default:
      if_not_found: success

comment:
  layout: "header, diff, files, footer"
  behavior: default
  require_changes: true
  require_base: yes
  require_head: yes

ignore:
  - "backend/tests/"
  - "backend/migrations/"
  - "backend/config.py"
```

### GitHub Actions Coverage Upload

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    flags: unittests
    name: codecov-umbrella
    fail_ci_if_error: true
    verbose: true
```

### Coverage Badge

Add to `README.md`:

```markdown
[![codecov](https://codecov.io/gh/username/video-message-app/branch/main/graph/badge.svg)](https://codecov.io/gh/username/video-message-app)
```

---

## Security Scanning

### Bandit Configuration

**File**: `pyproject.toml`

```toml
[tool.bandit]
exclude_dirs = [
    "/tests/",
    "/migrations/",
    "/.venv/"
]

skips = [
    "B101",  # assert_used (allowed in tests)
    "B601"   # paramiko_calls (if using paramiko)
]

[tool.bandit.assert_used]
skips = ["*/test_*.py"]
```

### Dependency Scanning

**File**: `.github/workflows/security-scan.yml`

```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  dependency-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt --desc

      - name: Run Safety check
        run: |
          pip install safety
          safety check -r backend/requirements.txt --json

  secret-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for secret scanning

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Docker Build & Push

### Multi-Stage Build

**File**: `backend/Dockerfile`

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . /app

# Make sure scripts are on PATH
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:55433/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "55433"]
```

### Docker Compose for CI

**File**: `docker-compose.ci.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=test
      - DATABASE_URL=postgresql://test:test@postgres:5432/test
    depends_on:
      - postgres
    ports:
      - "55433:55433"

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5432:5432"
```

---

## Deployment Pipeline

### Deployment Workflow

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to EC2

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Start EC2 instance
        run: |
          aws ec2 start-instances \
            --instance-ids i-0267e9e09093fd8b7 \
            --region ap-northeast-1
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Wait for instance to start
        run: sleep 30

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: 3.115.141.166
          username: ec2-user
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ~/video-message-app/video-message-app
            git pull origin main
            docker-compose down
            docker-compose pull
            docker-compose up -d
            docker-compose ps

      - name: Health check
        run: |
          sleep 10
          curl --fail http://3.115.141.166:55433/health

      - name: Send notification
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Notifications

### Slack Webhook Setup

1. Create Slack App: https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add webhook URL to GitHub Secrets: `SLACK_WEBHOOK`

### Custom Notification Template

```yaml
- name: Send Slack notification
  uses: 8398a7/action-slack@v3
  with:
    status: custom
    fields: repo,message,commit,author,action,eventName,ref,workflow
    custom_payload: |
      {
        "attachments": [{
          "color": "${{ job.status }}" == "success" ? "good" : "danger",
          "title": "CI Pipeline ${{ job.status }}",
          "fields": [
            {
              "title": "Branch",
              "value": "${{ github.ref }}",
              "short": true
            },
            {
              "title": "Author",
              "value": "${{ github.actor }}",
              "short": true
            },
            {
              "title": "Test Results",
              "value": "Unit: ${{ needs.unit-tests.result }}\nIntegration: ${{ needs.integration-tests.result }}\nE2E: ${{ needs.e2e-tests.result }}",
              "short": false
            }
          ]
        }]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Performance Monitoring

### Benchmark Tracking

**File**: `.github/workflows/benchmark.yml`

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  benchmark:
    runs-on: self-hosted  # EC2 with GPU

    steps:
      - uses: actions/checkout@v4

      - name: Run benchmarks
        run: |
          pytest backend/tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark.json

      - name: Store benchmark results
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          comment-on-alert: true
          alert-threshold: '150%'
```

---

## Troubleshooting

### Common CI/CD Issues

#### 1. Tests Pass Locally but Fail in CI

**Symptom**: Tests succeed on local machine but fail in GitHub Actions

**Possible Causes**:
- Different Python versions
- Missing environment variables
- Different dependency versions
- Timing issues (race conditions)

**Solution**:
```yaml
# Pin Python version
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11.9'  # Exact version

# Use dependency cache
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

---

#### 2. Flaky E2E Tests

**Symptom**: E2E tests fail intermittently

**Solution**:
```yaml
# Retry flaky tests
- name: Run E2E tests with retries
  run: |
    pytest backend/tests/e2e/ \
      -v \
      --reruns 2 \
      --reruns-delay 5
```

---

#### 3. Docker Build Timeout

**Symptom**: Docker build exceeds time limit

**Solution**:
```yaml
# Use BuildKit and layer caching
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    context: .
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

#### 4. EC2 Self-Hosted Runner Connection Issues

**Symptom**: Self-hosted runner offline or not responding

**Solution**:
```bash
# On EC2, restart runner
cd ~/actions-runner
sudo ./svc.sh stop
sudo ./svc.sh start

# Check runner logs
sudo journalctl -u actions.runner.* -f
```

---

## Appendix

### Required GitHub Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DOCKER_USERNAME` | Docker Hub username | `myusername` |
| `DOCKER_PASSWORD` | Docker Hub password | `dckr_pat_...` |
| `CODECOV_TOKEN` | Codecov upload token | `a1b2c3d4...` |
| `SLACK_WEBHOOK` | Slack webhook URL | `https://hooks.slack.com/...` |
| `AWS_ACCESS_KEY_ID` | AWS IAM access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | `abc123...` |
| `SSH_PRIVATE_KEY` | EC2 SSH private key | `-----BEGIN RSA PRIVATE KEY-----` |

### Self-Hosted Runner Setup (EC2)

```bash
# On EC2 instance
cd ~
mkdir actions-runner && cd actions-runner

# Download runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure
./config.sh --url https://github.com/username/video-message-app --token <TOKEN>

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

---

**Document Control**:
- **Author**: Muses (Knowledge Architect)
- **Version**: 1.0.0
- **Next Review**: 2025-12-07

---

*"Continuous integration is not just about automation; it's about building confidence in every commit."*

— Muses, Knowledge Architect
