# EC2 Quick Commands - Voice Clone System

## 🚀 EC2へのSSH接続

```bash
# SSHキーの場所を確認
ls -la ~/.ssh/*pem

# EC2に接続（キーファイル名を適切に変更してください）
ssh -i ~/.ssh/your-key.pem ec2-user@3.115.141.166
```

## 📦 EC2上での初期セットアップ

```bash
# 1. リポジトリのクローン（初回のみ）
cd ~
git clone https://github.com/apto-as/prototype-app video-message-app

# 2. UV環境のセットアップ
cd ~/video-message-app/video-message-app
./ec2_setup/setup_ec2_uv.sh

# 3. OpenVoiceサービスの起動
source ~/video-message-app/activate_openvoice.sh
cd ~/video-message-app/video-message-app/ec2_setup
python openvoice_ec2_service.py
```

## 🐳 Docker サービスの管理

```bash
# Dockerサービスの起動
cd ~/video-message-app/video-message-app
docker-compose up -d

# サービスの状態確認
docker-compose ps

# ログの確認
docker logs voice_backend --tail 50
docker logs voice_frontend --tail 50
docker logs voicevox_engine --tail 50

# サービスの再起動
docker-compose restart backend
docker-compose restart frontend

# サービスの停止
docker-compose down
```

## 🔍 動作確認コマンド

```bash
# ローカルから確認
# Backendヘルスチェック
curl http://3.115.141.166:55433/health

# OpenVoiceヘルスチェック
curl http://3.115.141.166:8001/health

# VoiceVoxエンジン確認
curl http://3.115.141.166:50021/speakers | jq

# Webサイトアクセス
open http://3.115.141.166:55434
```

## 🔧 トラブルシューティング

### OpenVoiceサービスが起動しない場合

```bash
# UV環境の再アクティベート
cd ~/video-message-app/video-message-app/openvoice_ec2
source .venv/bin/activate

# Python環境の確認
python --version
which python

# 依存関係の確認
pip list | grep -E "torch|openvoice|fastapi"

# 手動起動（デバッグモード）
python -u openvoice_ec2_service.py
```

### Dockerサービスが起動しない場合

```bash
# Dockerデーモンの確認
sudo systemctl status docker

# Dockerの再起動
sudo systemctl restart docker

# コンテナの強制削除と再作成
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### ポートの確認

```bash
# 使用中のポート確認
sudo netstat -tulpn | grep -E "8001|55433|55434|50021"

# プロセスの確認
ps aux | grep -E "python|docker"
```

## 📋 ファイル同期

```bash
# EC2上でGitから最新を取得
cd ~/video-message-app
git pull origin master

# 特定ファイルのコピー（ローカルから）
scp -i ~/.ssh/your-key.pem \
  ./video-message-app/ec2_setup/openvoice_ec2_service.py \
  ec2-user@3.115.141.166:~/video-message-app/video-message-app/ec2_setup/

# ディレクトリ全体の同期
rsync -avz -e "ssh -i ~/.ssh/your-key.pem" \
  ./video-message-app/ \
  ec2-user@3.115.141.166:~/video-message-app/video-message-app/
```

## 🎯 統合テスト

```bash
# 1. プロファイル作成テスト
curl -X POST http://3.115.141.166:55433/api/voice-clone/create \
  -F "name=Test Profile" \
  -F "audio_file=@test_audio.wav" \
  -F "language=ja"

# 2. プロファイル一覧確認
curl http://3.115.141.166:55433/api/voice-clone/profiles | jq

# 3. 音声合成テスト
curl -X POST http://3.115.141.166:55433/api/voice-clone/test/{profile_id} \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは、テスト音声です。"}' \
  --output test_output.wav
```

---
*EC2 Instance IP: 3.115.141.166*
*Region: ap-northeast-1 (Tokyo)*
*Created: 2025-08-20*