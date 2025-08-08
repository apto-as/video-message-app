# AWS移行計画書（開発環境版）- Video Message App

## 概要
開発環境として使用することを前提に、**シンプル・低コスト・実用的**な構成でAWS移行を行います。

## 1. 最小構成アーキテクチャ

### 1.1 単一EC2インスタンス構成（最もシンプル）

```yaml
構成:
  EC2インスタンス: 1台（t3.medium または t3.large）
  OS: Ubuntu 22.04 LTS
  内容:
    - Docker Compose で全サービス稼働
    - Frontend (React)
    - Backend (FastAPI)
    - VOICEVOX Engine
    - OpenVoice Service（CPU版に変更）
  ストレージ: 
    - EBS 100GB (gp3)
    - S3バケット 1個（バックアップ用）
```

**月額コスト目安**: 約$50-70
- EC2 t3.medium: $30/月
- EBS 100GB: $10/月
- S3 + データ転送: $10/月
- Elastic IP: $4/月

### 1.2 推奨構成（コスト効率重視）

```yaml
構成パターンA - EC2単体運用:
  インスタンスタイプ: t3.large (2vCPU, 8GB RAM)
  自動停止: 夜間・週末停止でコスト70%削減
  
構成パターンB - ECS on EC2（少し高度）:
  EC2: t3.medium 1台
  ECS: Dockerコンテナ管理
  利点: デプロイが簡単、ログ管理が楽
```

## 2. シンプルなネットワーク構成

```yaml
VPC:
  CIDR: 10.0.0.0/16（デフォルトVPCでもOK）
  
サブネット:
  パブリック: 10.0.1.0/24（1個で十分）
  
セキュリティグループ:
  インバウンド:
    - 22/tcp (SSH) - 自分のIPのみ
    - 80/tcp (HTTP)
    - 443/tcp (HTTPS) 
    - 55433/tcp (Backend)
    - 55434/tcp (Frontend)
```

## 3. 最小限のセキュリティ

```yaml
基本セキュリティ:
  - SSH: キーペア認証のみ
  - セキュリティグループ: 必要最小限のポート開放
  - IAMロール: EC2用の基本ロール（S3アクセス）
  
省略する項目:
  - WAF（不要）
  - CloudTrail（不要）
  - 複雑な暗号化（デフォルトで十分）
```

## 4. データ管理（シンプル版）

```yaml
ストレージ:
  音声プロファイル: EC2のEBSに直接保存
  バックアップ: S3に日次バックアップ（スクリプトで自動化）
  
データベース:
  選択肢1: EC2内のSQLite（最も簡単）
  選択肢2: EC2内のPostgreSQL（Docker）
  選択肢3: RDS t3.micro（月$15追加だが管理が楽）
```

## 5. 超簡単デプロイメント

### 5.1 初期セットアップ（30分で完了）

```bash
# 1. EC2インスタンス作成（AWS Console）
- AMI: Ubuntu 22.04 LTS
- インスタンスタイプ: t3.large
- ストレージ: 100GB
- セキュリティグループ設定

# 2. SSH接続して環境構築
ssh -i mykey.pem ubuntu@<EC2-IP>

# 3. Dockerインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 4. Docker Compose インストール
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 5. アプリケーションクローン
git clone <repository>
cd video-message-app

# 6. 環境変数設定
cp backend/.env.example backend/.env
# D-ID APIキー設定

# 7. 起動
docker compose up -d
```

### 5.2 自動起動設定

```bash
# systemdサービス作成
sudo tee /etc/systemd/system/video-app.service << EOF
[Unit]
Description=Video Message App
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/video-message-app
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable video-app
sudo systemctl start video-app
```

## 6. コスト削減テクニック

### 6.1 自動停止スクリプト

```python
# Lambda関数で実装（月数円のコスト）
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='ap-northeast-1')
    
    # 開発環境タグが付いたインスタンスを停止
    if event['action'] == 'stop':
        ec2.stop_instances(
            InstanceIds=['i-xxxxx']  # インスタンスID
        )
    elif event['action'] == 'start':
        ec2.start_instances(
            InstanceIds=['i-xxxxx']
        )
    
    return {'statusCode': 200}
```

### 6.2 CloudWatch Events設定

```yaml
停止スケジュール:
  平日: 19:00 JST に自動停止
  土日: 終日停止
  
起動スケジュール:
  平日: 08:00 JST に自動起動
  
コスト削減効果: 約70%（168時間→50時間稼働）
```

## 7. 段階的な改善プラン

### Phase 1: 最小構成でスタート（今すぐ）
- 単一EC2インスタンス
- Docker Compose運用
- 手動デプロイ

### Phase 2: 自動化追加（1ヶ月後）
- GitHub Actions でCI/CD
- 自動バックアップ
- 監視追加（CloudWatch基本メトリクス）

### Phase 3: スケーラビリティ考慮（3ヶ月後）
- ECS移行検討
- RDS導入検討
- Auto Scaling検討

## 8. 簡易監視設定

```yaml
CloudWatch（無料枠内）:
  基本メトリクス:
    - CPU使用率
    - メモリ使用率
    - ディスク使用率
  
  アラート（最小限）:
    - インスタンス停止
    - ディスク容量80%超過
  
  通知:
    - メールのみ（SNS経由）
```

## 9. バックアップ戦略（シンプル版）

```bash
#!/bin/bash
# 日次バックアップスクリプト
BACKUP_DIR="/home/ubuntu/backups"
S3_BUCKET="my-video-app-backups"
DATE=$(date +%Y%m%d)

# データディレクトリのバックアップ
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /home/ubuntu/video-message-app/data/

# S3へアップロード
aws s3 cp $BACKUP_DIR/data_$DATE.tar.gz s3://$S3_BUCKET/

# 7日以上前のローカルバックアップ削除
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

# S3の30日以上前のバックアップは自動削除（ライフサイクルポリシー）
```

## 10. 月額コスト試算

### 最小構成（推奨）
```
EC2 t3.large (稼働時間30%): $25
EBS 100GB gp3: $10
S3 50GB + 転送: $5
Elastic IP: $4
CloudWatch: $0（無料枠）
-------------------
合計: 約$44/月
```

### 24時間稼働の場合
```
EC2 t3.large (24/7): $70
EBS 100GB gp3: $10
S3 50GB + 転送: $5
Elastic IP: $0（使用中は無料）
-------------------
合計: 約$85/月
```

### さらに安くする方法
- t3.medium使用: -$15/月
- Spot Instance使用: -50%
- Reserved Instance (1年): -40%

## 11. 移行手順（1日で完了）

### 午前（2時間）
1. AWSアカウント作成
2. EC2インスタンス起動
3. セキュリティグループ設定

### 午後（4時間）
4. Docker環境構築
5. アプリケーションデプロイ
6. 動作確認
7. データ移行（必要なら）

### 完了後
8. 自動停止設定
9. バックアップ設定
10. 簡易監視設定

## 12. トラブルシューティング

### よくある問題

```yaml
メモリ不足:
  症状: OpenVoiceがクラッシュ
  対策: t3.large以上を使用 or スワップ追加

ポート接続できない:
  症状: ブラウザからアクセス不可
  対策: セキュリティグループ確認

Docker Compose起動失敗:
  症状: コンテナが起動しない
  対策: docker logs で確認、メモリ・ディスク確認
```

## 13. 次のステップ

1. **今すぐ実行**
   - EC2インスタンス作成
   - 基本セットアップ

2. **1週間以内**
   - 自動停止設定
   - バックアップ設定

3. **必要に応じて**
   - CI/CD追加
   - 監視強化
   - スケーリング対応

---

## まとめ

この構成なら：
- **初期費用**: $0（無料利用枠活用可能）
- **月額費用**: $44〜85
- **構築時間**: 1日
- **管理負荷**: 最小限
- **拡張性**: 段階的に改善可能

開発環境として十分な性能を持ちながら、コストを最小限に抑えた実用的な構成です。

---

*作成日: 2025-08-07*
*バージョン: Simple & Cost-Effective Edition*