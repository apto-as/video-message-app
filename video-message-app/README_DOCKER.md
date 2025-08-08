# 🐳 Docker版 ビデオメッセージアプリ

OpenVoice V2 + VOICEVOX + D-ID ハイブリッド動画生成システム

## 🚀 クイックスタート

### 1. 環境設定

```bash
# リポジトリをクローン
git clone [your-repo-url]
cd video-message-app

# 環境変数ファイルを作成
cp .env.example .env

# .envファイルを編集してD-ID APIキーを設定
nano .env
```

### 2. アプリケーション起動

```bash
# 自動起動スクリプトを実行
./docker-start.sh
```

### 3. アプリケーション停止

```bash
# 自動停止スクリプトを実行
./docker-stop.sh
```

## 📱 アクセス情報

| サービス | URL | 説明 |
|---------|-----|------|
| **フロントエンド WebUI** | http://localhost:55434 | メイン操作画面 |
| **バックエンド API** | http://localhost:55433 | REST API |
| **VOICEVOX エンジン** | http://localhost:50021 | 音声合成エンジン |

## 🎙️ 利用可能な機能

### 1. VOICEVOX 音声合成
- 日本語特化の高品質音声合成
- ズンダモン、四国めたんなどのキャラクター音声
- リアルタイム音声生成

### 2. OpenVoice V2 音声クローン
- 自分の声をクローンして動画生成
- 多言語対応（日本語、英語、中国語など）
- 感情表現のカスタマイズ

### 3. D-ID 動画生成
- 写真から話す動画を生成
- リップシンク技術
- 高品質な映像出力

### 4. ハイブリッドシステム
- 3つの技術を組み合わせた最適化
- 用途に応じた自動選択
- シームレスな統合体験

## 🛠️ 開発者向けコマンド

### Docker Compose コマンド

```bash
# コンテナ起動（バックグラウンド）
docker-compose up -d

# コンテナ停止
docker-compose down

# ログ確認
docker-compose logs [service-name]

# 特定サービスの再起動
docker-compose restart [service-name]

# イメージ再ビルド
docker-compose build

# 完全クリーンアップ（ボリューム含む）
docker-compose down --volumes --remove-orphans
```

### サービス名

- `voicevox` - VOICEVOX音声合成エンジン
- `backend` - FastAPI バックエンド
- `frontend` - React フロントエンド

### ログ確認例

```bash
# 全サービスのログ
docker-compose logs

# バックエンドのログのみ
docker-compose logs backend

# リアルタイムログ監視
docker-compose logs -f frontend
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. ポートが既に使用されている

```bash
# ポート使用状況確認
lsof -i :55433
lsof -i :55434
lsof -i :50021

# 強制停止
./docker-stop.sh
```

#### 2. Docker コンテナが起動しない

```bash
# ログ確認
docker-compose logs

# システムリソース確認
docker system df

# イメージ再ビルド
docker-compose build --no-cache
```

#### 3. VOICEVOX が応答しない

```bash
# VOICEVOXコンテナの状態確認
docker-compose ps voicevox

# VOICEVOXログ確認
docker-compose logs voicevox

# VOICEVOXコンテナ再起動
docker-compose restart voicevox
```

#### 4. メモリ不足エラー

```bash
# .envファイルでメモリ制限を調整
VOICEVOX_MEMORY_LIMIT=1  # 2GB → 1GB
BACKEND_MEMORY_LIMIT=512M  # 1GB → 512MB

# Docker Desktop のメモリ設定を確認
```

### システム要件

- **OS**: macOS 10.15+, Ubuntu 18.04+, Windows 10+
- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **メモリ**: 最低4GB推奨
- **ディスク容量**: 5GB以上

### パフォーマンス最適化

#### Mac環境での最適化

```bash
# .envファイルでCPUスレッド数を調整
VOICEVOX_CPU_NUM_THREADS=1  # Mac M1では1-2推奨

# Docker Desktop リソース制限
# CPU: 4コア, メモリ: 8GB, スワップ: 2GB
```

## 📚 API ドキュメント

### バックエンド API

- **Swagger UI**: http://localhost:55433/docs
- **OpenAPI仕様**: http://localhost:55433/openapi.json

### 主要エンドポイント

```bash
# ヘルスチェック
curl http://localhost:55433/health

# 音声一覧取得
curl http://localhost:55433/api/unified-voice/voices

# VOICEVOX スピーカー一覧
curl http://localhost:50021/speakers

# 動画生成（VOICEVOX）
curl -X POST http://localhost:55433/api/hybrid-video/generate-with-voicevox \
  -F "image=@your-image.jpg" \
  -F "text=こんにちは、世界！" \
  -F "speaker_id=3"

# 動画生成（OpenVoice）
curl -X POST http://localhost:55433/api/hybrid-video/generate-with-openvoice \
  -F "image=@your-image.jpg" \
  -F "text=Hello, World!" \
  -F "voice_profile_id=your-voice-id"
```

## 🔐 セキュリティ

### 環境変数の管理

- `.env` ファイルは **絶対にGitにコミットしない**
- 本番環境では強力なAPIキーを使用
- CORS設定を適切に構成

### API キーの取得

1. **D-ID API**: https://www.d-id.com/ でアカウント作成
2. APIキーを取得して `.env` ファイルに設定

```bash
# .env ファイル例
DID_API_KEY=your_actual_api_key_here
```

## 🤝 貢献・開発

### 開発環境セットアップ

```bash
# 開発用起動（ホットリロード有効）
docker-compose -f docker-compose.dev.yml up

# テスト実行
docker-compose exec backend python -m pytest
docker-compose exec frontend npm test
```

### コード品質

```bash
# リンター実行
docker-compose exec backend black .
docker-compose exec frontend npm run lint

# 型チェック
docker-compose exec backend mypy .
docker-compose exec frontend npm run type-check
```

## 📞 サポート

- **GitHub Issues**: [プロジェクトのIssuesページ]
- **ドキュメント**: プロジェクト内のREADMEファイル群
- **ログ確認**: `docker-compose logs` コマンド

---

**Video Message App** - OpenVoice V2 + VOICEVOX + D-ID による次世代動画生成システム 🎬✨