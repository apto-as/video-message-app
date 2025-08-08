#!/bin/bash
# OpenVoice Native Service 起動スクリプト (UV Modern Project Management)
# UV標準方式: uv run コマンドを使用

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

echo "🚀 OpenVoice Native Service 起動中 (UV Modern版)..."

# UV仮想環境の存在確認
if [ ! -d ".venv" ]; then
    echo "❌ UV仮想環境が見つかりません。setup_uv_modern.sh を実行してください。"
    exit 1
fi

# pyproject.tomlの存在確認
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml が見つかりません。UVプロジェクトが正しく設定されていません。"
    exit 1
fi

# UV標準方式でサービス起動
echo "🎵 OpenVoice Native Service 起動 (Port: 8001)"
echo "ℹ️  UV が自動的に仮想環境を管理します"

# UVプロジェクト実行（自動的に仮想環境を使用）
uv run python main.py