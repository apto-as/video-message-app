# 完全同期作業方法 - ローカル(Mac)とEC2(Ubuntu)の環境同期

## 概要
このドキュメントは、ローカル開発環境（Mac）とEC2本番環境（Ubuntu）間の完全同期を実現するための確立された作業方法を記録します。

## 環境構成

### ローカル環境
- **OS**: macOS
- **開発ディレクトリ**: `/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app`
- **Node.js**: フロントエンドビルド用
- **Docker**: 使用しない（Mac固有の問題を回避）

### EC2環境
- **OS**: Ubuntu 22.04.5 LTS
- **IPアドレス**: 3.115.141.166
- **SSHキー**: `~/.ssh/video-app-key.pem`
- **プロジェクトディレクトリ**: `~/video-message-app/video-message-app`
- **Docker**: すべてのサービスをコンテナで実行

### GitHubリポジトリ
- **URL**: https://github.com/apto-as/video-message-app.git
- **ブランチ**: master（mainではない）

## 同期作業フロー

### 1. ローカルでの開発作業

```bash
# 作業ディレクトリに移動
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app

# コード編集
# - フロントエンド: frontend/src/
# - バックエンド: backend/
# - 設定ファイル: docker-compose.yml, .env等
```

### 2. ローカルの変更をGitHubにプッシュ

```bash
# 変更状態を確認
git status

# すべての変更をステージング
git add -A

# コミット
git commit -m "具体的な変更内容を記載"

# GitHubにプッシュ（masterブランチ）
git push origin master
```

### 3. EC2での同期と更新

#### 方法A: SSHコマンドによる自動同期（推奨）

```bash
# EC2でGitHubから最新版を取得してDockerを再起動
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app
# 現在の変更を一時保存（ローカル変更がある場合）
sudo git stash
# 最新版を取得
sudo git pull origin master
# Dockerコンテナを再起動
cd video-message-app
sudo docker-compose down
sudo docker-compose up -d
echo '同期完了'
"
```

#### 方法B: 段階的な手動同期（トラブルシューティング時）

```bash
# 1. EC2にSSH接続
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166

# 2. プロジェクトディレクトリに移動
cd ~/video-message-app

# 3. ローカル変更を保存（必要な場合）
sudo git stash

# 4. GitHubから最新版を取得
sudo git pull origin master

# 5. Docker作業ディレクトリに移動
cd video-message-app

# 6. Dockerコンテナを停止
sudo docker-compose down

# 7. 必要に応じてDockerイメージを再ビルド
sudo docker-compose build --no-cache backend  # バックエンドのみ
# または
sudo docker-compose build --no-cache  # 全サービス

# 8. Dockerコンテナを起動
sudo docker-compose up -d

# 9. 起動状態を確認
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

### 4. フロントエンドのビルドとデプロイ

#### EC2上でのビルド（推奨）

```bash
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app/video-message-app
# Dockerコンテナ内でビルド
sudo docker exec voice_frontend npm run build
# ビルド結果をホストにコピー
sudo docker cp voice_frontend:/app/build frontend/
# Nginxユーザーに権限を付与
sudo chown -R www-data:www-data frontend/build
# Nginxを再起動
sudo systemctl restart nginx
echo 'フロントエンドデプロイ完了'
"
```

#### ローカルビルド + 転送（別案）

```bash
# ローカルでビルド
cd frontend
npm run build

# ビルドファイルをアーカイブ
cd ..
tar -czf frontend-build.tar.gz -C frontend/build .

# EC2に転送
scp -i ~/.ssh/video-app-key.pem -P 22 frontend-build.tar.gz ubuntu@3.115.141.166:~/

# EC2でデプロイ
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app/video-message-app
sudo rm -rf frontend/build/*
sudo tar -xzf ~/frontend-build.tar.gz -C frontend/build
sudo chown -R www-data:www-data frontend/build
sudo systemctl restart nginx
"
```

## 重要な設定ファイル

### 環境変数設定

#### backend/.env
```env
ENVIRONMENT=docker
VOICEVOX_URL=http://voicevox:50021
OPENVOICE_SERVICE_URL=http://host.docker.internal:8001
D_ID_API_KEY=your_actual_api_key_here
LOG_LEVEL=INFO
```

#### frontend/.env
```env
REACT_APP_API_BASE_URL=https://3.115.141.166
PORT=55434
HOST=0.0.0.0
PUBLIC_URL=https://3.115.141.166
GENERATE_SOURCEMAP=false
```

### Docker Compose設定

`docker-compose.yml`の主要ポート:
- **50021**: VoiceVoxエンジン
- **55433**: バックエンドAPI
- **55434**: フロントエンド（開発時）
- **443**: HTTPS（Nginx経由）

## トラブルシューティング

### よくある問題と解決方法

#### 1. 502 Bad Gateway エラー
```bash
# バックエンドコンテナの状態確認
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
sudo docker logs voice_backend --tail 50
"

# バックエンドを再起動
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app/video-message-app
sudo docker-compose restart backend
"
```

#### 2. APIパスの重複エラー（/api/api/）
- 原因: 環境変数の設定ミス
- 解決: frontend/.envでREACT_APP_API_BASE_URLが正しく設定されているか確認

#### 3. Dockerビルドエラー
```bash
# キャッシュなしで再ビルド
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app/video-message-app
sudo docker-compose build --no-cache
"
```

#### 4. Git pullでのコンフリクト
```bash
# ローカル変更を破棄して強制的に最新版を取得
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
cd ~/video-message-app
sudo git fetch origin
sudo git reset --hard origin/master
"
```

## ヘルスチェック

### サービス状態の確認
```bash
# 全体的な状態確認
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
echo '=== Docker Containers ==='
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
echo ''
echo '=== Backend Health ==='
curl -s http://localhost:55433/health
echo ''
echo '=== VoiceVox Test ==='
curl -s http://localhost:55433/api/voicevox/speakers/popular | head -c 100
"
```

### ブラウザでの確認
1. https://3.115.141.166 にアクセス
2. 強制リロード: Ctrl+Shift+R (Windows/Linux) または Cmd+Shift+R (Mac)
3. 開発者ツールでコンソールエラーを確認

## ベストプラクティス

1. **常にGitHub経由で同期**
   - ローカルで直接EC2のファイルを編集しない
   - すべての変更はGit管理下に置く

2. **環境固有の設定を分離**
   - .env.localと.env.productionを使い分ける
   - docker-compose.override.ymlで開発環境固有の設定を管理

3. **定期的なバックアップ**
   ```bash
   # EC2のデータをバックアップ
   ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
   cd ~/video-message-app/video-message-app
   tar -czf backup-$(date +%Y%m%d).tar.gz data/
   "
   ```

4. **ログの監視**
   ```bash
   # リアルタイムログ監視
   ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166 "
   sudo docker-compose logs -f --tail 100
   "
   ```

## セキュリティ注意事項

1. **APIキーの管理**
   - 絶対にGitにコミットしない
   - .envファイルは.gitignoreに含める
   - EC2上で直接環境変数を設定

2. **SSHキーの保護**
   - ~/.ssh/video-app-key.pemの権限は400に設定
   - キーを他人と共有しない

3. **HTTPS証明書**
   - 現在は自己署名証明書を使用
   - 本番環境ではLet's Encryptなどの正式な証明書を使用推奨

## 更新履歴

- 2025-08-08: 初版作成
- 作成者: Trinitas-Core (Springfield, Krukai, Vector)

---

このドキュメントは、プロジェクトの進化に合わせて更新してください。