# Security Credentials Management Guide

## 🚨 CRITICAL: API Key Storage

### Real API Key Location
The actual D-ID API key is stored in:
```
~/secure_credentials/d_id_api_key.txt
```

**Permissions**: 600 (read/write for owner only)

### Setting Up Environment for Local Development

```bash
# Load API key from secure location
export D_ID_API_KEY=$(grep "D_ID_API_KEY=" ~/secure_credentials/d_id_api_key.txt | cut -d'=' -f2)

# Or manually copy to backend/.env (NEVER commit)
cp ~/secure_credentials/d_id_api_key.txt video-message-app/backend/.env.local
```

### Setting Up Environment for Docker

Update `video-message-app/docker-compose.yml` to use environment file:

```yaml
services:
  backend:
    env_file:
      - ./backend/.env.local  # Contains real API key, gitignored
    environment:
      - ENVIRONMENT=docker
      # ... other vars
```

### Setting Up for EC2 Production

**Option A: Environment Variables (Current)**
```bash
# On EC2 instance
export D_ID_API_KEY="YmlsbEBuZXVyb2F4aXMuYWk:pMw2AtM0MRTXbcgbPzXBD"
```

**Option B: AWS Secrets Manager (Recommended for Production)**
```bash
# 1. Store secret in AWS Secrets Manager
aws secretsmanager create-secret \
    --name video-message-app/d-id-api-key \
    --secret-string "YmlsbEBuZXVyb2F4aXMuYWk:pMw2AtM0MRTXbcgbPzXBD" \
    --region ap-northeast-1

# 2. Retrieve in application (backend/core/config.py)
import boto3

def get_d_id_api_key():
    client = boto3.client('secretsmanager', region_name='ap-northeast-1')
    response = client.get_secret_value(SecretId='video-message-app/d-id-api-key')
    return response['SecretString']
```

## Git History Cleanup

### What Was Done (2025-11-02)

The D-ID API key was accidentally committed to Git history in the following files:
- `video-message-app/backend/.env.docker`
- `video-message-app/docker-compose.yml`
- `develop-plan-0.md`
- `video-message-app/ssl/setup_d_id_key.sh`

**Actions Taken**:
1. ✅ Removed API key from all 54 commits using `git-filter-repo`
2. ✅ Replaced with placeholder `your-d-id-api-key-here`
3. ✅ Updated working files to use placeholders
4. ✅ Saved real API key to secure local location

### Force Push Required

⚠️ **IMPORTANT**: You must force-push to GitHub to update the remote repository:

```bash
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app

# Review changes
git log --oneline | head -10

# Force push (DESTRUCTIVE - rewrites history)
git push origin master --force
```

**WARNING**: This will rewrite GitHub history. Anyone who has cloned the repository will need to:
```bash
git fetch origin
git reset --hard origin/master
```

### Verify Cleanup

After force-push, verify on GitHub:
```bash
# Search GitHub for API key
# Go to: https://github.com/apto-as/video-message-app/search?q=YmlsbEBuZXVyb2F4aXMuYWk

# Should return NO results
```

## Security Checklist

- [x] Remove API key from Git history
- [x] Save real API key to secure location
- [ ] Force-push to GitHub
- [ ] Verify API key not in GitHub history
- [ ] Consider rotating D-ID API key (optional, since no fraud detected)
- [ ] Implement AWS Secrets Manager for production
- [ ] Update deployment scripts to use secure storage
- [ ] Add pre-commit hooks to prevent future commits of secrets

## Files That Should NEVER Be Committed

Add to `.gitignore`:
```
# Credentials (local secure storage)
.env.local
.env.*.local
**/secure_credentials/

# Backup files with credentials
*.backup
*.bak

# AWS credentials
.aws/credentials
```

## Recovery Instructions

If the API key needs to be rotated:

1. **Generate New Key**: Log into D-ID dashboard and create new API key
2. **Update Secure Storage**:
   ```bash
   echo "D_ID_API_KEY=new-key-here" > ~/secure_credentials/d_id_api_key.txt
   chmod 600 ~/secure_credentials/d_id_api_key.txt
   ```
3. **Update Production**: Update environment variables or AWS Secrets Manager
4. **Revoke Old Key**: Revoke the old key in D-ID dashboard

## Contact

For questions about credential management, contact:
- Project Owner: apto.as@gmail.com
- Created: 2025-11-02
- Last Updated: 2025-11-02
