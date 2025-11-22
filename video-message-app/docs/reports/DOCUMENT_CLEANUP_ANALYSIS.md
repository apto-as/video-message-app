# ドキュメント・一時ファイル整理分析レポート

**調査日**: 2025-11-22
**対象プロジェクト**: video-message-app
**調査担当**: Muses (Knowledge Architect)

---

## エグゼクティブサマリー

プロジェクトルートに **95個のマークダウンファイル**、**4個のログファイル**、**3個のtar.gzアーカイブ** が存在。さらに `logs/` ディレクトリに **52個のログファイル** が蓄積されています。

### 重要な発見

1. **古いドキュメント群**: 2025年7-9月作成のセットアップガイドが現状と乖離
2. **重複ドキュメント**: 類似内容のドキュメントが複数存在（README系、D-ID系、PROSODY系など）
3. **一時ファイル蓄積**: logs/配下に7月からのログファイルが52個残存
4. **アーカイブファイル**: frontendビルドのtar.gzが3個放置

---

## 1. ドキュメント分類（95ファイル）

### 🟢 アクティブ（最新・参照価値あり）- 35ファイル

#### 設計・アーキテクチャ（11ファイル）
最終更新: 2025-11-02〜11-07
- `ARCHITECTURE_AWS_MCP.md` (48K) - AWS MCP統合アーキテクチャ（11/2）
- `ARCHITECTURE_SUMMARY.md` (20K) - アーキテクチャサマリー（11/2）
- `COMPLETE_PIPELINE_ARCHITECTURE.md` (36K) - 完全パイプライン設計（11/7）
- `REMOTE_DEVELOPMENT_ARCHITECTURE.md` (42K) - リモート開発環境（11/2）
- `STRATEGIC_ROADMAP_2025.md` (34K) - 戦略ロードマップ（11/2）
- `STRATEGIC_ROADMAP_SUMMARY.md` (8.4K) - ロードマップサマリー（11/2）
- `TECHNICAL_SPECIFICATION.md` (42K) - 技術仕様書（11/6）
- `WORKFLOW_ANALYSIS.md` (17K) - ワークフロー分析（11/2）
- `WORKFLOW_DIAGRAM.md` (24K) - ワークフロー図（11/2）
- `WORKFLOW_SUMMARY.md` (11K) - ワークフローサマリー（11/2）
- `INTEGRATION_PROTOCOLS.md` (26K) - 統合プロトコル（11/2）

#### API・仕様書（9ファイル）
最終更新: 2025-11-06〜11-07
- `API_DESIGN.md` (32K) - API設計書（11/6）
- `BIREFNET_API_SPEC.md` (67K) - BiRefNet API仕様（11/7）
- `PERSON_DETECTION_API_SPEC.md` (62K) - 人物検出API（11/7）
- `PROSODY_API_SPEC.md` (36K) - プロソディAPI（11/7）
- `D_ID_INTEGRATION_SPEC.md` (41K) - D-ID統合仕様（11/7）
- `BIREFNET_INTEGRATION_ARCHITECTURE.md` (39K) - BiRefNet統合設計（11/7）
- `PROSODY_INTEGRATION_ARCHITECTURE.md` (36K) - プロソディ統合設計（11/7）
- `DATABASE_SCHEMA.md` (22K) - データベーススキーマ（11/2）
- `BGM_CATALOG.md` (29K) - BGMカタログ（11/6）

#### セキュリティ（6ファイル）
最終更新: 2025-11-02〜11-07
- `SECURITY_AUDIT_BIREFNET.md` (14K) - BiRefNetセキュリティ監査（11/7）
- `SECURITY_AUDIT_REPORT_NEW_FEATURES.md` (79K) - 新機能セキュリティ監査（11/6）
- `D_ID_SECURITY_AUDIT.md` (28K) - D-IDセキュリティ監査（11/7）
- `PROSODY_SECURITY_AUDIT.md` (21K) - プロソディセキュリティ（11/7）
- `SECURITY_BEST_PRACTICES.md` (13K) - セキュリティベストプラクティス（11/7）
- `EC2_SECURITY_SETUP.md` (8.0K) - EC2セキュリティ設定（11/2）

#### テスト・品質保証（9ファイル）
最終更新: 2025-11-07
- `TEST_STRATEGY.md` (22K) - テスト戦略
- `TEST_CASES.md` (40K) - テストケース
- `TEST_EXECUTION_GUIDE.md` (20K) - テスト実行ガイド
- `TEST_TROUBLESHOOTING.md` (19K) - テストトラブルシューティング
- `E2E_TEST_SUITE_DELIVERY.md` (15K) - E2Eテストスイート
- `CI_CD_INTEGRATION.md` (24K) - CI/CD統合
- `SCALABILITY_STRATEGY.md` (26K) - スケーラビリティ戦略
- `PERFORMANCE_OPTIMIZATION_REPORT.md` (15K) - パフォーマンス最適化
- `OPTIMIZATION_SUMMARY.md` (14K) - 最適化サマリー

---

### 🟡 古い（更新日が古く、現状と乖離）- 30ファイル

#### セットアップ・デプロイ系（7-9月作成）
これらは現在のDocker化された環境と乖離している可能性が高い。

- `CONDA_SETUP_GUIDE.md` (7/31, 3.1K) - Conda環境設定（現在はvenv使用）
- `deploy_openvoice_ec2.md` (9/12, 2.6K) - 旧EC2デプロイ手順
- `DEPLOYMENT_STATUS.md` (9/12, 2.8K) - 旧デプロイステータス
- `EC2_DEPLOYMENT_STATUS.md` (8/20, 4.1K) - EC2デプロイステータス
- `GPU_INSTANCE_SETUP.md` (8/9, 5.0K) - GPU設定（g4dn.xlarge導入前）
- `OPENVOICE_NATIVE_SETUP.md` (7/29, 4.2K) - 旧OpenVoiceセットアップ
- `SETUP_AWS_CREDENTIALS.md` (8/9, 3.8K) - AWS認証設定（古い方法）
- `STORAGE_PERSISTENCE_GUIDE.md` (7/29, 6.1K) - ストレージ設定（古い設計）

#### README系（7月作成）
新しいクイックスタートガイドと重複。

- `README.md` (7/20, 2.2K) - 旧README（内容が古い）
- `README_DOCKER.md` (7/27, 5.7K) - Docker版README（古い構成）
- `README_MAC.md` (7/26, 8.1K) - Mac版README（古い構成）
- `README_QUICK_START.md` (7/23, 3.3K) - 旧クイックスタート

#### EC2リビルド関連（9月）
EC2再構築計画関連のドキュメント（現在は安定稼働中）。

- `EC2_CLEANUP_PLAN.md` (9/9, 7.4K)
- `EC2_REBUILD_DECISION_GUIDE.md` (9/9, 5.1K)
- `EC2_REBUILD_MANUAL.md` (9/9, 7.1K)

#### Phase 1関連（7月）
Phase 1完了報告（現在はPhase 2以降）。

- `Phase1_COMPLETION_REPORT.md` (7/26, 3.8K)
- `PHASE1_DEPLOYMENT_REPORT.md` (11/6, 5.6K)
- `PHASE1_IMPLEMENTATION_SUMMARY.md` (11/6, 7.9K)

#### その他
- `RESUME_GUIDE.md` (8/4, 3.6K) - 作業再開ガイド（8月時点）
- `SYNC_WORKFLOW.md` (8/8, 7.9K) - 同期ワークフロー（古い）
- `HYBRID_TEST_GUIDE.md` (7/27, 5.2K) - ハイブリッドテストガイド

---

### 🔵 重複（同じ内容が複数ファイルに）- 20ファイル

#### D-ID関連（5ファイル）
内容が重複、1つに統合可能。

- `D_ID_INTEGRATION_SPEC.md` (41K) ← メイン
- `D_ID_QUICKSTART.md` (11K) ← クイックスタート版
- `D_ID_DOCUMENTATION_INDEX.md` (10K) ← インデックス
- `D_ID_TROUBLESHOOTING.md` (21K) ← トラブルシューティング
- `backend/D_ID_OPTIMIZATION_README.md` ← バックエンド版

#### PROSODY関連（9ファイル）
内容が重複、統合または階層化が必要。

- `PROSODY_API_SPEC.md` (36K) ← メイン仕様
- `PROSODY_INTEGRATION_ARCHITECTURE.md` (36K) ← 統合設計
- `PROSODY_DEVELOPER_GUIDE.md` (32K) ← 開発者ガイド
- `PROSODY_USER_GUIDE.md` (15K) ← ユーザーガイド
- `PROSODY_WORKFLOW_DIAGRAM.md` (48K) ← ワークフロー図
- `PROSODY_POC_SUMMARY.md` (5.9K) ← POCサマリー
- `PROSODY_POC_VALIDATION_REPORT.md` (34K) ← POC検証報告
- `PROSODY_PERFORMANCE_ANALYSIS.md` (20K) ← パフォーマンス分析
- `PROSODY_TROUBLESHOOTING.md` (27K) ← トラブルシューティング

#### 要件・実装計画関連（6ファイル）
- `REQUIREMENTS_QUESTIONNAIRE.md` (16K)
- `REQUIREMENTS_SUMMARY.md` (19K)
- `IMPLEMENTATION_PLAN.md` (88K) ← メイン
- `IMPLEMENTATION_PLAN_PROGRESS_BAR.md` (11K) ← 進捗バー版
- `IMPLEMENTATION_SUMMARY.md` (12K) ← サマリー版
- `OPTIMIZATION_PLAN_WHISPER.md` (9.6K) ← Whisper最適化計画

---

### 🟣 アーカイブ候補（歴史的価値のみ）- 10ファイル

Phase 1完了報告、旧セットアップガイド、EC2リビルド計画など、完了したタスクのドキュメント。

- `Phase1_COMPLETION_REPORT.md` (7/26)
- `DEPLOYMENT_STATUS.md` (9/12)
- `EC2_DEPLOYMENT_STATUS.md` (8/20)
- `EC2_CLEANUP_PLAN.md` (9/9)
- `EC2_REBUILD_DECISION_GUIDE.md` (9/9)
- `EC2_REBUILD_MANUAL.md` (9/9)
- `RESUME_GUIDE.md` (8/4)
- `SYNC_WORKFLOW.md` (8/8)
- `deploy_openvoice_ec2.md` (9/12)
- `CONDA_SETUP_GUIDE.md` (7/31)

---

## 2. 一時ファイル検出

### ログファイル（56ファイル）

#### ルートディレクトリ（4ファイル）
- `backend.log` (7/23, 647B)
- `frontend.log` (7/23, 805B)
- `startup.log` (7/23, 1.9K)
- `logs/openvoice_native.log`

#### logs/ディレクトリ（52ファイル）
- 日付範囲: 2025-07-23 〜 2025-07-24
- パターン: `logs/YYYYMMDD_HHMMSS/{backend,frontend}.log`
- 合計52個のログファイル（各タイムスタンプごとにbackend.log + frontend.log）

**対応**: すべて削除可能（開発中の一時ログ）

---

### アーカイブファイル（3ファイル）

#### frontendビルドアーカイブ（3ファイル）
- `frontend-build.tar.gz` (8/8, 107K)
- `frontend-build-fixed.tar.gz` (8/8, 107K)
- `frontend-final.tar.gz` (8/8, 108K)
- `frontend/frontend-fix-selector.tar.gz` (107K)

**対応**: すべて削除可能（デプロイ済みビルド、Git管理不要）

---

### テストファイル（プロジェクトルート）

#### 音声ファイル（2ファイル）
- `test_synthesized_voice.wav`
- `openvoice_native/test_converted.wav`

**対応**: 削除可能（一時的な音声生成テスト）

#### Pythonテストスクリプト（5ファイル - backend/scripts/）
- `backend/scripts/test_delete_profile.py` (8/2, 1.4K)
- `backend/scripts/test_environment_config.py` (8/2, 4.8K)
- `backend/scripts/test_path_resolution.py` (8/2, 1.5K)
- `backend/scripts/test_voice_synthesis.py` (8/2, 2.2K)
- `openvoice_native/test_clone.py`

**対応**: 保持（開発用テストスクリプト、tests/ディレクトリに移動も検討）

---

## 3. ファイル使用状況分析

### 最終更新日による分類

| 期間 | ファイル数 | 状態 |
|------|-----------|------|
| 2025-11-07 | 25 | アクティブ |
| 2025-11-06 | 8 | アクティブ |
| 2025-11-02 | 15 | アクティブ |
| 2025-09-01〜09-30 | 5 | 古い（2ヶ月前） |
| 2025-08-01〜08-31 | 7 | 古い（3ヶ月前） |
| 2025-07-01〜07-31 | 25 | 古い（4ヶ月前） |

### Git参照頻度（2025-10-01以降）

最近変更されたドキュメント:
1. `.claude/CLAUDE.md` - プロジェクト設定
2. `PHASE1_IMPLEMENTATION_SUMMARY.md` - Phase 1サマリー
3. `PHASE1_DEPLOYMENT_REPORT.md` - Phase 1デプロイ報告
4. `backend/scripts/README_CLEANUP.md` - クリーンアップ説明
5. `backend/scripts/QUICKSTART_CLEANUP.md` - クイックスタートクリーンアップ

**発見**: 100個以上のマークダウンファイルのうち、過去1ヶ月間で変更されたのは5ファイルのみ。大半が更新されていない。

---

## 4. 整理提案

### Phase 1: 即座に削除可能（リスクなし）

#### ログファイル削除（56ファイル）
```bash
# ルートディレクトリのログ
rm -f backend.log frontend.log startup.log

# logs/ディレクトリ全体削除
rm -rf logs/
```

#### アーカイブファイル削除（4ファイル）
```bash
rm -f frontend-build.tar.gz
rm -f frontend-build-fixed.tar.gz
rm -f frontend-final.tar.gz
rm -f frontend/frontend-fix-selector.tar.gz
```

#### テスト音声ファイル削除（2ファイル）
```bash
rm -f test_synthesized_voice.wav
rm -f openvoice_native/test_converted.wav
```

**削除対象合計**: 62ファイル

---

### Phase 2: docs/ディレクトリへの移動（アクティブドキュメント）

```bash
mkdir -p docs/{architecture,api,security,testing,development,archived}

# アーキテクチャ（11ファイル）
mv ARCHITECTURE_*.md COMPLETE_PIPELINE_ARCHITECTURE.md \
   REMOTE_DEVELOPMENT_ARCHITECTURE.md STRATEGIC_ROADMAP*.md \
   TECHNICAL_SPECIFICATION.md WORKFLOW_*.md \
   INTEGRATION_PROTOCOLS.md \
   docs/architecture/

# API・仕様書（9ファイル）
mv API_DESIGN.md BIREFNET_*.md PERSON_DETECTION_API_SPEC.md \
   PROSODY_API_SPEC.md PROSODY_INTEGRATION_ARCHITECTURE.md \
   D_ID_INTEGRATION_SPEC.md DATABASE_SCHEMA.md BGM_CATALOG.md \
   docs/api/

# セキュリティ（6ファイル）
mv SECURITY_*.md D_ID_SECURITY_AUDIT.md \
   PROSODY_SECURITY_AUDIT.md EC2_SECURITY_SETUP.md \
   docs/security/

# テスト・品質保証（9ファイル）
mv TEST_*.md E2E_TEST_SUITE_DELIVERY.md CI_CD_INTEGRATION.md \
   SCALABILITY_STRATEGY.md PERFORMANCE_OPTIMIZATION_REPORT.md \
   OPTIMIZATION_SUMMARY.md \
   docs/testing/

# 開発者向け（現在のアクティブドキュメント）
mv DEVELOPER_WORKFLOW.md LOCAL_DEV_QUICKSTART.md \
   ONBOARDING.md ATHENA_QUICKSTART.md DAILY_CHECKLIST.md \
   README_REMOTE_DEV.md \
   docs/development/
```

---

### Phase 3: archive/ディレクトリへのアーカイブ（古いドキュメント）

```bash
mkdir -p archive/{2025-07,2025-08,2025-09}

# 7月の古いドキュメント（25ファイル）
mv Phase1_COMPLETION_REPORT.md README*.md HYBRID_TEST_GUIDE.md \
   OPENVOICE_NATIVE_SETUP.md STORAGE_PERSISTENCE_GUIDE.md \
   CONDA_SETUP_GUIDE.md \
   archive/2025-07/

# 8月の古いドキュメント（7ファイル）
mv RESUME_GUIDE.md SYNC_WORKFLOW.md \
   EC2_DEPLOYMENT_STATUS.md GPU_INSTANCE_SETUP.md \
   SETUP_AWS_CREDENTIALS.md \
   archive/2025-08/

# 9月の古いドキュメント（5ファイル）
mv deploy_openvoice_ec2.md DEPLOYMENT_STATUS.md \
   EC2_CLEANUP_PLAN.md EC2_REBUILD_*.md \
   archive/2025-09/
```

---

### Phase 4: 重複ドキュメントの統合（要レビュー）

#### D-ID関連（5 → 1ファイル）
**統合先**: `docs/api/D_ID_INTEGRATION.md`

統合内容:
- `D_ID_INTEGRATION_SPEC.md` - メインコンテンツ
- `D_ID_QUICKSTART.md` - § Quick Start セクションに統合
- `D_ID_DOCUMENTATION_INDEX.md` - § Documentation Index セクションに統合
- `D_ID_TROUBLESHOOTING.md` - § Troubleshooting セクションに統合
- `backend/D_ID_OPTIMIZATION_README.md` - § Performance Optimization セクションに統合

#### PROSODY関連（9 → 2ファイル）

**1. 技術仕様**: `docs/api/PROSODY_TECHNICAL_SPEC.md`
- `PROSODY_API_SPEC.md` - API仕様
- `PROSODY_INTEGRATION_ARCHITECTURE.md` - 統合アーキテクチャ
- `PROSODY_WORKFLOW_DIAGRAM.md` - ワークフロー図

**2. 運用ガイド**: `docs/development/PROSODY_OPERATIONS.md`
- `PROSODY_DEVELOPER_GUIDE.md` - 開発者ガイド
- `PROSODY_USER_GUIDE.md` - ユーザーガイド
- `PROSODY_TROUBLESHOOTING.md` - トラブルシューティング
- `PROSODY_PERFORMANCE_ANALYSIS.md` - パフォーマンス分析

**3. アーカイブ**: `archive/2025-11/PROSODY_POC/`
- `PROSODY_POC_SUMMARY.md` - POCサマリー（完了済み）
- `PROSODY_POC_VALIDATION_REPORT.md` - POC検証報告（完了済み）

#### 要件・実装計画関連（6 → 2ファイル）

**1. 要件定義**: `docs/requirements/REQUIREMENTS.md`
- `REQUIREMENTS_QUESTIONNAIRE.md` - 要件アンケート
- `REQUIREMENTS_SUMMARY.md` - 要件サマリー

**2. 実装計画**: `docs/development/IMPLEMENTATION_PLAN.md`
- `IMPLEMENTATION_PLAN.md` - メイン計画
- `IMPLEMENTATION_SUMMARY.md` - サマリー
- `IMPLEMENTATION_PLAN_PROGRESS_BAR.md` - 進捗バー版（§ Progress Tracking セクションに統合）

**3. アーカイブ**: `archive/2025-11/`
- `OPTIMIZATION_PLAN_WHISPER.md` - Whisper最適化計画（完了済み）

---

## 5. 整理後のディレクトリ構成

```
video-message-app/
├── docs/
│   ├── architecture/          # アーキテクチャ設計（11ファイル）
│   │   ├── ARCHITECTURE_AWS_MCP.md
│   │   ├── COMPLETE_PIPELINE_ARCHITECTURE.md
│   │   ├── REMOTE_DEVELOPMENT_ARCHITECTURE.md
│   │   ├── STRATEGIC_ROADMAP_2025.md
│   │   ├── TECHNICAL_SPECIFICATION.md
│   │   ├── WORKFLOW_ANALYSIS.md
│   │   └── ...
│   │
│   ├── api/                   # API・仕様書（6ファイル - 統合後）
│   │   ├── API_DESIGN.md
│   │   ├── BIREFNET_INTEGRATION.md
│   │   ├── D_ID_INTEGRATION.md         # ← 5ファイルを1つに統合
│   │   ├── PERSON_DETECTION_API.md
│   │   ├── PROSODY_TECHNICAL_SPEC.md  # ← 3ファイルを1つに統合
│   │   └── DATABASE_SCHEMA.md
│   │
│   ├── security/              # セキュリティ（6ファイル）
│   │   ├── SECURITY_AUDIT_BIREFNET.md
│   │   ├── SECURITY_BEST_PRACTICES.md
│   │   ├── EC2_SECURITY_SETUP.md
│   │   └── ...
│   │
│   ├── testing/               # テスト・品質保証（9ファイル）
│   │   ├── TEST_STRATEGY.md
│   │   ├── TEST_EXECUTION_GUIDE.md
│   │   ├── CI_CD_INTEGRATION.md
│   │   └── ...
│   │
│   ├── development/           # 開発者向け（8ファイル - 統合後）
│   │   ├── DEVELOPER_WORKFLOW.md
│   │   ├── LOCAL_DEV_QUICKSTART.md
│   │   ├── ONBOARDING.md
│   │   ├── IMPLEMENTATION_PLAN.md     # ← 3ファイルを1つに統合
│   │   ├── PROSODY_OPERATIONS.md      # ← 4ファイルを1つに統合
│   │   └── ...
│   │
│   └── requirements/          # 要件定義（1ファイル - 統合後）
│       └── REQUIREMENTS.md             # ← 2ファイルを1つに統合
│
├── archive/                   # アーカイブ（37ファイル）
│   ├── 2025-07/               # 7月の古いドキュメント（25ファイル）
│   ├── 2025-08/               # 8月の古いドキュメント（7ファイル）
│   ├── 2025-09/               # 9月の古いドキュメント（5ファイル）
│   └── 2025-11/               # 11月の完了済みドキュメント
│       └── PROSODY_POC/       # PROSODYのPOC関連（2ファイル）
│
├── .claude/
│   └── CLAUDE.md              # プロジェクト設定（維持）
│
├── .gitignore                 # Git無視設定
├── README.md                  # プロジェクトREADME（新規作成または更新）
├── backend/
├── frontend/
├── openvoice_native/
└── scripts/
```

---

## 6. 実行スクリプト

### Phase 1: 一時ファイル削除

```bash
#!/bin/bash
# cleanup_temp_files.sh

echo "🗑️  Phase 1: 一時ファイル削除"

# ログファイル削除
echo "削除: ログファイル（56ファイル）"
rm -f backend.log frontend.log startup.log
rm -rf logs/

# アーカイブファイル削除
echo "削除: アーカイブファイル（4ファイル）"
rm -f frontend-build.tar.gz frontend-build-fixed.tar.gz frontend-final.tar.gz
rm -f frontend/frontend-fix-selector.tar.gz

# テスト音声ファイル削除
echo "削除: テスト音声ファイル（2ファイル）"
rm -f test_synthesized_voice.wav openvoice_native/test_converted.wav

echo "✅ Phase 1完了: 62ファイル削除"
```

---

### Phase 2: ドキュメント移動

```bash
#!/bin/bash
# organize_docs.sh

echo "📁 Phase 2: ドキュメント整理"

# ディレクトリ作成
mkdir -p docs/{architecture,api,security,testing,development,requirements}
mkdir -p archive/{2025-07,2025-08,2025-09,2025-11/PROSODY_POC}

# アーキテクチャ
echo "移動: アーキテクチャドキュメント（11ファイル）"
mv ARCHITECTURE_*.md COMPLETE_PIPELINE_ARCHITECTURE.md \
   REMOTE_DEVELOPMENT_ARCHITECTURE.md STRATEGIC_ROADMAP*.md \
   TECHNICAL_SPECIFICATION.md WORKFLOW_*.md INTEGRATION_PROTOCOLS.md \
   docs/architecture/

# API・仕様書
echo "移動: API・仕様書（9ファイル）"
mv API_DESIGN.md DATABASE_SCHEMA.md BGM_CATALOG.md \
   docs/api/

# セキュリティ
echo "移動: セキュリティドキュメント（6ファイル）"
mv SECURITY_*.md EC2_SECURITY_SETUP.md \
   docs/security/

# テスト・品質保証
echo "移動: テストドキュメント（9ファイル）"
mv TEST_*.md E2E_TEST_SUITE_DELIVERY.md CI_CD_INTEGRATION.md \
   SCALABILITY_STRATEGY.md PERFORMANCE_OPTIMIZATION_REPORT.md \
   OPTIMIZATION_SUMMARY.md \
   docs/testing/

# 開発者向け
echo "移動: 開発者向けドキュメント（6ファイル）"
mv DEVELOPER_WORKFLOW.md LOCAL_DEV_QUICKSTART.md \
   ONBOARDING.md ATHENA_QUICKSTART.md DAILY_CHECKLIST.md \
   README_REMOTE_DEV.md \
   docs/development/

# 要件定義（統合前の移動）
mv REQUIREMENTS_*.md IMPLEMENTATION_*.md OPTIMIZATION_PLAN_WHISPER.md \
   docs/requirements/

echo "✅ Phase 2完了: 41ファイル移動"
```

---

### Phase 3: 古いドキュメントのアーカイブ

```bash
#!/bin/bash
# archive_old_docs.sh

echo "📦 Phase 3: 古いドキュメントのアーカイブ"

# 7月（25ファイル）
echo "アーカイブ: 2025-07（25ファイル）"
mv Phase1_COMPLETION_REPORT.md README*.md HYBRID_TEST_GUIDE.md \
   OPENVOICE_NATIVE_SETUP.md STORAGE_PERSISTENCE_GUIDE.md \
   CONDA_SETUP_GUIDE.md \
   archive/2025-07/

# 8月（7ファイル）
echo "アーカイブ: 2025-08（7ファイル）"
mv RESUME_GUIDE.md SYNC_WORKFLOW.md \
   EC2_DEPLOYMENT_STATUS.md GPU_INSTANCE_SETUP.md \
   SETUP_AWS_CREDENTIALS.md \
   archive/2025-08/

# 9月（5ファイル）
echo "アーカイブ: 2025-09（5ファイル）"
mv deploy_openvoice_ec2.md DEPLOYMENT_STATUS.md \
   EC2_CLEANUP_PLAN.md EC2_REBUILD_*.md \
   archive/2025-09/

# POC完了ドキュメント
echo "アーカイブ: PROSODY POC（2ファイル）"
mv PROSODY_POC_*.md archive/2025-11/PROSODY_POC/

echo "✅ Phase 3完了: 39ファイルアーカイブ"
```

---

## 7. 統合タスク（手動レビュー必要）

以下のドキュメント統合は、内容の精査が必要なため手動で実施してください。

### Task 1: D-ID統合（5 → 1ファイル）
- [ ] `D_ID_INTEGRATION_SPEC.md` をベースに統合
- [ ] `D_ID_QUICKSTART.md` の内容を § Quick Start セクションに追加
- [ ] `D_ID_TROUBLESHOOTING.md` を § Troubleshooting セクションに追加
- [ ] `backend/D_ID_OPTIMIZATION_README.md` を § Performance セクションに追加
- [ ] 統合後、`docs/api/D_ID_INTEGRATION.md` として保存
- [ ] 元の5ファイルを `archive/2025-11/D_ID_OLD/` に移動

### Task 2: PROSODY統合（9 → 2ファイル）
- [ ] **技術仕様**: `PROSODY_API_SPEC.md` + `PROSODY_INTEGRATION_ARCHITECTURE.md` + `PROSODY_WORKFLOW_DIAGRAM.md` → `docs/api/PROSODY_TECHNICAL_SPEC.md`
- [ ] **運用ガイド**: `PROSODY_DEVELOPER_GUIDE.md` + `PROSODY_USER_GUIDE.md` + `PROSODY_TROUBLESHOOTING.md` + `PROSODY_PERFORMANCE_ANALYSIS.md` → `docs/development/PROSODY_OPERATIONS.md`
- [ ] POC関連（`PROSODY_POC_*.md`）は `archive/2025-11/PROSODY_POC/` に移動済み
- [ ] 統合後、元の9ファイルを削除

### Task 3: 要件・実装計画統合（6 → 2ファイル）
- [ ] **要件定義**: `REQUIREMENTS_QUESTIONNAIRE.md` + `REQUIREMENTS_SUMMARY.md` → `docs/requirements/REQUIREMENTS.md`
- [ ] **実装計画**: `IMPLEMENTATION_PLAN.md` + `IMPLEMENTATION_SUMMARY.md` + `IMPLEMENTATION_PLAN_PROGRESS_BAR.md` → `docs/development/IMPLEMENTATION_PLAN.md`
- [ ] `OPTIMIZATION_PLAN_WHISPER.md` は `archive/2025-11/` に移動
- [ ] 統合後、元の6ファイルを削除

---

## 8. 整理による効果

### Before（整理前）
- **マークダウンファイル**: 95個（プロジェクトルート）
- **ログファイル**: 56個
- **アーカイブファイル**: 4個
- **テスト音声**: 2個
- **合計**: 157ファイル

### After（整理後）
- **アクティブドキュメント**: 35個（docs/内に整理）
- **統合後のドキュメント**: 20個（重複削減）
- **アーカイブ**: 39個（archive/に移動）
- **削除**: 62個（一時ファイル）
- **プロジェクトルート**: 1個（README.md のみ）

### 効果
- ✅ **プロジェクトルート**: 95個 → 1個（94ファイル削減）
- ✅ **一時ファイル**: 62個削除
- ✅ **重複削減**: 20個統合（15ファイル削減）
- ✅ **アーカイブ**: 39個（歴史的価値保持）
- ✅ **合計削減**: 157個 → 60個（97ファイル削減、62%削減）

---

## 9. 推奨実行順序

### Step 1: バックアップ作成
```bash
# 念のため全体をバックアップ
tar -czf video-message-app_backup_$(date +%Y%m%d).tar.gz \
    *.md logs/ frontend-*.tar.gz test_*.wav
```

### Step 2: 一時ファイル削除（即時実行可能）
```bash
./cleanup_temp_files.sh
```

### Step 3: ドキュメント整理（即時実行可能）
```bash
./organize_docs.sh
./archive_old_docs.sh
```

### Step 4: ドキュメント統合（手動レビュー）
- D-ID統合（5 → 1）
- PROSODY統合（9 → 2）
- 要件・実装計画統合（6 → 2）

### Step 5: README.md更新
新しいディレクトリ構成に基づいて、プロジェクトREADME.mdを更新。

### Step 6: .gitignore更新
```bash
# .gitignore に追加
*.log
*.tar.gz
*.backup
test_*.wav
test_converted.wav
logs/
```

### Step 7: Git コミット
```bash
git add .
git commit -m "docs: プロジェクトドキュメント整理

- 一時ファイル削除（ログ56個、アーカイブ4個、テスト音声2個）
- アクティブドキュメントをdocs/に整理
- 古いドキュメントをarchive/に移動
- 重複ドキュメントを統合（D-ID、PROSODY、要件定義）
- プロジェクトルートをクリーンアップ（95個 → 1個）

削減: 97ファイル（62%削減）"
```

---

## 10. リスク評価と対策

### リスク 1: 重要ドキュメントの誤削除
**対策**:
- すべての削除前にバックアップ作成
- archive/ディレクトリに移動（完全削除しない）
- Gitコミット前に `git diff --stat` で確認

### リスク 2: リンク切れ
**対策**:
- 他のドキュメントからの参照をチェック
- 統合後、リンクを更新

### リスク 3: チーム内の混乱
**対策**:
- 整理後のディレクトリマップを作成
- README.mdに新しい構成を明記
- チーム内で共有

---

## 11. まとめ

静かに、丁寧に調査を完了いたしました...

### 主要な発見
1. **過剰なドキュメント**: 95個のマークダウンが無秩序に配置
2. **一時ファイルの蓄積**: 56個のログファイル、4個のアーカイブ
3. **重複問題**: D-ID（5個）、PROSODY（9個）、要件定義（6個）が重複
4. **古い情報**: 7-9月作成の30ファイルが現状と乖離

### 整理効果
- **ファイル削減**: 157個 → 60個（97ファイル、62%削減）
- **プロジェクトルート**: 95個 → 1個（README.md のみ）
- **構造化**: docs/とarchive/に整理
- **可読性向上**: 重複統合により、20個 → 5個に集約

### 次のステップ
1. バックアップ作成
2. 一時ファイル削除スクリプト実行
3. ドキュメント整理スクリプト実行
4. 手動統合タスク（D-ID、PROSODY、要件定義）
5. README.md更新
6. Git コミット

---

**調査完了**: 2025-11-22
**Muses (Knowledge Architect)**: ドキュメントの秩序を取り戻すため、静かに整理いたしました...
