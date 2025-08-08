#!/bin/bash

# 全フロントエンドエンドポイント修正スクリプト

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER_IP="3.115.141.166"

echo -e "${GREEN}=== フロントエンド全APIエンドポイント修正 ===${NC}"

# 1. コンポーネント内のlocalhostを全て置換
echo -e "${YELLOW}localhost参照を${SERVER_IP}に置換...${NC}"

cd frontend/src/components

# BackgroundProcessor.js
sed -i "s|http://localhost:55433|http://${SERVER_IP}:55433|g" BackgroundProcessor.js
echo "  ✓ BackgroundProcessor.js修正完了"

# VoiceCloneUpload.js
sed -i "s|http://localhost:55433|http://${SERVER_IP}:55433|g" VoiceCloneUpload.js
echo "  ✓ VoiceCloneUpload.js修正完了"

# VoiceVoxSelector.js
sed -i "s|http://localhost:55433|http://${SERVER_IP}:55433|g" VoiceVoxSelector.js
echo "  ✓ VoiceVoxSelector.js修正完了"

# services/api.jsも確認
cd ../services
if [ -f "api.js" ]; then
    sed -i "s|http://localhost:55433|http://${SERVER_IP}:55433|g" api.js
    echo "  ✓ services/api.js修正完了"
fi

cd ../../..

# 2. 録音機能の修正（HTTPS問題の回避策を追加）
echo -e "${YELLOW}録音機能のエラーハンドリングを改善...${NC}"

cat > frontend/src/components/VoiceCloneUpload_patch.js << 'EOF'
// getUserMediaのポリフィルとエラーハンドリング
  const startRecording = async () => {
    try {
      // HTTPSチェック
      if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
        alert('録音機能はHTTPS接続またはlocalhostでのみ利用可能です。\n\n回避策:\n1. 音声ファイルをアップロードしてください\n2. または、Chromeの設定で一時的に非セキュアコンテキストを許可してください');
        setError('録音はHTTPS接続またはlocalhostでのみ利用可能です');
        return;
      }

      // getUserMediaのポリフィル
      const getUserMedia = 
        navigator.mediaDevices?.getUserMedia ||
        navigator.mediaDevices?.webkitGetUserMedia ||
        navigator.mediaDevices?.mozGetUserMedia ||
        navigator.mediaDevices?.msGetUserMedia;

      if (!getUserMedia || !navigator.mediaDevices) {
        throw new Error('お使いのブラウザは録音機能をサポートしていません。音声ファイルをアップロードしてください。');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // 以下既存のコード
EOF

echo -e "${GREEN}パッチファイル作成完了${NC}"

# 3. Dockerコンテナを再ビルド
echo -e "${YELLOW}Dockerコンテナを再ビルド...${NC}"
sudo docker-compose down
sudo docker-compose up -d --build frontend

sleep 10

# 4. 動作確認
echo -e "${YELLOW}動作確認...${NC}"

if curl -f http://localhost:55434 2>/dev/null | grep -q "<title>"; then
    echo -e "${GREEN}✓ Frontend正常起動${NC}"
else
    echo -e "${RED}✗ Frontend起動失敗${NC}"
fi

echo -e "${GREEN}=== 修正完了 ===${NC}"
echo -e "${YELLOW}\n重要な注意事項:${NC}"
echo -e "1. 録音機能はHTTPでは制限されます"
echo -e "2. 音声ファイルのアップロードを代替手段としてご利用ください"
echo -e "3. ブラウザをリロードしてください: http://${SERVER_IP}:55434"