# EC2インスタンス再構築 実行マニュアル

## 前提条件
- AWS Management Consoleへのアクセス権限
- 現在のインスタンス: i-09a9d522f733a3bb5
- Elastic IP: 3.115.141.166
- リージョン: ap-northeast-1 (東京)

## 🚀 実行手順

### Step 1: AWS Management Consoleにログイン
1. https://console.aws.amazon.com/ にアクセス
2. 適切なアカウントでログイン
3. リージョンを「アジアパシフィック (東京) ap-northeast-1」に設定

### Step 2: 現在のインスタンス情報を確認
1. EC2ダッシュボードを開く
2. 「インスタンス」をクリック
3. インスタンスID `i-09a9d522f733a3bb5` を検索
4. 以下の情報をメモ：
   - セキュリティグループID
   - サブネットID
   - キーペア名（video-app-key）

### Step 3: Elastic IPの関連付け解除
1. EC2 → ネットワーク&セキュリティ → Elastic IP
2. `3.115.141.166` を選択
3. 「アクション」→「Elastic IPアドレスの関連付けの解除」
4. 確認して「関連付け解除」

⚠️ **重要**: この時点から課金が始まります（$0.005/時間）。迅速に作業を進めてください。

### Step 4: 現在のインスタンスを終了
1. EC2 → インスタンス
2. インスタンスID `i-09a9d522f733a3bb5` を選択
3. 「インスタンスの状態」→「インスタンスを終了」
4. 確認ダイアログで「終了」をクリック

### Step 5: 新規インスタンスの起動

#### 5.1 基本設定
1. EC2 → インスタンス → 「インスタンスを起動」
2. **名前**: `video-message-app-v2`

#### 5.2 AMI選択
- **Ubuntu Server 22.04 LTS (HVM), SSD Volume Type**
- アーキテクチャ: 64ビット (x86)

#### 5.3 インスタンスタイプ
- **t3.large** (2 vCPU, 8 GiB メモリ)

#### 5.4 キーペア
- **既存のキーペアを選択**: `video-app-key`

#### 5.5 ネットワーク設定
- VPC: デフォルトVPC
- サブネット: 元のインスタンスと同じ（メモした値）
- パブリックIPの自動割り当て: 有効化
- セキュリティグループ: **既存のセキュリティグループを選択**（メモした値）

#### 5.6 ストレージ設定
- **20 GiB** GP3 (3000 IOPS, 125 MB/s)
- 終了時に削除: はい

#### 5.7 高度な詳細（ユーザーデータ）
以下のスクリプトを「ユーザーデータ」に貼り付け：

```bash
#!/bin/bash
# 基本パッケージのインストール
apt-get update
apt-get install -y \
    git \
    docker.io \
    docker-compose \
    nginx \
    python3-pip \
    nodejs \
    npm \
    ffmpeg \
    curl \
    wget

# Dockerの設定
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu

# 作業ディレクトリ作成
mkdir -p /home/ubuntu/video-message-app
chown -R ubuntu:ubuntu /home/ubuntu/video-message-app

# UVのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/ubuntu/.bashrc

# 完了マーカー
touch /home/ubuntu/setup_complete.txt
echo "Basic setup completed at $(date)" >> /home/ubuntu/setup_complete.txt
```

### Step 6: インスタンスの起動確認
1. 「インスタンスを起動」をクリック
2. インスタンスIDをメモ
3. ステータスが「実行中」になるまで待機（約1-2分）

### Step 7: Elastic IPの再関連付け
1. EC2 → ネットワーク&セキュリティ → Elastic IP
2. `3.115.141.166` を選択
3. 「アクション」→「Elastic IPアドレスの関連付け」
4. リソースタイプ: インスタンス
5. インスタンス: 新しく起動したインスタンスを選択
6. 「関連付ける」をクリック

✅ **課金停止**: Elastic IPが再関連付けされ、追加課金が停止します。

### Step 8: SSH接続確認
```bash
ssh -i ~/.ssh/video-app-key.pem ubuntu@3.115.141.166
```

接続できたら：
```bash
# セットアップ完了確認
cat ~/setup_complete.txt

# Dockerバージョン確認
docker --version
docker-compose --version

# UVインストール確認
source ~/.bashrc
uv --version
```

## 📋 次のステップ

新しいEC2インスタンスで以下を実行：

### 1. リポジトリのクローン
```bash
cd ~
git clone https://github.com/apto-as/prototype-app video-message-app
cd video-message-app
```

### 2. UV環境でOpenVoiceセットアップ
```bash
cd video-message-app
./ec2_setup/setup_ec2_uv.sh
```

### 3. Docker環境の起動
```bash
docker-compose up -d
```

### 4. OpenVoiceサービスの起動
```bash
source ~/video-message-app/activate_openvoice.sh
cd ~/video-message-app/video-message-app
python openvoice_ec2_service.py
```

## ⏱️ 推定作業時間
- Elastic IP解除〜再関連付け: 10-15分
- 初期セットアップ: 20-30分
- 合計: 30-45分

## 💰 コスト影響
- Elastic IP未使用時間を15分と仮定: $0.005 × 0.25 = $0.00125（約0.2円）
- 新規EBSボリューム: 20GB × $0.08/GB/月 = $1.60/月

## ⚠️ トラブルシューティング

### SSH接続できない場合
1. セキュリティグループでポート22が開いているか確認
2. インスタンスのステータスチェックが2/2パスしているか確認
3. キーペアのパーミッション: `chmod 600 ~/.ssh/video-app-key.pem`

### Dockerが起動しない場合
```bash
sudo systemctl status docker
sudo systemctl restart docker
```

---
*作成日: 2025-08-20*
*Trinitas-Core*