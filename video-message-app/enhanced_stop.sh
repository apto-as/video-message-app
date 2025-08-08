#!/bin/bash
# Enhanced Video Message App Stop Script
# Trinitas強化版 - 確実なプロセス終了を保証

set -euo pipefail

# === 設定 ===
BACKEND_PORT=55433
FRONTEND_PORT=55434
GRACE_PERIOD=5  # 正常終了の猶予期間（秒）

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
        *)      echo "[$timestamp] $message" ;;
    esac
}

# === プロセス終了関数 ===
stop_process_gracefully() {
    local pid=$1
    local name=$2
    
    if kill -0 $pid 2>/dev/null; then
        print_color blue "🔄 ${name}を正常終了中 (PID: $pid)"
        
        # 正常終了シグナル送信
        kill -TERM $pid
        
        # 猶予期間待機
        local count=0
        while kill -0 $pid 2>/dev/null && [ $count -lt $GRACE_PERIOD ]; do
            sleep 1
            ((count++))
        done
        
        # まだ生きている場合は強制終了
        if kill -0 $pid 2>/dev/null; then
            print_color yellow "⚠️  ${name}の強制終了を実行 (PID: $pid)"
            kill -KILL $pid
            
            # 子プロセスも強制終了
            pkill -P $pid 2>/dev/null || true
        fi
        
        # 終了確認
        if ! kill -0 $pid 2>/dev/null; then
            print_color green "✅ ${name}を正常に終了しました"
        else
            print_color red "❌ ${name}の終了に失敗しました"
            return 1
        fi
    else
        print_color yellow "⚠️  ${name}は既に終了しています"
    fi
}

# === ポート番号による強制終了 ===
stop_by_port() {
    local port=$1
    local name=$2
    
    local pids=$(lsof -ti :$port 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        print_color blue "🔄 ポート${port}のプロセスを終了中"
        for pid in $pids; do
            stop_process_gracefully $pid "${name}(port:$port)"
        done
    else
        print_color green "✅ ポート${port}は既に解放されています"
    fi
}

print_color blue "🛑 動画メッセージアプリを終了中..."

# === PIDファイルによる終了 ===
if [[ -f "backend.pid" ]]; then
    BACKEND_PID=$(cat backend.pid)
    stop_process_gracefully $BACKEND_PID "バックエンドサーバー"
    rm -f backend.pid
else
    print_color yellow "⚠️  backend.pidが見つかりません"
fi

if [[ -f "frontend.pid" ]]; then
    FRONTEND_PID=$(cat frontend.pid)
    stop_process_gracefully $FRONTEND_PID "フロントエンドサーバー"
    rm -f frontend.pid
else
    print_color yellow "⚠️  frontend.pidが見つかりません"
fi

# === フォールバック: ポート番号による終了 ===
print_color blue "🔍 ポート使用状況の最終確認..."
stop_by_port $BACKEND_PORT "バックエンド"
stop_by_port $FRONTEND_PORT "フロントエンド"

# === パターンマッチングによるフォールバック ===
print_color blue "🔍 残存プロセスの確認..."

# より厳密なパターンでプロセス検索
REMAINING_BACKEND=$(pgrep -f "python.*main\.py.*$BACKEND_PORT" || true)
if [[ -n "$REMAINING_BACKEND" ]]; then
    print_color yellow "⚠️  残存バックエンドプロセスを発見: $REMAINING_BACKEND"
    for pid in $REMAINING_BACKEND; do
        stop_process_gracefully $pid "残存バックエンド"
    done
fi

REMAINING_FRONTEND=$(pgrep -f "node.*react-scripts.*start.*$FRONTEND_PORT" || true)
if [[ -n "$REMAINING_FRONTEND" ]]; then
    print_color yellow "⚠️  残存フロントエンドプロセスを発見: $REMAINING_FRONTEND"
    for pid in $REMAINING_FRONTEND; do
        stop_process_gracefully $pid "残存フロントエンド"
    done
fi

# === 最終確認 ===
print_color blue "🔍 最終ポート確認..."
if lsof -i :$BACKEND_PORT >/dev/null 2>&1; then
    print_color red "❌ ポート${BACKEND_PORT}がまだ使用されています"
    lsof -i :$BACKEND_PORT
else
    print_color green "✅ ポート${BACKEND_PORT}は解放されました"
fi

if lsof -i :$FRONTEND_PORT >/dev/null 2>&1; then
    print_color red "❌ ポート${FRONTEND_PORT}がまだ使用されています"
    lsof -i :$FRONTEND_PORT
else
    print_color green "✅ ポート${FRONTEND_PORT}は解放されました"
fi

# === 一時ファイルのクリーンアップ ===
print_color blue "🧹 一時ファイルをクリーンアップ中..."
rm -f *.pid 2>/dev/null || true

print_color green "🎉 アプリケーションを正常に終了しました"
print_color blue "📋 ログファイルは保持されています"