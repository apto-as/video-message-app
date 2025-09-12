#!/bin/bash

# OpenVoice Native Service EC2起動スクリプト
# SSH経由で実行するためのコマンド集

echo "=== OpenVoice Native Service EC2 Setup & Start ==="

# EC2にSSH接続して以下のコマンドを実行
cat << 'EOF'

# 1. 最新コードを取得
cd /home/ec2-user/video-message-app/video-message-app
git pull origin master

# 2. OpenVoiceディレクトリに移動
cd openvoice_native

# 3. 既存プロセスを停止
echo "Stopping existing OpenVoice processes..."
pkill -f "python main.py" || true
sleep 2

# 4. Python仮想環境をセットアップ
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 5. 仮想環境を有効化
source venv/bin/activate

# 6. 依存関係をインストール
echo "Installing dependencies..."
pip install --upgrade pip

# NumPy 1.22.0を最初にインストール（重要！）
pip install numpy==1.22.0

# PyTorch CUDA版をインストール
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# その他の依存関係
pip install librosa==0.10.0
pip install soundfile==0.12.1
pip install unidecode==1.3.6
pip install eng_to_ipa==0.0.2
pip install inflect==7.0.0
pip install scipy==1.10.1
pip install mecab-python3==1.0.8
pip install unidic-lite==1.0.8

# FastAPI関連
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install python-multipart==0.0.6
pip install aiofiles==23.2.1
pip install httpx==0.25.2
pip install pydantic==2.5.0
pip install python-dotenv==1.0.0
pip install mutagen==1.47.0
pip install pydub==0.25.1
pip install ffmpeg-python==0.2.0

# 7. MeCab辞書をダウンロード
echo "Downloading MeCab dictionary..."
python -m unidic download

# 8. OpenVoice V2をクローン（まだない場合）
if [ ! -d "OpenVoiceV2" ]; then
    echo "Cloning OpenVoice V2..."
    git clone https://github.com/myshell-ai/OpenVoice.git OpenVoiceV2
    cd OpenVoiceV2
    git checkout v2
    cd ..
fi

# 9. サービスを起動
echo "Starting OpenVoice Native Service..."
nohup python main.py > openvoice.log 2>&1 &

# 10. 起動確認
sleep 5
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ OpenVoice Native Service is running!"
    echo "Check logs: tail -f openvoice.log"
else
    echo "❌ Failed to start OpenVoice Native Service"
    echo "Check logs: cat openvoice.log"
fi

EOF

echo ""
echo "上記のコマンドをEC2で実行してください："
echo "ssh -p 22 ec2-user@3.115.141.166"
echo ""
echo "または、このスクリプトを直接実行："
echo "ssh -p 22 ec2-user@3.115.141.166 'bash -s' < start_openvoice_ec2.sh"