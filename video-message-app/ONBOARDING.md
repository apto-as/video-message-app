# Developer Onboarding Guide - Video Message App

**Welcome!** This guide will get you from zero to productive in **15 minutes**.

---

## Prerequisites

Before starting, ensure you have:

- [ ] macOS (11.0 or later) or Linux
- [ ] **Homebrew** installed: [brew.sh](https://brew.sh)
- [ ] **Docker Desktop** installed: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
- [ ] **Git** configured with your credentials
- [ ] **VS Code** (recommended): [code.visualstudio.com](https://code.visualstudio.com)

---

## Quick Start (15 Minutes)

### Step 1: Clone Repository (1 min)

```bash
cd ~/workspace
git clone https://github.com/apto-as/prototype-app.git
cd prototype-app/video-message-app
```

### Step 2: Install System Dependencies (3 min)

```bash
# Install FFmpeg, Python 3.11, Node.js
brew install ffmpeg python@3.11 node

# Verify installations
ffmpeg -version
python3.11 --version
node --version
npm --version
```

Expected output:
- FFmpeg: 6.x or later
- Python: 3.11.x
- Node: 20.x or later
- npm: 10.x or later

### Step 3: Backend Setup (4 min)

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Mac/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your D-ID API key
nano .env  # or: code .env
# Set: D_ID_API_KEY=your-actual-api-key-here
```

**Where to get D-ID API Key**:
1. Sign up at [studio.d-id.com](https://studio.d-id.com)
2. Go to Account Settings → API Key
3. Copy and paste into `.env`

### Step 4: Frontend Setup (2 min)

```bash
cd ../frontend

# Install dependencies
npm install

# Verify installation
npm run build  # Test build (should succeed)
```

### Step 5: Start Docker Desktop (1 min)

```bash
# Start Docker Desktop
open -a Docker

# Wait for Docker to be ready (30 seconds)
sleep 30

# Verify Docker is running
docker ps  # Should show empty list (OK)
```

### Step 6: Start Development Services (2 min)

**Terminal 1 - VOICEVOX (Docker)**:
```bash
cd ~/workspace/prototype-app/video-message-app
docker-compose up -d voicevox

# Verify VOICEVOX is running
curl http://localhost:50021/version
```

**Terminal 2 - Backend (FastAPI)**:
```bash
cd ~/workspace/prototype-app/video-message-app/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 55433
```

**Terminal 3 - Frontend (React)**:
```bash
cd ~/workspace/prototype-app/video-message-app/frontend
npm run dev
```

### Step 7: Verify Everything Works (2 min)

**Open your browser**:
```bash
open http://localhost:55434
```

**Test the application**:
1. You should see the Video Message App UI
2. Upload a test image (any photo)
3. Enter text: "こんにちは、テストです"
4. Select a voice (e.g., "ずんだもん")
5. Click "Generate Video"
6. Video should generate successfully ✅

**Check health endpoints**:
```bash
# Backend health
curl http://localhost:55433/health
# Expected: {"status": "healthy", ...}

# VOICEVOX health
curl http://localhost:50021/version
# Expected: {"version": "0.14.x"}
```

---

## First Day Checklist

### Morning (Setup)
- [ ] Completed Quick Start (Steps 1-7)
- [ ] All services running successfully
- [ ] Generated first test video

### Afternoon (Explore)
- [ ] Read [`DEVELOPER_WORKFLOW.md`](./DEVELOPER_WORKFLOW.md)
- [ ] Read [`CLAUDE.md`](./CLAUDE.md) (project overview)
- [ ] Explored codebase structure (see below)
- [ ] Made a small test change and saw hot reload work

### Evening (Optional - EC2 Testing)
- [ ] Obtained EC2 SSH key from admin
- [ ] Configured `~/.ssh/config` for easy EC2 access
- [ ] Tested deployment: `./deploy_to_ec2.sh`

---

## Codebase Structure Tour

### Backend (FastAPI)

```
backend/
├── main.py                 # FastAPI app entry point
├── app/
│   ├── routers/           # API endpoints
│   │   ├── voice.py       # Voice synthesis routes
│   │   ├── voicevox.py    # VOICEVOX integration
│   │   ├── voice_clone.py # OpenVoice integration
│   │   └── d_id.py        # D-ID video generation
│   ├── services/          # Business logic
│   │   ├── voice_storage_service.py  # File management
│   │   └── ...
│   ├── models/            # Pydantic models
│   └── utils/             # Helper functions
├── tests/                 # Unit tests
└── requirements.txt       # Python dependencies
```

**Key files to understand**:
- `main.py`: Start here, see all routers
- `app/routers/voice_clone.py`: OpenVoice voice cloning logic
- `app/routers/d_id.py`: D-ID video generation
- `app/services/voice_storage_service.py`: File storage abstraction

### Frontend (React 19)

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── VoiceSelector.tsx    # Voice selection UI
│   │   ├── ImageUploader.tsx    # Drag-drop image upload
│   │   └── VideoGenerator.tsx   # Main video generation
│   ├── pages/            # Page components
│   ├── hooks/            # Custom React hooks
│   ├── api/              # API client
│   └── App.tsx           # Root component
├── public/               # Static assets
└── package.json          # Node dependencies
```

**Key files to understand**:
- `src/App.tsx`: Main application structure
- `src/components/VideoGenerator.tsx`: Core video generation flow
- `src/api/client.ts`: Backend API calls

### OpenVoice Native Service (Python)

```
openvoice_native/
├── main.py               # FastAPI service (port 8001)
├── OpenVoiceV2/          # OpenVoice V2 library (git submodule)
├── checkpoints/          # Pre-trained models
└── requirements.txt      # Python dependencies (GPU-specific)
```

**Note**: OpenVoice runs **outside Docker** due to GPU requirements.

---

## VS Code Setup (Recommended)

### Install Extensions

Press `Cmd+Shift+X` and install:

1. **Python** (`ms-python.python`)
   - IntelliSense, linting, debugging

2. **ESLint** (`dbaeumer.vscode-eslint`)
   - JavaScript/TypeScript linting

3. **Prettier** (`esbenp.prettier-vscode`)
   - Code formatting

4. **Docker** (`ms-azuretools.vscode-docker`)
   - Docker management inside VS Code

5. **Remote - SSH** (`ms-vscode-remote.remote-ssh`)
   - Optional: For EC2 debugging

### Workspace Settings

Create `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
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

### Launch Configuration (Debugging)

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI Backend",
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

Now you can press **F5** to start debugging with breakpoints!

---

## Common Commands Cheat Sheet

### Daily Startup (3 commands)

```bash
# Terminal 1: VOICEVOX
docker-compose up -d voicevox

# Terminal 2: Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Health Checks

```bash
# Backend
curl http://localhost:55433/health

# VOICEVOX
curl http://localhost:50021/version

# OpenVoice (when running on EC2)
curl http://localhost:8001/health
```

### Testing

```bash
# Backend unit tests
cd backend
pytest tests/ -v

# Frontend linting
cd frontend
npm run lint

# Frontend build test
npm run build
```

### Git Workflow

```bash
# Daily workflow
git checkout -b feature/my-new-feature
# ... make changes ...
git add .
git commit -m "Feature: Add new feature"
git push origin feature/my-new-feature

# Test on EC2 before merging
./deploy_to_ec2.sh
```

### Docker Management

```bash
# View running containers
docker ps

# View logs
docker logs voice_backend --tail 50 -f

# Restart specific service
docker-compose restart backend

# Stop all services
docker-compose down

# Clean up (removes containers + volumes)
docker-compose down -v
```

---

## Troubleshooting First-Time Setup

### Issue: "Port already in use"

**Error**: `Address already in use: port 55433`

**Solution**:
```bash
# Find process using port
lsof -i :55433

# Kill process
kill -9 <PID>

# Or use different port
uvicorn main:app --reload --port 55435
```

### Issue: "Cannot connect to Docker daemon"

**Error**: `docker-compose up` fails

**Solution**:
```bash
# Ensure Docker Desktop is running
open -a Docker

# Wait 30 seconds for Docker to initialize
sleep 30

# Retry
docker-compose up -d voicevox
```

### Issue: "Module not found" (Python)

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Activate virtual environment first
cd backend
source venv/bin/activate  # Your terminal should show (venv) prefix

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "npm ERR! ENOENT" (Frontend)

**Error**: `npm: command not found` or `ENOENT: no such file`

**Solution**:
```bash
# Reinstall Node.js
brew install node

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: D-ID API Key Invalid

**Error**: `401 Unauthorized` when generating video

**Solution**:
1. Verify API key is correct in `backend/.env`
2. Check D-ID account has credits: [studio.d-id.com/account](https://studio.d-id.com/account)
3. Restart backend after changing `.env`:
   ```bash
   # Press Ctrl+C in backend terminal
   uvicorn main:app --reload
   ```

---

## Next Steps After Onboarding

### Week 1: Familiarization
- [ ] Read all documentation in `video-message-app/` directory
- [ ] Make a small UI change and test locally
- [ ] Deploy to EC2 at least once
- [ ] Review recent Git commits to understand changes

### Week 2: First Feature
- [ ] Pick a small feature from backlog
- [ ] Implement locally with hot reload
- [ ] Write unit tests (`pytest`)
- [ ] Test on EC2 with real OpenVoice
- [ ] Submit pull request

### Week 3: Deep Dive
- [ ] Understand OpenVoice Native Service integration
- [ ] Explore D-ID API capabilities
- [ ] Optimize a slow API endpoint
- [ ] Propose workflow improvement

---

## Resources

### Documentation
- **Project README**: [`README.md`](./README.md)
- **Developer Workflow**: [`DEVELOPER_WORKFLOW.md`](./DEVELOPER_WORKFLOW.md)
- **Claude Context**: [`CLAUDE.md`](./CLAUDE.md)
- **Architecture**: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

### External References
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **React 19 Docs**: [react.dev](https://react.dev)
- **D-ID API Docs**: [docs.d-id.com](https://docs.d-id.com)
- **OpenVoice GitHub**: [github.com/myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice)
- **VOICEVOX Engine**: [github.com/VOICEVOX/voicevox_engine](https://github.com/VOICEVOX/voicevox_engine)

### Support
- **Questions?** → Open a GitHub Issue
- **Bugs?** → Create a detailed bug report with logs
- **Workflow improvements?** → Propose in pull request

---

## Welcome Aboard! 🎉

You're now ready to start developing the Video Message App. Remember:

- **Work locally 90% of the time** (fast iteration)
- **Test on EC2 when needed** (GPU features, integration testing)
- **Use Git branches** for all features
- **Ask questions early** (don't stay stuck)

**Happy coding!**

---

**Last Updated**: 2025-11-02
**Maintained By**: Athena (Harmonious Conductor)
