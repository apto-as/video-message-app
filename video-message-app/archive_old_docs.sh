#!/bin/bash
# archive_old_docs.sh
# Phase 3: 古いドキュメントのアーカイブ
# 生成日: 2025-11-22

set -e  # エラーで停止

echo "📦 Phase 3: 古いドキュメントのアーカイブ"
echo "========================================"
echo ""

# 確認プロンプト
echo "古いドキュメントを archive/ ディレクトリに移動します。"
echo ""
read -p "実行しますか？ (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "キャンセルされました。"
    exit 0
fi

echo ""
echo "アーカイブを開始します..."
echo ""

# ディレクトリ作成
echo "📂 アーカイブディレクトリを作成中..."
mkdir -p archive/{2025-07,2025-08,2025-09,2025-11/PROSODY_POC,2025-11/D_ID_OLD}
echo "  ✓ archive/2025-07/"
echo "  ✓ archive/2025-08/"
echo "  ✓ archive/2025-09/"
echo "  ✓ archive/2025-11/PROSODY_POC/"
echo "  ✓ archive/2025-11/D_ID_OLD/"
echo ""

archived_count=0

# 7月の古いドキュメント
echo "📅 2025-07 ドキュメントをアーカイブ中..."
july_files=(
    "Phase1_COMPLETION_REPORT.md"
    "README.md"
    "README_DOCKER.md"
    "README_MAC.md"
    "README_QUICK_START.md"
    "HYBRID_TEST_GUIDE.md"
    "OPENVOICE_NATIVE_SETUP.md"
    "STORAGE_PERSISTENCE_GUIDE.md"
    "CONDA_SETUP_GUIDE.md"
)

for file in "${july_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" archive/2025-07/
        echo "  ✓ $file"
        ((archived_count++))
    fi
done
echo ""

# 8月の古いドキュメント
echo "📅 2025-08 ドキュメントをアーカイブ中..."
august_files=(
    "RESUME_GUIDE.md"
    "SYNC_WORKFLOW.md"
    "EC2_DEPLOYMENT_STATUS.md"
    "GPU_INSTANCE_SETUP.md"
    "SETUP_AWS_CREDENTIALS.md"
)

for file in "${august_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" archive/2025-08/
        echo "  ✓ $file"
        ((archived_count++))
    fi
done
echo ""

# 9月の古いドキュメント
echo "📅 2025-09 ドキュメントをアーカイブ中..."
september_files=(
    "deploy_openvoice_ec2.md"
    "DEPLOYMENT_STATUS.md"
    "EC2_CLEANUP_PLAN.md"
    "EC2_REBUILD_DECISION_GUIDE.md"
    "EC2_REBUILD_MANUAL.md"
)

for file in "${september_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" archive/2025-09/
        echo "  ✓ $file"
        ((archived_count++))
    fi
done
echo ""

# 11月 - Phase 1関連
echo "📅 2025-11 Phase 1関連ドキュメントをアーカイブ中..."
phase1_files=(
    "PHASE1_DEPLOYMENT_REPORT.md"
    "PHASE1_IMPLEMENTATION_SUMMARY.md"
    "OPTION_B_VERIFICATION_REPORT.md"
)

for file in "${phase1_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" archive/2025-11/
        echo "  ✓ $file"
        ((archived_count++))
    fi
done
echo ""

# PROSODY POC完了ドキュメント
echo "🗣️  PROSODY POC完了ドキュメントをアーカイブ中..."
# これらは organize_docs.sh で docs/api/ に移動済みの場合があるので、両方確認
prosody_poc_files=(
    "PROSODY_POC_SUMMARY.md"
    "PROSODY_POC_VALIDATION_REPORT.md"
)

for file in "${prosody_poc_files[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" archive/2025-11/PROSODY_POC/
        echo "  ✓ $file"
        ((archived_count++))
    elif [ -f "docs/api/$file" ]; then
        mv "docs/api/$file" archive/2025-11/PROSODY_POC/
        echo "  ✓ docs/api/$file"
        ((archived_count++))
    fi
done
echo ""

echo "========================================"
echo "✅ Phase 3完了"
echo "アーカイブされたファイル: ${archived_count}個"
echo ""
echo "次のステップ:"
echo "  1. ドキュメント統合タスク（手動）"
echo "     - D-ID: 5ファイル → 1ファイル"
echo "     - PROSODY: 9ファイル → 2ファイル"
echo "     - 要件定義: 6ファイル → 2ファイル"
echo "  2. README.md 更新"
echo "  3. .gitignore 更新"
echo "  4. Git コミット"
echo ""
