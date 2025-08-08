#!/bin/bash

# AWS EC2インスタンスへのVideo Message Appデプロイスクリプト

set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Video Message App デプロイ開始 ===${NC}"

# 設定
KEY_PATH="~/.ssh/video-app-key.pem"
APP_SERVER_IP=$(cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/terraform/gpu && terraform output -raw app_server_public_ip)
REPO_URL="https://github.com/apto-as/prototype-app.git"

if [ -z "$APP_SERVER_IP" ]; then
    echo -e "${RED}エラー: アプリケーションサーバーのIPアドレスが取得できません${NC}"
    exit 1
fi

echo -e "${GREEN}対象サーバー: $APP_SERVER_IP${NC}"

# SSH接続確認
echo -e "${YELLOW}SSHキーのパーミッション設定...${NC}"
chmod 600 ~/.ssh/video-app-key.pem

# デプロイスクリプト作成
cat > /tmp/deploy_on_server.sh << 'EOF'
#!/bin/bash
set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== サーバー上でのセットアップ開始 ===${NC}"

# 1. 必要なパッケージのインストール
echo -e "${YELLOW}1. パッケージのインストール...${NC}"
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git curl jq

# Dockerサービス開始
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# 2. アプリケーションのクローン
echo -e "${YELLOW}2. アプリケーションディレクトリの作成...${NC}"
cd ~
mkdir -p prototype-app
cd prototype-app

# 3. 環境変数ファイルの作成
echo -e "${YELLOW}3. 環境変数ファイルの作成...${NC}"

# backend/.env.docker の作成
cat > backend/.env.docker << 'ENVEOF'
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

# OpenVoice Native Service設定
OPENVOICE_SERVICE_URL=http://host.docker.internal:8001

# VOICEVOX設定
VOICEVOX_URL=http://voicevox:50021
ENVEOF

# frontend/.env.docker の作成
cat > frontend/.env.docker << 'ENVEOF'
REACT_APP_API_URL=http://localhost:55433
ENVEOF

# 4. 必要なディレクトリの作成
echo -e "${YELLOW}4. ディレクトリ構造の作成...${NC}"
mkdir -p data/backend/storage/{voices,profiles,backgrounds,avatars,temp,output,openvoice}

# 5. Docker Composeの起動
echo -e "${YELLOW}5. Docker Composeサービスの起動...${NC}"

# 既存のコンテナがあれば停止
sudo docker-compose down || true

# イメージをプル
sudo docker-compose pull

# サービス起動
sudo docker-compose up -d

# 6. ヘルスチェック
echo -e "${YELLOW}6. サービスのヘルスチェック...${NC}"
sleep 10

# Backend health check
if curl -f http://localhost:55433/health 2>/dev/null; then
    echo -e "${GREEN}✓ Backend APIが正常に起動しました${NC}"
else
    echo -e "${RED}✗ Backend APIの起動に失敗しました${NC}"
fi

# Frontend check
if curl -f http://localhost:55434 2>/dev/null | grep -q "<title>"; then
    echo -e "${GREEN}✓ Frontendが正常に起動しました${NC}"
else
    echo -e "${RED}✗ Frontendの起動に失敗しました${NC}"
fi

# VOICEVOX check
if curl -f http://localhost:50021/version 2>/dev/null; then
    echo -e "${GREEN}✓ VOICEVOXが正常に起動しました${NC}"
else
    echo -e "${RED}✗ VOICEVOXの起動に失敗しました${NC}"
fi

echo -e "${GREEN}=== デプロイ完了 ===${NC}"
echo -e "${GREEN}アクセスURL:${NC}"
echo -e "  Frontend: http://$1:55434"
echo -e "  Backend API: http://$1:55433"
echo -e "  VOICEVOX: http://$1:50021"

echo -e "${YELLOW}\n注意: D-ID APIキーを設定してください:${NC}"
echo -e "  1. backend/.env.docker を編集"
echo -e "  2. D_ID_API_KEY=<your_actual_key> を設定"
echo -e "  3. docker-compose restart backend でバックエンドを再起動"

EOF

# デプロイスクリプトをサーバーにコピーして実行
echo -e "${YELLOW}サーバーにデプロイスクリプトを転送...${NC}"
scp -i $KEY_PATH -P 22 -o StrictHostKeyChecking=no /tmp/deploy_on_server.sh ubuntu@$APP_SERVER_IP:/tmp/

echo -e "${YELLOW}デプロイを実行中...${NC}"
ssh -i $KEY_PATH -p 22 -o StrictHostKeyChecking=no ubuntu@$APP_SERVER_IP "bash /tmp/deploy_on_server.sh $APP_SERVER_IP"

echo -e "${GREEN}\n=== デプロイが完了しました ===${NC}"
echo -e "${GREEN}アプリケーションURL:${NC}"
echo -e "  Frontend: http://$APP_SERVER_IP:55434"
echo -e "  Backend API: http://$APP_SERVER_IP:55433/docs"
echo -e "  VOICEVOX: http://$APP_SERVER_IP:50021"

echo -e "${YELLOW}\n次のステップ:${NC}"
echo -e "  1. D-ID APIキーの設定（必須）:"
echo -e "     ssh -i $KEY_PATH ubuntu@$APP_SERVER_IP"
echo -e "     cd prototype-app"
echo -e "     nano backend/.env.docker  # D_ID_API_KEYを設定"
echo -e "     sudo docker-compose restart backend"
echo -e ""
echo -e "  2. ログの確認:"
echo -e "     ssh -i $KEY_PATH ubuntu@$APP_SERVER_IP"
echo -e "     cd prototype-app"
echo -e "     sudo docker-compose logs -f"