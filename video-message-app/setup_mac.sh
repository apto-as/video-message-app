#!/bin/bash

# Mac環境用 VOICEVOX統合システム セットアップスクリプト
# Phase 1: VOICEVOX + OpenVoice V2 統合環境構築

set -e

echo "🍎 Mac環境用 VOICEVOX統合システム セットアップ開始"
echo "=================================================="

# システム要件チェック
echo "📋 システム要件をチェック中..."

# Homebrewの確認
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrewが見つかりません。まずHomebrewをインストールしてください。"
    echo "インストールコマンド: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Dockerの確認
if ! command -v docker &> /dev/null; then
    echo "❌ Dockerが見つかりません。Docker Desktopをインストールしてください。"
    echo "ダウンロード: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Docker Composeの確認
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Composeが見つかりません。Docker Desktopに含まれているか確認してください。"
    exit 1
fi

# FFmpegの確認とインストール
if ! command -v ffmpeg &> /dev/null; then
    echo "📦 FFmpegをインストール中..."
    brew install ffmpeg
fi

# Node.jsの確認
if ! command -v node &> /dev/null; then
    echo "📦 Node.jsをインストール中..."
    brew install node
fi

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "📦 Python3をインストール中..."
    brew install python3
fi

echo "✅ システム要件チェック完了"

# プロジェクトディレクトリの確認
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.ymlが見つかりません。プロジェクトルートディレクトリで実行してください。"
    exit 1
fi

# 環境変数ファイルの設定
echo "⚙️ 環境変数を設定中..."

if [ ! -f ".env" ]; then
    cat > .env << EOL
# Mac環境用設定
DID_API_KEY=your_did_api_key_here
VOICEVOX_BASE_URL=http://localhost:50021
OPENVOICE_API_URL=http://localhost:8001
TORCH_DEVICE=cpu
OMP_NUM_THREADS=2
MKL_NUM_THREADS=2

# フロントエンド設定
REACT_APP_API_BASE_URL=http://localhost:8000
EOL
    echo "📝 .envファイルを作成しました。必要に応じてD-ID APIキーを設定してください。"
else
    echo "✅ 既存の.envファイルを使用します"
fi

# Docker イメージのビルド
echo "🐳 Dockerイメージをビルド中..."
docker-compose build --no-cache

# VOICEVOXコンテナの準備
echo "🎤 VOICEVOXコンテナを準備中..."
docker-compose pull voicevox

# バックエンド依存関係のインストール（ローカル開発用）
echo "🐍 バックエンド依存関係をインストール中..."
cd backend

# 仮想環境の作成
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 仮想環境の有効化
source venv/bin/activate

# Mac環境用のPyTorchインストール
echo "🔧 Mac環境用PyTorchをインストール中..."
if [[ $(uname -m) == "arm64" ]]; then
    # Apple Silicon (M1/M2)
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
else
    # Intel Mac
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# その他の依存関係
pip install -r requirements.txt

cd ..

# フロントエンド依存関係のインストール
echo "⚛️ フロントエンド依存関係をインストール中..."
cd frontend
npm install
cd ..

# ストレージディレクトリの作成
echo "📁 ストレージディレクトリを作成中..."
mkdir -p backend/storage/voices
mkdir -p backend/storage/openvoice
mkdir -p backend/storage/voice_clones

# 権限設定
chmod 755 backend/storage/voices
chmod 755 backend/storage/openvoice
chmod 755 backend/storage/voice_clones

echo ""
echo "🎉 Mac環境用セットアップ完了！"
echo "=================================================="
echo ""
echo "🚀 起動方法:"
echo "1. すべてのサービス: ./start_mac.sh"
echo "2. VOICEVOXのみ: docker-compose up voicevox"
echo "3. バックエンドのみ: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "4. フロントエンドのみ: cd frontend && npm start"
echo ""
echo "🌐 アクセスURL:"
echo "- フロントエンド: http://localhost:3000"
echo "- バックエンドAPI: http://localhost:8000"
echo "- VOICEVOX API: http://localhost:50021"
echo ""
echo "📝 注意事項:"
echo "- D-ID APIを使用する場合は .env ファイルでAPIキーを設定してください"
echo "- OpenVoice機能はMac環境では制限があります"
echo "- 初回起動時はDockerイメージのダウンロードに時間がかかる場合があります"
echo ""

# 起動確認
read -p "今すぐシステムを起動しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 システムを起動中..."
    exec ./start_mac.sh
fi

echo "✅ セットアップ完了。後で ./start_mac.sh で起動してください。"