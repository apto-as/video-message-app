# Video Message App

AI音声合成とD-ID APIを使用した、トーキングアバタービデオ生成アプリケーション

## 🎯 プロジェクト概要

写真とテキストから、AIが音声を合成し、D-IDで動く動画を生成するWebアプリケーションです。

### 主な機能

- ✨ **AI音声合成**: VOICEVOX + OpenVoice V2による高品質な日本語音声
- 🎭 **声質クローニング**: 自分の声でアバターを喋らせることができる
- 🎬 **動画生成**: D-ID APIによるリアルなトーキングアバター
- 🚀 **高速処理**: GPU加速（CUDA対応）
- 🔒 **セキュアな接続**: HTTPS対応

## 🏗️ アーキテクチャ

```
Frontend (React 19)
    ↓
Backend (FastAPI)
    ↓
├─→ VOICEVOX (基本音声)
├─→ OpenVoice V2 (声質変換)
└─→ D-ID API (動画生成)
```

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md) を参照

## 🚀 クイックスタート

### 必要なもの

- Docker Desktop
- D-ID APIキー（[https://studio.d-id.com/](https://studio.d-id.com/)）
- SSH鍵（EC2接続用、プロダクションのみ）

### ローカル開発環境

```bash
# 1. リポジトリクローン
git clone <repository-url>
cd video-message-app/video-message-app

# 2. 環境変数設定
cp .env.example .env
# .env を編集して D_ID_API_KEY を設定

# 3. OpenVoice Service起動（別ターミナル）
cd openvoice_native
conda create -n openvoice_v2 python=3.11
conda activate openvoice_v2
pip install -r requirements.txt
python main.py

# 4. Dockerサービス起動
cd ..
docker-compose up -d

# 5. アクセス
open https://localhost
```

詳細は [SETUP.md](./SETUP.md) を参照

## 📦 デプロイ

### EC2へのデプロイ

```bash
# ワンコマンドデプロイ
./deploy.sh deploy

# バックエンドのみ更新
./deploy.sh deploy --service=backend

# ステータス確認
./deploy.sh status
```

詳細は [DEPLOYMENT.md](./DEPLOYMENT.md) を参照

## 🛠️ 技術スタック

### Frontend
- React 19
- Material-UI
- Axios

### Backend
- FastAPI (Python 3.11)
- httpx (非同期HTTP)
- Pydantic (データ検証)

### 音声合成
- **VOICEVOX**: 日本語TTS
- **OpenVoice V2**: 声質クローニング
  - Whisper (音声特徴抽出)
  - Tone Color Converter (声質変換)

### インフラ
- Docker + Docker Compose
- Nginx (リバースプロキシ)
- AWS EC2 (GPU: Tesla T4)
- CUDA 12.8

## 📚 ドキュメント

- [SETUP.md](./SETUP.md) - セットアップ手順
- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ
- [CLAUDE.md](./CLAUDE.md) - プロジェクト詳細（Claude Code用）

## 🔧 開発

### ディレクトリ構造

```
video-message-app/
├── backend/              # FastAPI バックエンド
│   ├── routers/         # APIルーター
│   ├── services/        # ビジネスロジック
│   └── main.py          # エントリーポイント
├── frontend/            # React フロントエンド
│   └── src/
│       ├── components/  # UIコンポーネント
│       └── services/    # API通信
├── openvoice_native/    # OpenVoice Service
│   ├── openvoice_service.py
│   └── main.py
├── nginx/               # Nginx設定
├── data/                # データ永続化（.gitignore）
│   └── backend/storage/ # 音声ファイル、埋め込み
└── docker-compose.yml   # Docker構成
```

### 環境別設定

#### ローカル開発

```bash
# .env.local
APP_ENVIRONMENT=local
OPENVOICE_URL=http://localhost:8001
MOUNT_CODE=rw  # ホットリロード有効
```

#### EC2プロダクション

```bash
# .env.prod
APP_ENVIRONMENT=production
OPENVOICE_URL=http://host.docker.internal:8001
MOUNT_CODE=ro
CUDA_DEVICE=0
```

### Docker統一環境（推奨）

```bash
# ローカル
docker-compose -f docker-compose.unified.yml --env-file .env.local up -d

# EC2（OpenVoice含む）
docker-compose -f docker-compose.unified.yml --env-file .env.prod --profile production up -d
```

## 🐛 トラブルシューティング

### よくある問題

#### 1. OpenVoice接続エラー

```bash
# サービス確認
curl http://localhost:8001/health

# EC2の場合
sudo systemctl status openvoice
```

#### 2. embedding_path が null

**原因**: `openvoice_native_client.py` のバグ（修正済み）

**解決済み**: レスポンスから `embedding_path` を抽出するように修正

#### 3. CUDA/CuDNN エラー

```bash
# LD_LIBRARY_PATH 確認（EC2）
sudo systemctl cat openvoice | grep LD_LIBRARY_PATH
```

詳細は各ドキュメントの「トラブルシューティング」セクションを参照

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📝 変更履歴

### v1.1.0 (2025-01-06)

- ✅ `embedding_path` null問題の修正
- ✅ Docker統一環境の整備
- ✅ デプロイスクリプトの追加
- ✅ ドキュメント整備

### v1.0.0 (2024-12-XX)

- ✨ 初期リリース
- ✨ VOICEVOX + OpenVoice統合
- ✨ D-ID API連携
- ✨ EC2プロダクション環境構築

## 📄 ライセンス

This project is licensed under the MIT License

## 🙏 謝辞

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - オープンソース日本語TTS
- [OpenVoice V2](https://github.com/myshell-ai/OpenVoice) - 声質クローニング
- [D-ID](https://www.d-id.com/) - トーキングアバター生成API

## 📧 連絡先

質問や問題がある場合は、Issueを作成してください。

---

**Built with ❤️ using Claude Code**
