#!/bin/bash
# OpenVoice Native Service セットアップ (Conda + UV版)
# 既存のConda環境内でUVを使用する簡潔なセットアップ

set -e  # エラー時に停止

echo "🚀 OpenVoice Native Service セットアップ開始 (Conda + UV版)"

# 現在のディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# UV インストール確認
if ! command -v uv &> /dev/null; then
    echo "📦 UV をインストールします..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 既存の.venvディレクトリを削除（クリーンインストール）
if [ -d ".venv" ]; then
    echo "🧹 既存の仮想環境を削除します..."
    rm -rf .venv
fi

# 現在のPythonバージョンを確認
PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "🔍 現在のConda環境: Python $PYTHON_VERSION"

# UV仮想環境作成（現在のPythonバージョンを使用）
echo "🔧 UV仮想環境を作成します (Python $PYTHON_VERSION)..."
uv venv --python "$PYTHON_VERSION"

# 仮想環境を有効化してからパッケージインストール
echo "📦 依存関係をインストールします..."
source .venv/bin/activate

# PyTorch CPU版を先にインストール（index-strategyを使用）
echo "🔥 PyTorch CPUバージョンをインストール..."
uv pip install --index-strategy unsafe-best-match torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# NumPy互換性問題を回避するため、安全なインデックス戦略を使用
echo "🔧 NumPy と依存関係をインストールします..."
uv pip install --index-strategy unsafe-best-match numpy

# 依存関係を直接インストール（pyproject.tomlのパッケージ化は不要）
echo "📦 FastAPI関連パッケージをインストールします..."
uv pip install --index-strategy unsafe-best-match \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6

echo "🎵 Audio処理パッケージをインストールします..."
uv pip install --index-strategy unsafe-best-match \
    librosa \
    soundfile \
    unidecode \
    eng_to_ipa \
    inflect \
    scipy \
    aiofiles \
    httpx \
    pydantic==2.5.0 \
    python-dotenv \
    mutagen \
    pydub \
    ffmpeg-python

# OpenVoice関連（依存関係制約を回避）
echo "🎵 OpenVoice関連パッケージをインストールします..."

# OpenVoiceを依存関係なしでインストール後、互換性のある依存関係を手動インストール
echo "📥 OpenVoice本体をインストール（依存関係スキップ）..."
uv pip install --index-strategy unsafe-best-match --no-deps git+https://github.com/myshell-ai/OpenVoice.git

echo "📦 OpenVoice互換依存関係をインストール..."
uv pip install --index-strategy unsafe-best-match \
    "librosa>=0.9.1" \
    "faster-whisper>=0.9.0" \
    "pydub>=0.25.1" \
    "wavmark>=0.0.3" \
    "whisper-timestamped>=1.14.2" \
    "pypinyin>=0.50.0" \
    "cn2an>=0.5.22" \
    "jieba>=0.42.1" \
    "langid>=1.1.6"

echo "📥 MeloTTSをインストール..."
uv pip install --index-strategy unsafe-best-match --no-deps git+https://github.com/myshell-ai/MeloTTS.git

echo "📦 MeloTTS互換依存関係をインストール..."
uv pip install --index-strategy unsafe-best-match \
    "txtsplit" \
    "transformers>=4.27.4" \
    "num2words>=0.5.12" \
    "unidic-lite>=1.0.8" \
    "mecab-python3>=1.0.9" \
    "pykakasi>=2.2.1" \
    "fugashi>=1.3.0" \
    "g2p-en>=2.1.0" \
    "anyascii>=0.3.2" \
    "jamo>=0.4.1" \
    "gruut[de,es,fr]>=2.2.3" \
    "g2pkk>=0.1.1" \
    "tqdm" \
    "loguru>=0.7.2"

echo "📚 Unidic本体をUV環境にインストール..."
uv pip install --index-strategy unsafe-best-match "unidic>=1.1.0"

# Unidic辞書（オプション）
echo "📚 日本語辞書をダウンロードします..."

# unidic モジュールの存在確認
if python -c "import unidic" 2>/dev/null; then
    echo "✅ Unidic モジュール確認完了"
    
    # 辞書ダウンロード（エラーが出ても処理を続行）
    if python -m unidic download 2>/dev/null; then
        echo "✅ Unidic辞書ダウンロード完了"
    else
        echo "⚠️  Unidic辞書ダウンロードスキップ（既にダウンロード済みまたはエラー）"
    fi
else
    echo "❌ Unidic モジュールのインポートに失敗しました"
    echo "ℹ️  MeloTTSの日本語機能に影響する可能性がありますが、OpenVoiceの基本機能は動作します"
fi

# 仮想環境を非有効化
deactivate

# テンポラリディレクトリ作成
mkdir -p temp

echo "✅ セットアップ完了!"
echo ""
echo "🚀 起動方法:"
echo "   ./start_uv.sh"
echo ""
echo "📊 ヘルスチェック:"
echo "   curl http://localhost:8001/health"