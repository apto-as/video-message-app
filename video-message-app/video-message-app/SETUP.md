# Video Message App - セットアップガイド

このドキュメントでは、ローカル開発環境とEC2プロダクション環境のセットアップ手順を説明します。

## 📋 目次

- [前提条件](#前提条件)
- [ローカル開発環境](#ローカル開発環境)
- [EC2プロダクション環境](#ec2プロダクション環境)
- [トラブルシューティング](#トラブルシューティング)

## 前提条件

### 共通要件

- **Docker Desktop**: 最新版
- **Docker Compose**: v2.0以上
- **Git**: 最新版
- **SSH鍵**: EC2接続用（`~/.ssh/video-app-key.pem`）

### ローカル開発環境（Mac）

- **macOS**: 12.0 (Monterey) 以上
- **Python**: 3.11以上（OpenVoice Service用）
- **Conda**: miniconda または anaconda
- **メモリ**: 8GB以上推奨
- **ディスク**: 20GB以上の空き容量

### EC2プロダクション環境

- **インスタンスタイプ**: g4dn.xlarge（Tesla T4 GPU）
- **OS**: Amazon Linux 2023 (Deep Learning AMI)
- **CUDA**: 12.8
- **Docker**: 最新版（NVIDIA Runtime対応）

## ローカル開発環境

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd video-message-app/video-message-app
```

### 2. 環境変数の設定

```bash
# .env.example をコピー
cp .env.example .env

# .env を編集
nano .env
```

**必須設定**:
```bash
APP_ENVIRONMENT=local
D_ID_API_KEY=your_d_id_api_key_here
OPENVOICE_URL=http://localhost:8001
```

### 3. OpenVoice Native Service のセットアップ

OpenVoice ServiceはMac MPSに対応するため、Dockerコンテナ外で実行します。

```bash
# Conda環境の作成
cd openvoice_native
conda create -n openvoice_v2 python=3.11
conda activate openvoice_v2

# 依存関係のインストール
pip install -r requirements.txt

# サービスの起動
python main.py
```

**確認**:
```bash
curl http://localhost:8001/health
# {"status":"healthy", ...} が返ればOK
```

### 4. Dockerサービスの起動

```bash
# プロジェクトルートに戻る
cd ..

# Dockerイメージのビルド
docker-compose build

# サービスの起動
docker-compose up -d

# ステータス確認
docker-compose ps
```

### 5. 動作確認

```bash
# バックエンドAPI
curl https://localhost/api/health
# → {"status":"healthy"}

# フロントエンド
open https://localhost
# → Reactアプリが表示される（SSL警告は無視）
```

## EC2プロダクション環境

### 1. SSH接続の確認

```bash
# SSH鍵のパーミッション設定
chmod 600 ~/.ssh/video-app-key.pem

# 接続テスト
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166
```

### 2. 初回セットアップ（EC2上で実行）

```bash
# プロジェクトディレクトリの作成
mkdir -p ~/video-message-app
cd ~/video-message-app

# Gitからクローン
git clone <repository-url>
cd video-message-app

# 環境変数の設定
cp .env.example .env
nano .env
```

**プロダクション設定**:
```bash
APP_ENVIRONMENT=docker
D_ID_API_KEY=your_d_id_api_key_here
OPENVOICE_URL=http://host.docker.internal:8001
CUDA_DEVICE=0
```

### 3. OpenVoice Native Service（systemd）

```bash
# サービスファイルの作成
sudo nano /etc/systemd/system/openvoice.service
```

**サービス設定**:
```ini
[Unit]
Description=OpenVoice Native Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/video-message-app/video-message-app/openvoice_native
Environment="LD_LIBRARY_PATH=/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/torch/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cuda_nvrtc/lib:/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/lib/python3.9/site-packages/nvidia/cudnn/lib:/usr/local/cuda/lib64:/usr/lib64"
ExecStart=/home/ec2-user/video-message-app/video-message-app/openvoice_native/venv/bin/python -u main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# サービスの有効化と起動
sudo systemctl daemon-reload
sudo systemctl enable openvoice
sudo systemctl start openvoice

# ステータス確認
sudo systemctl status openvoice
```

### 4. Dockerサービスの起動

```bash
# Docker Composeでビルド
docker-compose build

# サービスの起動
docker-compose up -d

# ログ確認
docker-compose logs -f
```

### 5. 動作確認

```bash
# ローカルから確認
curl https://3.115.141.166/api/health
# → {"status":"healthy"}

# ブラウザでアクセス
open https://3.115.141.166
```

## Docker統一環境の使用

### docker-compose.unified.yml の使用

```bash
# 環境変数ファイルの準備
cp .env.example .env.local  # ローカル用
cp .env.example .env.prod   # プロダクション用

# ローカル環境で起動
docker-compose -f docker-compose.unified.yml --env-file .env.local up -d

# EC2環境で起動（OpenVoice含む）
docker-compose -f docker-compose.unified.yml --env-file .env.prod --profile production up -d
```

### 環境別の設定

**ローカル（.env.local）**:
```bash
APP_ENVIRONMENT=local
MOUNT_CODE=rw  # 開発時はコード変更を即反映
OPENVOICE_URL=http://localhost:8001  # ホスト環境
```

**プロダクション（.env.prod）**:
```bash
APP_ENVIRONMENT=production
MOUNT_CODE=ro  # 読み取り専用
OPENVOICE_URL=http://openvoice:8001  # Docker内
```

## トラブルシューティング

### OpenVoice接続エラー

**症状**: Backend → OpenVoice 接続失敗

**原因**:
- OpenVoice Serviceが起動していない
- ポート8001が使用中

**解決策**:
```bash
# サービス確認
# ローカル
lsof -i :8001

# EC2
sudo systemctl status openvoice
```

### CUDA/CuDNN エラー（EC2）

**症状**: `Could not load library libcudnn_cnn_infer.so.8`

**解決策**:
```bash
# LD_LIBRARY_PATH の確認
sudo systemctl cat openvoice | grep LD_LIBRARY_PATH

# 不足している場合は追加
sudo systemctl edit openvoice
# Environment="LD_LIBRARY_PATH=..." を追加
```

### Docker接続エラー

**症状**: `connection reset by peer`

**解決策**:
```bash
# Docker Desktop起動確認（Mac）
open -a Docker

# EC2でDockerサービス確認
sudo systemctl status docker
```

### ポート競合

**症状**: `port is already allocated`

**解決策**:
```bash
# 使用中のポートを確認
lsof -i :80
lsof -i :443
lsof -i :8001

# 競合プロセスを停止
kill -9 <PID>
```

## 次のステップ

- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ
- [CLAUDE.md](./CLAUDE.md) - プロジェクト詳細
