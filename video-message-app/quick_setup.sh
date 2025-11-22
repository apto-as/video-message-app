#!/bin/bash
# ========================================
# Quick Setup Script
# Athena's Harmonious All-in-One Setup
# ========================================

set -e

echo "🌸 Athena's Quick Setup - 全自動環境構築 🌸"
echo "======================================================"
echo ""
echo "このスクリプトは以下を自動実行します:"
echo "  1. OpenVoice Conda環境作成（5分）"
echo "  2. D-ID APIキー設定（30秒）"
echo "  3. Backend依存関係インストール（2分）"
echo "  4. Frontend依存関係インストール（2分）"
echo "  5. ストレージディレクトリ作成（10秒）"
echo ""
echo "推定時間: 約8分"
echo ""

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# プロジェクトルートの確認
if [ ! -d "openvoice_native" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${YELLOW}⚠️  プロジェクトルートディレクトリで実行してください${NC}"
    echo "現在のディレクトリ: $(pwd)"
    exit 1
fi

# 実行確認
read -p "続行しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "セットアップをキャンセルしました"
    exit 0
fi

echo ""
echo "======================================================"
echo "Step 1/5: OpenVoice Conda環境作成"
echo "======================================================"

# Conda環境の確認
if conda env list | grep -q "openvoice_v2"; then
    echo -e "${GREEN}✅ openvoice_v2 環境は既に存在します（スキップ）${NC}"
else
    echo -e "${BLUE}🐍 openvoice_v2 環境を作成中...（5分程度かかります）${NC}"
    conda create -n openvoice_v2 python=3.11.12 -y
    echo -e "${GREEN}✅ openvoice_v2 環境作成完了${NC}"
fi

# OpenVoice依存関係のインストール
echo ""
echo -e "${BLUE}📦 OpenVoice依存関係をインストール中...${NC}"
cd openvoice_native

# Conda環境でインストール
if [ -f requirements.txt ]; then
    conda run -n openvoice_v2 pip install -r requirements.txt
    echo -e "${GREEN}✅ OpenVoice依存関係インストール完了${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt が見つかりません${NC}"
fi

cd ..

echo ""
echo "======================================================"
echo "Step 2/5: D-ID APIキー設定"
echo "======================================================"

# D-ID APIキーの設定
if [ -f ~/secure_credentials/d_id_api_key.txt ]; then
    export D_ID_API_KEY=$(grep "D_ID_API_KEY=" ~/secure_credentials/d_id_api_key.txt | cut -d'=' -f2)

    if [ -n "$D_ID_API_KEY" ]; then
        echo -e "${GREEN}✅ D-ID APIキーを読み込みました${NC}"

        # Backend .envファイルの作成/更新
        cd backend
        if [ ! -f .env ]; then
            cp .env.example .env
            echo -e "${BLUE}📝 .env ファイルを作成しました${NC}"
        fi

        # macOS用のsed
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/D_ID_API_KEY=.*/D_ID_API_KEY=$D_ID_API_KEY/" .env
        else
            sed -i "s/D_ID_API_KEY=.*/D_ID_API_KEY=$D_ID_API_KEY/" .env
        fi

        echo -e "${GREEN}✅ D-ID APIキーを .env に設定しました${NC}"
        cd ..
    else
        echo -e "${YELLOW}⚠️  D-ID APIキーが空です${NC}"
        cd ..
    fi
else
    echo -e "${YELLOW}⚠️  D-ID APIキーファイルが見つかりません${NC}"
    echo "    ~/secure_credentials/d_id_api_key.txt を作成してください"
fi

echo ""
echo "======================================================"
echo "Step 3/5: Backend依存関係インストール"
echo "======================================================"

cd backend

# Python仮想環境の作成（Conda環境とは別）
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}🐍 Python仮想環境を作成中...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ Python仮想環境作成完了${NC}"
else
    echo -e "${GREEN}✅ Python仮想環境は既に存在します（スキップ）${NC}"
fi

# 依存関係のインストール
echo -e "${BLUE}📦 Backend依存関係をインストール中...${NC}"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo -e "${GREEN}✅ Backend依存関係インストール完了${NC}"

cd ..

echo ""
echo "======================================================"
echo "Step 4/5: Frontend依存関係インストール"
echo "======================================================"

cd frontend

echo -e "${BLUE}📦 Frontend依存関係をインストール中...${NC}"
npm install

echo -e "${GREEN}✅ Frontend依存関係インストール完了${NC}"

cd ..

echo ""
echo "======================================================"
echo "Step 5/5: ストレージディレクトリ作成"
echo "======================================================"

# 必要なディレクトリの作成
mkdir -p data/backend/storage/voices
mkdir -p data/backend/storage/openvoice
mkdir -p data/backend/storage/voice_clones
mkdir -p data/backend/storage/videos

# 権限設定
chmod 755 data/backend/storage/voices
chmod 755 data/backend/storage/openvoice
chmod 755 data/backend/storage/voice_clones
chmod 755 data/backend/storage/videos

echo -e "${GREEN}✅ ストレージディレクトリ作成完了${NC}"

echo ""
echo "======================================================"
echo "🎉 セットアップ完了！"
echo "======================================================"
echo ""
echo "次のステップ:"
echo ""
echo "  1. サービスを起動:"
echo "     ./start_all_services.sh"
echo ""
echo "  2. または個別に起動:"
echo "     ./start_all_services.sh --help"
echo ""
echo "  3. ブラウザでアクセス:"
echo "     http://localhost:55434"
echo ""
echo "======================================================"
