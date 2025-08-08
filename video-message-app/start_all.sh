#!/bin/bash
# 統合起動スクリプト - OpenVoice Native + Docker Services

set -e

# 色付き出力用の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# スクリプトのディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${GREEN}🚀 Video Message App 統合起動開始${NC}"
echo "================================================"

# 1. OpenVoice Native Service の起動確認と起動
echo -e "\n${YELLOW}[1/3] OpenVoice Native Service チェック${NC}"

# OpenVoiceが既に起動しているかチェック
if lsof -i :8001 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OpenVoice Native Service は既に起動しています (Port 8001)${NC}"
else
    echo "🎵 OpenVoice Native Service を起動します..."
    
    # OpenVoice Native ディレクトリ存在確認
    OPENVOICE_DIR="$SCRIPT_DIR/openvoice_native"
    if [ ! -d "$OPENVOICE_DIR" ]; then
        echo -e "${RED}❌ OpenVoice Native ディレクトリが見つかりません${NC}"
        echo "先に OpenVoice Native Service のセットアップを実行してください:"
        echo "  cd openvoice_native && ./setup_conda_uv.sh"
        exit 1
    fi
    
    # UV環境確認（Modern方式優先）
    if [ ! -d "$OPENVOICE_DIR/.venv" ] || [ ! -f "$OPENVOICE_DIR/pyproject.toml" ]; then
        echo -e "${YELLOW}⚠️  UV環境が見つかりません。セットアップを実行します...${NC}"
        cd "$OPENVOICE_DIR"
        if [ -f "setup_uv_modern.sh" ]; then
            ./setup_uv_modern.sh
        elif [ -f "setup_conda_uv.sh" ]; then
            echo -e "${YELLOW}⚠️  旧方式のセットアップを使用します${NC}"
            ./setup_conda_uv.sh
        else
            echo -e "${RED}❌ セットアップスクリプトが見つかりません${NC}"
            exit 1
        fi
        cd "$SCRIPT_DIR"
    fi
    
    # OpenVoice をバックグラウンドで起動（Modern方式優先）
    echo "🎵 OpenVoice Native Service をバックグラウンドで起動..."
    cd "$OPENVOICE_DIR"
    if [ -f "start_uv_modern.sh" ]; then
        nohup ./start_uv_modern.sh > "$SCRIPT_DIR/logs/openvoice_native.log" 2>&1 &
    else
        nohup ./start_uv.sh > "$SCRIPT_DIR/logs/openvoice_native.log" 2>&1 &
    fi
    OPENVOICE_PID=$!
    cd "$SCRIPT_DIR"
    
    # 起動待機
    echo -n "OpenVoice Native Service の起動を待機中"
    for i in {1..30}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ OpenVoice Native Service 起動完了${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "\n${RED}❌ OpenVoice Native Service の起動に失敗しました${NC}"
        echo "ログを確認してください: logs/openvoice_native.log"
        exit 1
    fi
fi

# 2. Docker サービスの起動
echo -e "\n${YELLOW}[2/3] Docker サービス起動${NC}"

# Docker Compose 起動
echo "🐳 Docker サービスを起動します..."
docker-compose up -d

# サービスの起動待機
echo -n "Docker サービスの起動を待機中"
for i in {1..60}; do
    if curl -s http://localhost:55433/health > /dev/null 2>&1; then
        echo -e "\n${GREEN}✅ Backend サービス起動完了${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# 3. 起動状態の確認
echo -e "\n${YELLOW}[3/3] サービス状態確認${NC}"

# 各サービスの状態を確認
echo ""
echo "サービス状態:"
echo "============="

# OpenVoice Native
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "🎵 OpenVoice Native:  ${GREEN}✅ 稼働中${NC} (http://localhost:8001)"
else
    echo -e "🎵 OpenVoice Native:  ${RED}❌ 停止${NC}"
fi

# Backend
if curl -s http://localhost:55433/health > /dev/null 2>&1; then
    echo -e "🔧 Backend:           ${GREEN}✅ 稼働中${NC} (http://localhost:55433)"
else
    echo -e "🔧 Backend:           ${RED}❌ 停止${NC}"
fi

# Frontend
if curl -s http://localhost:55434 > /dev/null 2>&1; then
    echo -e "🎨 Frontend:          ${GREEN}✅ 稼働中${NC} (http://localhost:55434)"
else
    echo -e "🎨 Frontend:          ${RED}❌ 停止${NC}"
fi

# VoiceVox
if curl -s http://localhost:50021 > /dev/null 2>&1; then
    echo -e "🗣️  VoiceVox:          ${GREEN}✅ 稼働中${NC} (http://localhost:50021)"
else
    echo -e "🗣️  VoiceVox:          ${RED}❌ 停止${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}🎉 起動完了！${NC}"
echo ""
echo "📱 フロントエンドにアクセス: http://localhost:55434"
echo ""
echo "💡 停止方法: ./stop_all.sh"
echo "📊 ログ確認:"
echo "  - OpenVoice: tail -f logs/openvoice_native.log"
echo "  - Docker:    docker-compose logs -f"
echo ""

# プロセスIDを保存（停止スクリプト用）
if [ ! -z "$OPENVOICE_PID" ]; then
    echo $OPENVOICE_PID > "$SCRIPT_DIR/.openvoice_pid"
fi