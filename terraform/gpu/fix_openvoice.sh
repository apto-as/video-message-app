#!/bin/bash

# OpenVoice設定修正スクリプト

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== OpenVoice設定修正 ===${NC}"

# 1. 環境変数ファイルの作成
echo -e "${YELLOW}環境変数ファイルを作成...${NC}"

cat > backend/.env.docker << 'EOF'
# Docker環境用設定
ENVIRONMENT=docker
D_ID_API_KEY=${D_ID_API_KEY:-your_api_key_here}

# パス設定（Docker内部パス）
STORAGE_PATH=/app/storage
OPENVOICE_PATH=/app/storage/openvoice
VOICES_PATH=/app/storage/voices
PROFILES_PATH=/app/storage/profiles
BACKGROUNDS_PATH=/app/storage/backgrounds
AVATARS_PATH=/app/storage/avatars
TEMP_PATH=/app/storage/temp
OUTPUT_PATH=/app/storage/output

# OpenVoice Native Service設定（EC2では使用不可）
# OpenVoiceは現在無効化
OPENVOICE_SERVICE_URL=http://localhost:8001
DISABLE_OPENVOICE=true

# VOICEVOX設定
VOICEVOX_URL=http://voicevox:50021
EOF

# 2. Backendコンテナ再起動
echo -e "${YELLOW}Backendコンテナを再起動...${NC}"
sudo docker-compose restart voice_backend

sleep 5

# 3. 動作確認
echo -e "${YELLOW}動作確認...${NC}"

# Health check
if curl -f http://localhost:55433/health 2>/dev/null; then
    echo -e "${GREEN}✓ Backend API正常稼働${NC}"
else
    echo -e "${RED}✗ Backend API起動失敗${NC}"
fi

# VOICEVOX test
if curl -f http://localhost:50021/version 2>/dev/null; then
    echo -e "${GREEN}✓ VOICEVOX正常稼働${NC}"
else
    echo -e "${RED}✗ VOICEVOX起動失敗${NC}"
fi

echo -e "${GREEN}=== 設定完了 ===${NC}"
echo -e "${YELLOW}注意: OpenVoiceは現在無効化されています。${NC}"
echo -e "${GREEN}VOICEVOXによる日本語音声合成は利用可能です。${NC}"