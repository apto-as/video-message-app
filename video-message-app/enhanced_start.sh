#!/bin/bash
# Enhanced Video Message App Startup Script
# Trinitas強化版 - プロセス管理とエラーハンドリングを改善

set -euo pipefail  # エラー時即座に停止

# === 設定 ===
BACKEND_PORT=55433
FRONTEND_PORT=55434
LOG_DIR="./logs/$(date +%Y%m%d_%H%M%S)"
MAX_WAIT_TIME=60
HEALTH_CHECK_INTERVAL=5

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

# === クリーンアップ関数 ===
cleanup() {
    print_color yellow "🧹 システムクリーンアップを実行中..."
    
    # PIDファイルから読み取って終了
    if [[ -f "backend.pid" ]]; then
        BACKEND_PID=$(cat backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            print_color blue "🔄 バックエンドプロセスを終了中 (PID: $BACKEND_PID)"
            kill $BACKEND_PID
            # 子プロセスも終了
            pkill -P $BACKEND_PID 2>/dev/null || true
        fi
        rm -f backend.pid
    fi
    
    if [[ -f "frontend.pid" ]]; then
        FRONTEND_PID=$(cat frontend.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            print_color blue "🔄 フロントエンドプロセスを終了中 (PID: $FRONTEND_PID)"
            kill $FRONTEND_PID
            pkill -P $FRONTEND_PID 2>/dev/null || true
        fi
        rm -f frontend.pid
    fi
    
    # フォールバック: ポート番号による強制終了
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        PID=$(lsof -ti :$port 2>/dev/null || true)
        if [[ -n "$PID" ]]; then
            print_color yellow "⚠️  ポート${port}の強制解放 (PID: $PID)"
            kill -9 $PID 2>/dev/null || true
        fi
    done
    
    print_color green "✅ クリーンアップ完了"
}

# === エラーハンドリング ===
trap cleanup EXIT ERR INT TERM

# === ログディレクトリ準備 ===
mkdir -p "$LOG_DIR"
print_color blue "📁 ログディレクトリ: $LOG_DIR"

# === 既存プロセスのクリーンアップ ===
cleanup

# === 環境チェック ===
print_color blue "🔍 環境チェックを実行中..."

if ! command -v python3 &> /dev/null; then
    print_color red "❌ Python3が見つかりません"
    exit 1
fi

if ! command -v node &> /dev/null; then
    print_color red "❌ Node.jsが見つかりません"
    exit 1
fi

# === バックエンド起動 ===
print_color blue "🚀 バックエンドサーバーを起動中..."
cd backend

# 依存関係チェック
if [[ ! -f "main.py" ]]; then
    print_color red "❌ main.pyが見つかりません"
    exit 1
fi

# Conda環境の有効化
if command -v conda &> /dev/null; then
    print_color blue "🐍 Conda環境を有効化中..."
    source /Users/apto-as/miniforge3/etc/profile.d/conda.sh
    conda activate demo_softel 2>/dev/null || print_color yellow "⚠️  demo_softel環境の有効化に失敗（デフォルト環境を使用）"
fi

# バックエンド起動（詳細ログ付き）
python main.py > "../$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid

print_color green "✅ バックエンド起動 (PID: $BACKEND_PID)"
cd ..

# === バックエンドヘルスチェック ===
print_color blue "🏥 バックエンドのヘルスチェック中..."
for i in $(seq 1 $MAX_WAIT_TIME); do
    if curl -s "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
        print_color green "✅ バックエンドが正常に起動しました"
        break
    fi
    
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_color red "❌ バックエンドプロセスが異常終了しました"
        print_color red "📋 ログを確認してください: $LOG_DIR/backend.log"
        if [[ -f "$LOG_DIR/backend.log" ]]; then
            tail -20 "$LOG_DIR/backend.log"
        else
            print_color red "❌ ログファイルが見つかりません: $LOG_DIR/backend.log"
        fi
        exit 1
    fi
    
    if [[ $i -eq $MAX_WAIT_TIME ]]; then
        print_color red "❌ バックエンドのヘルスチェックがタイムアウトしました"
        exit 1
    fi
    
    sleep 1
done

# === フロントエンド起動 ===
print_color blue "🎨 フロントエンドサーバーを起動中..."
cd frontend

# 依存関係チェック
if [[ ! -f "package.json" ]]; then
    print_color red "❌ package.jsonが見つかりません"
    exit 1
fi

# npmパッケージの確認
if [[ ! -d "node_modules" ]]; then
    print_color yellow "📦 npm依存関係をインストール中..."
    npm install
fi

# フロントエンド起動
PORT=$FRONTEND_PORT npm start > "../$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid

print_color green "✅ フロントエンド起動 (PID: $FRONTEND_PID)"
cd ..

# === フロントエンドヘルスチェック ===
print_color blue "🏥 フロントエンドのヘルスチェック中..."
for i in $(seq 1 $MAX_WAIT_TIME); do
    if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
        print_color green "✅ フロントエンドが正常に起動しました"
        break
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_color red "❌ フロントエンドプロセスが異常終了しました"
        print_color red "📋 ログを確認してください: $LOG_DIR/frontend.log"
        if [[ -f "$LOG_DIR/frontend.log" ]]; then
            tail -20 "$LOG_DIR/frontend.log"
        else
            print_color red "❌ ログファイルが見つかりません: $LOG_DIR/frontend.log"
        fi
        exit 1
    fi
    
    if [[ $i -eq $MAX_WAIT_TIME ]]; then
        print_color red "❌ フロントエンドのヘルスチェックがタイムアウトしました"
        exit 1
    fi
    
    sleep 1
done

# === 統合テスト ===
print_color blue "🧪 統合テストを実行中..."
if curl -s "http://localhost:$BACKEND_PORT/api/" >/dev/null 2>&1; then
    print_color green "✅ APIエンドポイントが正常です"
else
    print_color yellow "⚠️  APIエンドポイントの一部が利用できません（通常動作の可能性）"
fi

# === 起動完了 ===
print_color green "🎉 アプリケーションが正常に起動しました！"
print_color blue "📱 フロントエンド: http://localhost:$FRONTEND_PORT"
print_color blue "🔧 バックエンド API: http://localhost:$BACKEND_PORT"
print_color blue "📋 ログディレクトリ: $LOG_DIR"

# === 継続監視モード ===
print_color blue "👁️  プロセス監視を開始します（Ctrl+Cで終了）"

while true; do
    # バックエンドチェック
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_color red "❌ バックエンドプロセスが停止しました"
        break
    fi
    
    # フロントエンドチェック
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_color red "❌ フロントエンドプロセスが停止しました"
        break
    fi
    
    # ヘルスチェック
    if ! curl -s "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
        print_color yellow "⚠️  バックエンドのヘルスチェックに失敗"
    fi
    
    sleep $HEALTH_CHECK_INTERVAL
done

print_color red "🛑 プロセス監視を終了します"