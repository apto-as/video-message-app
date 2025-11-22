#!/bin/bash
# ========================================
# Start All Services
# Athena's Harmonious Service Orchestrator
# ========================================

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# ヘルプ表示
show_help() {
    echo "🌸 Athena's Service Orchestrator 🌸"
    echo ""
    echo "使い方:"
    echo "  ./start_all_services.sh [オプション]"
    echo ""
    echo "オプション:"
    echo "  --all          すべてのサービスを起動（デフォルト）"
    echo "  --openvoice    OpenVoice Native Serviceのみ起動"
    echo "  --voicevox     VOICEVOXコンテナのみ起動"
    echo "  --backend      Backendのみ起動"
    echo "  --frontend     Frontendのみ起動"
    echo "  --status       サービスの稼働状況を確認"
    echo "  --stop         すべてのサービスを停止"
    echo "  --help         このヘルプを表示"
    echo ""
    echo "例:"
    echo "  ./start_all_services.sh                # すべて起動"
    echo "  ./start_all_services.sh --backend      # Backendのみ起動"
    echo "  ./start_all_services.sh --status       # 稼働確認"
    echo "  ./start_all_services.sh --stop         # すべて停止"
}

# サービス稼働状況の確認
check_status() {
    echo "🔍 サービス稼働状況チェック"
    echo "======================================================"

    # OpenVoice Native Service
    echo ""
    echo "1. OpenVoice Native Service (Port 8001):"
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 起動中${NC}"
    else
        echo -e "${RED}❌ 停止中${NC}"
    fi

    # VOICEVOX
    echo ""
    echo "2. VOICEVOX Engine (Port 50021):"
    if curl -s http://localhost:50021/version > /dev/null 2>&1; then
        VERSION=$(curl -s http://localhost:50021/version)
        echo -e "${GREEN}✅ 起動中 (Version: $VERSION)${NC}"
    else
        echo -e "${RED}❌ 停止中${NC}"
    fi

    # Backend
    echo ""
    echo "3. Backend API (Port 55433):"
    if curl -s http://localhost:55433/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 起動中${NC}"
    else
        echo -e "${RED}❌ 停止中${NC}"
    fi

    # Frontend
    echo ""
    echo "4. Frontend (Port 55434):"
    if curl -s http://localhost:55434 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 起動中${NC}"
    else
        echo -e "${RED}❌ 停止中${NC}"
    fi

    echo ""
    echo "======================================================"
}

# すべてのサービスを停止
stop_all() {
    echo "🛑 すべてのサービスを停止中..."
    echo "======================================================"

    # OpenVoice Native Service
    echo ""
    echo "1. OpenVoice Native Serviceを停止..."
    pkill -f "python.*main.py" 2>/dev/null && echo -e "${GREEN}✅ 停止完了${NC}" || echo -e "${YELLOW}⚠️  プロセスが見つかりません${NC}"

    # Backend
    echo ""
    echo "2. Backendを停止..."
    pkill -f "uvicorn.*main:app" 2>/dev/null && echo -e "${GREEN}✅ 停止完了${NC}" || echo -e "${YELLOW}⚠️  プロセスが見つかりません${NC}"

    # Frontend
    echo ""
    echo "3. Frontendを停止..."
    pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✅ 停止完了${NC}" || echo -e "${YELLOW}⚠️  プロセスが見つかりません${NC}"

    # VOICEVOX
    echo ""
    echo "4. VOICEVOXコンテナを停止..."
    docker-compose down 2>/dev/null && echo -e "${GREEN}✅ 停止完了${NC}" || echo -e "${YELLOW}⚠️  コンテナが見つかりません${NC}"

    echo ""
    echo "======================================================"
    echo -e "${GREEN}✅ すべてのサービスを停止しました${NC}"
}

# OpenVoice Native Service起動
start_openvoice() {
    echo ""
    echo "======================================================"
    echo "1/4: OpenVoice Native Service 起動"
    echo "======================================================"

    cd openvoice_native

    # 既存プロセスのチェック
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OpenVoice Native Service は既に起動しています${NC}"
    else
        echo -e "${BLUE}🚀 OpenVoice Native Service を起動中...${NC}"

        # バックグラウンドで起動
        nohup conda run -n openvoice_v2 python main.py > openvoice.log 2>&1 &

        # 起動待機（最大30秒）
        echo -n "起動中"
        for i in {1..30}; do
            sleep 1
            echo -n "."
            if curl -s http://localhost:8001/health > /dev/null 2>&1; then
                echo ""
                echo -e "${GREEN}✅ OpenVoice Native Service 起動完了${NC}"
                break
            fi
            if [ $i -eq 30 ]; then
                echo ""
                echo -e "${RED}❌ OpenVoice Native Service の起動に失敗しました${NC}"
                echo "ログを確認: tail -f openvoice_native/openvoice.log"
            fi
        done
    fi

    cd ..
}

# VOICEVOX起動
start_voicevox() {
    echo ""
    echo "======================================================"
    echo "2/4: VOICEVOX Engine 起動"
    echo "======================================================"

    # Docker Desktop起動確認
    if ! docker ps > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Docker Desktopが起動していません${NC}"
        echo "起動中..."
        open -a Docker
        echo -n "Docker Desktop起動待機中"
        for i in {1..30}; do
            sleep 1
            echo -n "."
            if docker ps > /dev/null 2>&1; then
                echo ""
                echo -e "${GREEN}✅ Docker Desktop 起動完了${NC}"
                break
            fi
        done
    fi

    # VOICEVOXコンテナ起動
    if curl -s http://localhost:50021/version > /dev/null 2>&1; then
        echo -e "${GREEN}✅ VOICEVOX Engine は既に起動しています${NC}"
    else
        echo -e "${BLUE}🚀 VOICEVOX Engine を起動中...${NC}"
        docker-compose up -d voicevox

        # 起動待機（最大20秒）
        echo -n "起動中"
        for i in {1..20}; do
            sleep 1
            echo -n "."
            if curl -s http://localhost:50021/version > /dev/null 2>&1; then
                echo ""
                VERSION=$(curl -s http://localhost:50021/version)
                echo -e "${GREEN}✅ VOICEVOX Engine 起動完了 (Version: $VERSION)${NC}"
                break
            fi
        done
    fi
}

# Backend起動
start_backend() {
    echo ""
    echo "======================================================"
    echo "3/4: Backend API 起動"
    echo "======================================================"

    cd backend

    if curl -s http://localhost:55433/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend API は既に起動しています${NC}"
    else
        echo -e "${BLUE}🚀 Backend API を起動中...${NC}"
        echo ""
        echo "📝 注意: Backend は新しいターミナルウィンドウで起動します"
        echo ""

        # 新しいターミナルウィンドウで起動（macOS）
        osascript -e "tell application \"Terminal\"
            do script \"cd $(pwd) && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 55433 --reload\"
            activate
        end tell"

        echo -e "${GREEN}✅ Backend API 起動コマンド実行完了${NC}"
        echo "   起動には数秒かかります: http://localhost:55433/health"
    fi

    cd ..
}

# Frontend起動
start_frontend() {
    echo ""
    echo "======================================================"
    echo "4/4: Frontend 起動"
    echo "======================================================"

    cd frontend

    if curl -s http://localhost:55434 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend は既に起動しています${NC}"
    else
        echo -e "${BLUE}🚀 Frontend を起動中...${NC}"
        echo ""
        echo "📝 注意: Frontend は新しいターミナルウィンドウで起動します"
        echo ""

        # 新しいターミナルウィンドウで起動（macOS）
        osascript -e "tell application \"Terminal\"
            do script \"cd $(pwd) && npm run dev\"
            activate
        end tell"

        echo -e "${GREEN}✅ Frontend 起動コマンド実行完了${NC}"
        echo "   起動には数秒かかります: http://localhost:55434"
    fi

    cd ..
}

# メイン処理
main() {
    echo "🌸 Athena's Service Orchestrator 🌸"
    echo "======================================================"
    echo ""

    case "${1:-}" in
        --help)
            show_help
            ;;
        --status)
            check_status
            ;;
        --stop)
            stop_all
            ;;
        --openvoice)
            start_openvoice
            ;;
        --voicevox)
            start_voicevox
            ;;
        --backend)
            start_backend
            ;;
        --frontend)
            start_frontend
            ;;
        --all|"")
            echo "すべてのサービスを起動します..."
            start_openvoice
            start_voicevox
            start_backend
            start_frontend

            echo ""
            echo "======================================================"
            echo "🎉 すべてのサービスを起動しました！"
            echo "======================================================"
            echo ""
            echo "アクセスURL:"
            echo "  Frontend:        http://localhost:55434"
            echo "  Backend API:     http://localhost:55433"
            echo "  OpenVoice:       http://localhost:8001"
            echo "  VOICEVOX:        http://localhost:50021"
            echo ""
            echo "稼働確認:"
            echo "  ./start_all_services.sh --status"
            echo ""
            echo "停止:"
            echo "  ./start_all_services.sh --stop"
            echo ""

            # 5秒後にブラウザ自動オープン
            echo -e "${BLUE}5秒後にブラウザを開きます...${NC}"
            sleep 5
            open http://localhost:55434
            ;;
        *)
            echo -e "${RED}❌ 不明なオプション: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
