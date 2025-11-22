# デプロイメントガイド

このドキュメントでは、Video Message Appのデプロイメント手順とワークフローを説明します。

## 📋 目次

- [デプロイフロー](#デプロイフロー)
- [自動デプロイ](#自動デプロイ)
- [手動デプロイ](#手動デプロイ)
- [ロールバック](#ロールバック)
- [環境別デプロイ](#環境別デプロイ)

## デプロイフロー

### 推奨ワークフロー

```
ローカル開発
    ↓
Git Commit & Push
    ↓
EC2で Pull
    ↓
Docker Compose Restart
    ↓
動作確認
```

### ブランチ戦略

- **main**: プロダクション（EC2）
- **develop**: 開発版
- **feature/***: 機能開発

## 自動デプロイ

### deploy.sh の使用

`deploy.sh` スクリプトで簡単にデプロイできます。

#### 基本コマンド

```bash
# フルデプロイ（バックアップ + 同期 + 再起動）
./deploy.sh deploy

# ソースコード同期のみ
./deploy.sh sync

# ステータス確認
./deploy.sh status

# ログ表示
./deploy.sh logs backend

# SSH接続
./deploy.sh ssh
```

#### オプション

```bash
# Dry Run（変更内容の確認のみ）
./deploy.sh deploy --dry-run

# 特定サービスのみ再起動
./deploy.sh deploy --service=backend
./deploy.sh deploy --service=frontend

# バックアップなしでデプロイ
./deploy.sh deploy --no-backup
```

### デプロイ例

```bash
# Backend APIの修正をデプロイ
./deploy.sh deploy --service=backend

# Frontend UIの修正をデプロイ
./deploy.sh deploy --service=frontend

# 全サービスをデプロイ（推奨）
./deploy.sh deploy
```

## 手動デプロイ

自動スクリプトを使わない場合の手順です。

### 1. ローカルでの準備

```bash
# 変更をコミット
git add .
git commit -m "Fix: embedding_path issue"
git push origin main
```

### 2. EC2での作業

```bash
# EC2に接続
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166

# プロジェクトディレクトリへ移動
cd ~/video-message-app/video-message-app

# 最新コードを取得
git pull origin main

# Dockerサービスを再起動
docker-compose restart backend

# ログで確認
docker-compose logs -f backend
```

### 3. 動作確認

```bash
# ローカルから確認
curl https://3.115.141.166/api/health

# ブラウザでテスト
open https://3.115.141.166
```

## ロールバック

問題が発生した場合、前回のバックアップに戻せます。

### 自動ロールバック

```bash
./deploy.sh rollback
```

### 手動ロールバック

```bash
# EC2に接続
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166

# バックアップ一覧
ls -lt ~/video-message-app/backups/

# 最新バックアップの確認
cat ~/video-message-app/backups/latest.txt

# バックアップを復元
cd ~/video-message-app/video-message-app
BACKUP_NAME=$(cat ../backups/latest.txt)
tar -xzf ../backups/$BACKUP_NAME.tar.gz

# サービス再起動
docker-compose restart
```

## 環境別デプロイ

### ローカル開発環境

```bash
# .env.local を使用
docker-compose --env-file .env.local up -d

# ホットリロード有効
MOUNT_CODE=rw docker-compose up -d
```

### ステージング環境（将来）

```bash
# ステージング用設定
docker-compose -f docker-compose.staging.yml up -d
```

### プロダクション環境（EC2）

```bash
# .env.prod を使用
docker-compose --env-file .env.prod up -d

# 読み取り専用マウント
MOUNT_CODE=ro docker-compose up -d
```

## デプロイチェックリスト

### デプロイ前

- [ ] コードレビュー完了
- [ ] ローカルでテスト実施
- [ ] `.env` ファイル確認（機密情報の除外）
- [ ] バックアップ作成確認

### デプロイ中

- [ ] SSH接続確認
- [ ] ソースコード同期
- [ ] Dockerサービス再起動
- [ ] エラーログ確認

### デプロイ後

- [ ] ヘルスチェック（`/api/health`）
- [ ] 主要機能の動作確認
- [ ] ログにエラーがないか確認
- [ ] パフォーマンス確認

## トラブルシューティング

### デプロイ失敗時

**症状**: デプロイスクリプトがエラーで停止

**確認事項**:
```bash
# SSH接続確認
ssh -i ~/.ssh/video-app-key.pem -p 22 ec2-user@3.115.141.166 "echo OK"

# ディスク容量確認
./deploy.sh ssh
df -h

# Dockerサービス確認
docker-compose ps
```

### サービス起動失敗

**症状**: Docker Composeが起動しない

**解決策**:
```bash
# ログ確認
docker-compose logs backend

# 個別起動で原因特定
docker-compose up backend

# 設定ファイル検証
docker-compose config
```

### データベース接続エラー

**症状**: Backend → OpenVoice 接続失敗

**解決策**:
```bash
# OpenVoice Service確認
sudo systemctl status openvoice

# 再起動
sudo systemctl restart openvoice

# ログ確認
sudo journalctl -u openvoice -n 50
```

## ベストプラクティス

### 1. 段階的デプロイ

```bash
# Step 1: 変更内容の確認
./deploy.sh sync --dry-run

# Step 2: バックアップ付きデプロイ
./deploy.sh deploy --service=backend

# Step 3: 動作確認
./deploy.sh logs backend

# Step 4: 問題があればロールバック
./deploy.sh rollback
```

### 2. 本番デプロイのタイミング

- **推奨時間**: 深夜または早朝（利用者が少ない時間）
- **避けるべき時間**: ピークタイム、営業時間中

### 3. デプロイ後の監視

```bash
# リアルタイムログ監視
./deploy.sh logs backend --follow

# エラー検出
./deploy.sh ssh
docker-compose logs | grep -i error
```

### 4. Git タグの活用

```bash
# バージョンタグ
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# デプロイ記録
git tag -a deploy-20250106 -m "Deployed to EC2"
git push origin deploy-20250106
```

## CI/CD（将来の拡張）

### GitHub Actions 例

```yaml
name: Deploy to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy to EC2
        env:
          SSH_KEY: ${{ secrets.EC2_SSH_KEY }}
        run: |
          echo "$SSH_KEY" > key.pem
          chmod 600 key.pem
          ./deploy.sh deploy
```

## 参考リンク

- [SETUP.md](./SETUP.md) - セットアップ手順
- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ
- [deploy.sh](./deploy.sh) - デプロイスクリプト
