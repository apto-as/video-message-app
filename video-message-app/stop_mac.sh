#!/bin/bash

# Mac環境用 VOICEVOX統合システム 停止スクリプト

echo "🛑 Mac環境用 VOICEVOX統合システム 停止中..."
echo "=================================================="

# プロジェクトディレクトリの確認
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.ymlが見つかりません。プロジェクトルートディレクトリで実行してください。"
    exit 1
fi

# 全サービスの停止
echo "🔄 すべてのサービスを停止中..."
docker-compose down

# 未使用コンテナのクリーンアップ
echo "🧹 未使用リソースをクリーンアップ中..."
docker system prune -f --volumes

# 停止確認
echo ""
echo "🔍 停止確認中..."

# ポート確認
if ! netstat -an | grep -q ":3000.*LISTEN"; then
    echo "✅ フロントエンド (3000): 停止済み"
else
    echo "⚠️ フロントエンド (3000): まだ動作中"
fi

if ! netstat -an | grep -q ":8000.*LISTEN"; then
    echo "✅ バックエンド (8000): 停止済み"
else
    echo "⚠️ バックエンド (8000): まだ動作中"
fi

if ! netstat -an | grep -q ":50021.*LISTEN"; then
    echo "✅ VOICEVOX (50021): 停止済み"
else
    echo "⚠️ VOICEVOX (50021): まだ動作中"
fi

echo ""
echo "✅ システム停止完了"
echo "=================================================="
echo ""
echo "🔄 再起動方法: ./start_mac.sh"
echo "🧹 完全リセット: docker-compose down --volumes --remove-orphans"
echo "