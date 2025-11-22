# Daily Development Checklist - Video Message App

**Quick Reference for Local-First Workflow**

---

## Morning Startup (2 minutes)

```bash
# Navigate to project
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app

# 1. Start Docker Desktop (if not running)
open -a Docker
sleep 30

# 2. Start VOICEVOX
docker-compose up -d voicevox

# 3. Start Backend (Terminal 1)
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 55433

# 4. Start Frontend (Terminal 2)
cd frontend
npm run dev
```

✅ **Done when**: Browser at `http://localhost:55434` shows app

---

## Before Starting Work

- [ ] Pull latest changes: `git pull origin master`
- [ ] Check services are running:
  - [ ] Backend: `curl http://localhost:55433/health`
  - [ ] Frontend: Browser at `http://localhost:55434`
  - [ ] VOICEVOX: `curl http://localhost:50021/version`
- [ ] Create feature branch: `git checkout -b feature/my-feature`

---

## During Development (Local)

### For Backend Changes

```bash
# Edit Python files in backend/
# Watch terminal for auto-reload messages:
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:55433
```

**Testing**:
```bash
# Manual API test
curl -X POST http://localhost:55433/api/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "テスト", "speaker_id": 1}'

# Run unit tests
cd backend
pytest tests/ -v

# Check logs
# Terminal 1 shows real-time logs
```

### For Frontend Changes

```bash
# Edit React files in frontend/src/
# Vite HMR will auto-update browser
# Check browser console for errors
```

**Testing**:
- Open DevTools (F12)
- Check Console tab (no errors)
- Check Network tab (API calls succeed)
- Test UI interactions

---

## Pre-Commit Checklist

Before committing your changes:

### Code Quality

- [ ] **Backend linting**:
  ```bash
  cd backend
  flake8 app/ --max-line-length 100
  ```

- [ ] **Frontend linting**:
  ```bash
  cd frontend
  npm run lint
  ```

- [ ] **Backend tests**:
  ```bash
  cd backend
  pytest tests/ -v --cov=app
  ```

- [ ] **Frontend build**:
  ```bash
  cd frontend
  npm run build
  ```

### Manual Testing

- [ ] Tested feature in browser (happy path)
- [ ] Tested error cases (invalid input)
- [ ] No console errors in DevTools
- [ ] API responses are correct

### Git Hygiene

- [ ] Only relevant files staged:
  ```bash
  git status  # Review changes
  git diff    # Review diff
  ```

- [ ] Clear commit message:
  ```bash
  git add .
  git commit -m "Feature: Add voice selection dropdown

  - Added VoiceSelector component
  - Integrated with backend API
  - Added error handling for failed requests"
  ```

---

## When to Test on EC2

Deploy to EC2 when you need to test:

- [ ] **OpenVoice voice cloning** (GPU required)
- [ ] **D-ID video generation** (external API)
- [ ] **Full integration** (all services together)
- [ ] **Performance under load** (stress testing)
- [ ] **Before merging to master** (final validation)

### EC2 Deployment Checklist

```bash
# 1. Commit all changes
git add .
git commit -m "Feature: <description>"
git push origin <branch-name>

# 2. Deploy to EC2
./deploy_to_ec2.sh

# 3. Verify deployment
curl https://3.115.141.166/api/health
open https://3.115.141.166

# 4. Test OpenVoice
# Upload reference audio
# Generate cloned voice
# Verify audio quality

# 5. Check EC2 logs if needed
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
tail -f /home/ec2-user/video-message-app/video-message-app/openvoice_native/openvoice.log
```

---

## End of Day

### Cleanup (Optional)

```bash
# Stop local services
# Press Ctrl+C in Terminal 1 (Backend)
# Press Ctrl+C in Terminal 2 (Frontend)

# Stop Docker containers (saves CPU)
docker-compose down

# Or keep running (services auto-restart on Mac reboot)
```

### Commit Work in Progress

```bash
# If work is incomplete, commit to branch
git add .
git commit -m "WIP: <description>"
git push origin <branch-name>

# Or use git stash for uncommitted changes
git stash save "WIP: <description>"
```

### EC2 Cost Optimization

If you tested on EC2 today:

```bash
# Stop EC2 instance (save ~$5/day)
aws ec2 stop-instances --instance-ids <instance-id> --region ap-northeast-1

# Or via AWS Console:
# EC2 Dashboard → Instances → Select → Instance State → Stop
```

---

## Weekly Tasks

### Monday

- [ ] Pull latest master: `git pull origin master`
- [ ] Review project roadmap: Check GitHub Issues
- [ ] Plan week's features

### Friday

- [ ] Merge completed features to master
- [ ] Deploy to EC2 for weekend testing
- [ ] Document any issues in GitHub Issues
- [ ] Update CHANGELOG.md (if applicable)

---

## Monthly Tasks

### First Monday of Month

- [ ] Update dependencies:
  ```bash
  # Backend
  cd backend
  pip list --outdated
  # Review and update requirements.txt

  # Frontend
  cd frontend
  npm outdated
  npm update
  ```

- [ ] Review AWS costs:
  - AWS Console → Billing Dashboard
  - Ensure EC2 costs are within budget (~$20-50/month)

- [ ] Run full test suite:
  ```bash
  # Backend
  cd backend
  pytest tests/ -v --cov=app --cov-report=html

  # Frontend
  cd frontend
  npm run test
  ```

---

## Emergency Procedures

### Backend Not Starting

```bash
# Check if port is in use
lsof -i :55433

# Kill process if needed
kill -9 <PID>

# Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Restart backend
uvicorn main:app --reload
```

### Frontend Not Building

```bash
# Clear cache
cd frontend
rm -rf node_modules/.vite
rm -rf node_modules
rm package-lock.json

# Reinstall
npm install

# Restart
npm run dev
```

### Docker Issues

```bash
# Restart Docker Desktop
pkill Docker
open -a Docker
sleep 30

# Clean up Docker
docker system prune -a  # Removes unused containers/images
docker-compose down -v  # Removes volumes

# Rebuild
docker-compose up -d voicevox
```

### EC2 Deployment Failed

```bash
# Check SSH connection
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166

# Check EC2 logs
cd /home/ec2-user/video-message-app/video-message-app
docker logs voice_backend --tail 50
tail -f openvoice_native/openvoice.log

# Restart services manually
docker-compose restart backend
cd openvoice_native
pkill -f "python main.py"
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8001 > openvoice.log 2>&1 &
```

---

## Quick Command Reference

### Most Used Commands

```bash
# Start development
docker-compose up -d voicevox
cd backend && source venv/bin/activate && uvicorn main:app --reload
cd frontend && npm run dev

# Health checks
curl http://localhost:55433/health
curl http://localhost:50021/version

# Testing
cd backend && pytest tests/ -v
cd frontend && npm run lint

# Git workflow
git checkout -b feature/<name>
git add .
git commit -m "Message"
git push origin feature/<name>

# Deploy to EC2
./deploy_to_ec2.sh

# View logs
docker logs voice_backend --tail 50 -f
tail -f openvoice_native/openvoice.log
```

### Environment Variables

```bash
# Check backend environment
cd backend
cat .env

# Check if D-ID API key is set
grep D_ID_API_KEY .env

# Enable/disable OpenVoice mock
# .env: OPENVOICE_MOCK_MODE=true (local)
# .env: OPENVOICE_MOCK_MODE=false (EC2)
```

---

## Productivity Tips

### VS Code Shortcuts

- `Cmd+P`: Quick file open
- `Cmd+Shift+F`: Search across files
- `Cmd+B`: Toggle sidebar
- `Cmd+J`: Toggle terminal
- `F5`: Start debugging (with launch.json)

### Terminal Shortcuts

- `Ctrl+C`: Stop current process
- `Ctrl+R`: Search command history
- `Cmd+T`: New terminal tab
- `Cmd+W`: Close current tab

### Git Shortcuts

```bash
# Aliases (add to ~/.gitconfig)
[alias]
  st = status
  co = checkout
  br = branch
  ci = commit
  df = diff
  lg = log --oneline --graph
```

### Browser DevTools

- `Cmd+Opt+I`: Open DevTools
- `Cmd+Opt+J`: Open Console
- `Cmd+R`: Reload page
- `Cmd+Shift+R`: Hard reload (bypass cache)

---

## Success Metrics

Track your productivity:

- [ ] **Fast iteration**: Code change to browser update < 1 second
- [ ] **Low EC2 costs**: Monthly bill < $50
- [ ] **High code quality**: All tests passing, no linting errors
- [ ] **Clean Git history**: Clear commit messages, logical branches
- [ ] **Minimal bugs**: Caught errors locally before EC2 testing

---

**Last Updated**: 2025-11-02
**Maintained By**: Athena (Harmonious Conductor)
**Print this file**: Keep near your desk for quick reference
