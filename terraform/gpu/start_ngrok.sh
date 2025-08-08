#!/bin/bash

# ngrok起動スクリプト

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== ngrok HTTPSトンネル起動 ===${NC}"

# ngrokプロセスが既に実行中か確認
if pgrep -x "ngrok" > /dev/null; then
    echo -e "${YELLOW}ngrokは既に実行中です。停止します...${NC}"
    pkill ngrok
    sleep 2
fi

# ngrokをバックグラウンドで起動
echo -e "${YELLOW}ngrokをバックグラウンドで起動中...${NC}"
nohup ./ngrok http 55434 > ngrok.log 2>&1 &

# ngrokが起動するまで待機
echo -e "${YELLOW}ngrokの起動を待っています...${NC}"
sleep 5

# ngrok URLを取得
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}ngrok URLの取得に失敗しました${NC}"
    echo -e "${YELLOW}ngrok.logを確認してください:${NC}"
    tail -20 ngrok.log
    exit 1
fi

echo -e "${GREEN}\n=== ngrok起動成功！ ===${NC}"
echo -e "${BLUE}\nHTTPS URL: $NGROK_URL${NC}"
echo -e "${GREEN}\nこのURLでアプリケーションにアクセスできます。${NC}"
echo -e "${YELLOW}\n注意事項:${NC}"
echo -e "  1. このURLはngrokを再起動するたびに変わります"
echo -e "  2. 録音機能が使用可能になりました"
echo -e "  3. ngrokを停止するには: pkill ngrok"
echo -e "  4. ログを確認するには: tail -f ngrok.log"

# URLをファイルに保存
echo "$NGROK_URL" > ~/current_ngrok_url.txt
echo -e "${GREEN}\nURLが ~/current_ngrok_url.txt に保存されました${NC}"

# フロントエンド環境変数を更新するか確認
echo -e "${YELLOW}\nフロントエンドをngrok URLに更新しますか？ (y/n)${NC}"
read -p "> " update_frontend

if [ "$update_frontend" = "y" ]; then
    echo -e "${YELLOW}フロントエンド環境変数を更新中...${NC}"
    
    # API URLをngrok URLに変更
    cd ~/video-message-app/video-message-app
    
    # フロントエンドコンポーネントを更新
    cd frontend/src/components
    
    # 全ての3.115.141.166参照をngrok URLに置換
    NGROK_DOMAIN=$(echo $NGROK_URL | sed 's|https://||')
    
    sed -i "s|http://3.115.141.166:55433|$NGROK_URL|g" *.js
    sed -i "s|https://3.115.141.166:55433|$NGROK_URL|g" *.js
    
    # servicesディレクトリも更新
    cd ../services
    if [ -f "api.js" ]; then
        sed -i "s|http://3.115.141.166:55433|$NGROK_URL|g" api.js
        sed -i "s|https://3.115.141.166:55433|$NGROK_URL|g" api.js
    fi
    
    cd ~/video-message-app/video-message-app
    
    # Dockerコンテナ再ビルド
    echo -e "${YELLOW}Dockerコンテナを再ビルド中...${NC}"
    sudo docker-compose down
    sudo docker-compose up -d --build frontend
    
    echo -e "${GREEN}\nフロントエンド更新完了！${NC}"
    echo -e "${BLUE}\nアクセスURL: $NGROK_URL${NC}"
else
    echo -e "${YELLOW}\nフロントエンドは更新しませんでした。${NC}"
    echo -e "${YELLOW}APIエンドポイントは引き続きEC2のIPを使用します。${NC}"
fi

echo -e "${GREEN}\n=== セットアップ完了 ===${NC}"