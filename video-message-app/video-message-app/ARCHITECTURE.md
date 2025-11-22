# Video Message App - アーキテクチャ設計書

## システム概要

AI音声合成とD-ID APIを使用したビデオメッセージ生成アプリケーション

### コアテクノロジー
- **音声合成**: VOICEVOX + OpenVoice V2
- **動画生成**: D-ID API
- **バックエンド**: FastAPI (Python)
- **フロントエンド**: React 19
- **インフラ**: Docker + AWS EC2 (GPU)

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                      User Browser                            │
│                  https://3.115.141.166                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Nginx (Port 443/80)                        │
│              - SSL Termination                               │
│              - Reverse Proxy                                 │
└────────┬────────────────────────┬───────────────────────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐     ┌──────────────────────┐
│   Frontend       │     │   Backend API        │
│   (React)        │     │   (FastAPI)          │
│   Port: 80       │     │   Port: 55433        │
│   Container      │     │   Container          │
└──────────────────┘     └──────┬───────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  VOICEVOX    │  │  OpenVoice   │  │   D-ID API   │
    │  Engine      │  │  Native      │  │  (External)  │
    │  Port: 50021 │  │  Port: 8001  │  │              │
    │  Container   │  │  Host/Cont.  │  │              │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## サービス構成

### 1. Frontend (React Container)
- **役割**: ユーザーインターフェース
- **技術**: React 19, Material-UI
- **ポート**: 80 (コンテナ内部)
- **環境**: Production build

### 2. Backend (FastAPI Container)
- **役割**: APIサーバー、ビジネスロジック
- **技術**: FastAPI, Python 3.11
- **ポート**: 55433 (コンテナ内部)
- **主要機能**:
  - 音声合成オーケストレーション
  - D-ID API連携
  - ファイル管理
  - 音声プロファイル管理

### 3. VOICEVOX Engine (Container)
- **役割**: 日本語TTS
- **ポート**: 50021
- **環境**: CPU版（Mac互換性）

### 4. OpenVoice Native Service
- **役割**: 音声クローニング、声質変換
- **ポート**: 8001
- **環境**:
  - **EC2**: Docker Container (NVIDIA Runtime)
  - **Local**: Host環境（Mac MPS対応）

### 5. Nginx (Container)
- **役割**: リバースプロキシ、SSL終端
- **ポート**: 80, 443
- **機能**:
  - HTTPS対応
  - API/Frontend ルーティング
  - ファイルアップロード制限

## データフロー

### 音声生成フロー

```
1. User → Frontend
   ↓ (画像 + テキスト)

2. Frontend → Backend API (/api/d-id/create-video)
   ↓

3. Backend → Voice Synthesis
   ├─→ VOICEVOX (日本語基本音声)
   └─→ OpenVoice (声質変換)
       ↓ (音声ファイル)

4. Backend → D-ID API
   ↓ (画像 + 音声)

5. D-ID → Video Generation
   ↓

6. Backend → Frontend
   ↓ (動画URL)

7. Frontend → User
   (動画再生)
```

### 音声クローニングフロー

```
1. User → Frontend (音声サンプル x3)
   ↓

2. Frontend → Backend API (/api/voice-clone/create)
   ↓

3. Backend → OpenVoice Native Service
   ├─ 音声特徴抽出（Whisper）
   ├─ 埋め込みベクトル生成
   └─ .pkl ファイル保存
   ↓

4. Backend → Profile Storage
   └─ voices_metadata.json 更新

5. Backend → Frontend
   (プロファイルID)
```

## 環境別設定

### ローカル開発環境

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=local
      - OPENVOICE_SERVICE_URL=http://localhost:8001

  openvoice:
    # Host環境で実行（Mac MPS対応）
    # ポート: 8001
```

### EC2プロダクション環境

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=docker
      - OPENVOICE_SERVICE_URL=http://host.docker.internal:8001
    extra_hosts:
      - "host.docker.internal:host-gateway"

  openvoice:
    image: openvoice-native:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0
```

## パス管理戦略

### Docker環境でのパス変換

**Backend Container**:
- 内部パス: `/app/storage/`
- マウント: `./data/backend/storage:/app/storage`

**OpenVoice Service**:
- EC2 Docker: `/app/storage/` (同じマウント)
- Local Host: `/Users/.../data/backend/storage/`

### EnvironmentConfig による自動検出

```python
class EnvironmentConfig:
    @staticmethod
    def is_docker():
        return os.environ.get('ENVIRONMENT') == 'docker'

    @staticmethod
    def get_storage_path():
        if EnvironmentConfig.is_docker():
            return Path('/app/storage')
        else:
            return Path(__file__).parent.parent / 'data/backend/storage'
```

## セキュリティ

### SSL/TLS
- 自己証明書（開発/テスト）
- Let's Encrypt対応可能（`setup_letsencrypt.sh`）

### API認証
- D-ID API Key（環境変数）
- 内部サービス間通信は認証なし（Docker Network内）

### ファイルアップロード
- 最大サイズ: 100MB
- 許可形式: WAV, MP3, PNG, JPG

## スケーラビリティ

### 現在の制約
- シングルインスタンス
- GPU 1枚（Tesla T4）
- 同時処理数: ~5リクエスト

### 今後の拡張案
1. **水平スケーリング**
   - Kubernetes対応
   - Load Balancer

2. **非同期処理**
   - Celery + Redis
   - タスクキュー

3. **キャッシング**
   - 音声ファイルキャッシュ
   - プロファイルメタデータキャッシュ

## トラブルシューティング

### よくある問題

1. **OpenVoice接続エラー**
   - 原因: `host.docker.internal` 解決失敗
   - 解決: `extra_hosts` 設定確認

2. **embedding_path が null**
   - 原因: `openvoice_native_client.py` のバグ（修正済み）
   - 解決: レスポンスから `embedding_path` を抽出

3. **CUDA/CuDNN エラー**
   - 原因: LD_LIBRARY_PATH 未設定
   - 解決: systemd service に環境変数追加

## 参考リンク

- [CLAUDE.md](./CLAUDE.md) - プロジェクト詳細
- [SETUP.md](./SETUP.md) - セットアップ手順
- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
