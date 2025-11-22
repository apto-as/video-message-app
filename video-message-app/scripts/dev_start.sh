#!/bin/bash
# Development Environment Startup Script
# Usage: ./scripts/dev_start.sh

set -e

echo "🚀 Starting Video Message App Development Environment"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if running on Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is designed for Mac. For EC2, use docker-compose directly.${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker installed${NC}"

# Check Conda
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ Conda not found. Please install Miniconda/Anaconda.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conda installed${NC}"

# Check SSH connection to EC2
echo -e "${YELLOW}Checking EC2 connection...${NC}"
if ssh -o ConnectTimeout=5 -o BatchMode=yes ec2-video-app "echo 'Connection successful'" &> /dev/null; then
    echo -e "${GREEN}✅ EC2 connection OK${NC}"
else
    echo -e "${RED}❌ Cannot connect to EC2. Check your SSH config.${NC}"
    echo "Expected SSH config entry: ec2-video-app"
    exit 1
fi

# Start OpenVoice Native Service (Mac)
echo ""
echo -e "${YELLOW}Starting OpenVoice Native Service (Mac)...${NC}"

# Check if openvoice_v2 environment exists
if conda env list | grep -q "openvoice_v2"; then
    echo -e "${GREEN}✅ openvoice_v2 environment found${NC}"
else
    echo -e "${RED}❌ openvoice_v2 environment not found. Creating...${NC}"
    conda create -n openvoice_v2 python=3.11 -y
    conda activate openvoice_v2
    cd openvoice_native
    pip install -r requirements.txt
    cd ..
fi

# Check if OpenVoice is already running
if lsof -i :8001 &> /dev/null; then
    echo -e "${YELLOW}⚠️  OpenVoice already running on port 8001${NC}"
else
    echo -e "${GREEN}Starting OpenVoice Native Service...${NC}"
    osascript -e 'tell application "Terminal" to do script "cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/openvoice_native && conda activate openvoice_v2 && python main.py"'
    echo -e "${GREEN}✅ OpenVoice started in new terminal window${NC}"
    sleep 5
fi

# Verify OpenVoice health
echo -e "${YELLOW}Verifying OpenVoice health...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8001/health &> /dev/null; then
        echo -e "${GREEN}✅ OpenVoice is healthy${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}❌ OpenVoice health check failed after 10 attempts${NC}"
        exit 1
    fi
    echo "Waiting for OpenVoice to start... ($i/10)"
    sleep 2
done

# Start Docker services on EC2
echo ""
echo -e "${YELLOW}Starting Docker services on EC2...${NC}"
ssh ec2-video-app << 'EOF'
    cd /home/ubuntu/video-message-app
    docker-compose -f docker-compose.dev.yml up -d
    echo "Waiting for services to start..."
    sleep 10
    docker-compose ps
EOF
echo -e "${GREEN}✅ Docker services started on EC2${NC}"

# Setup SSH port forwarding
echo ""
echo -e "${YELLOW}Setting up SSH port forwarding...${NC}"
ssh -f -N -L 55433:localhost:55433 -L 55441:localhost:55441 -L 50021:localhost:50021 ec2-video-app
echo -e "${GREEN}✅ Port forwarding established${NC}"

# Verify health checks
echo ""
echo -e "${YELLOW}Running health checks...${NC}"

# Backend
if curl -s http://localhost:55433/health | jq -e '.status == "healthy"' &> /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "Response: $(curl -s http://localhost:55433/health | jq)"
fi

# VOICEVOX
if curl -s http://localhost:50021/version &> /dev/null; then
    echo -e "${GREEN}✅ VOICEVOX is healthy${NC}"
else
    echo -e "${RED}❌ VOICEVOX health check failed${NC}"
fi

# Print summary
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 Development environment ready!${NC}"
echo "=================================================="
echo ""
echo "Services:"
echo "  - OpenVoice Native:  http://localhost:8001"
echo "  - Backend API:       http://localhost:55433"
echo "  - VOICEVOX:          http://localhost:50021"
echo "  - Frontend:          http://localhost:55434"
echo ""
echo "Next steps:"
echo "  1. Open VS Code: code ."
echo "  2. Connect to EC2: Cmd+Shift+P → 'Remote-SSH: Connect to Host' → ec2-video-app"
echo "  3. Start coding! Changes will hot-reload automatically."
echo ""
echo "Logs:"
echo "  - OpenVoice: Check the new terminal window"
echo "  - Backend: ssh ec2-video-app 'docker logs voice_backend_dev -f'"
echo "  - All: ssh ec2-video-app 'docker-compose -f docker-compose.dev.yml logs -f'"
echo ""
echo "Stop services: ./scripts/dev_stop.sh"
echo ""
