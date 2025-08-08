# 🍎 Mac環境用 VOICEVOX統合システム

**Phase 1: VOICEVOX + OpenVoice V2 統合による日本語音声システム**

## 📋 概要

このシステムは、Mac環境でVOICEVOXとOpenVoice V2を統合し、高品質な日本語音声合成を提供します。D-IDの代替技術として、完全にオープンソースの音声ソリューションを実現しています。

## 🎯 主な機能

- ✅ **VOICEVOX日本語音声合成**: 高品質な日本語音声（CPU最適化）
- ✅ **統合音声管理**: 複数プロバイダーの統一インターフェース
- ✅ **カスタム音声対応**: ユーザー音声のアップロードと管理
- ⚠️ **OpenVoice音声クローン**: Mac環境では制限付き
- ✅ **D-ID連携**: 既存のD-ID機能との並行利用

## 🛠️ システム要件

### 必須
- **OS**: macOS 11.0以降 (Intel/Apple Silicon対応)
- **Docker**: Docker Desktop 4.0以降
- **Node.js**: 16.0以降
- **Python**: 3.9以降
- **メモリ**: 8GB以上推奨

### 推奨
- **CPU**: 4コア以上
- **メモリ**: 16GB以上
- **ストレージ**: 5GB以上の空き容量

## 🚀 インストールと起動

### ワンステップセットアップ

```bash
# 1. プロジェクトディレクトリに移動
cd /path/to/video-message-app

# 2. Mac環境用セットアップを実行
./setup_mac.sh

# 3. システム起動
./start_mac.sh
```

### 手動セットアップ（詳細）

#### 1. 依存関係のインストール

```bash
# Homebrew（未インストールの場合）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 必要なツール
brew install ffmpeg node python3

# Docker Desktop
# https://www.docker.com/products/docker-desktop/ からダウンロード
```

#### 2. 環境変数設定

```bash
# .envファイルを作成
cp .env.example .env

# D-ID APIキーを設定（オプション）
nano .env
```

#### 3. Docker環境構築

```bash
# イメージビルド
docker-compose build

# VOICEVOX起動
docker-compose up -d voicevox
```

#### 4. 開発環境セットアップ

```bash
# バックエンド
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# フロントエンド
cd ../frontend
npm install
```

## 🎮 使用方法

### 基本操作

1. **システム起動**
   ```bash
   ./start_mac.sh
   ```

2. **ブラウザでアクセス**
   - メインアプリ: http://localhost:3000
   - API管理: http://localhost:8000/docs

3. **音声テスト**
   - 音声管理タブで各種音声を試聴
   - VOICEVOX音声の品質確認

4. **システム停止**
   ```bash
   ./stop_mac.sh
   ```

### 高度な使用法

#### VOICEVOX音声のカスタマイズ

```bash
# 音声合成パラメータAPI
curl -X POST "http://localhost:8000/api/voicevox/synthesis" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは、VOICEVOXです",
    "speaker_id": 1,
    "speed_scale": 1.0,
    "pitch_scale": 0.0,
    "preset": "normal"
  }'
```

#### 統合音声サービス

```bash
# 利用可能な音声一覧
curl "http://localhost:8000/api/unified-voice/voices"

# ヘルスチェック
curl "http://localhost:8000/api/unified-voice/health"
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. VOICEVOXが起動しない

```bash
# コンテナログ確認
docker-compose logs voicevox

# メモリ使用量確認
docker stats

# 再起動
docker-compose restart voicevox
```

#### 2. バックエンドAPIエラー

```bash
# バックエンドログ確認
docker-compose logs backend

# 依存関係再インストール
cd backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

#### 3. フロントエンドが表示されない

```bash
# Node.jsモジュール再インストール
cd frontend
rm -rf node_modules package-lock.json
npm install

# 開発サーバー再起動
npm start
```

#### 4. Apple Silicon (M1/M2) 固有の問題

```bash
# Rosetta 2でDockerを実行
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# または、設定でRosetta 2を有効化
# Docker Desktop > Settings > General > Use Rosetta for x86/amd64 emulation
```

### パフォーマンス最適化

#### CPU使用率が高い場合

```bash
# VOICEVOX CPU使用数を制限
# docker-compose.ymlで調整:
# - VOICEVOX_CPU_NUM_THREADS=1
```

#### メモリ使用量を抑える場合

```bash
# Dockerメモリ制限
# docker-compose.ymlで調整:
# deploy:
#   resources:
#     limits:
#       memory: 1G
```

## 📊 システム構成

### アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   VOICEVOX      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Docker)      │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 50021   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ 統合音声サービス    │
                    │ (Unified Voice) │
                    └─────────────────┘
```

### ディレクトリ構造

```
video-message-app/
├── backend/
│   ├── services/
│   │   ├── voicevox_client.py      # VOICEVOX統合
│   │   ├── openvoice_client.py     # OpenVoice統合
│   │   └── unified_voice_service.py # 統合サービス
│   ├── routers/
│   │   ├── voicevox.py            # VOICEVOX API
│   │   └── unified_voice.py       # 統合音声API
│   └── storage/                   # 音声ファイル保存
├── frontend/
│   └── src/components/
│       └── VoiceVoxSelector.js    # 音声選択UI
├── docker-compose.yml             # Mac最適化済み
├── setup_mac.sh                  # セットアップスクリプト
├── start_mac.sh                  # 起動スクリプト
└── stop_mac.sh                   # 停止スクリプト
```

## 📈 パフォーマンス指標

### 期待値（Mac環境）

| 項目 | 目標値 | 実測例 |
|------|--------|--------|
| VOICEVOX音声合成 | <3秒 | 1-2秒 |
| API応答時間 | <200ms | 50-150ms |
| システム起動時間 | <3分 | 2-3分 |
| メモリ使用量 | <4GB | 2-3GB |
| CPU使用率 | <50% | 20-40% |

### ベンチマーク

```bash
# 音声合成性能テスト
curl -w "@curl-format.txt" -X POST \
  "http://localhost:8000/api/voicevox/synthesis" \
  -H "Content-Type: application/json" \
  -d '{"text": "パフォーマンステスト実行中", "speaker_id": 1}'
```

## 🔮 今後の拡張予定

### Phase 2: リップシンク統合
- MuseTalk統合によるリアルタイム動画生成
- WebRTC対応によるストリーミング配信

### Phase 3: 完全独立システム
- D-ID完全代替
- エンタープライズ機能追加

## 📞 サポート

### ドキュメント
- [API仕様書](http://localhost:8000/docs)
- [VOICEVOX公式](https://voicevox.hiroshiba.jp/)
- [OpenVoice](https://github.com/myshell-ai/OpenVoice)

### 問題報告
Issue を作成するか、以下の情報を含めてお問い合わせください：

```bash
# システム情報収集
echo "=== システム情報 ==="
uname -a
docker --version
docker-compose --version
python3 --version
node --version

echo "=== Dockerコンテナ状態 ==="
docker-compose ps

echo "=== ログ（最新50行） ==="
docker-compose logs --tail=50
```

---

**Mac環境用 VOICEVOX統合システム v1.0**

*"日本語音声合成の新しいスタンダード、Mac環境で完全実現"*