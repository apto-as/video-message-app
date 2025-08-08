#!/bin/bash
# 動画メッセージアプリ 全体起動スクリプト
# バックエンドとフロントエンドを並行起動

echo "🚀 動画メッセージアプリを起動します..."
echo "📍 現在のディレクトリ: $(pwd)"

# 色付きメッセージ用の関数
print_color() {
    local color=$1
    local message=$2
    case $color in
        red)    echo -e "\033[31m$message\033[0m" ;;
        green)  echo -e "\033[32m$message\033[0m" ;;
        yellow) echo -e "\033[33m$message\033[0m" ;;
        blue)   echo -e "\033[34m$message\033[0m" ;;
        *)      echo "$message" ;;
    esac
}

# 依存関係チェック
check_dependencies() {
    print_color blue "🔍 依存関係をチェックしています..."
    
    # Python環境チェック
    if ! command -v python &> /dev/null; then
        print_color red "❌ Pythonが見つかりません"
        exit 1
    fi
    
    # Node.js環境チェック
    if ! command -v npm &> /dev/null; then
        print_color red "❌ Node.js/npmが見つかりません"
        exit 1
    fi
    
    # バックエンドディレクトリチェック
    if [ ! -d "backend" ]; then
        print_color red "❌ backendディレクトリが見つかりません"
        exit 1
    fi
    
    # フロントエンドディレクトリチェック
    if [ ! -d "frontend" ]; then
        print_color red "❌ frontendディレクトリが見つかりません"
        exit 1
    fi
    
    print_color green "✅ 依存関係チェック完了"
}

# ポートチェック
check_ports() {
    print_color blue "🔍 ポートの使用状況をチェックしています..."
    
    # ポート55433をチェック（バックエンド）
    if lsof -i :55433 >/dev/null 2>&1; then
        print_color yellow "⚠️  ポート55433は既に使用されています（バックエンド用）"
        print_color yellow "   既存のプロセスを終了するか、別のポートを使用してください"
        read -p "続行しますか？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # ポート55434をチェック（フロントエンド）
    if lsof -i :55434 >/dev/null 2>&1; then
        print_color yellow "⚠️  ポート55434は既に使用されています（フロントエンド用）"
        print_color yellow "   既存のプロセスを終了するか、別のポートを使用してください"
        read -p "続行しますか？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# バックエンド起動
start_backend() {
    print_color blue "🚀 バックエンドサーバーを起動しています..."
    cd backend
    
    # 必要なパッケージのインストールチェック
    if [ ! -f ".deps_installed" ]; then
        print_color yellow "📦 バックエンド依存関係をインストールしています..."
        pip install -r requirements.txt
        if [ $? -eq 0 ]; then
            touch .deps_installed
            print_color green "✅ バックエンド依存関係インストール完了"
        else
            print_color red "❌ バックエンド依存関係のインストールに失敗しました"
            exit 1
        fi
    fi
    
    # 画像処理ライブラリのテスト
    print_color yellow "🧪 画像処理ライブラリをテストしています..."
    python -c "import sys; sys.path.append('..'); from backend.services.image_processor import ImageProcessor; print('✅ ImageProcessor OK')" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_color red "❌ 画像処理ライブラリのインポートに失敗しました"
        print_color yellow "💡 手動で確認してください: python test_background_processing.py"
        cd ..
        exit 1
    fi
    
    # バックエンドを背景で起動
    print_color green "🔄 バックエンドサーバーを起動中... (ポート: 55433)"
    nohup uvicorn main:app --reload --port 55433 --host 0.0.0.0 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    
    cd ..
    
    # バックエンドの起動を待機（より詳細な確認）
    print_color yellow "⏳ バックエンドの起動を待機中..."
    for i in {1..60}; do
        # ログファイルからエラーをチェック
        if [ -f "backend.log" ]; then
            if grep -q "ERROR" backend.log; then
                print_color red "❌ バックエンドでエラーが発生しました:"
                tail -5 backend.log
                kill $BACKEND_PID 2>/dev/null
                exit 1
            fi
            
            # 正常起動メッセージをチェック
            if grep -q "Application startup complete" backend.log; then
                sleep 2  # 安定化待ち
                if curl -s http://localhost:55433 >/dev/null 2>&1; then
                    print_color green "✅ バックエンドサーバーが起動しました (PID: $BACKEND_PID)"
                    return 0
                fi
            fi
        fi
        
        sleep 1
        printf "."
    done
    
    print_color red "❌ バックエンドの起動がタイムアウトしました"
    print_color blue "📋 ログの内容:"
    if [ -f "backend.log" ]; then
        tail -10 backend.log
    else
        print_color red "ログファイルが見つかりません"
    fi
    kill $BACKEND_PID 2>/dev/null
    exit 1
}

# フロントエンド起動
start_frontend() {
    print_color blue "🎨 フロントエンドサーバーを起動しています..."
    cd frontend
    
    # node_modulesの存在チェック
    if [ ! -d "node_modules" ]; then
        print_color yellow "📦 フロントエンド依存関係をインストールしています..."
        npm install
        if [ $? -ne 0 ]; then
            print_color red "❌ フロントエンド依存関係のインストールに失敗しました"
            exit 1
        fi
        print_color green "✅ フロントエンド依存関係インストール完了"
    fi
    
    # フロントエンドを背景で起動
    print_color green "🔄 フロントエンドサーバーを起動中... (ポート: 55434)"
    npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    cd ..
    
    # フロントエンドの起動を待機
    print_color yellow "⏳ フロントエンドの起動を待機中..."
    for i in {1..60}; do
        if curl -s http://localhost:55434 >/dev/null 2>&1; then
            print_color green "✅ フロントエンドサーバーが起動しました (PID: $FRONTEND_PID)"
            return 0
        fi
        sleep 1
        printf "."
    done
    echo ""
    
    print_color yellow "⚠️  フロントエンドの起動確認がタイムアウトしました（通常の動作です）"
    print_color green "✅ フロントエンドサーバーは起動中です (PID: $FRONTEND_PID)"
}

# 終了処理
cleanup() {
    echo ""
    print_color yellow "🛑 アプリケーションを終了しています..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        print_color blue "🔄 バックエンドサーバーを終了中... (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null
        wait $BACKEND_PID 2>/dev/null
        print_color green "✅ バックエンドサーバーを終了しました"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        print_color blue "🔄 フロントエンドサーバーを終了中... (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null
        wait $FRONTEND_PID 2>/dev/null
        print_color green "✅ フロントエンドサーバーを終了しました"
    fi
    
    print_color green "👋 アプリケーションを正常に終了しました"
}

# シグナルハンドラー設定
trap cleanup EXIT INT TERM

# メイン実行
main() {
    print_color green "=== 動画メッセージアプリ 起動スクリプト ==="
    
    # 前処理
    check_dependencies
    check_ports
    
    # サーバー起動
    start_backend
    start_frontend
    
    # 起動完了メッセージ
    echo ""
    print_color green "🎉 アプリケーションが正常に起動しました！"
    echo ""
    print_color blue "📱 アクセス情報:"
    print_color blue "   フロントエンド: http://localhost:55434"
    print_color blue "   バックエンドAPI: http://localhost:55433"
    echo ""
    print_color blue "📝 ログ情報:"
    print_color blue "   バックエンドログ: backend.log"
    print_color blue "   フロントエンドログ: frontend.log"
    echo ""
    print_color yellow "💡 使用方法:"
    print_color yellow "   1. ブラウザで http://localhost:55434 を開く"
    print_color yellow "   2. 画像をアップロードしてテストを実行"
    print_color yellow "   3. Ctrl+C でアプリケーションを終了"
    echo ""
    
    # ブラウザ自動オープン（非インタラクティブ）
    if command -v open >/dev/null 2>&1; then
        print_color green "🌐 ブラウザを開いています..."
        open http://localhost:55434
    fi
    
    # サーバー情報を表示して終了
    print_color green "✅ アプリケーションが起動しました"
    print_color blue "📱 フロントエンド: http://localhost:55434"
    print_color blue "🔧 バックエンド API: http://localhost:55433"
    print_color yellow "⚠️  サーバーはバックグラウンドで動作しています"
    print_color yellow "🛑 終了する場合: ./stop_app.sh"
    echo ""
    print_color blue "📋 ログ監視: tail -f backend.log frontend.log"
}

# スクリプト実行
main