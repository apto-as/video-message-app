#!/bin/bash
# Development Environment Shutdown Script
# Usage: ./scripts/dev_stop.sh

set -e

echo "🛑 Stopping Video Message App Development Environment"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Stop Docker services on EC2
echo -e "${YELLOW}Stopping Docker services on EC2...${NC}"
ssh ec2-video-app << 'EOF'
    cd /home/ubuntu/video-message-app
    docker-compose -f docker-compose.dev.yml down
EOF
echo -e "${GREEN}✅ Docker services stopped on EC2${NC}"

# Kill SSH port forwarding
echo -e "${YELLOW}Stopping SSH port forwarding...${NC}"
pkill -f "ssh -f -N -L 55433" || true
echo -e "${GREEN}✅ Port forwarding stopped${NC}"

# Stop OpenVoice (optional, user can keep it running)
echo ""
echo -e "${YELLOW}OpenVoice Native Service is still running (Mac).${NC}"
echo "To stop it manually:"
echo "  1. Find the terminal window running OpenVoice"
echo "  2. Press Ctrl+C"
echo ""
echo "Or kill it automatically:"
read -p "Stop OpenVoice now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pkill -f "python main.py" || true
    echo -e "${GREEN}✅ OpenVoice stopped${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}Development environment stopped${NC}"
echo "=================================================="
