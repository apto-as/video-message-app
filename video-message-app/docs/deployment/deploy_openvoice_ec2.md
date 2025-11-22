# OpenVoice Native Service EC2 デプロイ手順

## 1. EC2へのSSH接続

```bash
ssh -p 22 ec2-user@3.115.141.166
```

## 2. 最新コードの取得

```bash
cd /home/ec2-user/video-message-app/video-message-app
git pull origin master
```

## 3. OpenVoice Native Serviceのセットアップ

```bash
cd openvoice_native

# 既存のサービスを停止（もし動作している場合）
pkill -f "python main.py" || true

# セットアップスクリプトを実行
chmod +x setup_ec2.sh
./setup_ec2.sh

# または手動でセットアップ
python3 -m venv venv
source venv/bin/activate

# NumPy 1.22.0をインストール（OpenVoice V2互換性のため）
pip install numpy==1.22.0

# PyTorchをCUDA対応版でインストール
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# その他の依存関係をインストール
pip install -r requirements_ec2.txt

# MeCab辞書のダウンロード
python -m unidic download

# OpenVoice V2をクローン（まだない場合）
if [ ! -d "OpenVoiceV2" ]; then
    git clone https://github.com/myshell-ai/OpenVoice.git OpenVoiceV2
    cd OpenVoiceV2
    git checkout v2
    cd ..
fi
```

## 4. サービスの起動

```bash
# バックグラウンドで起動
nohup python main.py > openvoice.log 2>&1 &

# ログを確認
tail -f openvoice.log
```

## 5. サービスの確認

```bash
# ヘルスチェック
curl http://localhost:8001/health

# プロセス確認
ps aux | grep "python main.py"
```

## 6. Dockerサービスの再起動

```bash
cd /home/ec2-user/video-message-app/video-message-app
docker-compose down
docker-compose up -d

# ログ確認
docker logs voice_backend --tail 50
```

## 7. トラブルシューティング

### NumPyバージョン競合の場合
```bash
# 仮想環境内で確認
python -c "import numpy; print(numpy.__version__)"
# 1.22.0が表示されるべき
```

### MeCabエラーの場合
```bash
# unidic辞書の再インストール
python -m unidic download
```

### CUDA関連エラーの場合
```bash
# GPUの確認
nvidia-smi

# PyTorchのCUDA利用確認
python -c "import torch; print(torch.cuda.is_available())"
```

### ポート競合の場合
```bash
# ポート8001の使用状況確認
lsof -i :8001

# 競合プロセスの停止
kill -9 [PID]
```

## 注意事項

- EC2上ではhost.docker.internalは動作しないため、プライベートIP（172.31.20.86）を使用
- NumPy 1.22.0はOpenVoice V2の要件
- CUDA対応のPyTorchインストールにはindex-urlの指定が必要
- MeCab辞書は初回のみダウンロードが必要