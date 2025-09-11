# EC2 Instance Rebuild Manual - Video Message App
## Complete Recovery and Cost Optimization Guide

### 🎯 Overview

This manual provides step-by-step instructions for either:
1. **Quick SSL Fix** (30 minutes, $0 cost)
2. **Full Instance Migration** (2-3 hours, $354/month savings)

Choose based on your priorities: immediate recovery vs. cost optimization.

---

## Option 1: Quick SSL Recovery (RECOMMENDED FOR IMMEDIATE FIX)

### Prerequisites
- SSH key for EC2 instance
- Domain `3.115.141.166` accessible
- Ports 80/443 open in security groups

### Step 1: Connect to Instance
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@3.115.141.166
```

### Step 2: Backup Current Configuration
```bash
cd ~/video-message-app/ssl
cp server.crt server.crt.backup
cp server.key server.key.backup
```

### Step 3: Execute SSL Setup
```bash
chmod +x setup_letsencrypt.sh
sudo ./setup_letsencrypt.sh
```

### Step 4: Verification
```bash
# Check services
docker-compose ps

# Test HTTPS
curl -I https://3.115.141.166

# Verify certificate
openssl s_client -connect 3.115.141.166:443 -servername 3.115.141.166 < /dev/null
```

**Expected Result**: Green HTTPS lock, fully functional application

---

## Option 2: Full Instance Migration (FOR COST OPTIMIZATION)

### Phase A: Preparation

#### Step 1: Create AMI Snapshot
```bash
# From local machine
aws ec2 create-image \
    --instance-id i-xxxxxxxxxxxxxx \
    --name "video-message-app-backup-$(date +%Y%m%d)" \
    --description "Backup before migration" \
    --no-reboot
```

#### Step 2: Launch New t3.medium Instance
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name your-key-name \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --associate-public-ip-address \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=video-message-app-optimized}]'
```

### Phase B: Environment Setup

#### Step 1: Connect to New Instance
```bash
NEW_IP="<new-instance-ip>"
ssh -i ~/.ssh/your-key.pem ubuntu@$NEW_IP
```

#### Step 2: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Install git
sudo apt install -y git
```

#### Step 3: Clone Application
```bash
cd ~
git clone https://github.com/apto-as/prototype-app.git
cd prototype-app/video-message-app
```

### Phase C: Data Migration

#### Step 1: Copy Application Data
```bash
# From old instance, create data archive
OLD_IP="3.115.141.166"
ssh ubuntu@$OLD_IP "cd ~/video-message-app && tar -czf app-data.tar.gz data/ ssl/ .env"

# Copy to new instance
scp ubuntu@$OLD_IP:~/video-message-app/app-data.tar.gz ~/video-message-app/

# Extract data
cd ~/video-message-app
tar -xzf app-data.tar.gz
```

#### Step 2: Update Configuration
```bash
# Update docker-compose.yml for new IP
sed -i 's/3.115.141.166/NEW_IP_ADDRESS/g' docker-compose.yml
sed -i 's/3.115.141.166/NEW_IP_ADDRESS/g' nginx/default.conf

# Update environment files
sed -i 's/3.115.141.166/NEW_IP_ADDRESS/g' backend/.env
```

### Phase D: SSL Setup

#### Step 1: Setup Let's Encrypt
```bash
cd ssl
chmod +x setup_letsencrypt.sh

# Update script for new IP
sed -i 's/3.115.141.166/NEW_IP_ADDRESS/g' setup_letsencrypt.sh

sudo ./setup_letsencrypt.sh
```

### Phase E: Service Startup

#### Step 1: Build and Start Services
```bash
cd ~/video-message-app

# Build containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

#### Step 2: Verification
```bash
# Check health endpoints
curl https://NEW_IP_ADDRESS/health
curl https://NEW_IP_ADDRESS/api/health

# Test frontend
curl -I https://NEW_IP_ADDRESS
```

### Phase F: DNS and Final Setup

#### Step 1: Update DNS Records
- Point domain to new IP address
- Wait for DNS propagation (up to 48 hours)

#### Step 2: Update Security Groups
- Ensure new instance has ports 80/443/8001 open
- Update any firewall rules

#### Step 3: Terminate Old Instance
```bash
# Only after confirming new instance works
aws ec2 terminate-instances --instance-ids i-old-instance-id
```

---

## Cost Comparison

### Current Setup (g4dn.xlarge)
- **Monthly Cost**: $384
- **Annual Cost**: $4,608
- **Specs**: 4 vCPU, 16GB RAM, 1x T4 GPU (unused)

### Optimized Setup (t3.medium)
- **Monthly Cost**: $30
- **Annual Cost**: $360
- **Specs**: 2 vCPU, 4GB RAM (sufficient for CPU workload)

### **Annual Savings: $4,248**

---

## Verification Checklist

### SSL Recovery Verification
- [ ] Browser shows green HTTPS lock
- [ ] No certificate warnings
- [ ] Auto-renewal configured
- [ ] All endpoints accessible via HTTPS

### Full Application Verification
- [ ] Frontend loads without errors
- [ ] Voice selection dropdown populated
- [ ] Image upload functionality works
- [ ] D-ID API integration functional
- [ ] VOICEVOX synthesis working
- [ ] OpenVoice cloning operational
- [ ] Video generation completes successfully

### Performance Verification
- [ ] API response times < 2 seconds
- [ ] Video generation completes within expected timeframe
- [ ] No memory/CPU bottlenecks observed
- [ ] All Docker containers healthy

---

## Troubleshooting

### Common SSL Issues
```bash
# Certificate not found
sudo certbot certificates

# Manual certificate request
sudo certbot certonly --manual -d your-domain.com

# Force renewal
sudo certbot renew --force-renewal
```

### Docker Issues
```bash
# Check container logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs nginx

# Restart services
docker-compose restart

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Network Issues
```bash
# Check port bindings
sudo netstat -tlnp | grep :443

# Test internal connectivity
docker exec voice_nginx ping backend
docker exec voice_backend ping voicevox
```

---

## Emergency Rollback

### If SSL Setup Fails
```bash
cd ~/video-message-app/ssl
cp server.crt.backup server.crt
cp server.key.backup server.key
docker-compose restart nginx
```

### If Migration Fails
1. Keep old instance running
2. Update DNS back to old IP
3. Debug new instance separately
4. Attempt migration again when ready

---

## Monitoring and Maintenance

### Daily Checks
```bash
# Service status
docker-compose ps

# Certificate expiry
sudo certbot certificates

# Disk usage
df -h
```

### Weekly Checks
```bash
# System updates
sudo apt update && sudo apt list --upgradable

# Docker image updates
docker-compose pull
docker-compose up -d

# Log rotation
docker system prune -f
```

### Monthly Checks
```bash
# Certificate renewal test
sudo certbot renew --dry-run

# Performance review
docker stats

# Cost analysis
aws ce get-cost-and-usage --time-period Start=2025-08-01,End=2025-09-01
```

---

**Success Criteria**: Application accessible via HTTPS with valid certificate, all features functional, appropriate cost optimization achieved.