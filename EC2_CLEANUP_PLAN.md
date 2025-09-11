# EC2環境クリーンアップ計画

## 現状の問題点

EC2環境（3.115.141.166）が以下の問題を抱えています：

1. **ディスク使用量**: 約11GB（不要ファイルが大半）
2. **Git同期崩壊**: 100個の未コミット変更
3. **重複環境**: Miniconda、古いOpenVoice環境、UV環境が混在
4. **散乱ファイル**: 56個の修正スクリプトやアーカイブがホームに散乱

## クリーンアップ手順

### Phase 1: バックアップ（念のため）
```bash
# 重要な設定のみバックアップ
ssh -i ~/.ssh/video-app-key.pem ubuntu@3.115.141.166
mkdir -p ~/backup_20250820
cp ~/video-message-app/video-message-app/.env ~/backup_20250820/
cp -r ~/video-message-app/video-message-app/data/backend/storage ~/backup_20250820/
```

### Phase 2: 不要ファイルの削除
```bash
# 修正スクリプトの削除
rm -f ~/fix_*.sh ~/fix_*.py

# アーカイブファイルの削除
rm -f ~/frontend*.tar.gz

# ngrok関連の削除
rm -rf ~/ngrok ~/ngrok*.tgz ~/start_ngrok.sh

# 古い環境の削除
rm -rf ~/miniconda3 ~/miniconda.sh
rm -rf ~/openvoice_v2_env
rm -rf ~/nltk_data

# その他不要ファイル
rm -f ~/openvoice.pid ~/mecabrc_fix.py ~/setup_complete.txt
rm -f ~/manage.sh ~/rebuild_clean.sh ~/test_voicevox.py
```

### Phase 3: Gitリポジトリのリセット
```bash
cd ~/video-message-app
# 未追跡ファイルとディレクトリを削除（危険：必ずバックアップ後に実行）
git clean -fd
# 変更を全て破棄
git reset --hard HEAD
# 最新のmasterを取得
git pull origin master
```

### Phase 4: UV環境の再構築
```bash
# 肥大化したUV環境を削除
cd ~/video-message-app/video-message-app
rm -rf openvoice_ec2/.venv
rm -rf openvoice_ec2/__pycache__

# 新規にUV環境を構築
./setup_ec2_uv.sh
```

### Phase 5: Dockerの再構築
```bash
# 全コンテナ停止・削除
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# イメージの削除（オプション）
docker rmi $(docker images -q)

# docker-compose.ymlを使って再構築
cd ~/video-message-app/video-message-app
docker-compose up -d
```

## 代替案：新規EC2インスタンスでの再構築

現在の環境があまりにも混乱している場合、新しいEC2インスタンスを起動して、クリーンな環境で再構築することも検討すべきです。

### 新規構築の利点
- クリーンな環境から開始
- 不要なファイルや設定の持ち越しなし
- 構築手順の文書化と自動化が可能

### 新規構築手順
1. 新しいEC2インスタンス（t3.large）を起動
2. Gitリポジトリをクローン
3. UV環境でOpenVoiceをセットアップ
4. Docker-composeでサービスを起動
5. 動作確認後、古いインスタンスを停止

## 推奨事項

**現在のインスタンスのクリーンアップよりも、新規インスタンスでの再構築を強く推奨します。**

理由：
- 現在の環境は複数の試行錯誤により複雑化
- クリーンアップ中に重要な設定を誤って削除するリスク
- 新規構築の方が時間的にも効率的
- 再現可能な構築手順を確立できる

---
*作成日: 2025-08-20*
*Trinitas-Core*