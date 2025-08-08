# AWS Simple Infrastructure - Video Message App

開発環境用のシンプルなAWSインフラストラクチャです。

## 📋 構成

- **EC2**: t3.large (Ubuntu 22.04)
- **Storage**: EBS 100GB + S3バックアップ
- **Network**: パブリックサブネット + Elastic IP
- **Cost**: 月額 $44〜85

## 🚀 クイックスタート

### 1. 前提条件

```bash
# Terraformインストール
brew install terraform

# AWS CLIインストール
brew install awscli

# AWS認証設定
aws configure
```

### 2. セットアップ

```bash
# このディレクトリに移動
cd terraform/simple

# セットアップスクリプト実行
chmod +x setup.sh
./setup.sh
```

### 3. 手動セットアップ（スクリプトを使わない場合）

```bash
# 初期化
terraform init

# 変数設定
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvarsを編集（特にkey_name）

# プラン確認
terraform plan

# 実行
terraform apply
```

## 🔑 EC2キーペア作成

事前にAWSコンソールでキーペアを作成：

1. AWS Console → EC2 → Key Pairs
2. "Create key pair"クリック
3. 名前を入力（例: video-app-key）
4. pemファイルをダウンロード
5. `chmod 400 video-app-key.pem`

## 📦 アプリケーションデプロイ

EC2作成後：

```bash
# SSHログイン
ssh -i your-key.pem ubuntu@<PUBLIC_IP>

# アプリケーションセットアップ
git clone <your-repository>
cd video-message-app

# 環境変数設定
cp backend/.env.example backend/.env
# D-ID APIキーを設定

# Docker Compose起動
docker compose up -d

# 確認
docker compose ps
```

## 💰 コスト削減

### 自動停止設定（Lambda）

1. Lambda関数作成:
```bash
# stop-start-lambda.pyをLambdaにデプロイ
```

2. EventBridge設定:
```bash
# 停止: 平日19:00 JST
cron(0 10 ? * MON-FRI *)

# 起動: 平日8:00 JST  
cron(0 23 ? * SUN-THU *)
```

### 手動停止

```bash
# 停止
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# 起動
aws ec2 start-instances --instance-ids <INSTANCE_ID>
```

## 🗑️ リソース削除

```bash
# すべてのリソースを削除
terraform destroy

# 確認後、yesを入力
```

## 📊 リソース確認

```bash
# 作成されたリソース一覧
terraform state list

# 出力値確認
terraform output

# 特定の出力値
terraform output instance_public_ip
```

## 🔧 トラブルシューティング

### メモリ不足

```bash
# スワップ追加（EC2内で実行）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### ポート接続できない

```bash
# セキュリティグループ確認
aws ec2 describe-security-groups --group-ids <SG_ID>
```

### Docker起動失敗

```bash
# ログ確認
docker compose logs -f

# リソース確認
df -h
free -h
```

## 📝 設定ファイル

### terraform.tfvars

```hcl
aws_region    = "ap-northeast-1"
instance_type = "t3.large"
app_name      = "video-message-app"
environment   = "dev"
key_name      = "your-key-name"
```

## 🔄 更新方法

```bash
# 設定変更後
terraform plan
terraform apply
```

## 📈 スケールアップ

必要に応じて:

1. `instance_type`を変更（t3.xlarge等）
2. EBSサイズを増やす
3. RDS追加
4. ECS/Fargate移行

## 📞 サポート

問題が発生した場合:

1. CloudWatch Logsを確認
2. EC2のシステムログを確認
3. `terraform plan`で差分確認

---

*Simple, Cost-Effective, Developer-Friendly*