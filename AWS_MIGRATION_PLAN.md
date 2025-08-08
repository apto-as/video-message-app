# AWS移行計画書 - Video Message App

## エグゼクティブサマリー

現在ローカル環境で動作しているVideo Message Appを、スケーラブルで高可用性のAWSクラウド環境へ移行する包括的な計画書です。

### 現状のアーキテクチャ
- **Frontend**: React 19（ポート55434）
- **Backend**: FastAPI（ポート55433）
- **音声エンジン**: VOICEVOX（Docker、ポート50021）
- **音声クローン**: OpenVoice Native Service（Conda環境、ポート8001）
- **外部API**: D-ID（動画生成）

## 1. 目標アーキテクチャ

### 1.1 コンピューティングサービス

#### Frontend
- **サービス**: AWS Fargate (ECS)
- **スケーリング**: Auto Scaling 1-10タスク
- **ロードバランサー**: Application Load Balancer
- **コンテナリソース**: 0.5 vCPU, 1GB RAM

#### Backend API
- **サービス**: AWS Fargate (ECS)
- **スケーリング**: Auto Scaling 2-20タスク
- **コンテナリソース**: 2 vCPU, 4GB RAM
- **ヘルスチェック**: /health エンドポイント

#### OpenVoice Service
- **サービス**: EC2 Auto Scaling Group
- **インスタンスタイプ**: g4dn.xlarge (GPU搭載)
- **スケーリング**: 1-5インスタンス
- **GPU**: NVIDIA Tesla T4
- **AMI**: Deep Learning AMI (Ubuntu 20.04)

#### VOICEVOX Engine
- **サービス**: AWS Fargate (ECS)
- **スケーリング**: Auto Scaling 1-3タスク
- **コンテナリソース**: 2 vCPU, 4GB RAM

### 1.2 ストレージアーキテクチャ

#### 音声プロファイル
- **プライマリ**: Amazon EFS（共有アクセス用）
- **バックアップ**: S3（バージョニング有効）
- **暗号化**: KMS管理キー

#### 生成動画
- **ストレージ**: S3（ライフサイクルポリシー付き）
- **配信**: CloudFront CDN
- **保持期間**: 30日（標準）、90日（Infrequent Access）

#### アプリケーションデータベース
- **サービス**: Amazon RDS PostgreSQL
- **構成**: Multi-AZ配置
- **バックアップ**: ポイントインタイムリカバリ

## 2. ネットワークアーキテクチャ

### 2.1 VPC設計
```
VPC CIDR: 10.0.0.0/16

Public Subnets:
- 10.0.1.0/24 (AZ-1) - ALB, NAT Gateway
- 10.0.2.0/24 (AZ-2) - ALB, NAT Gateway

Private Subnets:
- 10.0.11.0/24 (AZ-1) - ECS Tasks, EC2
- 10.0.12.0/24 (AZ-2) - ECS Tasks, EC2

Database Subnets:
- 10.0.21.0/24 (AZ-1) - RDS Primary
- 10.0.22.0/24 (AZ-2) - RDS Standby
```

### 2.2 セキュリティグループ

#### ALB Security Group
- インバウンド: 80/tcp (リダイレクト), 443/tcp (HTTPS)
- アウトバウンド: 全許可

#### Backend ECS Security Group
- インバウンド: 55433/tcp (ALBから)
- アウトバウンド: 全許可

#### OpenVoice EC2 Security Group
- インバウンド: 8001/tcp (Backend SGから), 22/tcp (Bastionから)
- アウトバウンド: 全許可

#### RDS Security Group
- インバウンド: 5432/tcp (Backend SGから)
- アウトバウンド: 全許可

## 3. セキュリティ実装

### 3.1 データ保護
- **暗号化（保存時）**: S3/EFS KMS暗号化
- **暗号化（転送時）**: TLS 1.3エンドツーエンド
- **キーローテーション**: 年次自動ローテーション

### 3.2 API セキュリティ
- **認証**: JWTトークン（短期有効期限）
- **レート制限**: API Gatewayスロットリング
- **入力検証**: WAFカスタムルール

### 3.3 コンプライアンス
- **監査ログ**: CloudTrail + CloudWatch
- **脆弱性スキャン**: ECR自動スキャン
- **侵入テスト**: 四半期ごとの評価

## 4. パフォーマンス最適化

### 4.1 OpenVoice GPU最適化
- **インスタンス**: g4dn.xlarge (4 vCPU, 16GB, T4 GPU)
- **CUDA**: バージョン11.8 + cuDNN 8
- **モデルキャッシング**: EFS共有ストレージ

### 4.2 キャッシング戦略
- **アプリケーションキャッシュ**: ElastiCache (Redis)
- **音声プロファイルキャッシュ**: TTL 24時間
- **CDN最適化**: CloudFrontエッジキャッシング

## 5. CI/CD パイプライン

### 5.1 ソース管理
- **リポジトリ**: AWS CodeCommit または GitHub
- **ブランチ戦略**: GitFlow

### 5.2 ビルド自動化
- **Frontend**: CodeBuild → ECR
- **Backend**: CodeBuild → ECR
- **OpenVoice**: EC2 Image Builder → カスタムAMI

### 5.3 デプロイメント
- **開発環境**: 自動デプロイ
- **ステージング**: 承認後デプロイ
- **本番環境**: Blue-Greenデプロイメント

## 6. コスト最適化

### 6.1 リソーススケジューリング
- **開発環境**: 営業時間外自動停止
- **本番環境**: Spot Instancesの活用

### 6.2 ストレージライフサイクル
- **標準**: 0-30日
- **Infrequent Access**: 30-90日
- **Glacier**: 90日以降（必要時）

### 6.3 予算管理
- **月次予算**: $500閾値アラート
- **異常検知**: 20%増加でアラート

## 7. 監視とオブザーバビリティ

### 7.1 メトリクス
- **音声合成レイテンシ**: <10秒 (P95)
- **動画生成時間**: <60秒 (P95)
- **API応答時間**: <200ms (P95)
- **システム可用性**: >99.9%

### 7.2 ログ管理
- **集約**: CloudWatch Logs
- **フォーマット**: JSON構造化ログ
- **保持期間**: アプリ30日、監査1年

### 7.3 アラート
- **エラー率**: >5%で5分間継続
- **リソース使用率**: CPU/メモリ >80%で10分間
- **通知**: SNS → Slack/PagerDuty

## 8. 移行スケジュール

### Phase 1: 基盤構築（第1-2週）
- AWS アカウントセットアップ
- VPC、サブネット、セキュリティグループ
- ECR リポジトリ作成

### Phase 2: コアサービス（第3-4週）
- RDS PostgreSQL構築
- ECS クラスター設定
- ALB と SSL証明書

### Phase 3: OpenVoice移行（第5-6週）
- GPU対応EC2 Auto Scaling Group
- カスタムAMI作成
- EFS統合

### Phase 4: 統合テスト（第7-8週）
- 全サービス統合テスト
- データ移行
- DNS切り替え準備

### Phase 5: 本番展開（第9-10週）
- 本番デプロイメント
- 監視・アラート設定
- パフォーマンス最適化

## 9. リスク管理

### 9.1 技術的リスク
- **OpenVoice GPU対応**: 事前検証実施
- **データ移行**: 段階的移行とロールバック計画
- **外部API依存**: タイムアウトとリトライ戦略

### 9.2 運用リスク
- **コスト超過**: 日次モニタリング
- **パフォーマンス劣化**: ベースライン設定と監視
- **セキュリティ侵害**: 多層防御とインシデント対応計画

## 10. 成功基準

### 10.1 技術指標
- 全サービス正常稼働
- レスポンスタイム目標達成
- 99.9%以上の可用性

### 10.2 ビジネス指標
- 月次コスト20%削減
- ユーザー満足度維持・向上
- スケーラビリティ確保

## 11. 次のステップ

1. AWS アカウント作成と初期設定
2. Terraform コード作成開始
3. 開発環境の構築
4. 段階的なサービス移行

---

*作成日: 2025-08-07*
*作成者: Trinitas-Core AWS Migration Team*