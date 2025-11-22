# ローカル開発環境 クイックスタートガイド

**ワークフロー**: Local-First with Remote Testing（承認済み）
**セットアップ時間**: 15分
**作成日**: 2025-11-02

---

## 🎯 このガイドについて

このガイドでは、**Macローカル環境**で90%の開発を行い、GPU処理が必要な時だけEC2を使用する「Local-First」ワークフローのセットアップ手順を説明します。

### メリット
- ✅ ホットリロード <0.5秒（リモートの6倍高速）
- ✅ ネイティブデバッグ（VSCodeブレークポイント使用可能）
- ✅ コスト削減：$0/日（ローカル） vs $5/日（24/7 EC2）
- ✅ オフライン作業可能

---

## 📋 前提条件

### 必須ソフトウェア

```bash
# 1. Docker Desktop（VOICEVOXコンテナ用）
# https://www.docker.com/products/docker-desktop/
# インストール後、Docker Desktopを起動してください

# 2. Homebrew（パッケージマネージャー）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Python 3.11（FastAPI Backend用）
brew install python@3.11

# 4. Node.js 20+（React Frontend用）
brew install node

# 5. Conda（OpenVoice Native Service用）
brew install --cask miniconda
conda init zsh  # または bash
```

### 任意ソフトウェア（推奨）

```bash
# 6. FFmpeg（音声・動画処理）
brew install ffmpeg

# 7. Git LFS（大容量ファイル管理）
brew install git-lfs
git lfs install
```

---

## ⚡ クイックスタート（15分）

### Step 1: プロジェクトクローンとD-ID APIキー設定（2分）

```bash
# 1. リポジトリをクローン
cd ~/workspace
git clone https://github.com/apto-as/video-message-app.git
cd video-message-app

# 2. D-ID APIキーを設定
# secure_credentialsから読み込み
export D_ID_API_KEY=$(grep "D_ID_API_KEY=" ~/secure_credentials/d_id_api_key.txt | cut -d'=' -f2)

# 3. Backend .envファイルに設定
cd video-message-app/backend
cp .env.example .env

# macOS
sed -i '' "s/your-d-id-api-key-here/$D_ID_API_KEY/" .env

# または手動で編集
nano .env  # D_ID_API_KEY行を実際のキーに変更
```

### Step 2: OpenVoice Native Service セットアップ（5分）

```bash
# 1. Conda環境作成
conda create -n openvoice_v2 python=3.11.12 -y
conda activate openvoice_v2

# 2. OpenVoice Native Service起動
cd ~/workspace/video-message-app/openvoice_native
pip install -r requirements.txt

# 3. サービス起動（バックグラウンド）
nohup python main.py > openvoice.log 2>&1 &

# 4. ヘルスチェック
sleep 5
curl http://localhost:8001/health

# 期待される出力:
# {"status": "healthy", "service": "OpenVoice Native"}
```

### Step 3: VOICEVOXコンテナ起動（2分）

```bash
# 1. Docker Desktopが起動していることを確認
open -a Docker

# 30秒待機
sleep 30

# 2. VOICEVOXコンテナ起動
cd ~/workspace/video-message-app/video-message-app
docker-compose up -d voicevox

# 3. ヘルスチェック
sleep 10
curl http://localhost:50021/version

# 期待される出力:
# "0.14.0"（またはバージョン番号）
```

### Step 4: Backend（FastAPI）起動（3分）

```bash
# 1. 依存パッケージインストール
cd ~/workspace/video-message-app/video-message-app/backend
pip install -r requirements.txt

# 2. ホットリロード有効でサーバー起動
uvicorn main:app --host 0.0.0.0 --port 55433 --reload

# 別ターミナルで確認
curl http://localhost:55433/health

# 期待される出力:
# {"status": "healthy", "services": {"voicevox": "ok", "openvoice": "ok"}}
```

### Step 5: Frontend（React）起動（3分）

```bash
# 新しいターミナルを開く
cd ~/workspace/video-message-app/video-message-app/frontend

# 1. 依存パッケージインストール
npm install

# 2. 開発サーバー起動（ホットリロード有効）
npm run dev

# 出力例:
#   VITE v5.0.0  ready in 500 ms
#   ➜  Local:   http://localhost:55434/
```

### Step 6: ブラウザでアクセス

```bash
# ブラウザを開く
open http://localhost:55434
```

**完了！** ローカル開発環境が起動しました 🎉

---

## 🔧 日常の開発フロー

### 朝の起動（2分）

```bash
# Terminal 1: OpenVoice Native Service
cd ~/workspace/video-message-app/openvoice_native
conda activate openvoice_v2
nohup python main.py > openvoice.log 2>&1 &

# Terminal 2: VOICEVOX
cd ~/workspace/video-message-app/video-message-app
docker-compose up -d voicevox

# Terminal 3: Backend
cd ~/workspace/video-message-app/video-message-app/backend
uvicorn main:app --host 0.0.0.0 --port 55433 --reload

# Terminal 4: Frontend
cd ~/workspace/video-message-app/video-message-app/frontend
npm run dev
```

### 開発作業（6-8時間）

1. **コード編集**: VSCodeで編集
2. **自動リロード**: 保存すると自動的に反映（0.5秒）
3. **テスト**: `http://localhost:55434` でUIテスト
4. **API確認**: `curl http://localhost:55433/api/...`

### 夕方の停止（1分）

```bash
# Backend/Frontend: Ctrl+C で停止

# VOICEVOX停止
docker-compose down

# OpenVoice Native Service停止
pkill -f "python main.py"
```

---

## 🧪 GPU処理テスト（EC2使用時のみ）

BiRefNet背景除去など、GPU処理が必要な場合のみEC2を使用：

### EC2インスタンス起動（手動）

```bash
# AWSコンソールまたはCLIで手動起動
# ⚠️ Rule 11: 自動起動禁止、必ず手動で起動すること

# CLI例（手動実行）
aws ec2 start-instances \
  --instance-ids i-xxxxxxxxx \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# 起動完了待機（約30秒）
aws ec2 wait instance-running \
  --instance-ids i-xxxxxxxxx \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

echo "EC2起動完了"
```

### EC2でGPU処理テスト

```bash
# SSH接続
ssh ec2-user@3.115.141.166

# Dockerサービス起動
cd /home/ec2-user/video-message-app/video-message-app
docker-compose up -d

# BiRefNet背景除去テスト
curl -X POST http://3.115.141.166:55433/api/v1/background/remove \
  -F "image=@test.jpg" \
  -o output_no_bg.png

# 処理時間を確認（目標: <80ms）
```

### EC2停止（コスト削減）

```bash
# SSH切断
exit

# EC2停止（手動）
aws ec2 stop-instances \
  --instance-ids i-xxxxxxxxx \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# または自動停止スクリプト（30分アイドル後）
# EC2上で: sudo shutdown -h +30
```

---

## 🐛 デバッグ方法

### Backend（Python）デバッグ

**VSCode launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--host", "0.0.0.0",
        "--port", "55433",
        "--reload"
      ],
      "cwd": "${workspaceFolder}/video-message-app/backend",
      "env": {
        "D_ID_API_KEY": "${env:D_ID_API_KEY}"
      }
    }
  ]
}
```

**ブレークポイント設定**:
1. VSCodeで `backend/routers/voice.py` を開く
2. 行番号の左をクリックしてブレークポイント設定
3. F5キーでデバッグ開始
4. APIリクエストを送信すると、ブレークポイントで停止

### Frontend（React）デバッグ

**Chrome DevTools**:
1. ブラウザで `http://localhost:55434` を開く
2. F12キーでDevToolsを開く
3. Sourcesタブ → `src/components/` → ファイル選択
4. ブレークポイント設定 → ページリロード

---

## 📊 パフォーマンス比較

| 操作 | ローカル | リモート（EC2） | 改善率 |
|------|---------|---------------|--------|
| コード編集→反映 | 0.5秒 | 2-3秒 | **6倍高速** |
| Backend再起動 | 2秒 | 5秒 | 2.5倍高速 |
| Frontend再ビルド | 3秒 | 8秒 | 2.7倍高速 |
| Git操作 | 即座 | 0.5秒 | ネットワーク遅延なし |
| デバッグ | ネイティブ | リモート | 圧倒的に快適 |

---

## 🔍 トラブルシューティング

### Q1: Docker Desktopが起動しない

```bash
# Docker Desktopを再起動
killall Docker
open -a Docker

# 30秒待ってから再試行
sleep 30
docker ps
```

### Q2: ポート55433が既に使用中

```bash
# 使用中のプロセスを確認
lsof -i :55433

# プロセスを停止
kill -9 <PID>
```

### Q3: OpenVoice Native Serviceが起動しない

```bash
# ログ確認
tail -f ~/workspace/video-message-app/openvoice_native/openvoice.log

# Conda環境再作成
conda deactivate
conda env remove -n openvoice_v2
conda create -n openvoice_v2 python=3.11.12 -y
conda activate openvoice_v2
pip install -r requirements.txt
```

### Q4: D-ID APIキーエラー

```bash
# 環境変数を確認
echo $D_ID_API_KEY

# 空の場合、再設定
export D_ID_API_KEY=$(grep "D_ID_API_KEY=" ~/secure_credentials/d_id_api_key.txt | cut -d'=' -f2)

# Backend .envを確認
cat video-message-app/backend/.env | grep D_ID_API_KEY
```

### Q5: VOICEVOXコンテナが起動しない

```bash
# Docker Desktop起動確認
docker ps

# コンテナログ確認
docker logs voicevox_engine

# 再起動
docker-compose restart voicevox
```

---

## 📚 次のステップ

### Phase 1完了後（ローカル環境動作確認）

- [ ] OpenVoice Voice Clone機能テスト
- [ ] VOICEVOX TTS機能テスト
- [ ] D-ID動画生成テスト（3秒動画）

### Phase 2: EC2セットアップ（GPUテスト前）

- [ ] EC2インスタンス起動（手動）
- [ ] BiRefNet GPUサービス構築
- [ ] YOLOv8人物検出実装

### Phase 3: 統合テスト

- [ ] ローカル → EC2 ハイブリッドテスト
- [ ] E2Eパイプライン確認
- [ ] パフォーマンスベンチマーク

---

## 📖 関連ドキュメント

- [TECHNICAL_SPECIFICATION.md](./TECHNICAL_SPECIFICATION.md) - 完全な技術仕様
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - 5.6週間スプリント計画
- [EC2_SECURITY_SETUP.md](./EC2_SECURITY_SETUP.md) - EC2セキュリティ設定
- [DEVELOPER_WORKFLOW.md](./DEVELOPER_WORKFLOW.md) - 詳細なワークフロー解説
- [DAILY_CHECKLIST.md](./DAILY_CHECKLIST.md) - 印刷用チェックリスト

---

**作成日**: 2025-11-02
**最終更新**: 2025-11-02
**承認ワークフロー**: Local-First with Remote Testing ✅
