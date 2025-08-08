# AWS クイックスタートガイド

## 📋 必要な作業（所要時間: 約30分）

### 1️⃣ AWSアカウント準備（10分）

```bash
# AWSアカウント作成（既にある場合はスキップ）
# https://aws.amazon.com/
```

### 2️⃣ IAMユーザー作成（5分）

**AWS Consoleで作業:**

1. https://console.aws.amazon.com/ にログイン
2. IAM → ユーザー → 「ユーザーを作成」
3. ユーザー名: `terraform-user`
4. 権限: `AdministratorAccess`（開発環境用）
5. アクセスキー作成 → CSVダウンロード

### 3️⃣ AWS CLI設定（5分）

```bash
# AWS CLIインストール
brew install awscli  # Mac
# または https://aws.amazon.com/cli/ から

# 設定
aws configure

# 入力内容
AWS Access Key ID: [CSVのアクセスキー]
AWS Secret Access Key: [CSVのシークレットキー]
Default region: ap-northeast-1
Default output format: json

# 確認
aws sts get-caller-identity
```

### 4️⃣ 環境チェック（1分）

```bash
# チェックスクリプト実行
chmod +x scripts/aws-setup-check.sh
./scripts/aws-setup-check.sh
```

### 5️⃣ EC2キーペア作成（2分）

```bash
# キーペア作成
aws ec2 create-key-pair \
  --key-name video-app-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/video-app-key.pem

# 権限設定
chmod 400 ~/.ssh/video-app-key.pem
```

### 6️⃣ Terraform実行（10分）

#### オプションA: シンプル構成（CPU only）

```bash
# ディレクトリ移動
cd terraform/simple

# 設定ファイル準備
cp terraform.tfvars.example terraform.tfvars

# terraform.tfvars を編集
nano terraform.tfvars
# key_name = "video-app-key" に変更

# Terraform実行
terraform init
terraform plan
terraform apply  # yesを入力
```

#### オプションB: GPU構成（高性能）

```bash
# ディレクトリ移動
cd terraform/gpu

# 設定ファイル準備
cp terraform.tfvars.example terraform.tfvars

# terraform.tfvars を編集
nano terraform.tfvars
# key_name = "video-app-key" に変更

# Terraform実行
terraform init
terraform plan
terraform apply  # yesを入力
```

## 🚀 デプロイ後の作業

### アプリケーションデプロイ

```bash
# Terraform出力から情報取得
terraform output

# EC2にSSH接続
ssh -i ~/.ssh/video-app-key.pem ubuntu@[PUBLIC_IP]

# アプリケーションセットアップ
git clone https://github.com/your-repo/video-message-app.git
cd video-message-app

# 環境変数設定
cp backend/.env.example backend/.env
nano backend/.env  # D_ID_API_KEY設定

# Docker起動
docker compose up -d

# 確認
docker compose ps
```

### アクセス確認

```bash
# ブラウザでアクセス
open http://[PUBLIC_IP]:55434  # Frontend
open http://[PUBLIC_IP]:55433  # Backend API
```

## 💰 コスト管理

### 自動停止設定

```bash
# 使わない時は停止（重要！）
aws ec2 stop-instances --instance-ids [INSTANCE_ID]

# 使う時に起動
aws ec2 start-instances --instance-ids [INSTANCE_ID]

# または管理スクリプト使用
./scripts/gpu-manage.sh stop-all  # 停止
./scripts/gpu-manage.sh start-app # 起動
```

### 料金アラート設定

1. AWS Console → Billing → Budgets
2. 「予算を作成」
3. 月額: $100
4. アラート: 80%でメール通知

## 🔧 トラブルシューティング

### よくある問題

```bash
# 問題: Permission denied
解決: IAMユーザーの権限確認

# 問題: Key pair not found
解決: EC2キーペア作成を確認

# 問題: terraform apply失敗
解決: AWS認証情報を確認
aws sts get-caller-identity

# 問題: EC2接続できない
解決: セキュリティグループ確認
```

## 📊 構成比較

| 項目 | シンプル構成 | GPU構成 |
|------|------------|---------|
| 初期構築時間 | 10分 | 15分 |
| 月額コスト | $35-85 | $40-60 |
| OpenVoice速度 | 遅い | 10倍高速 |
| 管理の簡単さ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## ✅ チェックリスト

- [ ] AWSアカウント作成
- [ ] IAMユーザー作成
- [ ] アクセスキー取得
- [ ] AWS CLI設定
- [ ] EC2キーペア作成
- [ ] Terraform実行
- [ ] EC2起動確認
- [ ] アプリデプロイ
- [ ] 自動停止設定
- [ ] 料金アラート設定

## 🆘 ヘルプ

詳細な手順が必要な場合:

- **IAM設定**: `AWS_IAM_SETUP_GUIDE.md`
- **シンプル構成**: `terraform/simple/README.md`
- **GPU構成**: `AWS_GPU_MIGRATION_PLAN.md`
- **開発フロー**: `AWS_DEVELOPMENT_WORKFLOW.md`

---

**30分で AWS 環境構築完了！** 🎉