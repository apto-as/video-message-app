#!/bin/bash
# cleanup_temp_files.sh
# Phase 1: 一時ファイル削除スクリプト
# 生成日: 2025-11-22

set -e  # エラーで停止

echo "🗑️  Phase 1: 一時ファイル削除"
echo "================================"
echo ""

# 削除前確認
echo "以下のファイルを削除します:"
echo ""
echo "【ログファイル】（56ファイル）"
echo "  - backend.log"
echo "  - frontend.log"
echo "  - startup.log"
echo "  - logs/ ディレクトリ全体（52ファイル）"
echo ""
echo "【アーカイブファイル】（4ファイル）"
echo "  - frontend-build.tar.gz"
echo "  - frontend-build-fixed.tar.gz"
echo "  - frontend-final.tar.gz"
echo "  - frontend/frontend-fix-selector.tar.gz"
echo ""
echo "【テスト音声ファイル】（2ファイル）"
echo "  - test_synthesized_voice.wav"
echo "  - openvoice_native/test_converted.wav"
echo ""
echo "合計: 62ファイル"
echo ""

# 確認プロンプト
read -p "削除を実行しますか？ (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "キャンセルされました。"
    exit 0
fi

echo ""
echo "削除を開始します..."
echo ""

# カウンター
deleted_count=0

# ログファイル削除
echo "📄 ログファイルを削除中..."
if [ -f backend.log ]; then
    rm -f backend.log
    echo "  ✓ backend.log"
    ((deleted_count++))
fi

if [ -f frontend.log ]; then
    rm -f frontend.log
    echo "  ✓ frontend.log"
    ((deleted_count++))
fi

if [ -f startup.log ]; then
    rm -f startup.log
    echo "  ✓ startup.log"
    ((deleted_count++))
fi

if [ -d logs/ ]; then
    log_count=$(find logs/ -type f -name "*.log" | wc -l | tr -d ' ')
    rm -rf logs/
    echo "  ✓ logs/ ディレクトリ（${log_count}ファイル）"
    deleted_count=$((deleted_count + log_count))
fi

echo ""

# アーカイブファイル削除
echo "📦 アーカイブファイルを削除中..."
if [ -f frontend-build.tar.gz ]; then
    rm -f frontend-build.tar.gz
    echo "  ✓ frontend-build.tar.gz"
    ((deleted_count++))
fi

if [ -f frontend-build-fixed.tar.gz ]; then
    rm -f frontend-build-fixed.tar.gz
    echo "  ✓ frontend-build-fixed.tar.gz"
    ((deleted_count++))
fi

if [ -f frontend-final.tar.gz ]; then
    rm -f frontend-final.tar.gz
    echo "  ✓ frontend-final.tar.gz"
    ((deleted_count++))
fi

if [ -f frontend/frontend-fix-selector.tar.gz ]; then
    rm -f frontend/frontend-fix-selector.tar.gz
    echo "  ✓ frontend/frontend-fix-selector.tar.gz"
    ((deleted_count++))
fi

echo ""

# テスト音声ファイル削除
echo "🎵 テスト音声ファイルを削除中..."
if [ -f test_synthesized_voice.wav ]; then
    rm -f test_synthesized_voice.wav
    echo "  ✓ test_synthesized_voice.wav"
    ((deleted_count++))
fi

if [ -f openvoice_native/test_converted.wav ]; then
    rm -f openvoice_native/test_converted.wav
    echo "  ✓ openvoice_native/test_converted.wav"
    ((deleted_count++))
fi

echo ""
echo "================================"
echo "✅ Phase 1完了"
echo "削除されたファイル: ${deleted_count}個"
echo ""
