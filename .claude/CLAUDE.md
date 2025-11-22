# Video Message App - Project Guide

## Project Overview

AI駆動のビデオメッセージ生成アプリケーション。D-ID API、VOICEVOX、OpenVoice V2を組み合わせて、写真とテキストから話すアバター動画を生成します。

**プロジェクト期間**: 〜2026年12月まで

**技術スタック**:
- Backend: FastAPI (Python 3.11)
- Frontend: React 19
- AI Services: OpenVoice V2, VOICEVOX, D-ID
- Infrastructure: Docker, AWS EC2 (g4dn.xlarge)

---

## Quick Start

### ⚠️ 重要: 環境の役割

**ローカル環境（Mac）**:
- **役割**: コード編集専用
- **用途**: ソースコード確認・修正・保存・コミット・プッシュのみ
- **動作確認**: ❌ ローカルでは動作確認しない（Docker環境は構築していない）

**本番環境（EC2）**:
- **役割**: 動作確認・本番運用
- **用途**: git pullでソースコード共有、すべての動作確認はEC2で実施

### ローカル開発（Mac）

```bash
# コード編集のみ
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app

# 編集後、コミット・プッシュ
git add .
git commit -m "feat: 修正内容"
git push origin main
```

### 本番デプロイ（EC2）

```bash
# 1. EC2インスタンス起動
aws ec2 start-instances --instance-ids i-0267e9e09093fd8b7 \
    --profile aws-mcp-admin-agents --region ap-northeast-1

# 2. 接続（30秒待機）
sleep 30
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166

# 3. 最新コードをプル + デプロイ
cd ~/video-message-app/video-message-app
git pull origin main
docker-compose up -d
```

**本番URL（HTTPS経由）**:
- **Frontend**: https://3.115.141.166/
- **Backend API**: https://3.115.141.166/api/
- **ヘルスチェック**: https://3.115.141.166/api/health

**アーキテクチャ**:
```
[ユーザー] → HTTPS (443)
    ↓
[Nginx Reverse Proxy]
    ├→ Frontend (内部 80ポート)
    ├→ Backend (内部 55433ポート、/api/* 経由)
    ├→ OpenVoice (内部 8001ポート、外部非公開)
    └→ VOICEVOX (内部 50021ポート、外部非公開)
```

**注意**: ポート55434, 55433, 8001, 50021は外部公開されていません。すべてnginx経由でアクセスしてください。

---

## Architecture Decisions (ADR)

### ADR-001: Python 3.11移行完了 (2025-11-02)

**Status**: ✅ Implemented

**Context**:
- Python 3.9 EOL: 2025年10月5日（残り7ヶ月）
- プロジェクト期間: 2026年12月まで（14ヶ月）
- YOLO環境（将来機能）との互換性確保

**Decision**: EC2環境をPython 3.9.23 → 3.11.9に移行

**Consequences**:
- ✅ セキュリティサポート期間を19ヶ月延長
- ✅ 最新ライブラリとの互換性確保
- ⚠️ パッケージバージョン変更が必要
  - numpy: 1.22.0 → 1.26.4
  - ctranslate2: 3.24.0 → 4.6.0 → 3.24.0 (melottsによりダウングレード)
  - faster-whisper: 0.9.0 → 1.2.1
  - librosa: 0.9.1 → 0.10.0 → 0.9.1 (melottsによりダウングレード)

**Implementation Details**:
```bash
# EC2での実装
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native
python3.11 -m venv venv_py311
source venv_py311/bin/activate
pip install numpy==1.24.0
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download  # 526MB
```

**Verification**: ✅ CUDA (Tesla T4) で正常稼働確認済み

---

### ADR-002: Docker統一戦略 (2025-11-02)

**Status**: 🚧 Planned

**Context**:
- Mac (ARM64, MPS) と EC2 (x86_64, CUDA) の環境差異
- パッケージバージョン管理の複雑化
- デプロイの一貫性確保

**Decision**: すべてのサービスをDockerコンテナで統一

**Benefits**:
- 環境差異の完全吸収
- 依存関係の再現性保証
- デプロイの簡素化

**Implementation Plan**:
1. OpenVoice Native Service の Docker化
2. Backend の Docker化（既存）
3. Frontend の Docker化（既存）
4. docker-compose.yml の統一

**Target Structure**:
```yaml
services:
  openvoice:
    build:
      context: ./openvoice_native
      args:
        - USE_CUDA=${USE_CUDA:-false}
    environment:
      - DEVICE=${DEVICE:-cpu}
    volumes:
      - ./data/backend/storage:/app/storage
```

---

## Environment Setup

### 環境差異マトリックス

| 項目 | Mac (開発) | EC2 (本番) | Docker (統一) |
|-----|-----------|-----------|-------------|
| **アーキテクチャ** | ARM64 | x86_64 | 両対応 |
| **GPU** | MPS (Metal) | CUDA (T4) | 環境変数で切替 |
| **Python** | 3.11.12 (Conda) | 3.11.9 (venv) | 3.11-slim |
| **PyTorch** | 2.0.1 (CPU/MPS) | 2.0.1+cu118 | ビルド時に選択 |
| **デプロイ** | docker-compose | docker-compose | 同一 |

### EC2 (Production)

**インスタンス情報**:
- Instance ID: `i-0267e9e09093fd8b7`
- Instance Type: g4dn.xlarge
- GPU: NVIDIA Tesla T4
- OS: Amazon Linux 2023
- Public IP: 3.115.141.166
- Region: ap-northeast-1 (Tokyo)

**Python環境**:
```bash
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native
source venv_py311/bin/activate
python --version  # Python 3.11.9

# デバイス確認
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# CUDA: True
```

**必須パッケージ（EC2専用）**:
```txt
torch==2.0.1+cu118
torchaudio==2.0.2+cu118
numpy==1.26.4
melotts==0.1.2 (from GitHub)
faster-whisper==1.2.1
whisper-timestamped==1.15.9
```

**サービス起動**:
```bash
cd /home/ec2-user/video-message-app/video-message-app/openvoice_native
source venv_py311/bin/activate
nohup python -u main.py > openvoice.log 2>&1 &

# プロセス確認
ps aux | grep main.py
curl http://localhost:8001/health
```

### Mac (Development)

**Python環境**:
```bash
conda activate openvoice_v2
python --version  # Python 3.11.12

# デバイス確認
python -c "import torch; print(f'MPS: {torch.backends.mps.is_available()}')"
# MPS: True
```

**必須パッケージ（Mac専用）**:
```txt
torch==2.0.1  # CPU/MPS版
torchaudio==2.0.2
numpy>=1.24.0,<2.0.0
# CUDA版パッケージは不要
```

**サービス起動**:
```bash
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/openvoice_native
conda activate openvoice_v2
python main.py
```

---

## Docker Configuration

### ディレクトリ構成（目標）

```
video-message-app/
├── .env                        # 環境変数（gitignore）
├── .env.example                # 環境変数のサンプル
├── docker-compose.yml          # 本番・開発共通
├── docker-compose.override.yml # ローカル開発用オーバーライド
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── Dockerfile
│   └── ...
├── openvoice_native/
│   ├── Dockerfile              # 🆕 作成予定
│   ├── requirements.txt
│   ├── main.py
│   └── OpenVoiceV2/           # Git submodule
├── data/
│   ├── backend/storage/        # 永続データ
│   └── logs/
└── scripts/
    ├── deploy.sh
    └── backup.sh
```

### OpenVoice Native Dockerfile（設計案）

```dockerfile
# openvoice_native/Dockerfile
FROM python:3.11-slim

# ビルド引数
ARG USE_CUDA=false

# 基本パッケージ
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# CUDA対応（EC2）
RUN if [ "$USE_CUDA" = "true" ]; then \
    # CUDA toolkitのインストール
    apt-get update && apt-get install -y \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*; \
fi

WORKDIR /app

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MeloTTS（GitHub）
RUN pip install --no-cache-dir git+https://github.com/myshell-ai/MeloTTS.git

# UniDic辞書（526MB）
RUN python -m unidic download

# アプリケーション
COPY . /app

# モデルファイル確認
RUN test -d /app/data/openvoice/checkpoints_v2 || \
    echo "Warning: Model files not found. Mount volume at /app/data"

EXPOSE 8001

CMD ["python", "-u", "main.py"]
```

### docker-compose.yml（統一版）

```yaml
version: '3.8'

services:
  # OpenVoice Native Service
  openvoice:
    build:
      context: ./openvoice_native
      args:
        USE_CUDA: ${USE_CUDA:-false}
    container_name: openvoice_native
    environment:
      - DEVICE=${DEVICE:-cpu}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./data/backend/storage:/app/storage
      - ./openvoice_native/data/openvoice:/app/data/openvoice:ro
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # Backend API
  backend:
    build: ./backend
    container_name: voice_backend
    environment:
      - D_ID_API_KEY=${D_ID_API_KEY}
      - OPENVOICE_URL=http://openvoice:8001
    volumes:
      - ./data/backend/storage:/app/storage
    ports:
      - "55433:55433"
    depends_on:
      - openvoice
    restart: unless-stopped

  # Frontend
  frontend:
    build: ./frontend
    container_name: voice_frontend
    environment:
      - REACT_APP_API_URL=http://localhost:55433
    ports:
      - "55434:55434"
    depends_on:
      - backend
    restart: unless-stopped

  # VOICEVOX Engine
  voicevox:
    image: voicevox/voicevox_engine:cpu-latest
    container_name: voicevox_engine
    ports:
      - "50021:50021"
    restart: unless-stopped
```

### .env.example

```bash
# Environment: development / production
ENVIRONMENT=development

# GPU Configuration
# Mac: USE_CUDA=false, DEVICE=mps
# EC2: USE_CUDA=true, DEVICE=cuda
USE_CUDA=false
DEVICE=cpu

# D-ID API Key
D_ID_API_KEY=your-d-id-api-key-here

# OpenVoice Service
OPENVOICE_URL=http://openvoice:8001
```

### docker-compose.override.yml（Mac専用）

```yaml
version: '3.8'

services:
  openvoice:
    build:
      args:
        USE_CUDA: false
    environment:
      - DEVICE=mps
    deploy:
      resources:
        reservations:
          devices: []  # GPUセクションを無効化
```

---

## API Reference

### OpenVoice Native Service

**Base URL**:
- Local: http://localhost:8001
- EC2: http://3.115.141.166:8001

**Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | ルート |
| GET | `/health` | ヘルスチェック |
| POST | `/voice-clone/create` | ボイスクローン作成 |
| POST | `/voice-clone/synthesize` | 音声合成 |
| GET | `/voice-clone/profiles` | プロファイル一覧 |
| DELETE | `/voice-clone/profiles/{profile_id}` | プロファイル削除 |

**Health Check Response**:
```json
{
  "status": "healthy",
  "service": "OpenVoice Native Service",
  "version": "1.0.0",
  "openvoice_available": true,
  "pytorch_device": "cuda",
  "model_files_status": {
    "checkpoint": true,
    "config": true,
    "japanese_speaker": true,
    "english_speaker": true
  }
}
```

**既存のボイスプロファイル**:
1. 女性１ (openvoice_c403f011) - 2025-09-13作成
2. 男性１ (openvoice_78450a3c) - 2025-09-14作成
3. 男性2 (openvoice_d4be3324) - 2025-10-06作成

---

## Troubleshooting

### OpenVoice起動失敗

#### 症状: `No module named 'whisper_timestamped'`
**原因**: whisper-timestampedがインストールされていない
**解決**:
```bash
pip install whisper-timestamped==1.14.2
```

#### 症状: `MeCab initialization failed`
**原因**: UniDic辞書がダウンロードされていない
**解決**:
```bash
python -m unidic download  # 526MBのダウンロード
```

#### 症状: `No module named 'melo'`
**原因**: melottsパッケージがインストールされていない（pipパッケージが壊れている）
**解決**:
```bash
pip install git+https://github.com/myshell-ai/MeloTTS.git
```

#### 症状: `CUDA out of memory`
**原因**: GPU メモリ不足
**解決**:
```python
# config.py で batch_size を削減
BATCH_SIZE = 1  # デフォルトから削減
```

### Docker関連

#### 症状: `nvidia-docker: command not found`
**原因**: NVIDIA Docker runtimeがインストールされていない（EC2）
**解決**:
```bash
# NVIDIA Docker runtime インストール
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

---

## Security

### 認証情報の管理

**絶対にGitにコミットしてはいけない情報**:
- AWS IAM認証情報
- D-ID API Key
- 環境変数ファイル (`.env`)

**保管場所**:

1. **AWS認証情報**:
   ```bash
   # ローカル
   ~/.aws/credentials

   [aws-mcp-admin-agents]
   aws_access_key_id = AKIA...
   aws_secret_access_key = ...
   ```

2. **D-ID API Key**:
   ```bash
   # ローカル
   ~/secure_credentials/d_id_api_key.txt

   # EC2（推奨: AWS Secrets Manager）
   aws secretsmanager get-secret-value \
     --secret-id video-message-app/d-id-api-key \
     --query SecretString \
     --output text
   ```

3. **環境変数**:
   ```bash
   # .env（gitignore済み）
   D_ID_API_KEY=your-actual-key-here

   # .env.example（Gitにコミット可能）
   D_ID_API_KEY=your-d-id-api-key-here
   ```

---

## Monitoring & Logs

### ログ確認

**EC2（直接起動の場合）**:
```bash
tail -f ~/video-message-app/video-message-app/openvoice_native/openvoice.log
```

**Docker**:
```bash
# すべてのコンテナ
docker-compose logs -f

# 特定のサービス
docker logs openvoice_native --tail 100 -f
docker logs voice_backend --tail 100 -f
```

### プロセス確認

**EC2**:
```bash
ps aux | grep main.py
ps aux | grep uvicorn
```

**Docker**:
```bash
docker-compose ps
docker stats
```

### ヘルスチェック

```bash
# OpenVoice
curl http://localhost:8001/health | jq

# Backend
curl http://localhost:55433/health | jq

# Frontend
curl http://localhost:55434
```

---

## Deployment

### EC2デプロイ手順

```bash
# 1. EC2起動
aws ec2 start-instances --instance-ids i-0267e9e09093fd8b7 \
    --profile aws-mcp-admin-agents --region ap-northeast-1

# 2. 接続確認（30秒待機）
sleep 30
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166 "echo 'Connected'"

# 3. 最新コードをプル（必要に応じて）
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166 << 'EOF'
cd ~/video-message-app/video-message-app
git pull origin main
EOF

# 4. Dockerコンテナ起動
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166 << 'EOF'
cd ~/video-message-app/video-message-app
docker-compose up -d
docker-compose ps
EOF

# 5. ヘルスチェック
curl http://3.115.141.166:8001/health
curl http://3.115.141.166:55433/health
```

### 停止手順

```bash
# 1. Dockerコンテナ停止
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166 \
    "cd ~/video-message-app/video-message-app && docker-compose down"

# 2. EC2インスタンス停止
aws ec2 stop-instances --instance-ids i-0267e9e09093fd8b7 \
    --profile aws-mcp-admin-agents --region ap-northeast-1
```

---

## Development Workflow

### ローカル開発フロー

1. **環境準備**:
   ```bash
   cd ~/workspace/github.com/apto-as/prototype-app/video-message-app
   cp .env.example .env
   # .env を編集（D-ID API Keyなど）
   ```

2. **Docker起動**:
   ```bash
   docker-compose up -d
   docker-compose logs -f
   ```

3. **開発**:
   - Frontend: http://localhost:55434
   - Backend API: http://localhost:55433/docs
   - OpenVoice: http://localhost:8001/docs

4. **テスト**:
   ```bash
   # Backend
   docker exec -it voice_backend pytest tests/

   # OpenVoice
   docker exec -it openvoice_native python -m pytest
   ```

5. **停止**:
   ```bash
   docker-compose down
   ```

### Git Workflow

```bash
# 1. ブランチ作成
git checkout -b feature/new-feature

# 2. 開発・コミット
git add .
git commit -m "feat: Add new feature"

# 3. プッシュ
git push origin feature/new-feature

# 4. プルリクエスト作成（GitHub）
```

---

## Future Roadmap

### Phase 1: Docker統一化（2025-11月）
- [x] EC2 Python 3.11移行完了
- [ ] OpenVoice Docker化
- [ ] docker-compose統一
- [ ] Mac環境での動作確認

### Phase 2: YOLO統合（2025-12月）
- [ ] YOLOv11環境構築
- [ ] 物体検出API実装
- [ ] フロントエンド統合

### Phase 3: 機能拡張（2026年）
- [ ] リアルタイムプレビュー
- [ ] 複数言語対応
- [ ] クラウドストレージ統合

---

## Contact & Support

**プロジェクト所在地**:
- Local: `~/workspace/github.com/apto-as/prototype-app`
- EC2: `~/video-message-app/video-message-app`

**ドキュメント**:
- この CLAUDE.md: プロジェクト固有の情報
- グローバル CLAUDE.md: 一般的なルールとガイドライン
- `video-message-app/ARCHITECTURE.md`: アーキテクチャ詳細
- `video-message-app/DEPLOYMENT.md`: デプロイメント詳細

**更新履歴**:
- 2025-11-02: 初版作成、Python 3.11移行完了、Docker化計画
