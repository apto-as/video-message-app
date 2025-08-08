# AWS IAMユーザー作成ガイド - Video Message App

## 概要
Terraformでインフラを構築するために必要なIAMユーザーの作成手順です。
セキュリティを考慮し、必要最小限の権限を設定します。

## 1. AWSアカウントの準備

### 1.1 AWSアカウント作成（既にある場合はスキップ）
1. https://aws.amazon.com/ にアクセス
2. 「AWSアカウントを作成」をクリック
3. メールアドレス、パスワード設定
4. クレジットカード情報登録（無料枠あり）
5. 本人確認（SMS/電話）

### 1.2 ルートユーザーでログイン
```
⚠️ 重要: ルートユーザーは初期設定のみ使用
日常作業はIAMユーザーで行う
```

## 2. IAMユーザー作成手順

### Step 1: AWS Console にログイン
1. https://console.aws.amazon.com/
2. ルートユーザーでログイン
3. リージョンを「アジアパシフィック（東京）ap-northeast-1」に設定

### Step 2: IAMサービスへ移動
1. 検索バーで「IAM」を検索
2. 「IAM」をクリック

### Step 3: IAMユーザー作成

#### 3.1 ユーザー追加
1. 左メニュー「ユーザー」→「ユーザーを作成」
2. ユーザー名: `terraform-user`（または任意の名前）
3. 「次へ」

#### 3.2 権限設定（オプション1: 開発環境用・簡単設定）
```
⚠️ 開発環境のみ推奨
```
1. 「ポリシーを直接アタッチする」を選択
2. 「AdministratorAccess」を検索して選択
3. 「次へ」→「ユーザーの作成」

#### 3.3 権限設定（オプション2: 本番環境用・最小権限）
1. 「ポリシーを直接アタッチする」を選択
2. 「ポリシーの作成」をクリック
3. JSONタブを選択
4. 以下のポリシーを貼り付け：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2FullAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPCFullAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:*Vpc*",
        "ec2:*Subnet*",
        "ec2:*Gateway*",
        "ec2:*Route*",
        "ec2:*SecurityGroup*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketTagging",
        "s3:PutBucketTagging",
        "s3:GetBucketLifecycleConfiguration",
        "s3:PutBucketLifecycleConfiguration",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMAccess",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:ListRoles",
        "iam:TagRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:GetRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListRolePolicies",
        "iam:CreateInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:GetInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile",
        "iam:ListInstanceProfiles",
        "iam:ListInstanceProfilesForRole",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EFSAccess",
      "Effect": "Allow",
      "Action": [
        "elasticfilesystem:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchAccess",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    },
    {
      "Sid": "STSAccess",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

5. ポリシー名: `TerraformDeploymentPolicy`
6. 「ポリシーの作成」
7. ユーザー作成画面に戻り、作成したポリシーを選択

### Step 4: アクセスキー作成

1. 作成したユーザーをクリック
2. 「セキュリティ認証情報」タブ
3. 「アクセスキーを作成」
4. 「コマンドラインインターフェイス（CLI）」を選択
5. 確認チェックボックスにチェック
6. 「次へ」
7. 説明タグ（オプション）: `terraform-access`
8. 「アクセスキーを作成」

### Step 5: 認証情報の保存

```
⚠️ 重要: この画面は一度しか表示されません！
```

1. 「.csvファイルをダウンロード」をクリック
2. 以下の情報を安全な場所に保存：
   - アクセスキーID: `AKIA...`
   - シークレットアクセスキー: `wJal...`

## 3. AWS CLI設定

### 3.1 AWS CLIインストール

#### macOS
```bash
# Homebrew使用
brew install awscli

# または公式インストーラー
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

#### Windows
```powershell
# 公式サイトからMSIをダウンロード
# https://aws.amazon.com/cli/
```

#### Linux
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### 3.2 AWS CLI設定

```bash
# 設定コマンド
aws configure

# 以下を入力
AWS Access Key ID [None]: AKIA... （ダウンロードしたキー）
AWS Secret Access Key [None]: wJal... （ダウンロードしたシークレット）
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

### 3.3 設定確認

```bash
# 接続テスト
aws sts get-caller-identity

# 成功時の出力例
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-user"
}
```

## 4. セキュリティベストプラクティス

### 4.1 MFA（多要素認証）設定

1. IAMコンソール → ユーザー → セキュリティ認証情報
2. 「MFAデバイスの割り当て」
3. 「仮想MFAデバイス」選択
4. Google Authenticator等でQRコード読み取り
5. 連続する2つのコードを入力

### 4.2 アクセスキーローテーション

```bash
# 3ヶ月ごとにキーを更新
# 古いキーは削除
```

### 4.3 認証情報の管理

```bash
# 環境変数で管理（推奨）
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="wJal..."
export AWS_DEFAULT_REGION="ap-northeast-1"

# または ~/.aws/credentials ファイル
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = wJal...

[dev]
aws_access_key_id = AKIA...
aws_secret_access_key = wJal...
```

### 4.4 .gitignore設定

```bash
# 認証情報を誤ってコミットしないように
echo "*.pem" >> .gitignore
echo ".env*" >> .gitignore
echo "terraform.tfvars" >> .gitignore
echo "*.tfstate*" >> .gitignore
```

## 5. Terraform実行準備

### 5.1 Terraformインストール

```bash
# macOS
brew install terraform

# Windows (Chocolatey)
choco install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### 5.2 Terraform初期化

```bash
# プロジェクトディレクトリへ移動
cd terraform/gpu  # または terraform/simple

# 初期化
terraform init

# 認証確認
terraform plan
```

## 6. トラブルシューティング

### エラー: UnauthorizedOperation

```bash
# 権限不足の場合
# IAMポリシーを確認し、必要な権限を追加
```

### エラー: InvalidUserID.NotFound

```bash
# アクセスキーが間違っている
aws configure list  # 設定確認
aws configure       # 再設定
```

### エラー: RequestLimitExceeded

```bash
# APIリクエスト制限
# 少し待ってから再実行
```

## 7. コスト管理設定

### 7.1 請求アラート設定

1. AWS Console → Billing
2. 「Budgets」→「予算を作成」
3. 月額予算: $100（任意）
4. アラート閾値: 80%
5. 通知先メール設定

### 7.2 Cost Explorer有効化

1. AWS Console → Cost Management
2. Cost Explorer → 有効化
3. 日次コストレポート確認

## 8. 次のステップ

IAMユーザー作成後：

```bash
# 1. 認証確認
aws sts get-caller-identity

# 2. Terraformディレクトリへ
cd terraform/gpu

# 3. 設定ファイル準備
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集

# 4. EC2キーペア作成
aws ec2 create-key-pair --key-name my-app-key \
  --query 'KeyMaterial' --output text > my-app-key.pem
chmod 400 my-app-key.pem

# 5. Terraform実行
terraform init
terraform plan
terraform apply
```

## まとめ

✅ **必要な作業**:
1. IAMユーザー作成（5分）
2. アクセスキー生成（1分）
3. AWS CLI設定（3分）
4. MFA設定（推奨）（3分）

**合計: 約15分で完了**

---

*Secure, Simple, Ready to Deploy*