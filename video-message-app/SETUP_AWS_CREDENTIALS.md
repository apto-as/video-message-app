# AWS認証設定ガイド

## AWS CLIの認証設定手順

### 1. AWS CLIの認証情報設定

以下のコマンドを実行して、AWS認証情報を設定してください：

```bash
aws configure
```

必要な情報：
- **AWS Access Key ID**: AWSコンソールから取得
- **AWS Secret Access Key**: AWSコンソールから取得  
- **Default region name**: `ap-northeast-1` (東京リージョン)
- **Default output format**: `json`

### 2. 認証情報の確認

設定後、以下のコマンドで確認：

```bash
aws sts get-caller-identity
```

### 3. スポットインスタンスの起動

認証設定完了後、以下のスクリプトでGPUインスタンスを起動できます：

```bash
# 作成済みのスクリプトを実行
~/launch_gpu_spot_simple.sh
```

## IAMユーザーに必要な権限

スポットインスタンスを起動するために、以下の権限が必要です：

### 最小限の権限ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:RequestSpotInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeSpotInstanceRequests",
                "ec2:DescribeSpotPriceHistory",
                "ec2:DescribeImages",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcs",
                "ec2:CreateTags",
                "ec2:TerminateInstances",
                "ec2:CancelSpotInstanceRequests"
            ],
            "Resource": "*"
        }
    ]
}
```

## セキュリティグループの設定

GPUインスタンス用のセキュリティグループ設定：

```bash
# セキュリティグループの作成
aws ec2 create-security-group \
    --group-name openvoice-gpu-sg \
    --description "Security group for OpenVoice GPU instance" \
    --vpc-id $(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text)

# 必要なポートを開放
# OpenVoice Service用
aws ec2 authorize-security-group-ingress \
    --group-name openvoice-gpu-sg \
    --protocol tcp \
    --port 8001 \
    --cidr 0.0.0.0/0

# SSH用（必要に応じて）
aws ec2 authorize-security-group-ingress \
    --group-name openvoice-gpu-sg \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0
```

## 起動後の確認手順

1. **インスタンスの状態確認**：
```bash
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=OpenVoice-GPU" \
    --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]" \
    --output table
```

2. **スポットリクエストの状態確認**：
```bash
aws ec2 describe-spot-instance-requests \
    --filters "Name=state,Values=active,open" \
    --query "SpotInstanceRequests[*].[SpotInstanceRequestId,State,InstanceId]" \
    --output table
```

## トラブルシューティング

### 認証エラーの場合

1. **認証情報の再設定**：
```bash
aws configure --profile default
```

2. **環境変数での設定**（一時的）：
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=ap-northeast-1
```

### スポットインスタンス起動エラー

1. **容量不足エラー**: 別のアベイラビリティゾーンを試す
2. **価格超過**: Max Spot Priceを調整
3. **権限不足**: IAMポリシーを確認

## 次のステップ

AWS認証設定が完了したら：

1. スポットインスタンスを起動
2. インスタンスのパブリックIPを取得
3. OpenVoice V2環境をセットアップ
4. 現在のt3.largeインスタンスと接続設定

---
作成: 2025-08-09
Trinitas-Core (Springfield, Krukai, Vector)