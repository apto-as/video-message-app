#!/bin/bash
# OpenVoice Native Service 開発起動スクリプト
# Conda環境でUVを使わずに直接起動する場合

cd "$(dirname "$0")"

echo "🚀 OpenVoice Native Service 起動中 (開発モード)..."
echo "⚠️  注意: Conda環境で必要なパッケージが既にインストールされていることを前提としています"

# 環境変数設定
export PYTHONPATH="$PWD:$PYTHONPATH"

# 直接起動（uvicornのreloadオプション付き）
echo "🎵 OpenVoice Native Service 起動 (Port: 8001) - 開発モード"
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload