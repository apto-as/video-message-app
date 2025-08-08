# AWS CLI 複数プロファイル管理ガイド

## 概要
複数のAWSアカウントやIAMユーザーを使い分ける方法です。
プロジェクトごとに異なる認証情報を安全に管理できます。

## 1. プロファイルの設定方法

### 方法1: aws configure --profile（推奨）

```bash
# デフォルトプロファイル（既存プロジェクト用）
aws configure
# これは [default] として保存される

# Video Message App用の新規プロファイル
aws configure --profile video-app

# 入力画面
AWS Access Key ID [None]: AKIA...（新しいIAMユーザーのキー）
AWS Secret Access Key [None]: wJal...（新しいシークレット）
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

### 方法2: 設定ファイル直接編集

```bash
# ~/.aws/credentials を編集
nano ~/.aws/credentials
```

```ini
# 既存のプロジェクト
[default]
aws_access_key_id = AKIA...既存のキー
aws_secret_access_key = wJal...既存のシークレット

# Video Message App用
[video-app]
aws_access_key_id = AKIA...新しいキー
aws_secret_access_key = wJal...新しいシークレット

# その他のプロジェクト
[project-b]
aws_access_key_id = AKIA...別のキー
aws_secret_access_key = wJal...別のシークレット
```

```bash
# ~/.aws/config を編集
nano ~/.aws/config
```

```ini
[default]
region = us-east-1
output = json

[profile video-app]
region = ap-northeast-1
output = json

[profile project-b]
region = eu-west-1
output = table
```

## 2. プロファイルの使い方

### AWS CLIでの使用

```bash
# デフォルトプロファイルを使用
aws s3 ls

# video-appプロファイルを使用
aws s3 ls --profile video-app

# 確認：どのアカウントを使っているか
aws sts get-caller-identity --profile video-app
```

### 環境変数での切り替え

```bash
# 一時的にプロファイルを切り替え
export AWS_PROFILE=video-app

# これ以降のコマンドはvideo-appプロファイルを使用
aws s3 ls  # --profileオプション不要

# デフォルトに戻す
unset AWS_PROFILE
# または
export AWS_PROFILE=default
```

### Terraformでの使用

```hcl
# terraform/gpu/main.tf に追加
provider "aws" {
  region  = var.aws_region
  profile = "video-app"  # プロファイル指定
}
```

または環境変数で：

```bash
export AWS_PROFILE=video-app
terraform init
terraform apply
```

## 3. 便利な管理方法

### 3.1 現在のプロファイル確認

```bash
# 現在使用中のプロファイル
echo $AWS_PROFILE

# 設定されている認証情報の確認
aws configure list
aws configure list --profile video-app

# すべてのプロファイル一覧
aws configure list-profiles
```

### 3.2 プロファイル切り替えスクリプト

```bash
# ~/.bashrc または ~/.zshrc に追加

# プロファイル切り替え関数
awsp() {
    if [ -z "$1" ]; then
        echo "Current profile: ${AWS_PROFILE:-default}"
        echo "Available profiles:"
        aws configure list-profiles
    else
        export AWS_PROFILE=$1
        echo "Switched to profile: $1"
        aws sts get-caller-identity
    fi
}

# エイリアス
alias aws-default='export AWS_PROFILE=default'
alias aws-video='export AWS_PROFILE=video-app'
alias aws-who='aws sts get-caller-identity'
```

使い方：

```bash
# プロファイル一覧表示
awsp

# video-appに切り替え
awsp video-app

# エイリアスで切り替え
aws-video

# 現在のユーザー確認
aws-who
```

### 3.3 プロジェクトごとの.envファイル

```bash
# プロジェクトルートに .env.aws を作成
cat > .env.aws << EOF
export AWS_PROFILE=video-app
export AWS_REGION=ap-northeast-1
EOF

# 使用時
source .env.aws
```

## 4. セキュリティベストプラクティス

### 4.1 認証情報の分離

```bash
# プロジェクトごとに異なるIAMユーザー
project-a/ → IAMユーザーA（権限制限）
project-b/ → IAMユーザーB（権限制限）
video-app/ → IAMユーザーC（必要な権限のみ）
```

### 4.2 MFA設定（プロファイルごと）

```ini
# ~/.aws/config
[profile video-app]
region = ap-northeast-1
mfa_serial = arn:aws:iam::123456789012:mfa/username
```

### 4.3 一時的な認証情報

```bash
# assume-roleを使用した一時認証
[profile video-app-admin]
source_profile = video-app
role_arn = arn:aws:iam::123456789012:role/AdminRole
mfa_serial = arn:aws:iam::123456789012:mfa/username
```

## 5. トラブルシューティング

### 問題: 間違ったプロファイルで実行

```bash
# 実行前に必ず確認
echo "Using profile: ${AWS_PROFILE:-default}"
aws sts get-caller-identity

# Terraformの場合
terraform plan  # 実行前にどのリソースが作成されるか確認
```

### 問題: プロファイルが見つからない

```bash
# エラー: The config profile (video-app) could not be found

# 解決法
aws configure --profile video-app
# または
aws configure list-profiles  # 正しい名前を確認
```

### 問題: 認証エラー

```bash
# プロファイルの認証情報を更新
aws configure --profile video-app
# 新しいアクセスキーを入力
```

## 6. 実用例

### 例1: 複数プロジェクトの同時作業

```bash
# ターミナル1: 既存プロジェクト
export AWS_PROFILE=default
cd ~/projects/existing-project
aws s3 sync . s3://existing-bucket/

# ターミナル2: Video Message App
export AWS_PROFILE=video-app
cd ~/projects/video-message-app
terraform apply

# ターミナル3: 別のプロジェクト
export AWS_PROFILE=project-b
cd ~/projects/another-project
aws ec2 describe-instances
```

### 例2: スクリプトでプロファイル指定

```bash
#!/bin/bash
# deploy.sh

# プロファイルを明示的に指定
AWS_PROFILE=video-app aws s3 cp ./dist s3://my-bucket/ --recursive
AWS_PROFILE=video-app aws cloudfront create-invalidation --distribution-id ABCD
```

### 例3: Docker Composeでの使用

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - AWS_PROFILE=${AWS_PROFILE:-video-app}
    volumes:
      - ~/.aws:/root/.aws:ro  # 認証情報をマウント
```

## 7. Video Message App用の設定

### 推奨設定手順

```bash
# 1. プロファイル作成
aws configure --profile video-app

# 2. 確認
aws sts get-caller-identity --profile video-app

# 3. デフォルトとして設定（このプロジェクトで作業時）
export AWS_PROFILE=video-app

# 4. Terraform実行
cd terraform/gpu
terraform init
terraform apply

# 5. 管理スクリプトで使用
AWS_PROFILE=video-app ./scripts/gpu-manage.sh status
```

### .bashrc/.zshrc への追加

```bash
# Video Message App用のエイリアス
alias video-aws='export AWS_PROFILE=video-app && echo "Switched to video-app profile"'
alias video-ssh='ssh -i ~/.ssh/video-app-key.pem ubuntu@$(aws ec2 describe-instances --profile video-app --query "Reservations[0].Instances[0].PublicIpAddress" --output text)'
alias video-status='AWS_PROFILE=video-app ./scripts/gpu-manage.sh status'
```

## まとめ

✅ **メリット**:
- 複数プロジェクトの認証情報を安全に管理
- 間違ったアカウントでの操作を防止
- チーム開発での権限分離が容易

✅ **ベストプラクティス**:
- プロジェクトごとに専用プロファイル
- 作業前に `aws-who` で確認
- 本番環境は別プロファイルで保護

---

*Multiple Projects, Safe & Organized*