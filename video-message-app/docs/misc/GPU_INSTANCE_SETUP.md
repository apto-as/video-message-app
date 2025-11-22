# GPUインスタンス構成ガイド

## 現在のアーキテクチャ構成

### 既存インスタンス (t3.large)
- **役割**: メインアプリケーション
- **IP**: 3.115.141.166
- **サービス**:
  - Frontend (React)
  - Backend API (FastAPI)
  - VoiceVox (Docker)
  - Nginx (HTTPS)

### 新規GPUインスタンス (g4dn.xlarge)
- **役割**: GPU処理専用
- **サービス**: OpenVoice V2 Native Service
- **ポート**: 8001
- **コスト**: スポット約$0.21/時間

## セットアップ手順

### ステップ1: AWS認証設定

```bash
# AWS CLIの設定
aws configure

# 以下を入力:
# AWS Access Key ID: [あなたのアクセスキー]
# AWS Secret Access Key: [あなたのシークレットキー]
# Default region name: ap-northeast-1
# Default output format: json
```

### ステップ2: GPUスポットインスタンス起動

```bash
# AWSコンソールまたはCLIで起動
# 設定内容:
# - AMI: Deep Learning Base GPU AMI (Ubuntu 22.04)
# - Instance Type: g4dn.xlarge
# - Spot Max Price: $0.35
# - Security Group: 8001ポート開放
# - User Data: 自動セットアップスクリプト付き
```

### ステップ3: 起動確認とIP取得

```bash
# インスタンス情報の取得
aws ec2 describe-instances \
    --filters "Name=instance-type,Values=g4dn.xlarge" \
              "Name=instance-state-name,Values=running" \
    --query "Reservations[*].Instances[*].[InstanceId,PublicIpAddress,State.Name]" \
    --output table
```

### ステップ4: t3.largeインスタンスの設定更新

GPUインスタンスのIPアドレスを取得後、t3.largeインスタンスで設定:

```bash
# EC2 (t3.large)にSSH接続
ssh -i ~/.ssh/video-app-key.pem ubuntu@3.115.141.166

# backend/.envを更新
cd ~/video-message-app/video-message-app
sudo nano backend/.env

# 以下の行を更新（GPU_INSTANCE_IPは実際のIPに置換）:
OPENVOICE_SERVICE_URL=http://GPU_INSTANCE_IP:8001

# Dockerコンテナを再起動
sudo docker-compose restart backend
```

## ネットワーク構成図

```
Internet
   |
   v
[Nginx on t3.large:443]
   |
   +---> [Frontend:55434]
   |
   +---> [Backend API:55433]
           |
           +---> [VoiceVox:50021] (同一Docker内)
           |
           +---> [OpenVoice GPU:8001] (別インスタンス)
                   ^
                   |
              [g4dn.xlarge]
```

## コスト最適化戦略

### 1. 自動停止スクリプト

```bash
# 未使用時の自動停止（t3.largeで実行）
cat > ~/stop_gpu_if_idle.sh << 'EOF'
#!/bin/bash
# 最後のリクエストから30分経過したら停止
IDLE_TIME=1800
LAST_REQUEST=$(curl -s http://GPU_INSTANCE_IP:8001/last_request_time)
CURRENT_TIME=$(date +%s)
if [ $((CURRENT_TIME - LAST_REQUEST)) -gt $IDLE_TIME ]; then
    aws ec2 stop-instances --instance-ids INSTANCE_ID
fi
EOF

# cronで定期実行
crontab -e
# 追加: */10 * * * * /home/ubuntu/stop_gpu_if_idle.sh
```

### 2. オンデマンド起動

```bash
# 必要時のみGPUインスタンスを起動
cat > ~/start_gpu_instance.sh << 'EOF'
#!/bin/bash
INSTANCE_ID="i-xxxxxxxxx"  # 実際のインスタンスID
aws ec2 start-instances --instance-ids $INSTANCE_ID
echo "GPUインスタンス起動中..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "GPUインスタンス起動完了"
EOF
```

## テスト手順

### 1. 接続テスト

```bash
# t3.largeから実行
curl http://GPU_INSTANCE_IP:8001/health
```

### 2. 音声クローンテスト

```bash
# ローカルから実行
curl -X POST https://3.115.141.166/api/voice-clone/create \
  -F "profile_name=test_gpu" \
  -F "audio_file=@test_voice.wav"
```

### 3. 音声合成テスト

```bash
curl -X POST https://3.115.141.166/api/unified-voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "GPUインスタンスでの音声合成テストです",
    "voice_profile": {
      "id": "test_gpu",
      "provider": "openvoice"
    }
  }' \
  --output test_gpu_output.wav
```

## トラブルシューティング

### GPUインスタンスが起動しない
- スポット価格を確認: 現在の相場を確認して調整
- 容量不足: 別のアベイラビリティゾーンを試す

### 接続できない
- セキュリティグループ: 8001ポートが開いているか確認
- OpenVoiceサービス: systemctl status openvoice確認

### 音声生成が遅い
- GPU使用状況: nvidia-smiで確認
- メモリ不足: インスタンスタイプをアップグレード

## モニタリング

### CloudWatchでの監視

```bash
# GPUメトリクスの有効化
aws cloudwatch put-metric-alarm \
  --alarm-name gpu-high-utilization \
  --alarm-description "Alert when GPU usage is high" \
  --metric-name GPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## 次のステップ

1. AWS認証情報の設定
2. GPUスポットインスタンスの起動
3. OpenVoice V2環境の構築
4. t3.largeとの接続設定
5. 統合テストの実施

---
作成: 2025-08-09
Trinitas-Core System