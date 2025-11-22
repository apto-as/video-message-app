# Developer Workflow Guide - Video Message App

**Last Updated**: 2025-11-02
**Status**: Production Ready
**Philosophy**: Harmonious Productivity with Minimal Friction

---

## Executive Summary

This guide presents a **Hybrid Development Workflow** optimized for a single developer managing both local (Mac) and EC2 environments. The workflow balances productivity, cost-efficiency, and ease of use.

### Recommended Primary Workflow: **Scenario 4 - Local-First with Remote Testing**

**Decision Rationale**:
- 90% of development happens locally (fast iteration, no network latency)
- GPU-dependent features (OpenVoice) tested on EC2 only when needed
- Cost-effective (EC2 only running during testing/deployment)
- Minimal complexity (no constant file sync or SSH dependency)

---

## Workflow Scenarios Comparison Matrix

| Aspect | Scenario 1: Pure Local | Scenario 2: Hybrid | Scenario 3: Full Remote | Scenario 4: Local-First ✅ |
|--------|------------------------|-------------------|------------------------|---------------------------|
| **Iteration Speed** | ⚡️ Fastest | 🟡 Medium | 🟡 Medium | ⚡️ Fastest |
| **Network Dependency** | ✅ None | 🟡 Moderate | ❌ High | ✅ Minimal |
| **GPU Testing** | ❌ Not possible | ✅ Real-time | ✅ Real-time | ✅ On-demand |
| **Cost (EC2 hours)** | ✅ Zero | ❌ High (24/7) | ❌ High (24/7) | ✅ Low (on-demand) |
| **Setup Complexity** | ⚡️ Simple | 🟡 Complex (sync) | 🟡 Medium (SSH) | ⚡️ Simple |
| **File Sync Issues** | ✅ None | ❌ Potential | ✅ None | ✅ None |
| **IDE Experience** | ⚡️ Native | 🟡 Remote | 🟡 Remote | ⚡️ Native |
| **Debugging** | ⚡️ Full breakpoints | 🟡 Possible | 🟡 Possible | ⚡️ Full breakpoints |
| **Offline Work** | ✅ Possible | ❌ Not possible | ❌ Not possible | ✅ Possible |

### Legend
- ⚡️ Excellent
- ✅ Good
- 🟡 Moderate
- ❌ Poor/High Cost

---

## Recommended Workflow: Local-First with Remote Testing

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Developer Mac (Primary)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  VS Code (Native)                                │   │
│  │  - FastAPI backend (hot reload)                  │   │
│  │  - React frontend (Vite hot reload)              │   │
│  │  - VOICEVOX (Docker)                             │   │
│  │  - OpenVoice (Mocked/Stub)                       │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│                         │ Git Push (when needed)         │
│                         ▼                                │
└─────────────────────────────────────────────────────────┘
                          │
                          │
┌─────────────────────────▼─────────────────────────────┐
│                  EC2 Instance (On-Demand)              │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Production Environment                          │ │
│  │  - Full Docker stack                             │ │
│  │  - OpenVoice Native (GPU)                        │ │
│  │  - Automated deployment script                   │ │
│  └──────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

### Daily Workflow Steps

#### Phase 1: Local Development (90% of time)

```bash
# Morning startup (5 minutes)
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app

# 1. Start Docker services (VOICEVOX only)
docker-compose up -d voicevox

# 2. Start Backend with hot reload
cd backend
source venv/bin/activate  # or conda activate if using conda
uvicorn main:app --reload --host 0.0.0.0 --port 55433

# 3. Start Frontend with hot reload (new terminal)
cd frontend
npm run dev  # Vite dev server on port 55434

# 4. Access local application
open http://localhost:55434
```

**Local Development Features**:
- ✅ FastAPI auto-reload on code changes
- ✅ React hot module replacement (HMR)
- ✅ VOICEVOX TTS works locally (CPU mode)
- ⚠️ OpenVoice mocked (stub responses for fast iteration)
- ✅ Full breakpoint debugging in VS Code
- ✅ No network latency

#### Phase 2: Remote Testing (10% of time - when needed)

```bash
# When to test on EC2:
# - Before deploying to production
# - Testing OpenVoice voice cloning (GPU required)
# - Integration testing with real D-ID API
# - Performance testing under load

# 1. Commit your changes
git add .
git commit -m "Feature: Add new voice selection UI"
git push origin master

# 2. Deploy to EC2 (automated)
./deploy_to_ec2.sh

# 3. Test on EC2
open https://3.115.141.166

# 4. Check logs if needed
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd /home/ec2-user/video-message-app/video-message-app
docker logs voice_backend --tail 50
tail -f openvoice_native/openvoice.log
```

---

## Setup Instructions

### Initial Setup (Once per machine)

#### 1. Mac Development Environment

```bash
# Clone repository
cd ~/workspace/github.com/apto-as
git clone <your-repo-url> prototype-app
cd prototype-app/video-message-app

# Install system dependencies
brew install ffmpeg python@3.11 node

# Backend setup
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Docker setup
brew install --cask docker
open -a Docker  # Start Docker Desktop

# Create environment files
cp backend/.env.example backend/.env
# Edit backend/.env and add your D_ID_API_KEY
```

#### 2. VS Code Configuration (Recommended Extensions)

```bash
# Install VS Code extensions
code --install-extension ms-python.python
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension ms-azuretools.vscode-docker
code --install-extension ms-vscode-remote.remote-ssh  # For EC2 access
```

**VS Code Settings** (`.vscode/settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### 3. Mock OpenVoice for Local Development

Create `backend/mocks/openvoice_mock.py`:

```python
"""
Mock OpenVoice service for local development without GPU.
Provides stub responses to enable fast iteration on UI/backend logic.
"""
import base64
import json
from pathlib import Path

class OpenVoiceMock:
    """Stub OpenVoice responses for local testing."""

    @staticmethod
    async def synthesize(text: str, profile_id: str = None) -> dict:
        """Return a dummy audio response."""
        # Return a minimal valid audio data (silence)
        silence_audio = b'\x00' * 1024  # 1KB of silence
        return {
            "status": "success",
            "audio_base64": base64.b64encode(silence_audio).decode(),
            "message": "Mock synthesis (local dev)",
            "profile_id": profile_id or "mock_profile"
        }

    @staticmethod
    async def health_check() -> dict:
        """Mock health check."""
        return {
            "status": "healthy",
            "mode": "mock",
            "message": "OpenVoice mocked for local development"
        }
```

**Enable mock in `backend/.env`:**

```env
# Local development
OPENVOICE_SERVICE_URL=http://localhost:8001
OPENVOICE_MOCK_MODE=true  # Enable mock for local dev

# Production (EC2) - disable mock
# OPENVOICE_MOCK_MODE=false
```

---

## Development Checklists

### Daily Startup Checklist

- [ ] Docker Desktop running
- [ ] `docker-compose up -d voicevox` (starts VOICEVOX)
- [ ] Backend running with hot reload (`uvicorn main:app --reload`)
- [ ] Frontend running with Vite dev server (`npm run dev`)
- [ ] Browser open to `http://localhost:55434`

**Estimated Time**: 2 minutes

### Pre-EC2 Testing Checklist

- [ ] All local tests passing (`pytest backend/tests`)
- [ ] No console errors in browser DevTools
- [ ] Linting checks pass (`flake8 backend`, `npm run lint`)
- [ ] Git working tree clean (committed all changes)
- [ ] `.env.docker` has correct `D_ID_API_KEY`

**Estimated Time**: 5 minutes

### EC2 Deployment Checklist

- [ ] Pre-testing checklist completed
- [ ] Ran `./deploy_to_ec2.sh` successfully
- [ ] Verified health endpoints:
  - [ ] `https://3.115.141.166/api/health` (Backend)
  - [ ] `https://3.115.141.166/` (Frontend)
- [ ] Tested OpenVoice voice cloning end-to-end
- [ ] Checked EC2 logs for errors

**Estimated Time**: 10-15 minutes

---

## Tooling Recommendations

### VS Code Remote SSH (Optional - for deep EC2 debugging)

When you need to debug directly on EC2 (rare cases):

```bash
# 1. Configure SSH in VS Code
# Press Cmd+Shift+P → "Remote-SSH: Connect to Host"
# Add: ec2-user@3.115.141.166

# 2. VS Code will connect via SSH
# 3. Open folder: /home/ec2-user/video-message-app/video-message-app
# 4. Install Python extension on remote
# 5. Debug as if local
```

**When to use**:
- OpenVoice Native Service debugging (GPU-specific issues)
- Performance profiling on EC2
- Docker networking issues

**When NOT to use**:
- Regular feature development (use local)
- UI changes (use local with hot reload)

### Docker Desktop for Mac

**Configuration**:
- Memory: 4GB (sufficient for VOICEVOX)
- CPUs: 2 cores
- Disk: 20GB

**Why NOT run full stack locally**:
- OpenVoice requires CUDA/GPU (Mac MPS not supported)
- Running full Docker stack uses unnecessary resources
- Hot reload slower inside Docker

### Git Workflow

```bash
# Feature development
git checkout -b feature/new-voice-ui
# ... make changes locally ...
git add .
git commit -m "Feature: Add new voice selection UI"
git push origin feature/new-voice-ui

# Test on EC2 (checkout feature branch on EC2)
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd /home/ec2-user/video-message-app/video-message-app
git fetch
git checkout feature/new-voice-ui
./deploy_local.sh  # Restart services

# Merge to master after testing
git checkout master
git merge feature/new-voice-ui
git push origin master
```

---

## Debugging Strategies

### Local Debugging (VS Code Breakpoints)

**Backend (FastAPI)**:

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "55433"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

Press F5 to start debugging. Set breakpoints in Python code.

**Frontend (React)**:

Browser DevTools:
- Sources tab → Set breakpoints in `.tsx` files
- React DevTools extension for component debugging

### Remote Debugging (EC2)

**View Real-Time Logs**:

```bash
# Option 1: SSH + tail
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
tail -f /home/ec2-user/video-message-app/video-message-app/openvoice_native/openvoice.log

# Option 2: Docker logs
docker logs voice_backend --tail 100 -f

# Option 3: System logs
journalctl -u docker -f
```

**Debug Specific Request**:

```bash
# Enable DEBUG logging
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd /home/ec2-user/video-message-app/video-message-app
docker-compose exec backend bash
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

---

## Performance Optimization Tips

### Local Development

1. **Skip unnecessary Docker containers**
   - Only run VOICEVOX locally (lightweight)
   - Mock OpenVoice for UI development

2. **Use Vite's HMR efficiently**
   - Keep browser DevTools open (Network tab) to see fast reloads
   - Use React Fast Refresh (auto-enabled in Vite)

3. **Backend hot reload optimization**
   - Use `--reload-dir backend/app` to watch only app code
   - Exclude `tests/`, `data/` directories from watch

### EC2 Testing

1. **Minimize EC2 runtime**
   - Batch testing sessions (test multiple features in one session)
   - Stop EC2 instance when not actively testing (save costs)

2. **Use EC2 instance wisely**
   - Keep deployment script idempotent (can run multiple times)
   - Cache Docker images to speed up restarts

---

## Cost Optimization

### EC2 Usage Recommendations

**Development Phase**:
- Start EC2 instance: 1-2 hours before testing
- Test all features in batch
- Stop instance after testing

**Production Phase**:
- Keep EC2 running 24/7
- Use t3.medium or better for stability

**Estimated Monthly Costs**:
- Development (4 hours/day): ~$20/month
- Production (24/7): ~$30-50/month

### Save Money Tips

1. **Use AWS Budgets**
   - Set alert at $50/month
   - Auto-stop EC2 if exceeds budget

2. **Schedule EC2 start/stop**
   ```bash
   # Add to crontab (EC2)
   # Stop at 8 PM daily
   0 20 * * * sudo shutdown -h now
   ```

3. **Use Reserved Instances** (if running 24/7 for 1 year)
   - Save up to 40% vs On-Demand

---

## Troubleshooting Guide

### Common Issues

#### Issue 1: "Cannot connect to Docker daemon"

**Symptom**: `docker-compose up` fails with connection error

**Solution**:
```bash
open -a Docker
sleep 30  # Wait for Docker to start
docker-compose up -d
```

#### Issue 2: "Port 55433 already in use"

**Symptom**: Backend fails to start

**Solution**:
```bash
# Find process using port
lsof -i :55433
# Kill process
kill -9 <PID>
# Or use different port
uvicorn main:app --reload --port 55435
```

#### Issue 3: "OpenVoice health check failed" on EC2

**Symptom**: Deployment script reports unhealthy OpenVoice

**Solution**:
```bash
# SSH to EC2
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native

# Check logs
tail -f openvoice.log

# Common fixes:
# 1. Missing dependencies
source venv/bin/activate
pip install -r requirements.txt

# 2. CUDA out of memory
# Restart service (clears GPU memory)
pkill -f "python main.py"
nohup uvicorn main:app --host 0.0.0.0 --port 8001 > openvoice.log 2>&1 &
```

#### Issue 4: Frontend not updating after code changes

**Symptom**: Browser shows old code

**Solution**:
```bash
# 1. Clear Vite cache
cd frontend
rm -rf node_modules/.vite

# 2. Hard reload browser
# Press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

# 3. Restart dev server
npm run dev
```

---

## Workflow Upgrade Paths

### Future Optimization: CI/CD Pipeline

When the project matures, consider:

```yaml
# .github/workflows/deploy-ec2.yml
name: Deploy to EC2

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to EC2
        env:
          SSH_KEY: ${{ secrets.EC2_SSH_KEY }}
        run: ./deploy_to_ec2.sh
```

**Benefits**:
- Push to master → Auto-deploy to EC2
- No manual deployment step
- Automated testing before deploy

### Future Optimization: Docker Dev Containers

For team collaboration (multiple developers):

```json
// .devcontainer/devcontainer.json
{
  "name": "Video Message App",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "backend",
  "workspaceFolder": "/app",
  "extensions": [
    "ms-python.python",
    "dbaeumer.vscode-eslint"
  ]
}
```

**Benefits**:
- Consistent environment across team
- No "works on my machine" issues
- VS Code Remote Containers experience

---

## Summary: Why Local-First Workflow Wins

| Criteria | Score | Rationale |
|----------|-------|-----------|
| **Productivity** | ⭐⭐⭐⭐⭐ | Fast hot reload, instant feedback |
| **Cost** | ⭐⭐⭐⭐⭐ | EC2 only when needed (~$20/month) |
| **Simplicity** | ⭐⭐⭐⭐⭐ | No file sync, no SSH dependency |
| **Debugging** | ⭐⭐⭐⭐⭐ | Full breakpoint debugging locally |
| **Reliability** | ⭐⭐⭐⭐⭐ | No network issues, offline capable |
| **GPU Testing** | ⭐⭐⭐⭐☆ | On-demand (not real-time) |

**Overall**: ⭐⭐⭐⭐⭐ (5/5)

---

**Last Updated**: 2025-11-02
**Maintained By**: Athena (Harmonious Conductor)
**Feedback**: Contact developer for workflow improvements
