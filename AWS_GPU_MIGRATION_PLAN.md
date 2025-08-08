# AWS GPU対応移行計画 - Video Message App

## 概要
OpenVoiceの性能を最大化するため、GPU インスタンスを活用した構成。使用時のみ起動することでコストを抑制。

## 1. 推奨アーキテクチャ（2インスタンス構成）

### 構成A: 分離型（推奨）

```yaml
インスタンス1 - アプリケーション用:
  タイプ: t3.large (2vCPU, 8GB RAM)
  用途:
    - Frontend (React)
    - Backend (FastAPI)
    - VOICEVOX Engine
    - データストレージ
  稼働: 開発時のみ（平日9-18時）
  コスト: 約$20/月

インスタンス2 - GPU処理用:
  タイプ: g4dn.xlarge (4vCPU, 16GB RAM, T4 GPU)
  用途:
    - OpenVoice V2 Service
    - 音声クローニング処理
    - 音声合成処理
  稼働: 必要時のみ（1日2-3時間）
  コスト: 約$40/月（使用時間による）
```

### 構成B: 統合型（シンプル）

```yaml
単一GPUインスタンス:
  タイプ: g4dn.xlarge
  用途: 全サービス
  稼働: 開発時のみ
  コスト: 約$80/月（1日8時間稼働）
```

## 2. コスト比較

### g4dn.xlarge料金（東京リージョン）

```yaml
オンデマンド:
  時間単価: $0.71/時間
  
使用パターン別月額:
  24時間稼働: $511/月
  平日8時間: $125/月
  平日4時間: $62/月
  必要時のみ（週10時間）: $31/月

スポットインスタンス（約70%割引）:
  時間単価: 約$0.21/時間
  平日8時間: 約$37/月
```

## 3. GPU最適化OpenVoice設定

### Dockerイメージ（GPU対応）

```dockerfile
# OpenVoice GPU Dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Python環境
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg

# PyTorch GPU版
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# OpenVoice V2
RUN git clone https://github.com/myshell-ai/OpenVoice.git /app/OpenVoice
WORKDIR /app/OpenVoice
RUN pip3 install -e .

# アプリケーションコード
COPY . /app/service
WORKDIR /app/service

# GPUを使用
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

CMD ["python3", "main.py"]
```

## 4. インスタンス管理戦略

### 自動起動・停止スケジュール

```python
# Lambda関数（コスト最適化）
import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # インスタンスタグで管理
    instances = {
        'app': 'i-xxxxx',     # t3.large
        'gpu': 'i-yyyyy'      # g4dn.xlarge
    }
    
    action = event.get('action')
    target = event.get('target', 'all')
    
    if action == 'start':
        if target in ['all', 'app']:
            ec2.start_instances(InstanceIds=[instances['app']])
        if target in ['all', 'gpu']:
            ec2.start_instances(InstanceIds=[instances['gpu']])
    
    elif action == 'stop':
        if target in ['all', 'app']:
            ec2.stop_instances(InstanceIds=[instances['app']])
        if target in ['all', 'gpu']:
            ec2.stop_instances(InstanceIds=[instances['gpu']])
    
    return {'statusCode': 200}
```

### EventBridgeスケジュール

```yaml
アプリケーションサーバー（t3.large）:
  平日朝起動: cron(0 0 ? * MON-FRI *)  # 9:00 JST
  平日夜停止: cron(0 10 ? * MON-FRI *) # 19:00 JST

GPUサーバー（g4dn.xlarge）:
  手動起動のみ（必要時にコマンドで起動）
```

## 5. 開発ワークフロー

### 通常の開発（GPUなし）

```bash
# アプリサーバーのみ起動
aws ec2 start-instances --instance-ids i-app-instance

# 開発作業
ssh ubuntu@app-server
cd video-message-app
docker compose up -d frontend backend voicevox

# 作業終了後
aws ec2 stop-instances --instance-ids i-app-instance
```

### OpenVoice開発時（GPU使用）

```bash
# 両方起動
aws ec2 start-instances --instance-ids i-app-instance i-gpu-instance

# GPUサーバーでOpenVoice起動
ssh ubuntu@gpu-server
cd openvoice-service
docker run --gpus all -p 8001:8001 openvoice-gpu

# 音声クローニング処理実行
# ... 処理 ...

# GPU使用終了後すぐ停止（コスト削減）
aws ec2 stop-instances --instance-ids i-gpu-instance
```

## 6. ネットワーク構成

```yaml
VPC: 10.0.0.0/16

サブネット:
  パブリック: 10.0.1.0/24
    - アプリサーバー: 10.0.1.10
    - GPUサーバー: 10.0.1.20

セキュリティグループ:
  app-sg:
    - 22/tcp (SSH)
    - 55433-55434/tcp (App)
    - 50021/tcp (VoiceVox)
  
  gpu-sg:
    - 22/tcp (SSH)
    - 8001/tcp (OpenVoice)
    - From app-sg only

内部通信:
  アプリ → GPU: http://10.0.1.20:8001
```

## 7. データ共有

### EFS（Elastic File System）使用

```yaml
共有ストレージ:
  タイプ: EFS
  マウント: /mnt/shared
  用途:
    - 音声プロファイル
    - 学習モデル
    - 生成データ
  
両インスタンスからアクセス:
  - アプリサーバー: 読み書き
  - GPUサーバー: 読み書き
```

## 8. コスト最適化テクニック

### 1. スポットインスタンス活用

```bash
# GPUインスタンスをスポットで起動
aws ec2 run-instances \
  --instance-type g4dn.xlarge \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.30"}}' \
  --image-id ami-xxxxxxxx
```

### 2. 処理のバッチ化

```python
# 複数の音声処理をまとめて実行
def batch_process():
    # GPU起動
    start_gpu_instance()
    
    # バッチ処理
    for task in pending_tasks:
        process_voice(task)
    
    # GPU停止
    stop_gpu_instance()
```

### 3. オートスケーリング

```yaml
処理キューベース:
  キュー長 > 10: GPU起動
  キュー長 = 0: GPU停止（5分後）
```

## 9. 月額コスト試算

### 最小構成（開発環境）

```
アプリサーバー (t3.large):
  8時間/日 × 22日 = 176時間
  $0.10 × 176 = $18

GPUサーバー (g4dn.xlarge):
  2時間/日 × 22日 = 44時間
  $0.71 × 44 = $31

EFS: $5
Elastic IP: $4
S3: $3

合計: 約$61/月
```

### スポット利用時

```
アプリサーバー: $18（変わらず）
GPUサーバー（スポット）: $9（70%割引）
その他: $12

合計: 約$39/月
```

## 10. セットアップ手順

### Step 1: インフラ作成

```bash
cd terraform/gpu
terraform init
terraform apply
```

### Step 2: アプリサーバー設定

```bash
ssh ubuntu@app-server

# Docker インストール
curl -fsSL https://get.docker.com | sh

# アプリケーションクローン
git clone <repository>
cd video-message-app

# 通常サービス起動
docker compose up -d frontend backend voicevox
```

### Step 3: GPUサーバー設定

```bash
ssh ubuntu@gpu-server

# NVIDIA Driver インストール（Deep Learning AMI使用時は不要）
# sudo apt install nvidia-driver-525

# Docker with GPU support
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# GPU確認
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# OpenVoiceセットアップ
git clone <openvoice-repo>
cd openvoice-gpu
docker build -t openvoice-gpu .
```

## 11. 管理スクリプト

### gpu-manage.sh

```bash
#!/bin/bash

case "$1" in
  start-all)
    aws ec2 start-instances --instance-ids i-app i-gpu
    ;;
  start-app)
    aws ec2 start-instances --instance-ids i-app
    ;;
  start-gpu)
    aws ec2 start-instances --instance-ids i-gpu
    ;;
  stop-all)
    aws ec2 stop-instances --instance-ids i-app i-gpu
    ;;
  stop-gpu)
    aws ec2 stop-instances --instance-ids i-gpu
    ;;
  status)
    aws ec2 describe-instances \
      --instance-ids i-app i-gpu \
      --query 'Reservations[*].Instances[*].[Tags[?Key==`Name`].Value|[0],State.Name,InstanceType]' \
      --output table
    ;;
esac
```

## 12. パフォーマンス比較

```yaml
処理速度:
  CPU (Mac M1): 30秒/音声
  CPU (t3.large): 45秒/音声
  GPU (T4): 3秒/音声  # 10-15倍高速

コスト効率:
  CPU 24時間: $70/月、処理能力 1x
  GPU 2時間/日: $31/月、処理能力 10x
  → GPUの方がコストパフォーマンス良好
```

## まとめ

**GPU利用のメリット**:
- OpenVoice処理が10-15倍高速
- 必要時のみ起動でコスト最適化
- 月額$40-60程度で高性能環境

**推奨運用**:
1. 通常開発: アプリサーバーのみ（$20/月）
2. 音声処理時: GPU追加起動（+$0.71/時間）
3. 処理完了後: GPU即停止

---

*High Performance, Cost Optimized, GPU Accelerated*