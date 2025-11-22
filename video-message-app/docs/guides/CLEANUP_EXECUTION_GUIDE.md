# ドキュメント整理 実行ガイド

**作成日**: 2025-11-22
**対象プロジェクト**: video-message-app

---

## クイックスタート

### 1. バックアップ作成（推奨）

```bash
# 全体バックアップ
tar -czf video-message-app_backup_$(date +%Y%m%d).tar.gz \
    *.md logs/ frontend-*.tar.gz test_*.wav

# バックアップの確認
ls -lh video-message-app_backup_*.tar.gz
```

### 2. 一時ファイル削除（Phase 1）

```bash
./cleanup_temp_files.sh
```

**削除対象**:
- ログファイル: 56個
- アーカイブファイル: 4個
- テスト音声: 2個
- **合計**: 62ファイル

### 3. ドキュメント整理（Phase 2）

```bash
./organize_docs.sh
```

**移動先**:
- `docs/architecture/` - アーキテクチャ設計（11ファイル）
- `docs/api/` - API・仕様書（28ファイル）
- `docs/security/` - セキュリティ（8ファイル）
- `docs/testing/` - テスト・品質保証（9ファイル）
- `docs/development/` - 開発者向け（8ファイル）
- `docs/requirements/` - 要件定義・実装計画（7ファイル）

### 4. 古いドキュメントのアーカイブ（Phase 3）

```bash
./archive_old_docs.sh
```

**アーカイブ先**:
- `archive/2025-07/` - 7月の古いドキュメント
- `archive/2025-08/` - 8月の古いドキュメント
- `archive/2025-09/` - 9月の古いドキュメント
- `archive/2025-11/` - 11月の完了済みドキュメント

---

## 手動タスク（Phase 4）

以下のドキュメント統合は手動で実施してください。

### Task 1: D-ID統合（5 → 1ファイル）

**場所**: `docs/api/`

```bash
cd docs/api/

# 統合先ファイル作成
# 以下のファイルを1つに統合:
# - D_ID_INTEGRATION_SPEC.md (メイン)
# - D_ID_QUICKSTART.md (§ Quick Start セクションに統合)
# - D_ID_DOCUMENTATION_INDEX.md (§ Index セクションに統合)
# - D_ID_TROUBLESHOOTING.md (§ Troubleshooting セクションに統合)
# - backend/D_ID_OPTIMIZATION_README.md (§ Performance セクションに統合)

# 統合後、元のファイルを削除
# mkdir -p ../../archive/2025-11/D_ID_OLD/
# mv D_ID_QUICKSTART.md D_ID_DOCUMENTATION_INDEX.md D_ID_TROUBLESHOOTING.md ../../archive/2025-11/D_ID_OLD/
```

### Task 2: PROSODY統合（9 → 2ファイル）

**場所**: `docs/api/`

```bash
cd docs/api/

# 統合1: 技術仕様
# PROSODY_API_SPEC.md + PROSODY_INTEGRATION_ARCHITECTURE.md + PROSODY_WORKFLOW_DIAGRAM.md
# → PROSODY_TECHNICAL_SPEC.md

# 統合2: 運用ガイド
# PROSODY_DEVELOPER_GUIDE.md + PROSODY_USER_GUIDE.md + PROSODY_TROUBLESHOOTING.md + PROSODY_PERFORMANCE_ANALYSIS.md
# → ../development/PROSODY_OPERATIONS.md

# POC関連はアーカイブ済み
# - PROSODY_POC_SUMMARY.md
# - PROSODY_POC_VALIDATION_REPORT.md
```

### Task 3: 要件・実装計画統合（6 → 2ファイル）

**場所**: `docs/requirements/`

```bash
cd docs/requirements/

# 統合1: 要件定義
# REQUIREMENTS_QUESTIONNAIRE.md + REQUIREMENTS_SUMMARY.md
# → REQUIREMENTS.md

# 統合2: 実装計画
# IMPLEMENTATION_PLAN.md + IMPLEMENTATION_SUMMARY.md + IMPLEMENTATION_PLAN_PROGRESS_BAR.md
# → ../development/IMPLEMENTATION_PLAN.md

# Whisper最適化計画はアーカイブ
# mv OPTIMIZATION_PLAN_WHISPER.md ../../archive/2025-11/
```

---

## Phase 5: .gitignore更新

```bash
# 新しい.gitignoreに置き換え
mv .gitignore .gitignore.backup
mv .gitignore.new .gitignore

# または手動で追記:
# - logs/
# - backend.log, frontend.log, startup.log
# - *.tar.gz
# - test_*.wav
```

---

## Phase 6: README.md更新

プロジェクトルートに新しいREADME.mdを作成:

```markdown
# Video Message App

AI駆動のビデオメッセージ生成アプリケーション。

## クイックスタート

詳細は以下のドキュメントを参照してください:
- [ローカル開発環境](docs/development/LOCAL_DEV_QUICKSTART.md)
- [オンボーディング](docs/development/ONBOARDING.md)
- [開発者ワークフロー](docs/development/DEVELOPER_WORKFLOW.md)

## ドキュメント構成

- `docs/architecture/` - システムアーキテクチャ設計
- `docs/api/` - API仕様書
- `docs/security/` - セキュリティドキュメント
- `docs/testing/` - テスト戦略・実行ガイド
- `docs/development/` - 開発者向けガイド
- `docs/requirements/` - 要件定義・実装計画

詳細は [ドキュメント整理分析レポート](DOCUMENT_CLEANUP_ANALYSIS.md) を参照。
```

---

## Phase 7: Gitコミット

```bash
# 変更確認
git status
git diff --stat

# ステージング
git add .
git add -u  # 削除されたファイル

# コミット
git commit -m "docs: プロジェクトドキュメント整理

- 一時ファイル削除（ログ56個、アーカイブ4個、テスト音声2個）
- アクティブドキュメントをdocs/に整理
- 古いドキュメントをarchive/に移動
- .gitignore更新（ログ、アーカイブ、テスト音声を除外）

削減: 97ファイル（62%削減）
プロジェクトルート: 95個 → 1個（README.md）"
```

---

## 整理前後の比較

### Before（整理前）
```
video-message-app/
├── *.md (95ファイル) ← プロジェクトルートに無秩序
├── logs/ (52ログファイル)
├── frontend-*.tar.gz (4アーカイブ)
└── test_*.wav (2音声ファイル)
```

### After（整理後）
```
video-message-app/
├── README.md ← 唯一のルートドキュメント
├── .claude/CLAUDE.md
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── security/
│   ├── testing/
│   ├── development/
│   └── requirements/
└── archive/
    ├── 2025-07/
    ├── 2025-08/
    ├── 2025-09/
    └── 2025-11/
```

---

## トラブルシューティング

### Q1: スクリプトが実行できない
```bash
# 実行権限を付与
chmod +x cleanup_temp_files.sh organize_docs.sh archive_old_docs.sh
```

### Q2: バックアップから復元したい
```bash
# アーカイブを展開
tar -xzf video-message-app_backup_YYYYMMDD.tar.gz
```

### Q3: 一部のファイルが見つからない
すでに削除済み、または移動済みの可能性があります。Git履歴を確認:
```bash
git log --all --full-history -- <filename>
```

---

## チェックリスト

- [ ] Phase 1: バックアップ作成
- [ ] Phase 2: 一時ファイル削除（cleanup_temp_files.sh）
- [ ] Phase 3: ドキュメント整理（organize_docs.sh）
- [ ] Phase 4: 古いドキュメントのアーカイブ（archive_old_docs.sh）
- [ ] Phase 5: ドキュメント統合（手動）
  - [ ] D-ID統合（5 → 1）
  - [ ] PROSODY統合（9 → 2）
  - [ ] 要件・実装計画統合（6 → 2）
- [ ] Phase 6: .gitignore更新
- [ ] Phase 7: README.md更新
- [ ] Phase 8: Gitコミット

---

**所要時間**: 30-60分
**難易度**: 中（手動統合タスクあり）

詳細な分析は [DOCUMENT_CLEANUP_ANALYSIS.md](DOCUMENT_CLEANUP_ANALYSIS.md) を参照してください。
