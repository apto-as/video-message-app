#\!/bin/bash
# OpenVoice Native Service 起動スクリプト

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

echo "🚀 OpenVoice Native Service 起動中..."

# 仮想環境の存在確認
if [ \! -d "venv" ]; then
    echo "❌ 仮想環境が見つかりません。setup.py を実行してください。"
    exit 1
fi

# 仮想環境アクティベート
source venv/bin/activate

# Pythonパス設定
export PYTHONPATH="$PWD:$PYTHONPATH"

# サービス起動
echo "🎵 OpenVoice Native Service 起動 (Port: 8001)"
python main.py
EOF < /dev/null