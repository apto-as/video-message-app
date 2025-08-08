#!/bin/bash
# Docker Compose Video Message App Stop Script
# OpenVoice V2 + VOICEVOX + D-ID ハイブリッドシステム対応

set -euo pipefail

# === 設定 ===
BACKEND_PORT=55433
FRONTEND_PORT=55434
VOICEVOX_PORT=50021
GRACE_PERIOD=10

# === 色付きメッセージ ===
print_color() {
    local color=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case $color in
        red)    echo -e "[$timestamp] \033[31m$message\033[0m" ;;
        green)  echo -e "[$timestamp] \033[32m$message\033[0m" ;;
        yellow) echo -e "[$timestamp] \033[33m$message\033[0m" ;;
        blue)   echo -e "[$timestamp] \033[34m$message\033[0m" ;;
        purple) echo -e "[$timestamp] \033[35m$message\033[0m" ;;
        *)      echo "[$timestamp] $message" ;;
    esac
}

print_color blue "🛑 ビデオメッセージアプリを停止中..."

# === Docker Composeチェック ===
if ! command -v docker-compose &> /dev/null; then
    print_color red "❌ Docker Composeが見つかりません"
    exit 1
fi

# === 現在の状態確認 ===
print_color blue "📊 現在のコンテナ状態:"
if docker-compose ps 2>/dev/null; then
    CONTAINERS_RUNNING=true
else
    CONTAINERS_RUNNING=false
    print_color yellow "⚠️  docker-composeプロジェクトが見つかりません"
fi

if [[ "$CONTAINERS_RUNNING" == "true" ]]; then
    # === 正常停止の試行 ===
    print_color blue "🔄 コンテナを正常停止中..."
    if docker-compose stop --timeout $GRACE_PERIOD; then
        print_color green "✅ 全コンテナが正常に停止しました"
    else
        print_color yellow "⚠️  一部のコンテナの正常停止に失敗しました"
    fi
    
    # === コンテナとネットワークの削除 ===
    print_color blue "🗑️  コンテナとネットワークを削除中..."
    if docker-compose down --remove-orphans; then
        print_color green "✅ コンテナとネットワークを削除しました"
    else
        print_color yellow "⚠️  一部のリソース削除に失敗しました"
    fi
    
    # === ボリュームの確認 ===
    print_color blue "💾 ボリューム情報:"
    docker volume ls | grep video-message-app || print_color blue "   ボリュームが見つかりません"
    
    read -p "永続ボリューム（VOICEVOX データなど）も削除しますか？ (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if docker-compose down --volumes; then
            print_color green "✅ ボリュームを削除しました"
        else
            print_color yellow "⚠️  ボリューム削除に失敗しました"
        fi
    else
        print_color blue "💾 ボリュームは保持されました"
    fi
fi

# === ポート解放確認 ===
print_color blue "🔍 ポート使用状況の最終確認..."

check_port() {
    local port=$1
    local name=$2
    
    if lsof -i :$port >/dev/null 2>&1; then
        print_color yellow "⚠️  ポート${port}(${name})がまだ使用されています"
        print_color blue "📋 使用プロセス:"
        lsof -i :$port
        
        read -p "このポートを強制解放しますか？ (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local pids=$(lsof -ti :$port)
            for pid in $pids; do
                print_color blue "🔄 プロセス $pid を終了中..."
                kill -TERM $pid 2>/dev/null || true
                sleep 2
                if kill -0 $pid 2>/dev/null; then
                    print_color yellow "⚠️  プロセス $pid を強制終了中..."
                    kill -KILL $pid 2>/dev/null || true
                fi
            done
            print_color green "✅ ポート${port}を解放しました"
        fi
    else
        print_color green "✅ ポート${port}(${name})は解放されています"
    fi
}

check_port $VOICEVOX_PORT "VOICEVOX"
check_port $BACKEND_PORT "Backend API"
check_port $FRONTEND_PORT "Frontend WebUI"

# === 孤立Dockerリソースの確認 ===
print_color blue "🔍 孤立したDockerリソースを確認中..."

# 停止中のコンテナ
STOPPED_CONTAINERS=$(docker ps -a --filter "status=exited" --format "table {{.Names}}\t{{.Status}}" | grep -E "(voice_|voicevox)" || true)
if [[ -n "$STOPPED_CONTAINERS" ]]; then
    print_color yellow "⚠️  停止中の関連コンテナが見つかりました:"
    echo "$STOPPED_CONTAINERS"
    
    read -p "これらのコンテナを削除しますか？ (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker ps -a --filter "status=exited" --format "{{.Names}}" | grep -E "(voice_|voicevox)" | xargs -r docker rm
        print_color green "✅ 停止中のコンテナを削除しました"
    fi
fi

# 未使用のイメージ
read -p "未使用のDockerイメージを削除しますか？ (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_color blue "🗑️  未使用イメージを削除中..."
    docker image prune -f
    print_color green "✅ 未使用イメージを削除しました"
fi

# === システムリソース確認 ===
print_color blue "📊 システムリソース使用状況:"
echo "🐳 Docker システム情報:"
docker system df 2>/dev/null || print_color yellow "   Docker情報の取得に失敗"

# === 一時ファイルのクリーンアップ ===
print_color blue "🧹 一時ファイルをクリーンアップ中..."

# ログファイル整理
if [[ -d "logs" ]]; then
    LOG_COUNT=$(find logs -name "*.log" | wc -l)
    if [[ $LOG_COUNT -gt 0 ]]; then
        print_color blue "📋 $LOG_COUNT 個のログファイルが見つかりました"
        read -p "古いログファイル（7日以上）を削除しますか？ (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
            print_color green "✅ 古いログファイルを削除しました"
        fi
    fi
fi

# PIDファイル削除
rm -f *.pid 2>/dev/null || true

# === 完了通知 ===
print_color green "🎉 ビデオメッセージアプリを正常に停止しました"
echo ""
print_color blue "┌─────────────────────────────────────────────┐"
print_color blue "│               📊 停止完了情報 📊               │"
print_color blue "├─────────────────────────────────────────────┤"
print_color blue "│  🛑 全サービス停止完了                         │"
print_color blue "│  🔓 全ポート解放完了                          │"
print_color blue "│  🧹 一時ファイル削除完了                       │"
print_color blue "└─────────────────────────────────────────────┘"
echo ""
print_color purple "🔄 再起動する場合:"
print_color purple "   ./docker-start.sh"
echo ""
print_color blue "📋 ログ確認（停止後）:"
print_color blue "   docker-compose logs [service]"
echo ""
print_color green "✅ 停止処理が完了しました。お疲れさまでした！"