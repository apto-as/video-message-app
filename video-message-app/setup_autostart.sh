#!/bin/bash

# EC2インスタンス起動時の自動起動設定スクリプト
# このスクリプトをEC2で実行することで、全サービスが自動起動するようになります

set -e

echo "🚀 Setting up auto-start services for EC2"
echo "========================================="

# 1. OpenVoice Native Service用のsystemdサービスファイルを作成
echo "Creating OpenVoice systemd service..."
sudo tee /etc/systemd/system/openvoice.service > /dev/null << 'EOF'
[Unit]
Description=OpenVoice Native Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/video-message-app/video-message-app/openvoice_native
Environment="PATH=/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStartPre=/bin/sleep 10
ExecStart=/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/bin/python /home/ec2-user/video-message-app/video-message-app/openvoice_native/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 2. Docker Compose用のsystemdサービスファイルを作成
echo "Creating Docker Compose systemd service..."
sudo tee /etc/systemd/system/video-app.service > /dev/null << 'EOF'
[Unit]
Description=Video Message App Docker Compose Services
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=true
User=ec2-user
WorkingDirectory=/home/ec2-user/video-message-app/video-message-app
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=300
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 3. 起動順序を管理するマスターサービスを作成
echo "Creating master startup service..."
sudo tee /etc/systemd/system/video-app-startup.service > /dev/null << 'EOF'
[Unit]
Description=Video App Complete Startup Service
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=true
User=ec2-user
ExecStart=/home/ec2-user/video-message-app/video-message-app/startup_sequence.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 4. 起動シーケンススクリプトを作成
echo "Creating startup sequence script..."
cat > /home/ec2-user/video-message-app/video-message-app/startup_sequence.sh << 'SCRIPT'
#!/bin/bash

# Video App Startup Sequence
# このスクリプトは全サービスを正しい順序で起動します

echo "Starting Video App services..."
echo "=============================="

# 1. 最新コードを取得
echo "📦 Pulling latest code from GitHub..."
cd /home/ec2-user/video-message-app/video-message-app
git pull origin master || echo "Git pull failed, continuing with local code"

# 2. Dockerサービスが起動するまで待機
echo "⏳ Waiting for Docker to be ready..."
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        echo "✅ Docker is ready"
        break
    fi
    sleep 1
done

# 3. Docker Composeサービスを起動
echo "🐳 Starting Docker Compose services..."
docker-compose up -d

# 4. OpenVoice Native Serviceを起動
echo "🎙️ Starting OpenVoice Native Service..."
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native

# 既存プロセスを停止
pkill -f "python main.py" || true
sleep 2

# 仮想環境をアクティベートして起動
if [ -d "venv" ]; then
    source venv/bin/activate
    nohup python main.py > /var/log/openvoice.log 2>&1 &
    echo "OpenVoice started with PID: $!"
else
    echo "❌ OpenVoice venv not found, skipping..."
fi

# 5. ヘルスチェック
echo "🔍 Performing health checks..."
sleep 15

# Backendヘルスチェック
if curl -s http://localhost:55433/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️ Backend health check failed"
fi

# OpenVoiceヘルスチェック
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ OpenVoice is healthy"
else
    echo "⚠️ OpenVoice health check failed"
fi

echo "✨ Startup sequence completed!"
echo "Access your application at: https://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
SCRIPT

chmod +x /home/ec2-user/video-message-app/video-message-app/startup_sequence.sh

# 5. systemdをリロード
echo "Reloading systemd..."
sudo systemctl daemon-reload

# 6. サービスを有効化（自動起動を有効に）
echo "Enabling services for auto-start..."
sudo systemctl enable docker
sudo systemctl enable openvoice.service
sudo systemctl enable video-app.service
sudo systemctl enable video-app-startup.service

# 7. 現在のサービス状態を確認
echo ""
echo "📊 Service Status:"
echo "=================="
sudo systemctl is-enabled docker
sudo systemctl is-enabled openvoice
sudo systemctl is-enabled video-app
sudo systemctl is-enabled video-app-startup

echo ""
echo "✅ Auto-start configuration completed!"
echo ""
echo "Services will automatically start when EC2 instance boots."
echo ""
echo "Manual commands:"
echo "  Start all:  sudo systemctl start video-app-startup"
echo "  Stop all:   sudo systemctl stop video-app && sudo systemctl stop openvoice"
echo "  Status:     sudo systemctl status video-app openvoice"
echo "  Logs:       sudo journalctl -u video-app-startup -f"
echo ""
echo "⚠️ IMPORTANT: Services will start automatically on next boot!"