# Docker Setup Guide

このガイドは、Video Message AppのDocker環境セットアップ手順を説明します。

## 🎯 作成されたファイル一覧

### Docker設定ファイル
- **openvoice_native/Dockerfile** - OpenVoice NativeサービスのDockerイメージ定義（Python 3.11対応）
- **openvoice_native/requirements.txt** - Python 3.11用の依存関係リスト（検証済み）
- **docker-compose.yml** - 全サービス（VOICEVOX, OpenVoice, Backend, Frontend, Nginx）の統合設定
- **docker-compose.override.yml** - Mac開発環境用の自動オーバーライド設定（MPS/CPU）
- **docker-compose.prod.yml** - EC2本番環境用の設定（CUDA/GPU対応）
- **.env.example** - 環境変数のテンプレート

### セキュリティ対策
- **.gitignore** - 機密情報（.env, 認証情報, SSLキーなど）を保護

## 🚀 Mac環境でのセットアップ

### 1. 環境変数の設定

```bash
cd video-message-app

# .env.exampleから.envを作成
cp .env.example .env

# .envを編集（必須）
nano .env
# または
code .env
```

**.envの設定例（Mac）:**
```bash
# Docker Build Configuration
USE_CUDA=false
DEVICE=mps  # Apple Silicon の場合。Intel Mac は cpu

# Application Configuration
LOG_LEVEL=INFO

# D-ID API Key（必須！）
D_ID_API_KEY=実際のAPIキーをここに記入
```

### 2. Dockerイメージのビルド

```bash
# OpenVoiceV2のソースコードをダウンロード（初回のみ）
cd openvoice_native
git clone https://github.com/myshell-ai/OpenVoice.git OpenVoiceV2
cd ..

# すべてのサービスをビルド
docker-compose build

# OpenVoiceのみビルドする場合
docker-compose build openvoice
```

### 3. サービスの起動

```bash
# すべてのサービスを起動
docker-compose up -d

# ログを確認
docker-compose logs -f openvoice
docker-compose logs -f backend

# ステータス確認
docker-compose ps
```

### 4. 動作確認

```bash
# OpenVoice ヘルスチェック
curl http://localhost:8001/health

# Backend ヘルスチェック
curl http://localhost:55433/health

# VOICEVOX ヘルスチェック
curl http://localhost:50021/version

# ブラウザでフロントエンドにアクセス
open http://localhost:55434
```

### 5. サービスの停止

```bash
# すべてのサービスを停止
docker-compose down

# データも削除する場合（注意！）
docker-compose down -v
```

## 🌩️ EC2環境でのセットアップ

### 前提条件

1. **NVIDIA Docker Runtimeのインストール**

```bash
# EC2にSSHでログイン
ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166

# NVIDIA Docker Runtimeをインストール（初回のみ）
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | sudo tee /etc/yum.repos.d/nvidia-docker.repo

sudo yum install -y nvidia-docker2
sudo systemctl restart docker

# GPU確認
nvidia-smi
```

2. **Docker Composeのインストール**

```bash
# Docker Compose V2をインストール（最新版）
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### EC2でのデプロイ手順

```bash
# プロジェクトディレクトリに移動
cd /home/ec2-user/video-message-app/video-message-app

# 環境変数を設定
cp .env.example .env
nano .env

# .envの設定例（EC2 with CUDA）:
USE_CUDA=true
DEVICE=cuda
LOG_LEVEL=INFO
D_ID_API_KEY=実際のAPIキー

# docker-compose.override.ymlを削除または無効化（重要！）
# Mac用の設定がEC2で読み込まれないようにする
mv docker-compose.override.yml docker-compose.override.yml.bak

# 本番環境用の設定でビルド＆起動
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# ログ確認
docker-compose logs -f openvoice

# GPU使用状況を確認
nvidia-smi

# ヘルスチェック
curl http://localhost:8001/health
```

### EC2での動作確認

```bash
# OpenVoiceがGPUを使用しているか確認
docker exec openvoice_native python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count()}')"

# 出力例:
# CUDA available: True
# Device count: 1

# コンテナ内でGPU確認
docker exec openvoice_native nvidia-smi
```

## 🔄 環境差異の管理

### Mac（開発環境）
- **自動適用**: `docker-compose.override.yml`が自動的に読み込まれる
- **デバイス**: `mps`（Apple Silicon）または `cpu`（Intel Mac）
- **CUDA**: 無効（`USE_CUDA=false`）
- **ホットリロード**: 有効（開発効率向上）

### EC2（本番環境）
- **明示指定**: `-f docker-compose.prod.yml`で本番設定を指定
- **デバイス**: `cuda`
- **CUDA**: 有効（`USE_CUDA=true`）
- **GPU**: NVIDIA Tesla T4を使用
- **最適化**: 本番モード、ホットリロード無効

## 🐛 トラブルシューティング

### 1. OpenVoiceコンテナが起動しない

```bash
# ログ確認
docker-compose logs openvoice

# よくあるエラー: MeloTTS インポートエラー
# 解決方法: Dockerfileが正しくGitHubからインストールしているか確認

# コンテナに直接入って確認
docker exec -it openvoice_native bash
python -c "from melo.api import TTS"
```

### 2. GPUが認識されない（EC2）

```bash
# NVIDIA Dockerランタイムの確認
docker info | grep -i nvidia

# 出力に "nvidia" が含まれていない場合、再インストール
sudo yum install -y nvidia-docker2
sudo systemctl restart docker
```

### 3. ポート競合エラー

```bash
# 既存プロセスの確認
sudo lsof -i :8001
sudo lsof -i :55433

# プロセスを停止してから再起動
docker-compose down
docker-compose up -d
```

### 4. ボリュームマウントエラー

```bash
# ストレージディレクトリを手動作成
mkdir -p data/backend/storage
mkdir -p openvoice_native/data/openvoice

# 権限を確認
ls -la data/backend/storage
```

### 5. D-ID API Keyエラー

```bash
# .envファイルの確認
cat .env | grep D_ID_API_KEY

# 実際のキーが設定されているか確認
# "your-d-id-api-key-here" のままでないか注意！
```

## 📊 パフォーマンス比較

### Mac（MPS）
- **ビルド時間**: 約10-15分
- **起動時間**: 約30-60秒
- **音声合成**: 約3-5秒/文
- **メモリ使用量**: 約2-3GB

### EC2（CUDA）
- **ビルド時間**: 約8-12分
- **起動時間**: 約20-40秒
- **音声合成**: 約1-2秒/文（GPU加速）
- **メモリ使用量**: 約3-4GB
- **GPU使用率**: 20-40%（アイドル時）、80-100%（推論時）

## 🔐 セキュリティベストプラクティス

1. **.envファイルは絶対にGitにコミットしない**
   - `.gitignore`で保護済み
   - `git status`で確認してからcommit

2. **D-ID APIキーの管理**
   - 本番: AWS Secrets Managerを推奨
   - 開発: `~/secure_credentials/`に保管

3. **SSL証明書**
   - 本番: Let's Encryptまたはaws Certificate Manager
   - 開発: 自己署名証明書でOK

4. **Docker Hubへのpush前**
   - 機密情報が含まれていないか確認
   - `docker history <image>`で確認

## 📚 次のステップ

1. **Macでのローカル開発環境構築**
   ```bash
   cd video-message-app
   cp .env.example .env
   # .envを編集してD_ID_API_KEYを設定
   docker-compose up -d
   ```

2. **EC2への初回デプロイ**
   ```bash
   # EC2にSSH
   ssh -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
   
   # リポジトリ更新
   cd /home/ec2-user/video-message-app/video-message-app
   git pull
   
   # デプロイ
   mv docker-compose.override.yml docker-compose.override.yml.bak
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

3. **新機能開発**
   - ローカル（Mac）で開発
   - コンテナ内で動作確認
   - EC2にデプロイして本番確認

## 💡 Tips

- **開発効率**: `docker-compose up`でローカル開発、`--build`不要（コード変更時のみ）
- **デバッグ**: `docker-compose logs -f <service>`でリアルタイムログ確認
- **クリーンビルド**: `docker-compose build --no-cache`でキャッシュなしビルド
- **ディスク節約**: `docker system prune -a`で未使用イメージ削除

---

作成日: 2025-11-02
最終更新: 2025-11-02
バージョン: 1.0
