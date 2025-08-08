#!/bin/bash
# バックエンド起動デバッグスクリプト

echo "🔍 バックエンド起動デバッグを開始します..."

cd backend

echo "📍 現在のディレクトリ: $(pwd)"
echo "📍 Python実行環境: $(which python)"
echo "📍 Python バージョン: $(python --version)"

echo ""
echo "🧪 依存関係チェック..."
python -c "
import sys
print(f'Python パス: {sys.executable}')

# 基本的なライブラリチェック
try:
    import fastapi
    print(f'✅ FastAPI: {fastapi.__version__}')
except ImportError as e:
    print(f'❌ FastAPI: {e}')

try:
    import uvicorn
    print(f'✅ Uvicorn: {uvicorn.__version__}')
except ImportError as e:
    print(f'❌ Uvicorn: {e}')

try:
    import rembg
    print(f'✅ rembg: OK')
except ImportError as e:
    print(f'❌ rembg: {e}')

try:
    from PIL import Image
    print(f'✅ Pillow: OK')
except ImportError as e:
    print(f'❌ Pillow: {e}')
"

echo ""
echo "🧪 画像処理モジュールテスト..."
python -c "
import sys
import os
sys.path.append('..')
try:
    from services.image_processor import ImageProcessor
    processor = ImageProcessor()
    print('✅ ImageProcessor: 正常に初期化されました')
    print(f'✅ rembgセッション: {processor.session is not None}')
except Exception as e:
    print(f'❌ ImageProcessor: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "🧪 基本的なアプリケーション起動テスト..."
python -c "
try:
    from main import app
    print('✅ FastAPIアプリケーション: 正常にインポートされました')
except Exception as e:
    print(f'❌ FastAPIアプリケーション: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "🚀 手動でサーバーを起動してみます（10秒後に終了）..."
# macOSではgtimeoutを使用、なければ手動でキル
if command -v gtimeout >/dev/null 2>&1; then
    gtimeout 10s uvicorn main:app --port 8000 --host 0.0.0.0 || echo "タイムアウトまたはエラーで終了"
else
    echo "⚠️ タイムアウト機能が使用できません。手動テストをスキップします。"
    echo "✅ 基本テストは完了しました。start_app.shで完全なテストを実行してください。"
fi

echo ""
echo "📋 デバッグ完了。上記の結果をもとに問題を特定してください。"