#!/bin/bash
# 統合停止スクリプト - OpenVoice Native + Docker Services

# set -e を削除（エラーがあっても停止処理を継続）

# 色付き出力用の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# スクリプトのディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${YELLOW}🛑 Video Message App 統合停止開始${NC}"
echo "================================================"

# 1. Docker サービスの停止
echo -e "\n${YELLOW}[1/3] Docker サービス停止${NC}"
echo "🐳 Docker サービスを停止します..."

if [ -f "docker-compose.yml" ]; then
    # 明示的にタイムアウトを設定してDocker停止を実行
    echo "🐳 Dockerコンテナを30秒タイムアウトで停止中..."
    docker-compose down --timeout 30
    
    # まだ動いているコンテナがある場合は強制停止
    REMAINING_CONTAINERS=$(docker ps -q)
    if [ ! -z "$REMAINING_CONTAINERS" ]; then
        echo "⚡ 残りのコンテナを強制停止中..."
        docker kill $REMAINING_CONTAINERS 2>/dev/null || true
        docker rm $REMAINING_CONTAINERS 2>/dev/null || true
    fi
    
    # Docker停止の完了を待つ
    sleep 3
    echo -e "${GREEN}✅ Docker サービス停止完了${NC}"
else
    echo -e "${RED}❌ docker-compose.yml が見つかりません${NC}"
fi

# 2. ローカル VOICEVOX アプリケーションの停止
echo -e "\n${YELLOW}[2/3] ローカル VOICEVOX アプリケーション停止${NC}"

# ローカルVOICEVOXアプリのプロセスを検索
VOICEVOX_PIDS=$(ps -ef | grep -E '(VOICEVOX\.app|vv-engine)' | grep -v grep | awk '{print $2}' | head -10)

if [ ! -z "$VOICEVOX_PIDS" ]; then
    echo "🗣️ ローカル VOICEVOX アプリケーションを停止します..."
    for pid in $VOICEVOX_PIDS; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "  VOICEVOX プロセス $pid を停止中..."
            kill $pid 2>/dev/null || true
        fi
    done
    
    sleep 3
    
    # まだ動いているプロセスを強制終了
    REMAINING_VOICEVOX=$(ps -ef | grep -E '(VOICEVOX\.app|vv-engine)' | grep -v grep | awk '{print $2}' | head -10)
    if [ ! -z "$REMAINING_VOICEVOX" ]; then
        echo "⚡ 残りの VOICEVOX プロセスを強制終了します..."
        for pid in $REMAINING_VOICEVOX; do
            kill -9 $pid 2>/dev/null || true
        done
    fi
    
    sleep 1
    if ! ps -ef | grep -E '(VOICEVOX\.app|vv-engine)' | grep -v grep > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ローカル VOICEVOX アプリケーション停止完了${NC}"
    else
        echo -e "${YELLOW}⚠️  一部の VOICEVOX プロセスが残っている可能性があります${NC}"
    fi
else
    echo -e "${GREEN}✅ ローカル VOICEVOX アプリケーションは動作していません${NC}"
fi

# 3. OpenVoice Native Service の停止
echo -e "\n${YELLOW}[3/3] OpenVoice Native Service 停止${NC}"

# プロセスIDファイルから停止
PID_FILE="$SCRIPT_DIR/.openvoice_pid"
if [ -f "$PID_FILE" ]; then
    OPENVOICE_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ ! -z "$OPENVOICE_PID" ] && ps -p $OPENVOICE_PID > /dev/null 2>&1; then
        echo "🎵 OpenVoice Native Service を停止します (PID: $OPENVOICE_PID)..."
        kill $OPENVOICE_PID 2>/dev/null || true
        sleep 3
        
        # まだ動いている場合は強制終了
        if ps -p $OPENVOICE_PID > /dev/null 2>&1; then
            echo "⚡ 強制終了します..."
            kill -9 $OPENVOICE_PID 2>/dev/null || true
        fi
        
        # 停止確認
        sleep 1
        if ! ps -p $OPENVOICE_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✅ OpenVoice Native Service 停止完了${NC}"
        else
            echo -e "${RED}⚠️  プロセス停止に失敗した可能性があります${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  プロセス $OPENVOICE_PID は既に停止しています${NC}"
    fi
    
    # PIDファイル削除
    rm -f "$PID_FILE"
else
    # PIDファイルがない場合は、ポートで検索して停止
    echo "🔍 OpenVoice Native Service をポートで検索..."
    
    if lsof -i :8001 > /dev/null 2>&1; then
        OPENVOICE_PIDS=$(lsof -ti :8001)
        echo "🎵 OpenVoice Native Service を停止します (Port 8001, PIDs: $OPENVOICE_PIDS)..."
        
        # 全てのプロセスを停止
        for pid in $OPENVOICE_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                echo "  プロセス $pid を停止中..."
                kill $pid 2>/dev/null || true
            fi
        done
        
        sleep 3
        
        # まだ動いているプロセスを強制終了
        REMAINING_PIDS=$(lsof -ti :8001 2>/dev/null || true)
        if [ ! -z "$REMAINING_PIDS" ]; then
            echo "⚡ 残りのプロセスを強制終了します..."
            for pid in $REMAINING_PIDS; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
        
        sleep 1
        if ! lsof -i :8001 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ OpenVoice Native Service 停止完了${NC}"
        else
            echo -e "${RED}⚠️  OpenVoice Native Service の停止に失敗した可能性があります${NC}"
        fi
    else
        echo -e "${GREEN}✅ OpenVoice Native Service は既に停止しています${NC}"
    fi
fi

# 4. 停止状態の確認（待機時間を追加）
echo -e "\n${YELLOW}[確認] サービス停止状態 - 3秒待機後に確認${NC}"
sleep 3

echo ""
echo "サービス状態:"
echo "============="

# 各ポートの状態を確認
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "$service ${RED}⚠️  まだ稼働中${NC} (Port $port)"
        # 稼働中のプロセス詳細を表示
        lsof -i :$port | head -2
    else
        echo -e "$service ${GREEN}✅ 停止${NC}"
    fi
}

check_port 8001 "🎵 OpenVoice Native: "
check_port 55433 "🔧 Backend:          "
check_port 55434 "🎨 Frontend:         "
check_port 50021 "🗣️  VoiceVox:         "

echo ""
echo "================================================"
echo -e "${GREEN}🎉 停止完了！${NC}"
echo ""
echo "💡 再起動方法: ./start_all.sh"
echo ""

# プロセス確認（修正版）
REMAINING_8001=$(lsof -i :8001 2>/dev/null | wc -l)
REMAINING_55433=$(lsof -i :55433 2>/dev/null | wc -l)
REMAINING_55434=$(lsof -i :55434 2>/dev/null | wc -l)
REMAINING_50021=$(lsof -i :50021 2>/dev/null | wc -l)

TOTAL_REMAINING=$((REMAINING_8001 + REMAINING_55433 + REMAINING_55434 + REMAINING_50021))

if [ "$TOTAL_REMAINING" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  一部のプロセスがまだ動作している可能性があります${NC}"
    echo "詳細確認コマンド:"
    echo "  lsof -i :8001    # OpenVoice"
    echo "  lsof -i :55433   # Backend"
    echo "  lsof -i :55434   # Frontend"
    echo "  lsof -i :50021   # VoiceVox"
fi