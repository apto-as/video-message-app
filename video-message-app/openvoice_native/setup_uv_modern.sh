#!/bin/bash
# OpenVoice Native Service セットアップ (UV Modern Project Management)
# UV標準方式: pyproject.toml + uv.lock を使用

set -e  # エラー時に停止

echo "🚀 OpenVoice Native Service セットアップ開始 (UV Modern版)"
echo "==============================================="

# 現在のディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# UV インストール確認
if ! command -v uv &> /dev/null; then
    echo "📦 UV をインストールします..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 現在のPythonバージョンを確認
PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "🔍 現在のConda環境: Python $PYTHON_VERSION"

# .python-versionファイル作成（UVプロジェクト標準）
echo "$PYTHON_VERSION" > .python-version
echo "📝 .python-version ファイル作成: Python $PYTHON_VERSION"

# PyTorchをCondaで事前インストール（CPUバージョン）
echo "🔥 PyTorchをCondaでインストールします..."
echo "ℹ️  PyTorchはConda環境で管理し、UVの仮想環境からアクセスします"

# PyTorchがインストールされているかチェック
if python -c "import torch; print(f'PyTorch {torch.__version__} 確認済み')" 2>/dev/null; then
    echo "✅ PyTorchは既にインストールされています"
else
    echo "📦 PyTorchをCondaでインストール中..."
    # Conda環境にCPU版PyTorchをインストール
    conda install pytorch torchaudio cpuonly -c pytorch -y
    
    # インストール確認
    if python -c "import torch; print(f'PyTorch {torch.__version__} インストール完了')" 2>/dev/null; then
        echo "✅ PyTorchインストール成功"
    else
        echo "❌ PyTorchインストール失敗"
        exit 1
    fi
fi

# 既存の仮想環境を削除（クリーンインストール）
if [ -d ".venv" ]; then
    echo "🧹 既存の仮想環境を削除します..."
    rm -rf .venv
fi

# 既存のlockファイルを削除（依存関係を再計算）
if [ -f "uv.lock" ]; then
    echo "🧹 既存のロックファイルを削除します..."
    rm -f uv.lock
fi

# UV仮想環境作成（system-site-packagesを有効にしてCondaパッケージにアクセス）
echo "🔧 UV仮想環境を作成します（Conda環境連携モード）..."
uv venv --system-site-packages

# UV プロジェクト同期（依存関係インストール）
echo "📦 UV プロジェクト環境を初期化します..."
echo "ℹ️  PyTorchはConda環境から、その他はPyPIから取得されます"

# 統合同期（pyproject.toml の設定に従って全依存関係をインストール）
uv sync

echo "🎵 OpenVoice/MeloTTSをGitリポジトリからインストール..."
echo "ℹ️  pyproject.tomlのsourcesセクションで既に指定済みです"

# UV pipコマンドで依存関係なしインストール（UVの正しい方法）
echo "📥 OpenVoiceをインストール..."
uv pip install --no-deps git+https://github.com/myshell-ai/OpenVoice.git || echo "⚠️  OpenVoice追加スキップ（既に設定済み）"

echo "📥 MeloTTSをインストール..."
uv pip install --no-deps git+https://github.com/myshell-ai/MeloTTS.git || echo "⚠️  MeloTTS追加スキップ（既に設定済み）"

# 辞書ダウンロード（オプション）
echo "📚 日本語辞書をダウンロードします..."
if uv run python -c "import unidic" 2>/dev/null; then
    echo "✅ Unidic モジュール確認完了"
    
    # 辞書ダウンロード（エラーが出ても処理を続行）
    if uv run python -m unidic download 2>/dev/null; then
        echo "✅ Unidic辞書ダウンロード完了"
    else
        echo "⚠️  Unidic辞書ダウンロードスキップ（既にダウンロード済みまたはエラー）"
    fi
else
    echo "❌ Unidic モジュールのインポートに失敗しました"
    echo "ℹ️  MeloTTSの日本語機能に影響する可能性がありますが、OpenVoiceの基本機能は動作します"
fi

# テンポラリディレクトリ作成
mkdir -p temp

# PyTorchアクセステスト
echo "🧪 PyTorchアクセステストを実行..."
if uv run python -c "import torch; print(f'✅ PyTorch {torch.__version__} アクセス成功')" 2>/dev/null; then
    echo "✅ UV仮想環境からCondaのPyTorchにアクセス可能"
else
    echo "❌ UV仮想環境からPyTorchにアクセスできません"
    echo "ℹ️  --system-site-packages オプションが正しく動作していない可能性があります"
fi

echo ""
echo "✅ セットアップ完了!"
echo "==============================================="
echo ""
echo "🚀 起動方法:"
echo "   ./start_uv_modern.sh"
echo "   または: uv run python main.py"
echo ""
echo "📊 環境確認:"
echo "   uv run python -c \"import fastapi, torch; print('環境OK')\""
echo ""
echo "🔍 依存関係確認:"
echo "   uv tree"
echo ""
echo "ℹ️  PyTorchはConda環境で管理され、その他の依存関係はUV環境で管理されます"
echo ""