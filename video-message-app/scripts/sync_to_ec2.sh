#!/bin/bash
# Sync local changes to EC2
# Usage: ./scripts/sync_to_ec2.sh [--watch]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
EC2_HOST="ec2-video-app"
EC2_PATH="/home/ubuntu/video-message-app"
LOCAL_PATH="."

# Rsync options
RSYNC_OPTIONS=(
    -avz
    --progress
    --delete
    --exclude 'node_modules'
    --exclude '__pycache__'
    --exclude '.git'
    --exclude 'data/'
    --exclude '.venv/'
    --exclude '.pytest_cache/'
    --exclude 'htmlcov/'
    --exclude '*.pyc'
    --exclude '.DS_Store'
)

# Function to perform sync
do_sync() {
    echo -e "${YELLOW}Syncing local changes to EC2...${NC}"
    rsync "${RSYNC_OPTIONS[@]}" "$LOCAL_PATH/" "$EC2_HOST:$EC2_PATH/"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Sync completed at $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    else
        echo -e "${RED}❌ Sync failed${NC}"
        exit 1
    fi
}

# Watch mode
if [ "$1" == "--watch" ]; then
    echo -e "${YELLOW}Starting watch mode (syncing on file changes)...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""

    # Check if fswatch is installed
    if ! command -v fswatch &> /dev/null; then
        echo -e "${RED}❌ fswatch not found. Installing...${NC}"
        brew install fswatch
    fi

    # Initial sync
    do_sync

    # Watch for changes
    fswatch -o \
        --exclude '\.git' \
        --exclude 'node_modules' \
        --exclude '__pycache__' \
        --exclude 'data/' \
        --exclude '.venv/' \
        . | while read f; do
        do_sync
    done
else
    # One-time sync
    do_sync
fi
