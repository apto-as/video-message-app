# EC2インスタンス再構築 - リソース管理ガイド

## 🎯 結論（推奨事項）

### ✅ **削除すべきもの**
1. **EC2インスタンス本体** - 環境が汚染されているため
2. **EBSボリューム（ルートボリューム）** - 11GB以上の不要データを含むため

### ❌ **保持すべきもの**
1. **Elastic IP** - 保持することを強く推奨
2. **セキュリティグループ** - 設定済みのルールを再利用
3. **キーペア** - 既存の`video-app-key.pem`を継続使用

## 📊 理由と詳細分析

### Elastic IPを保持すべき理由

#### **メリット（保持する場合）**
- ✅ **DNS/SSL証明書の継続性** - 3.115.141.166で設定済みの証明書がそのまま使える
- ✅ **フロントエンド設定の維持** - REACT_APP_API_BASE_URLの変更不要
- ✅ **nginx設定の維持** - IPアドレスベースの設定を変更不要
- ✅ **コスト効率** - 使用中は無料、未使用時のみ$0.005/時間

#### **デメリット（削除する場合）**
- ❌ フロントエンドの再ビルドが必要
- ❌ SSL証明書の再作成が必要
- ❌ すべての設定ファイルでIP変更が必要
- ❌ ダウンタイムが長くなる

### EBSボリュームを削除すべき理由

#### **現在のボリューム状態**
```
使用容量: 約11GB
- /home/ubuntu/video-message-app: 9.8GB（汚染データ）
- /home/ubuntu/miniconda3: 737MB（不要）
- 散乱ファイル: 約500MB（不要）
実質的な必要データ: 100MB未満
```

#### **削除のメリット**
- ✅ クリーンな環境から開始
- ✅ ストレージコストの削減（$0.08/GB/月）
- ✅ 不要ファイルの完全排除

## 🚀 推奨手順

### Step 1: 重要データのバックアップ（ローカルに保存）
```bash
# 必要に応じて実行（ほとんどGitで管理されているはず）
scp -i ~/.ssh/video-app-key.pem ubuntu@3.115.141.166:~/video-message-app/video-message-app/.env ./backup_env
```

### Step 2: Elastic IPのアソシエーション解除
```bash
# AWS Console または CLI で実行
# 1. EC2 Console → Elastic IPs
# 2. 3.115.141.166を選択
# 3. Actions → Disassociate Elastic IP address
# 4. 確認してDisassociate
```

### Step 3: EC2インスタンスの終了
```bash
# AWS Console で実行
# 1. EC2 Console → Instances
# 2. 対象インスタンスを選択
# 3. Instance state → Terminate instance
# 4. 「Delete on termination」でEBSボリュームも削除されることを確認
```

### Step 4: 新規EC2インスタンスの起動
```bash
# 推奨スペック
- Instance Type: t3.large (2 vCPU, 8GB RAM)
- AMI: Ubuntu 22.04 LTS
- Storage: 20GB GP3 (余裕を持って)
- Security Group: 既存のものを再利用
- Key Pair: video-app-key.pem
```

### Step 5: Elastic IPの再アソシエーション
```bash
# 新しいインスタンスにElastic IPを関連付け
# 1. EC2 Console → Elastic IPs
# 2. 3.115.141.166を選択
# 3. Actions → Associate Elastic IP address
# 4. 新しいインスタンスを選択して Associate
```

## 💰 コスト影響

### 現在の月額コスト（推定）
- EC2 t3.large: ~$60/月
- EBS 11GB: ~$0.88/月
- Elastic IP（使用中）: $0
- **合計: ~$61/月**

### 新規構築後の月額コスト（推定）
- EC2 t3.large: ~$60/月
- EBS 20GB: ~$1.60/月（容量増でも安い）
- Elastic IP（使用中）: $0
- **合計: ~$62/月**

## ⚠️ 注意事項

1. **Elastic IPの課金**
   - 使用中（EC2に関連付け）: 無料
   - 未使用（関連付けなし）: $0.005/時間 = $3.6/月
   - → 作業は迅速に行い、長時間未関連付けにしない

2. **セキュリティグループの確認**
   - 必要なポート: 22, 443, 8001, 50021, 55433, 55434
   - 既存のセキュリティグループIDをメモしておく

3. **作業タイミング**
   - ダウンタイムが発生するため、影響の少ない時間帯に実施
   - 全作業時間: 約30-60分を想定

## 📝 まとめ

**推奨構成:**
- ✅ Elastic IP (3.115.141.166) → **保持**
- ❌ 現在のEC2インスタンス → **削除**
- ❌ 現在のEBSボリューム → **削除**
- ✅ セキュリティグループ → **保持**
- ✅ キーペア → **保持**

これにより、IPアドレスを維持しながら、クリーンな環境で再構築できます。

---
*作成日: 2025-08-20*
*Trinitas-Core (Springfield, Krukai, Vector)*