#!/bin/bash

# Mac環境用 VOICEVOX統合システム 起動スクリプト
# Phase 1: VOICEVOX + OpenVoice V2 統合システム

set -e

echo "🍎 Mac環境用 VOICEVOX統合システム 起動中..."
echo "=================================================="

# プロジェクトディレクトリの確認
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.ymlが見つかりません。プロジェクトルートディレクトリで実行してください。"
    exit 1
fi

# Dockerの動作確認
if ! docker info > /dev/null 2>&1; then
    echo "❌ Dockerが動作していません。Docker Desktopを起動してください。"
    exit 1
fi

# 既存コンテナの停止とクリーンアップ
echo "🧹 既存コンテナをクリーンアップ中..."
docker-compose down --remove-orphans

# VOICEVOXサービスの起動
echo "🎤 VOICEVOXサービスを起動中..."
docker-compose up -d voicevox

# VOICEVOXの起動待機
echo "⏳ VOICEVOXの起動を待機中..."
for i in {1..30}; do
    if curl -s http://localhost:50021/version > /dev/null 2>&1; then
        echo "✅ VOICEVOX起動完了"
        break
    fi
    echo "   起動中... ($i/30)"
    sleep 2
done

# VOICEVOXの起動確認
if ! curl -s http://localhost:50021/version > /dev/null 2>&1; then
    echo "❌ VOICEVOXの起動に失敗しました。ログを確認してください:"
    docker-compose logs voicevox
    exit 1
fi

# バックエンドサービスの起動
echo "🐍 バックエンドサービスを起動中..."
docker-compose up -d backend

# バックエンドの起動待機
echo "⏳ バックエンドの起動を待機中..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ バックエンド起動完了"
        break
    fi
    echo "   起動中... ($i/30)"
    sleep 2
done

# バックエンドの起動確認
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ バックエンドの起動に失敗しました。ログを確認してください:"
    docker-compose logs backend
    exit 1
fi

# フロントエンドサービスの起動
echo "⚛️ フロントエンドサービスを起動中..."
docker-compose up -d frontend

# フロントエンドの起動待機
echo "⏳ フロントエンドの起動を待機中..."
for i in {1..60}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ フロントエンド起動完了"
        break
    fi
    echo "   起動中... ($i/60)"
    sleep 2
done

# サービス状態の確認
echo ""
echo "🔍 サービス状態を確認中..."

# VOICEVOX
if curl -s http://localhost:50021/version > /dev/null 2>&1; then
    VOICEVOX_VERSION=$(curl -s http://localhost:50021/version | tr -d '"')
    echo "✅ VOICEVOX: 起動中 (バージョン: $VOICEVOX_VERSION)"
else
    echo "❌ VOICEVOX: 停止中"
fi

# バックエンド
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ バックエンド: 起動中"
    
    # 統合音声サービスのテスト
    if curl -s http://localhost:8000/api/unified-voice/health > /dev/null 2>&1; then
        echo "✅ 統合音声サービス: 利用可能"
    else
        echo "⚠️ 統合音声サービス: 一部制限あり"
    fi
else
    echo "❌ バックエンド: 停止中"
fi

# フロントエンド
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ フロントエンド: 起動中"
else
    echo "❌ フロントエンド: 停止中"
fi

echo ""
echo "🎉 システム起動完了！"
echo "=================================================="
echo ""
echo "🌐 アクセスURL:"
echo "📱 メインアプリ: http://localhost:3000"
echo "🔧 API管理画面: http://localhost:8000/docs"
echo "🎤 VOICEVOX API: http://localhost:50021/docs"
echo ""
echo "🎛️ 利用可能な機能:"
echo "✅ VOICEVOX日本語音声合成"
echo "✅ カスタム音声アップロード"
echo "✅ 統合音声管理システム"
echo "⚠️ OpenVoice音声クローン (Mac環境では制限付き)"
echo "✅ D-ID動画生成 (APIキー設定時)"
echo ""
echo "📋 操作方法:"
echo "1. ブラウザで http://localhost:3000 を開く"
echo "2. 音声管理タブでVOICEVOX音声を試す"
echo "3. 動画生成タブで話すアバター動画を作成"
echo ""
echo "🛑 停止方法: ./stop_mac.sh または Ctrl+C"
echo "📊 ログ確認: docker-compose logs [service-name]"
echo ""

# ブラウザの自動起動（オプション）
if command -v open > /dev/null 2>&1; then
    read -p "ブラウザでアプリを開きますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🌐 ブラウザでアプリを開いています..."
        open http://localhost:3000
    fi
fi

# フォアグラウンドでログを表示
echo "📊 リアルタイムログ表示中... (Ctrl+C で停止)"
echo ""
docker-compose logs -f