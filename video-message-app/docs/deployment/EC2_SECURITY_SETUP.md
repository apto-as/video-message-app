# EC2 セキュリティグループ設定ガイド

**作成日**: 2025-11-02
**対象**: video-message-app EC2インスタンス (3.115.141.166)
**優先度**: CRITICAL-2 (CVSS 8.6)

---

## 🚨 現状の問題点

現在、EC2インスタンスのセキュリティグループが**全世界に開放**されています：

| ポート | サービス | 現状 | リスク |
|-------|---------|------|--------|
| 22 | SSH | 0.0.0.0/0 (全開放) | 🔴 CRITICAL |
| 55433 | Backend API | 0.0.0.0/0 (全開放) | 🔴 HIGH |
| 50021 | VOICEVOX | 0.0.0.0/0 (全開放) | 🟡 MEDIUM |
| 8001 | OpenVoice | 0.0.0.0/0 (全開放) | 🟡 MEDIUM |
| 80 | HTTP | 0.0.0.0/0 (開放) | 🟢 OK (本番時必要) |
| 443 | HTTPS | 0.0.0.0/0 (開放) | 🟢 OK (本番時必要) |

---

## ✅ 推奨設定（開発環境）

### Step 1: 現在のセキュリティグループIDを確認

```bash
# EC2インスタンスのセキュリティグループIDを取得
aws ec2 describe-instances \
  --instance-ids $(aws ec2 describe-instances \
    --filters "Name=ip-address,Values=3.115.141.166" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text) \
  --query "Reservations[0].Instances[0].SecurityGroups[*].[GroupId,GroupName]" \
  --output table \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents
```

**出力例**:
```
---------------------------------
|      DescribeInstances        |
+------------------+-------------+
|  sg-0abc123def   |  video-sg   |
+------------------+-------------+
```

`sg-0abc123def` をメモしてください。

### Step 2: 開発者IPアドレスを確認

```bash
# 現在のグローバルIPアドレスを確認
curl -s https://checkip.amazonaws.com

# 出力例: 203.0.113.42
```

このIPアドレスをメモしてください（以降 `YOUR_IP` として参照）。

### Step 3: 現在のルールを削除（SSH・APIポートのみ）

⚠️ **重要**: HTTP (80) と HTTPS (443) は削除しないでください（本番アクセス用）。

```bash
# セキュリティグループIDを環境変数に設定
export SG_ID="sg-0abc123def"  # Step 1で確認したID

# SSH (22) の既存ルールを削除
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# Backend API (55433) の既存ルールを削除
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 55433 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# VOICEVOX (50021) の既存ルールを削除
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 50021 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# OpenVoice (8001) の既存ルールを削除
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8001 \
  --cidr 0.0.0.0/0 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents
```

### Step 4: 開発者IP限定のルールを追加

```bash
# 開発者IPを環境変数に設定
export YOUR_IP="203.0.113.42"  # Step 2で確認したIP

# SSH (22) を開発者IPのみに制限
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr ${YOUR_IP}/32 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# Backend API (55433) を開発者IPのみに制限
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 55433 \
  --cidr ${YOUR_IP}/32 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# VOICEVOX (50021) を開発者IPのみに制限
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 50021 \
  --cidr ${YOUR_IP}/32 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents

# OpenVoice (8001) を開発者IPのみに制限
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8001 \
  --cidr ${YOUR_IP}/32 \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents
```

### Step 5: 設定を確認

```bash
# セキュリティグループのルールを確認
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --query "SecurityGroups[0].IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[0].CidrIp]" \
  --output table \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents
```

**期待される出力**:
```
-----------------------------------------------
|          DescribeSecurityGroups            |
+---------+--------+--------+----------------+
|  tcp    |  22    |  22    | YOUR_IP/32     |
|  tcp    |  80    |  80    | 0.0.0.0/0      |
|  tcp    |  443   |  443   | 0.0.0.0/0      |
|  tcp    |  50021 |  50021 | YOUR_IP/32     |
|  tcp    |  55433 |  55433 | YOUR_IP/32     |
|  tcp    |  8001  |  8001  | YOUR_IP/32     |
-----------------------------------------------
```

---

## 📋 本番環境用の推奨設定（将来）

本番デプロイ時は以下の設定を推奨：

### 1. VPN経由でのアクセス
```bash
# VPN IPレンジ（例: 10.0.0.0/16）からのみSSHを許可
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 10.0.0.0/16
```

### 2. ALB (Application Load Balancer) 経由
- ユーザーアクセス: ALB → EC2 (Backend 55433)
- EC2セキュリティグループ: ALBのセキュリティグループIDのみ許可

### 3. WAF (Web Application Firewall)
- ALBにAWS WAFを適用
- OWASP Top 10の脅威から保護

---

## 🔧 トラブルシューティング

### Q1: IPアドレスが動的に変わる場合は？

**Option A**: VPN経由でアクセス
```bash
# VPN IP固定レンジを設定
export VPN_IP="203.0.113.0/24"  # /24 = 256アドレス

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr $VPN_IP
```

**Option B**: Systems Managerセッションマネージャー使用
```bash
# SSHの代わりにSession Managerでアクセス（ポート22不要）
aws ssm start-session \
  --target i-xxxxxxxxx \
  --region ap-northeast-1 \
  --profile aws-mcp-admin-agents
```

### Q2: 複数の開発者がいる場合は？

```bash
# 開発者ごとにルールを追加
export DEV1_IP="203.0.113.42"
export DEV2_IP="198.51.100.15"

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr ${DEV1_IP}/32

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr ${DEV2_IP}/32
```

### Q3: 誤って全ポートを削除してしまった場合は？

```bash
# AWS Management Consoleからログインして復旧
# または IAM ロールを使用してEC2から内部修正
```

---

## ✅ セキュリティチェックリスト

設定完了後、以下を確認：

- [ ] SSH (22) は開発者IPのみ (`YOUR_IP/32`)
- [ ] Backend API (55433) は開発者IPのみ
- [ ] VOICEVOX (50021) は開発者IPのみ
- [ ] OpenVoice (8001) は開発者IPのみ
- [ ] HTTP (80) は 0.0.0.0/0 のまま（本番用）
- [ ] HTTPS (443) は 0.0.0.0/0 のまま（本番用）
- [ ] SSHログイン成功を確認: `ssh ec2-user@3.115.141.166`
- [ ] APIアクセス成功を確認: `curl http://3.115.141.166:55433/health`

---

## 📊 セキュリティ改善効果

| 項目 | 改善前 | 改善後 |
|------|-------|--------|
| SSHブルートフォース攻撃リスク | 🔴 HIGH (全世界から攻撃可能) | 🟢 LOW (単一IP限定) |
| API不正アクセスリスク | 🔴 HIGH | 🟢 LOW |
| 攻撃対象面 | 6ポート × 42億IP | 6ポート × 1IP |
| セキュリティスコア | CVSS 8.6 (HIGH) | CVSS 3.2 (LOW) |

---

**実施日時**: _____________
**実施者**: _____________
**次回レビュー日**: _____________

---

## 📚 関連ドキュメント

- [SECURITY_CREDENTIALS_GUIDE.md](./SECURITY_CREDENTIALS_GUIDE.md) - D-ID APIキー管理
- [AWS_MCP_ASSESSMENT.md](./AWS_MCP_ASSESSMENT.md) - AWS MCP必要性評価
- `./.claude/CLAUDE.md` Rule 11 - プロジェクト固有セキュリティ規則
