#!/bin/bash
# 動画メッセージアプリ 終了スクリプト

echo "🛑 動画メッセージアプリを終了しています..."

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

# バックエンドプロセスを終了
print_color blue "🔄 バックエンドサーバーを終了中..."
pkill -f "uvicorn main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    print_color green "✅ バックエンドサーバーを終了しました"
else
    print_color yellow "⚠️  バックエンドサーバーは既に終了しています"
fi

# フロントエンドプロセスを終了
print_color blue "🔄 フロントエンドサーバーを終了中..."
# React開発サーバー (react-scripts) を終了
pkill -f "react-scripts/scripts/start.js" 2>/dev/null
REACT_KILL_STATUS=$?

# npm startプロセスも終了
pkill -f "npm start" 2>/dev/null
NPM_KILL_STATUS=$?

if [ $REACT_KILL_STATUS -eq 0 ] || [ $NPM_KILL_STATUS -eq 0 ]; then
    print_color green "✅ フロントエンドサーバーを終了しました"
else
    print_color yellow "⚠️  フロントエンドサーバーは既に終了しています"
fi

# ポート確認
print_color blue "🔍 ポート使用状況を確認中..."
if lsof -i :55433 >/dev/null 2>&1; then
    print_color yellow "⚠️  ポート55433がまだ使用されています"
    lsof -i :55433
else
    print_color green "✅ ポート55433は解放されました"
fi

if lsof -i :55434 >/dev/null 2>&1; then
    print_color yellow "⚠️  ポート55434がまだ使用されています"
    lsof -i :55434
else
    print_color green "✅ ポート55434は解放されました"
fi

print_color green "👋 アプリケーションを正常に終了しました"