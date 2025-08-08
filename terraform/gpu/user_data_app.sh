#!/bin/bash
# Application Server Setup Script

# ログ出力
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting application server setup..."

# システム更新
apt-get update
apt-get upgrade -y

# 必要なパッケージインストール
apt-get install -y \
    docker.io \
    docker-compose-plugin \
    git \
    htop \
    ncdu \
    nfs-common \
    awscli

# Dockerグループにubuntuユーザー追加
usermod -aG docker ubuntu

# スワップファイル作成（メモリ不足対策）
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab

# EFSマウント
mkdir -p /mnt/shared
echo "${efs_id}.efs.${region}.amazonaws.com:/ /mnt/shared nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0" >> /etc/fstab
mount -a

# ディレクトリ構造作成
mkdir -p /mnt/shared/data/voices
mkdir -p /mnt/shared/data/models
mkdir -p /mnt/shared/data/generated
chown -R ubuntu:ubuntu /mnt/shared/data

# Docker Compose設定ファイル作成
cat > /home/ubuntu/docker-compose.yml << 'EOF'
version: '3.8'

services:
  frontend:
    image: node:18
    working_dir: /app
    volumes:
      - ./frontend:/app
      - /mnt/shared/data:/app/data
    ports:
      - "55434:55434"
    command: npm start
    restart: unless-stopped

  backend:
    image: python:3.10
    working_dir: /app
    volumes:
      - ./backend:/app
      - /mnt/shared/data:/app/data
    ports:
      - "55433:55433"
    environment:
      - OPENVOICE_API_URL=http://GPU_PRIVATE_IP:8001
    command: python main.py
    restart: unless-stopped

  voicevox:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    ports:
      - "50021:50021"
    restart: unless-stopped
EOF

chown ubuntu:ubuntu /home/ubuntu/docker-compose.yml

# 起動スクリプト作成
cat > /home/ubuntu/start.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/video-message-app
docker compose up -d frontend backend voicevox
echo "Application services started"
docker compose ps
EOF

chmod +x /home/ubuntu/start.sh
chown ubuntu:ubuntu /home/ubuntu/start.sh

# 管理スクリプト作成
cat > /home/ubuntu/manage.sh << 'EOF'
#!/bin/bash

GPU_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Type,Values=GPU" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text --region ${region})

case "$1" in
  update-gpu-ip)
    if [ "$GPU_IP" != "None" ]; then
      sed -i "s/GPU_PRIVATE_IP/$GPU_IP/g" /home/ubuntu/docker-compose.yml
      echo "GPU IP updated to: $GPU_IP"
    else
      echo "GPU instance not running"
    fi
    ;;
  start)
    ./start.sh
    ;;
  stop)
    docker compose down
    ;;
  logs)
    docker compose logs -f
    ;;
  *)
    echo "Usage: $0 {update-gpu-ip|start|stop|logs}"
    ;;
esac
EOF

chmod +x /home/ubuntu/manage.sh
chown ubuntu:ubuntu /home/ubuntu/manage.sh

echo "Application server setup completed at $(date)" > /home/ubuntu/setup_complete.txt
chown ubuntu:ubuntu /home/ubuntu/setup_complete.txt

echo "Setup complete!"