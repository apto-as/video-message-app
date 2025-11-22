# 作業再開ガイド - Video Message App

## 現在の状態 (2025-08-02)

### 🏷️ 現在のバージョン
- **タグ**: `v1.0-openvoice-native`
- **コミット**: `f0492e7`
- **状態**: OpenVoice V2 Native Service統合完了

### 🚀 実装済み機能
1. **OpenVoice V2 Native Service** - Mac環境で動作する音声クローンサービス
2. **環境変数によるパス管理** - Docker/ローカル環境の自動判定
3. **音声クローン機能** - 完全実装、プロファイル管理機能付き
4. **D-ID動画生成** - リップシンク動画生成機能

### 📦 起動方法

#### 1. OpenVoice Native Service (別ターミナル)
```bash
cd openvoice_native
conda activate openvoice_v2
python main.py
```

#### 2. Docker環境
```bash
docker-compose up -d
```

#### 3. アクセスURL
- フロントエンド: http://localhost:55434
- バックエンドAPI: http://localhost:55433
- VoiceVoxエンジン: http://localhost:50021
- OpenVoice Native: http://localhost:8001

### 🔧 環境設定ファイル
- `backend/.env` - ローカル環境用
- `backend/.env.docker` - Docker環境用
- 両ファイルに `D_ID_API_KEY` の設定が必要

### 📁 重要なディレクトリ
```
video-message-app/
├── backend/                 # FastAPIバックエンド
├── frontend/               # Reactフロントエンド
├── openvoice_native/       # OpenVoice V2 Native Service
├── data/backend/storage/   # データ保存領域
│   ├── voices/profiles/    # 音声プロファイル
│   └── openvoice/         # 埋め込みファイル(.pkl)
└── docker-compose.yml     # Docker設定
```

### 🛠️ トラブルシューティング

#### Dockerが起動しない場合
```bash
# Docker Desktopを起動
open -a Docker

# 30秒待ってから再度起動
docker-compose up -d
```

#### プロファイルが表示されない場合
```bash
# メタデータの確認
cat data/backend/storage/voices/voices_metadata.json | jq

# APIの確認
curl http://localhost:55433/api/voice-clone/profiles | jq
```

#### OpenVoice Native Serviceエラー
```bash
# Conda環境の確認
conda info --envs

# 必要に応じて環境を再作成
conda env create -f openvoice_native/environment.yml
```

### 📝 次のステップ候補
1. **音声品質の向上** - ノイズ除去、音質改善
2. **UI/UXの改善** - より使いやすいインターフェース
3. **バッチ処理** - 複数動画の一括生成
4. **プロファイル管理強化** - インポート/エクスポート機能
5. **多言語対応** - 英語、中国語などの追加

### 🌸 Trinitas-Core からのメッセージ

**Springfield**: 「指揮官、いつでもカフェ・ズッケロでお待ちしております。温かいコーヒーと共に、開発の続きをサポートさせていただきます。」

**Krukai**: 「フン、次はもっと効率的な実装を見せてあげるわ。404の技術力を甘く見ないことね。」

**Vector**: 「……システムは安全に保護されています。次回も、あなたのプロジェクトを守り抜きます……」

---

## クイックリスタート

```bash
# 1. プロジェクトディレクトリへ移動
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app

# 2. 最新の状態を確認
git status
git pull

# 3. OpenVoice Native Service起動（別ターミナル）
cd openvoice_native && conda activate openvoice_v2 && python main.py

# 4. Docker環境起動
docker-compose up -d

# 5. ブラウザでアクセス
open http://localhost:55434
```

*作業再開時は、このガイドを参照してください。*