#!/bin/bash

# 統合Conda環境セットアップスクリプト
# 使用方法: ./setup_new_env.sh [環境名] [--fix-only]

set -e

# 環境名（デフォルト: prototype-app）
ENV_NAME="${1:-prototype-app}"
FIX_ONLY=false

# --fix-onlyオプションの確認
if [[ "$2" == "--fix-only" ]] || [[ "$1" == "--fix-only" ]]; then
    FIX_ONLY=true
    ENV_NAME="${1:-prototype-app}"
    if [[ "$1" == "--fix-only" ]]; then
        ENV_NAME="prototype-app"
    fi
fi

if [[ "$FIX_ONLY" == "true" ]]; then
    echo "=== 既存環境の依存関係修正モード ==="
    echo "環境名: $ENV_NAME"
else
    echo "=== 新しいConda環境セットアップ開始 ==="
    echo "環境名: $ENV_NAME"
fi

# 既存環境の確認と作成
if [[ "$FIX_ONLY" == "false" ]]; then
    # 既存環境を確認
    if conda env list | grep -q "^$ENV_NAME "; then
        echo "⚠️  環境 '$ENV_NAME' は既に存在します。"
        read -p "削除して再作成しますか？ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "既存環境を削除中..."
            conda deactivate 2>/dev/null || true
            conda env remove -n "$ENV_NAME" -y
        else
            echo "既存環境を使用して依存関係のみ修正します..."
            FIX_ONLY=true
        fi
    fi

    if [[ "$FIX_ONLY" == "false" ]]; then
        # 現在の環境を非アクティブ化
        echo "現在の環境を非アクティブ化中..."
        conda deactivate 2>/dev/null || true

        # 新しい環境を作成
        echo "Python 3.11.12で新しい環境を作成中..."
        conda create -n "$ENV_NAME" python=3.11.12 -y
    fi
fi

# 環境をアクティベート
if [[ "$CONDA_DEFAULT_ENV" != "$ENV_NAME" ]]; then
    echo "環境をアクティベート中..."
    conda activate "$ENV_NAME"
fi

echo "現在の環境: $CONDA_DEFAULT_ENV"

# Python バージョンをチェック
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python バージョン: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" != "3.11" ]]; then
    echo "⚠️  Python 3.11が必要です。現在は $PYTHON_VERSION です。"
    if [[ "$FIX_ONLY" == "true" ]]; then
        echo "環境を再作成してください: ./setup_new_env.sh $ENV_NAME"
        exit 1
    fi
fi

# conda-forgeチャンネルを追加
echo "conda-forgeチャンネルを設定中..."
conda config --add channels conda-forge
conda config --set channel_priority strict

# 基本パッケージをcondaでインストール
echo "基本パッケージをcondaでインストール中..."
conda install -y \
    numpy=1.24.4 \
    scipy \
    scikit-learn \
    scikit-image \
    pillow \
    requests \
    tqdm \
    pyyaml \
    setuptools \
    wheel \
    pip

# pipを最新版にアップグレード
echo "pipをアップグレード中..."
pip install --upgrade pip

# pipキャッシュをクリア
echo "pipキャッシュをクリア中..."
pip cache purge

# 競合の可能性があるパッケージを先にアンインストール
echo "競合パッケージをクリア中..."
pip uninstall -y pydantic pydantic-settings fastapi rembg 2>/dev/null || true

# 段階的にパッケージをインストール
echo "段階1: Web Framework"
pip install fastapi==0.104.1
pip install "pydantic>=2.7.0,<3.0.0"
pip install "pydantic-settings>=2.1.0,<3.0.0"
pip install "uvicorn[standard]==0.24.0"
pip install python-multipart==0.0.6

echo "段階2: HTTP/Network"
pip install httpx==0.25.2
pip install requests

echo "段階3: File & Configuration"  
pip install python-dotenv==1.0.0
pip install aiofiles
pip install mutagen==1.47.0

echo "段階4: rembg依存関係"
pip install jsonschema pooch pymatting networkx imageio tifffile

echo "段階5: Image Processing"
pip install rembg==2.0.67
pip install opencv-python-headless
pip install onnxruntime

echo "段階6: Audio Processing"
pip install soundfile
pip install pydub
pip install ffmpeg-python

echo "段階7: Additional utilities"
pip install tqdm
pip install "loguru>=0.7.2"

# インストール結果を確認
echo "=== インストール完了確認 ==="
echo "Python バージョン:"
python --version

echo "主要パッケージ確認:"
python -c "
try:
    import fastapi, uvicorn, httpx, numpy, scipy, pydantic
    print('✅ FastAPI:', fastapi.__version__)
    print('✅ Uvicorn:', uvicorn.__version__)
    print('✅ HTTPX:', httpx.__version__)
    print('✅ NumPy:', numpy.__version__)
    print('✅ SciPy:', scipy.__version__)
    print('✅ Pydantic:', pydantic.__version__)
    
    # 추가 확인
    import PIL, cv2, onnxruntime, rembg, sklearn, skimage
    print('✅ Pillow:', PIL.__version__)
    print('✅ OpenCV:', cv2.__version__)
    print('✅ ONNX Runtime:', onnxruntime.__version__)
    print('✅ Rembg: imported successfully')
    print('✅ Scikit-learn:', sklearn.__version__)
    print('✅ Scikit-image:', skimage.__version__)
    
    print('\\n🎉 すべてのパッケージが正常にインストールされました')
except ImportError as e:
    print('❌ インポートエラー:', e)
    exit(1)
"

# pip check로 의존관계 확인
echo "=== 依存関係最終確認 ==="
pip check
if [ $? -eq 0 ]; then
    echo "✅ すべての依存関係が満足されました"
else
    echo "⚠️  一部依存関係問題が残っている可能性があります"
fi

if [[ "$FIX_ONLY" == "false" ]]; then
    echo "=== 環境セットアップ完了 ==="
    echo "次のコマンドで環境をアクティベートできます:"
    echo "conda activate $ENV_NAME"
    
    # 環境情報を保存
    conda list --export > "${ENV_NAME}_setup_$(date +%Y%m%d_%H%M%S).txt"
    echo "パッケージリストは ${ENV_NAME}_setup_*.txt に保存されました"
else
    echo "=== 依存関係修正完了 ==="
fi