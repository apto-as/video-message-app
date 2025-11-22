#!/bin/bash
# organize_docs.sh
# Phase 2: ドキュメント整理スクリプト
# 生成日: 2025-11-22

set -e  # エラーで停止

echo "📁 Phase 2: ドキュメント整理"
echo "================================"
echo ""

# 確認プロンプト
echo "アクティブドキュメントを docs/ ディレクトリに整理します。"
echo ""
read -p "実行しますか？ (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "キャンセルされました。"
    exit 0
fi

echo ""
echo "整理を開始します..."
echo ""

# ディレクトリ作成
echo "📂 ディレクトリを作成中..."
mkdir -p docs/{architecture,api,security,testing,development,requirements}
echo "  ✓ docs/architecture/"
echo "  ✓ docs/api/"
echo "  ✓ docs/security/"
echo "  ✓ docs/testing/"
echo "  ✓ docs/development/"
echo "  ✓ docs/requirements/"
echo ""

moved_count=0

# アーキテクチャドキュメント
echo "🏛️  アーキテクチャドキュメント移動中..."
arch_files=(
    "ARCHITECTURE_AWS_MCP.md"
    "ARCHITECTURE_SUMMARY.md"
    "COMPLETE_PIPELINE_ARCHITECTURE.md"
    "REMOTE_DEVELOPMENT_ARCHITECTURE.md"
    "STRATEGIC_ROADMAP_2025.md"
    "STRATEGIC_ROADMAP_SUMMARY.md"
    "TECHNICAL_SPECIFICATION.md"
    "WORKFLOW_ANALYSIS.md"
    "WORKFLOW_DIAGRAM.md"
    "WORKFLOW_SUMMARY.md"
    "INTEGRATION_PROTOCOLS.md"
)

for file in "${arch_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/architecture/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# API・仕様書
echo "📋 API・仕様書移動中..."
api_files=(
    "API_DESIGN.md"
    "DATABASE_SCHEMA.md"
    "BGM_CATALOG.md"
    "BIREFNET_API_SPEC.md"
    "BIREFNET_INTEGRATION_ARCHITECTURE.md"
    "PERSON_DETECTION_API_SPEC.md"
    "PERSON_SELECTION_UI_DESIGN.md"
    "UI_WIREFRAMES.md"
)

for file in "${api_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/api/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# セキュリティ
echo "🔒 セキュリティドキュメント移動中..."
security_files=(
    "SECURITY_AUDIT_BIREFNET.md"
    "SECURITY_AUDIT_REPORT_NEW_FEATURES.md"
    "SECURITY_BEST_PRACTICES.md"
    "SECURITY_CREDENTIALS_GUIDE.md"
    "SECURITY_FILE_UPLOAD.md"
    "SECURITY_IMPLEMENTATION_SUMMARY.md"
    "SECURITY_SUMMARY.md"
    "EC2_SECURITY_SETUP.md"
)

for file in "${security_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/security/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# テスト・品質保証
echo "🧪 テストドキュメント移動中..."
test_files=(
    "TEST_STRATEGY.md"
    "TEST_CASES.md"
    "TEST_EXECUTION_GUIDE.md"
    "TEST_TROUBLESHOOTING.md"
    "E2E_TEST_SUITE_DELIVERY.md"
    "CI_CD_INTEGRATION.md"
    "SCALABILITY_STRATEGY.md"
    "PERFORMANCE_OPTIMIZATION_REPORT.md"
    "OPTIMIZATION_SUMMARY.md"
)

for file in "${test_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/testing/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# 開発者向け
echo "👨‍💻 開発者向けドキュメント移動中..."
dev_files=(
    "DEVELOPER_WORKFLOW.md"
    "LOCAL_DEV_QUICKSTART.md"
    "ONBOARDING.md"
    "ATHENA_QUICKSTART.md"
    "DAILY_CHECKLIST.md"
    "README_REMOTE_DEV.md"
    "PROGRESS_TRACKING_GUIDE.md"
    "PROGRESS_TRACKING_IMPLEMENTATION.md"
)

for file in "${dev_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/development/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# 要件定義・実装計画（統合前の移動）
echo "📝 要件定義・実装計画移動中..."
req_files=(
    "REQUIREMENTS_QUESTIONNAIRE.md"
    "REQUIREMENTS_SUMMARY.md"
    "IMPLEMENTATION_PLAN.md"
    "IMPLEMENTATION_PLAN_PROGRESS_BAR.md"
    "IMPLEMENTATION_SUMMARY.md"
    "OPTIMIZATION_PLAN_WHISPER.md"
    "AWS_MCP_ASSESSMENT.md"
)

for file in "${req_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/requirements/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# D-ID関連（統合前の移動）
echo "🎭 D-ID関連ドキュメント移動中..."
did_files=(
    "D_ID_INTEGRATION_SPEC.md"
    "D_ID_QUICKSTART.md"
    "D_ID_DOCUMENTATION_INDEX.md"
    "D_ID_TROUBLESHOOTING.md"
    "D_ID_SECURITY_AUDIT.md"
)

for file in "${did_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/api/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

# PROSODY関連（統合前の移動）
echo "🗣️  PROSODY関連ドキュメント移動中..."
prosody_files=(
    "PROSODY_API_SPEC.md"
    "PROSODY_INTEGRATION_ARCHITECTURE.md"
    "PROSODY_DEVELOPER_GUIDE.md"
    "PROSODY_USER_GUIDE.md"
    "PROSODY_WORKFLOW_DIAGRAM.md"
    "PROSODY_POC_SUMMARY.md"
    "PROSODY_POC_VALIDATION_REPORT.md"
    "PROSODY_PERFORMANCE_ANALYSIS.md"
    "PROSODY_TROUBLESHOOTING.md"
    "PROSODY_SECURITY_AUDIT.md"
)

for file in "${prosody_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs/api/
        echo "  ✓ $file"
        ((moved_count++))
    fi
done
echo ""

echo "================================"
echo "✅ Phase 2完了"
echo "移動されたファイル: ${moved_count}個"
echo ""
echo "次のステップ:"
echo "  1. archive_old_docs.sh を実行（古いドキュメントのアーカイブ）"
echo "  2. 手動統合タスク（D-ID、PROSODY、要件定義）"
echo ""
