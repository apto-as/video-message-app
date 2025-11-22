# Remote Development Quick Start Guide

**For**: Mac (local) + EC2 g4dn.xlarge (remote GPU)
**Last Updated**: 2025-11-02

---

## Prerequisites

### On Mac
- ✅ VS Code with Remote-SSH extension
- ✅ Docker Desktop
- ✅ Conda (Miniconda or Anaconda)
- ✅ SSH access to EC2 (key file: `~/.ssh/your-key.pem`)

### On EC2 (Ubuntu 22.04)
- ✅ Docker + NVIDIA Docker runtime
- ✅ NVIDIA Driver (version 535+)
- ✅ Git

---

## Initial Setup (One-Time)

### Step 1: Configure SSH (Mac)

```bash
# Edit SSH config
nano ~/.ssh/config
```

Add the following:

```bash
Host ec2-video-app
    HostName 3.115.141.166
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/your-key.pem

    # Performance optimization
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h:%p
    ControlPersist 10m
    ServerAliveInterval 60
    ServerAliveCountMax 10
    Compression yes

    # Port forwarding
    LocalForward 55433 localhost:55433
    LocalForward 55441 localhost:55441
    LocalForward 50021 localhost:50021
```

```bash
# Create socket directory
mkdir -p ~/.ssh/sockets

# Set correct permissions
chmod 600 ~/.ssh/your-key.pem
```

### Step 2: Setup OpenVoice (Mac)

```bash
# Create Conda environment
conda create -n openvoice_v2 python=3.11 -y
conda activate openvoice_v2

# Install dependencies
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/openvoice_native
pip install -r requirements.txt
```

### Step 3: Install VS Code Extensions (Mac)

```bash
# Install Remote-SSH extension
code --install-extension ms-vscode-remote.remote-ssh

# Test connection
ssh ec2-video-app
```

If successful, you should see:

```
Welcome to Ubuntu 22.04.3 LTS
Last login: ...
ubuntu@ip-xxx-xxx-xxx-xxx:~$
```

---

## Daily Workflow

### Option A: Automated Start (Recommended)

```bash
# Start all services automatically
./scripts/dev_start.sh
```

This script will:
1. ✅ Start OpenVoice on Mac (port 8001)
2. ✅ Start Docker services on EC2 (via SSH)
3. ✅ Setup port forwarding
4. ✅ Run health checks

**Expected output**:
```
🚀 Starting Video Message App Development Environment
==================================================
✅ Docker installed
✅ Conda installed
✅ EC2 connection OK
✅ openvoice_v2 environment found
✅ OpenVoice started in new terminal window
✅ OpenVoice is healthy
✅ Docker services started on EC2
✅ Port forwarding established
✅ Backend is healthy
✅ VOICEVOX is healthy

🎉 Development environment ready!
==================================================

Services:
  - OpenVoice Native:  http://localhost:8001
  - Backend API:       http://localhost:55433
  - VOICEVOX:          http://localhost:50021
  - Frontend:          http://localhost:55434

Next steps:
  1. Open VS Code: code .
  2. Connect to EC2: Cmd+Shift+P → 'Remote-SSH: Connect to Host' → ec2-video-app
  3. Start coding! Changes will hot-reload automatically.
```

### Option B: Manual Start

#### Terminal 1: OpenVoice (Mac)
```bash
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/openvoice_native
conda activate openvoice_v2
python main.py
```

You should see:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

#### Terminal 2: Connect VS Code Remote

1. Open VS Code
2. Press `Cmd+Shift+P`
3. Type: "Remote-SSH: Connect to Host"
4. Select: `ec2-video-app`
5. Wait for connection (~5s)

#### Terminal 3 (VS Code Remote Terminal on EC2)
```bash
# Navigate to project
cd /home/ubuntu/video-message-app

# Start Docker services
docker-compose -f docker-compose.dev.yml up -d

# Verify services
docker ps

# Expected output:
# CONTAINER ID   IMAGE                                           STATUS
# abc123...      video-message-app_backend                       Up 10 seconds
# def456...      voicevox/voicevox_engine:cpu-ubuntu20.04...     Up 15 seconds
# ghi789...      video-message-app_frontend                      Up 8 seconds
```

---

## Development

### Edit Code

**In VS Code (connected to EC2)**:

1. Open file: `backend/main.py`
2. Make changes
3. Save (Cmd+S)
4. Watch terminal: FastAPI automatically reloads (~1-2s)

```
INFO:     Watching for file changes...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:55433
```

### Test API

**On Mac (local browser)**:

```bash
# Health check
curl http://localhost:55433/health | jq

# Test voice synthesis
curl -X POST http://localhost:55433/api/voices/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは", "speaker_id": 1}'

# Open frontend
open http://localhost:55434
```

### Debug with Breakpoints

1. Set breakpoint in VS Code (click left margin)
2. Press F5 (Start Debugging)
3. VS Code automatically attaches to `debugpy` (port 5678)
4. Trigger API call (curl or frontend)
5. Breakpoint hits → inspect variables, step through code

---

## Sync Code to EC2

### Automatic Sync (Watch Mode)

```bash
# Sync on file changes (runs in foreground)
./scripts/sync_to_ec2.sh --watch
```

This will:
- Watch local files for changes
- Automatically rsync to EC2 when files change
- Exclude `node_modules`, `__pycache__`, etc.

### Manual Sync

```bash
# One-time sync
./scripts/sync_to_ec2.sh
```

---

## Stop Services

```bash
# Stop all services
./scripts/dev_stop.sh
```

Or manually:

```bash
# Stop Docker on EC2
ssh ec2-video-app
cd /home/ubuntu/video-message-app
docker-compose -f docker-compose.dev.yml down

# Stop OpenVoice (Mac)
# Find terminal window running OpenVoice, press Ctrl+C

# Kill port forwarding
pkill -f "ssh -f -N -L 55433"
```

---

## View Logs

### Backend Logs (EC2)
```bash
# Real-time logs
ssh ec2-video-app
docker logs voice_backend_dev -f --tail 100

# Search for errors
docker logs voice_backend_dev 2>&1 | grep ERROR

# Export logs
docker logs voice_backend_dev > backend_logs.txt
scp ec2-video-app:~/backend_logs.txt ~/Downloads/
```

### OpenVoice Logs (Mac)
Check the terminal window where OpenVoice is running.

### All Services (EC2)
```bash
ssh ec2-video-app
docker-compose -f docker-compose.dev.yml logs -f
```

---

## Troubleshooting

### Issue 1: "Cannot connect to EC2"

**Solution**:
```bash
# Test SSH connection
ssh ec2-video-app

# If fails, check:
# 1. Is EC2 instance running?
aws ec2 describe-instances --instance-ids i-xxxxxxxxx --query 'Reservations[0].Instances[0].State.Name'

# 2. Is SSH key correct?
ls -la ~/.ssh/your-key.pem
chmod 600 ~/.ssh/your-key.pem

# 3. Is Security Group allowing port 22?
aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
```

### Issue 2: "Port 8001 already in use" (OpenVoice)

**Solution**:
```bash
# Find process using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>

# Or kill by name
pkill -f "python main.py"
```

### Issue 3: "Connection refused: http://host.docker.internal:8001"

**Root Cause**: OpenVoice not running on Mac, or Docker can't access host.

**Solution**:
```bash
# 1. Verify OpenVoice is running on Mac
curl http://localhost:8001/health

# 2. Test from EC2 Docker
ssh ec2-video-app
docker exec voice_backend_dev curl http://host.docker.internal:8001/health

# 3. Check extra_hosts in docker-compose.yml
docker inspect voice_backend_dev | jq '.[0].HostConfig.ExtraHosts'

# Should show: ["host.docker.internal:host-gateway"]
```

### Issue 4: "Hot reload not working"

**Solution**:
```bash
# 1. Verify volume mount
ssh ec2-video-app
docker inspect voice_backend_dev | jq '.[0].Mounts'

# Should show bind mount: /home/ubuntu/video-message-app/backend -> /app

# 2. Check uvicorn --reload flag
docker exec voice_backend_dev ps aux | grep uvicorn

# Should show: --reload --reload-dir /app

# 3. Restart container
docker-compose -f docker-compose.dev.yml restart backend
```

### Issue 5: "Out of memory (GPU)"

**Solution**:
```bash
# Check GPU memory
ssh ec2-video-app
nvidia-smi

# Clear CUDA cache
docker exec image_service_gpu python -c "import torch; torch.cuda.empty_cache()"

# Reduce batch size or stream count in code
```

---

## Performance Tips

### 1. Use SSH Multiplexing
Already configured in `~/.ssh/config` (ControlMaster).

**Benefit**: 20x faster SSH commands (2s → 0.1s)

### 2. Use rsync for Large Files
```bash
# Instead of scp
scp large_file.zip ec2-video-app:~/  # Slow

# Use rsync (incremental, compressed)
rsync -avz large_file.zip ec2-video-app:~/  # Fast
```

### 3. Exclude Large Directories from File Watcher
VS Code settings already configured (`.vscode/settings.json`):
- `node_modules`
- `data/`
- `__pycache__`

### 4. Use Docker Layer Caching
Dockerfiles already optimized with `--mount=type=cache`.

---

## Production Deployment

When ready to deploy:

```bash
# SSH to EC2
ssh ec2-video-app

# Pull latest code
cd /home/ubuntu/video-message-app
git pull origin master

# Rebuild production images
docker-compose -f docker-compose.prod.yml build --no-cache

# Deploy with zero-downtime
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl http://localhost/health
curl https://your-domain.com/health
```

---

## Reference

- **Full Architecture**: [REMOTE_DEVELOPMENT_ARCHITECTURE.md](./REMOTE_DEVELOPMENT_ARCHITECTURE.md)
- **AWS MCP Integration**: [ARCHITECTURE_AWS_MCP.md](./ARCHITECTURE_AWS_MCP.md)
- **Security**: [SECURITY_CREDENTIALS_GUIDE.md](./SECURITY_CREDENTIALS_GUIDE.md)

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Start dev environment | `./scripts/dev_start.sh` |
| Stop dev environment | `./scripts/dev_stop.sh` |
| Sync code to EC2 | `./scripts/sync_to_ec2.sh` |
| Connect VS Code Remote | Cmd+Shift+P → "Remote-SSH: Connect to Host" → ec2-video-app |
| View backend logs | `ssh ec2-video-app 'docker logs voice_backend_dev -f'` |
| Restart backend | `ssh ec2-video-app 'cd /home/ubuntu/video-message-app && docker-compose restart backend'` |
| Test API | `curl http://localhost:55433/health` |
| Open frontend | `open http://localhost:55434` |

---

**Happy coding! 🚀**

*Designed with technical perfection by Artemis 🏹*
