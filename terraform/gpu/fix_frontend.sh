#!/bin/bash

# フロントエンド環境変数修正スクリプト

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER_IP="3.115.141.166"

echo -e "${GREEN}=== Frontend環境変数修正 ===${NC}"

# 1. 環境変数ファイルの作成
echo -e "${YELLOW}Frontend環境変数を更新...${NC}"

cat > frontend/.env << EOF
REACT_APP_API_URL=http://${SERVER_IP}:55433
EOF

echo -e "${GREEN}環境変数設定:${NC}"
echo "  REACT_APP_API_URL=http://${SERVER_IP}:55433"

# 2. Docker Composeファイルを更新
echo -e "${YELLOW}Docker Compose設定を更新...${NC}"

# docker-compose.ymlのfrontend部分を更新
cat > docker-compose-update.yml << 'EOF'
version: '3.8'

services:
  voicevox:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    container_name: voicevox_engine
    ports:
      - "50021:50021"
    networks:
      - voice_network
    restart: unless-stopped

  backend:
    build: ./backend
    container_name: voice_backend
    ports:
      - "55433:55433"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./backend:/app
    environment:
      - ENVIRONMENT=docker
      - VOICEVOX_URL=http://voicevox:50021
      - OPENVOICE_SERVICE_URL=http://host.docker.internal:8001
      - DID_API_KEY=${DID_API_KEY}
    networks:
      - voice_network
    depends_on:
      - voicevox
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: voice_frontend
    ports:
      - "55434:55434"
    environment:
      - REACT_APP_API_URL=http://3.115.141.166:55433
      - NODE_ENV=development
    networks:
      - voice_network
    depends_on:
      - backend
    restart: unless-stopped

networks:
  voice_network:
    driver: bridge
EOF

# 既存のdocker-compose.ymlをバックアップ
cp docker-compose.yml docker-compose.yml.bak

# 新しい設定に置き換え
mv docker-compose-update.yml docker-compose.yml

# 3. コンテナを再起動
echo -e "${YELLOW}コンテナを再起動...${NC}"
sudo docker-compose down
sudo docker-compose up -d --build frontend

sleep 10

# 4. 動作確認
echo -e "${YELLOW}動作確認...${NC}"

# Frontend health check
if curl -f http://localhost:55434 2>/dev/null | grep -q "<title>"; then
    echo -e "${GREEN}✓ Frontend正常起動${NC}"
else
    echo -e "${RED}✗ Frontend起動失敗${NC}"
fi

# Backend health check
if curl -f http://localhost:55433/health 2>/dev/null; then
    echo -e "${GREEN}✓ Backend API正常稼働${NC}"
else
    echo -e "${RED}✗ Backend API起動失敗${NC}"
fi

echo -e "${GREEN}=== 修正完了 ===${NC}"
echo -e "${GREEN}ブラウザをリロードしてください: http://${SERVER_IP}:55434${NC}"