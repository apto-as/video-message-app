#!/bin/bash
# ========================================
# Prerequisites Checker
# Athena's Harmonious Setup Assistant
# ========================================

set -e

echo "🌸 Athena's Setup Assistant - 前提条件チェック 🌸"
echo "======================================================"
echo ""

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# チェック結果格納
ALL_OK=true

# 1. Homebrew
echo "🍺 Homebrew のチェック..."
if command -v brew &> /dev/null; then
    echo -e "${GREEN}✅ Homebrew インストール済み${NC}"
else
    echo -e "${RED}❌ Homebrew が見つかりません${NC}"
    echo "   インストールコマンド:"
    echo '   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    ALL_OK=false
fi

# 2. Docker Desktop
echo ""
echo "🐳 Docker Desktop のチェック..."
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✅ Docker Desktop 起動済み${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker Desktop がインストール済みですが、起動していません${NC}"
        echo "   起動方法: open -a Docker"
        echo "   30秒待機後、再度このスクリプトを実行してください"
        ALL_OK=false
    fi
else
    echo -e "${RED}❌ Docker Desktop が見つかりません${NC}"
    echo "   ダウンロード: https://www.docker.com/products/docker-desktop/"
    ALL_OK=false
fi

# 3. Python 3.11
echo ""
echo "🐍 Python 3.11 のチェック..."
if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python 3.11 インストール済み (${PYTHON_VERSION})${NC}"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $PYTHON_VERSION == 3.11* ]]; then
        echo -e "${GREEN}✅ Python 3.11 インストール済み (${PYTHON_VERSION})${NC}"
    else
        echo -e "${YELLOW}⚠️  Python ${PYTHON_VERSION} がインストールされています${NC}"
        echo "   Python 3.11が推奨されます: brew install python@3.11"
    fi
else
    echo -e "${RED}❌ Python 3 が見つかりません${NC}"
    echo "   インストール: brew install python@3.11"
    ALL_OK=false
fi

# 4. Node.js
echo ""
echo "🟢 Node.js のチェック..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js インストール済み (${NODE_VERSION})${NC}"
else
    echo -e "${RED}❌ Node.js が見つかりません${NC}"
    echo "   インストール: brew install node"
    ALL_OK=false
fi

# 5. Conda
echo ""
echo "🐍 Conda のチェック..."
if command -v conda &> /dev/null; then
    CONDA_VERSION=$(conda --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Conda インストール済み (${CONDA_VERSION})${NC}"

    # openvoice_v2 環境の確認
    if conda env list | grep -q "openvoice_v2"; then
        echo -e "${GREEN}✅ openvoice_v2 環境作成済み${NC}"
    else
        echo -e "${YELLOW}⚠️  openvoice_v2 環境が未作成です${NC}"
        echo "   自動セットアップスクリプトで作成できます"
    fi
else
    echo -e "${YELLOW}⚠️  Conda が見つかりません（OpenVoice Native Service用）${NC}"
    echo "   インストール: brew install --cask miniconda"
    echo "   初期化: conda init zsh (または bash)"
    echo "   ターミナル再起動が必要です"
fi

# 6. FFmpeg (Optional)
echo ""
echo "🎬 FFmpeg のチェック（任意）..."
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✅ FFmpeg インストール済み${NC}"
else
    echo -e "${YELLOW}⚠️  FFmpeg が見つかりません（音声処理に推奨）${NC}"
    echo "   インストール: brew install ffmpeg"
fi

# 7. D-ID API Key
echo ""
echo "🔑 D-ID API Key のチェック..."
if [ -f ~/secure_credentials/d_id_api_key.txt ]; then
    API_KEY_LENGTH=$(grep "D_ID_API_KEY=" ~/secure_credentials/d_id_api_key.txt | cut -d'=' -f2 | wc -c)
    if [ $API_KEY_LENGTH -gt 10 ]; then
        echo -e "${GREEN}✅ D-ID API Key 設定済み${NC}"
    else
        echo -e "${YELLOW}⚠️  D-ID API Key ファイルは存在しますが、空です${NC}"
        echo "   ~/secure_credentials/d_id_api_key.txt を確認してください"
    fi
else
    echo -e "${YELLOW}⚠️  D-ID API Key ファイルが見つかりません${NC}"
    echo "   作成方法:"
    echo "   mkdir -p ~/secure_credentials"
    echo "   echo 'D_ID_API_KEY=your-actual-key-here' > ~/secure_credentials/d_id_api_key.txt"
    echo "   chmod 600 ~/secure_credentials/d_id_api_key.txt"
fi

# 最終判定
echo ""
echo "======================================================"
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}🎉 すべての前提条件が満たされています！${NC}"
    echo ""
    echo "次のステップ:"
    echo "  ./quick_setup.sh を実行してセットアップを開始してください"
else
    echo -e "${YELLOW}⚠️  いくつかの前提条件が不足しています${NC}"
    echo ""
    echo "上記のインストール手順に従って、不足しているソフトウェアをインストールしてください。"
    echo "インストール後、このスクリプトを再度実行して確認してください。"
fi
echo "======================================================"
