#!/bin/bash
# OpenVoice Native Service 起動スクリプト (UV版)

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

echo "🚀 OpenVoice Native Service 起動中 (UV版)..."

# UV仮想環境の存在確認
if [ ! -d ".venv" ]; then
    echo "❌ UV仮想環境が見つかりません。setup_uv.py を実行してください。"
    exit 1
fi

# 仮想環境のPythonを直接使用（バックグラウンド実行対応）
echo "🎵 OpenVoice Native Service 起動 (Port: 8001)"

# 環境変数設定
export PYTHONPATH="$PWD:$PYTHONPATH"

# 仮想環境のPythonを直接実行
.venv/bin/python main.py