#!/bin/bash
# Docker Compose Video Message App Startup Script
# OpenVoice V2 + VOICEVOX + D-ID ハイブリッドシステム対応

set -euo pipefail

# === 設定 ===
BACKEND_PORT=55433
FRONTEND_PORT=55434
VOICEVOX_PORT=50021
MAX_WAIT_TIME=120
HEALTH_CHECK_INTERVAL=5

# === 色付きメッセージ ===
print_color() {
    local color=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case $color in
        red)    echo -e "[$timestamp] \033[31m$message\033[0m" ;;
        green)  echo -e "[$timestamp] \033[32m$message\033[0m" ;;
        yellow) echo -e "[$timestamp] \033[33m$message\033[0m" ;;
        blue)   echo -e "[$timestamp] \033[34m$message\033[0m" ;;
        purple) echo -e "[$timestamp] \033[35m$message\033[0m" ;;
        *)      echo "[$timestamp] $message" ;;
    esac
}

# === エラーハンドリング ===
cleanup() {
    print_color yellow "🧹 緊急停止が検出されました。Dockerコンテナを停止中..."
    docker-compose down --remove-orphans >/dev/null 2>&1 || true
    print_color green "✅ クリーンアップ完了"
}

trap cleanup EXIT ERR INT TERM

# === Docker/Docker Composeチェック ===
print_color blue "🔍 システム要件チェック中..."

if ! command -v docker &> /dev/null; then
    print_color red "❌ Dockerが見つかりません。Dockerをインストールしてください。"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_color red "❌ Docker Composeが見つかりません。Docker Composeをインストールしてください。"
    exit 1
fi

# === Docker Engineの状態確認 ===
if ! docker info >/dev/null 2>&1; then
    print_color red "❌ Docker Engineが起動していません。Docker Desktopを起動してください。"
    exit 1
fi

print_color green "✅ Docker環境の確認完了"

# === 環境ファイルチェック ===
if [[ ! -f ".env" ]]; then
    print_color yellow "⚠️  .envファイルが見つかりません。.env.exampleから作成してください。"
    if [[ -f ".env.example" ]]; then
        print_color blue "📄 .env.exampleから.envを作成します..."
        cp .env.example .env
        print_color green "✅ .envファイルを作成しました。必要に応じて編集してください。"
    else
        print_color yellow "⚠️  環境変数が未設定の可能性があります。"
    fi
fi

# === 既存コンテナの停止 ===
print_color blue "🛑 既存のコンテナを停止中..."
docker-compose down --remove-orphans >/dev/null 2>&1 || true

# === 既存イメージとビルドキャッシュの確認 ===
print_color blue "🔍 既存のDockerイメージを確認中..."

# イメージ存在チェック
BACKEND_IMAGE_EXISTS=$(docker images -q voice_backend:latest)
FRONTEND_IMAGE_EXISTS=$(docker images -q voice_frontend:latest)
VOICEVOX_IMAGE_EXISTS=$(docker images -q voicevox/voicevox_engine:cpu-ubuntu20.04-latest)

# ソースファイル変更チェック（簡易版）
BACKEND_CHANGED=false
FRONTEND_CHANGED=false

if [[ -n "$BACKEND_IMAGE_EXISTS" ]]; then
    # バックエンドイメージの作成日時とソースファイルの更新日時を比較
    IMAGE_DATE=$(docker inspect --format='{{.Created}}' voice_backend:latest 2>/dev/null | head -c 19)
    if [[ -n "$IMAGE_DATE" ]]; then
        # 主要ファイルが最近変更されているかチェック
        if find ./backend -name "*.py" -newer <(date -d "$IMAGE_DATE" 2>/dev/null || date -r $(date -d "$IMAGE_DATE" +%s 2>/dev/null || echo 0)) 2>/dev/null | grep -q .; then
            BACKEND_CHANGED=true
        fi
        if [[ ./backend/requirements.txt -nt <(date -d "$IMAGE_DATE" 2>/dev/null || date -r $(date -d "$IMAGE_DATE" +%s 2>/dev/null || echo 0)) ]] 2>/dev/null; then
            BACKEND_CHANGED=true
        fi
    else
        BACKEND_CHANGED=true
    fi
else
    BACKEND_CHANGED=true
fi

if [[ -n "$FRONTEND_IMAGE_EXISTS" ]]; then
    # フロントエンドイメージの作成日時とソースファイルの更新日時を比較
    IMAGE_DATE=$(docker inspect --format='{{.Created}}' voice_frontend:latest 2>/dev/null | head -c 19)
    if [[ -n "$IMAGE_DATE" ]]; then
        if find ./frontend -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.json" | xargs ls -t 2>/dev/null | head -1 | xargs stat -c %Y 2>/dev/null | awk -v img_date="$(date -d "$IMAGE_DATE" +%s 2>/dev/null || echo 0)" '$1 > img_date' | grep -q .; then
            FRONTEND_CHANGED=true
        fi
    else
        FRONTEND_CHANGED=true
    fi
else
    FRONTEND_CHANGED=true
fi

# === 効率的なビルドと起動 ===
print_color blue "🏗️  Dockerイメージの最適化ビルド中..."

# VOICEVOX イメージは公式イメージなのでプル確認のみ
if [[ -z "$VOICEVOX_IMAGE_EXISTS" ]]; then
    print_color blue "📥 VOICEVOX公式イメージをプル中..."
    docker pull voicevox/voicevox_engine:cpu-ubuntu20.04-latest
fi

# バックエンドの条件付きビルド
if [[ "$BACKEND_CHANGED" == "true" ]]; then
    print_color yellow "🔨 バックエンドに変更が検出されました。リビルド中..."
    if ! docker-compose build backend; then
        print_color red "❌ バックエンドイメージのビルドに失敗しました"
        exit 1
    fi
else
    print_color green "✅ バックエンドイメージは最新です。ビルドをスキップします。"
fi

# フロントエンドの条件付きビルド
if [[ "$FRONTEND_CHANGED" == "true" ]]; then
    print_color yellow "🔨 フロントエンドに変更が検出されました。リビルド中..."
    if ! docker-compose build frontend; then
        print_color red "❌ フロントエンドイメージのビルドに失敗しました"
        exit 1
    fi
else
    print_color green "✅ フロントエンドイメージは最新です。ビルドをスキップします。"
fi

# 全体ビルドが必要な場合（最初の起動時など）
if [[ "$BACKEND_CHANGED" == "false" ]] && [[ "$FRONTEND_CHANGED" == "false" ]] && [[ -n "$BACKEND_IMAGE_EXISTS" ]] && [[ -n "$FRONTEND_IMAGE_EXISTS" ]]; then
    print_color green "⚡ 既存イメージを使用します。ビルド時間を大幅短縮！"
fi

print_color blue "🚀 コンテナを起動中..."
if ! docker-compose up -d; then
    print_color red "❌ コンテナの起動に失敗しました"
    print_color blue "📋 エラーログを確認してください: docker-compose logs"
    exit 1
fi

# === コンテナ状態確認 ===
print_color blue "📊 コンテナ状態を確認中..."
docker-compose ps

# === サービス別ヘルスチェック ===
print_color blue "🏥 VOICEVOXエンジンのヘルスチェック中..."
for i in $(seq 1 $MAX_WAIT_TIME); do
    if curl -s "http://localhost:$VOICEVOX_PORT/" >/dev/null 2>&1; then
        print_color green "✅ VOICEVOXエンジンが正常に起動しました"
        break
    fi
    
    if [[ $i -eq $MAX_WAIT_TIME ]]; then
        print_color red "❌ VOICEVOXエンジンのヘルスチェックがタイムアウトしました"
        print_color blue "📋 ログを確認: docker-compose logs voicevox"
        exit 1
    fi
    
    print_color yellow "⏳ VOICEVOXエンジン待機中... ($i/$MAX_WAIT_TIME)"
    sleep 2
done

print_color blue "🏥 バックエンドAPIのヘルスチェック中..."
for i in $(seq 1 $MAX_WAIT_TIME); do
    if curl -s "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
        print_color green "✅ バックエンドAPIが正常に起動しました"
        break
    fi
    
    if [[ $i -eq $MAX_WAIT_TIME ]]; then
        print_color red "❌ バックエンドAPIのヘルスチェックがタイムアウトしました"
        print_color blue "📋 ログを確認: docker-compose logs backend"
        exit 1
    fi
    
    print_color yellow "⏳ バックエンドAPI待機中... ($i/$MAX_WAIT_TIME)"
    sleep 2
done

print_color blue "🏥 フロントエンドWebUIのヘルスチェック中..."
for i in $(seq 1 $MAX_WAIT_TIME); do
    if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
        print_color green "✅ フロントエンドWebUIが正常に起動しました"
        break
    fi
    
    if [[ $i -eq $MAX_WAIT_TIME ]]; then
        print_color red "❌ フロントエンドWebUIのヘルスチェックがタイムアウトしました"
        print_color blue "📋 ログを確認: docker-compose logs frontend"
        exit 1
    fi
    
    print_color yellow "⏳ フロントエンドWebUI待機中... ($i/$MAX_WAIT_TIME)"
    sleep 2
done

# === 統合テスト ===
print_color blue "🧪 統合システムテスト中..."

# VOICEVOX API テスト
if curl -s "http://localhost:$VOICEVOX_PORT/speakers" | grep -q "name"; then
    print_color green "✅ VOICEVOX音声合成エンジンが正常です"
else
    print_color yellow "⚠️  VOICEVOX APIの一部機能が制限されている可能性があります"
fi

# 統合音声API テスト
if curl -s "http://localhost:$BACKEND_PORT/api/unified-voice/health" >/dev/null 2>&1; then
    print_color green "✅ 統合音声APIが正常です"
else
    print_color yellow "⚠️  統合音声APIの準備中です"
fi

# === 起動完了通知 ===
print_color green "🎉 ビデオメッセージアプリが正常に起動しました！"
echo ""
print_color blue "┌─────────────────────────────────────────────┐"
print_color blue "│               🌟 アクセス情報 🌟               │"
print_color blue "├─────────────────────────────────────────────┤"
print_color blue "│  📱 フロントエンド WebUI:                      │"
print_color blue "│      http://localhost:$FRONTEND_PORT                   │"
print_color blue "│                                             │"
print_color blue "│  🔧 バックエンド API:                         │"
print_color blue "│      http://localhost:$BACKEND_PORT                   │"
print_color blue "│                                             │"
print_color blue "│  🎙️ VOICEVOX エンジン:                        │"
print_color blue "│      http://localhost:$VOICEVOX_PORT                    │"
print_color blue "└─────────────────────────────────────────────┘"
echo ""
print_color purple "🚀 利用可能な機能:"
print_color purple "   • VOICEVOX日本語音声合成 (ズンダモンなど)"
print_color purple "   • OpenVoice V2音声クローン (自分の声)"
print_color purple "   • D-ID動画生成 (リップシンク)"
print_color purple "   • ハイブリッド動画生成システム"
echo ""
print_color blue "📋 便利なコマンド:"
print_color blue "   • ログ確認: docker-compose logs [service]"
print_color blue "   • 停止: ./docker-stop.sh または docker-compose down"
print_color blue "   • 再起動: docker-compose restart [service]"
echo ""

# === 継続監視モード（オプション） ===
read -p "プロセス監視モードを開始しますか？ (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_color blue "👁️  プロセス監視を開始します（Ctrl+Cで終了）"
    
    while true; do
        # コンテナ状態チェック（より信頼性の高い方法）
        RUNNING_COUNT=$(docker ps --filter "name=voice_" --filter "name=voicevox_" --filter "status=running" -q | wc -l)
        
        if [[ $RUNNING_COUNT -lt 3 ]]; then
            print_color red "❌ 一部のコンテナが停止しました（実行中: $RUNNING_COUNT/3）"
            print_color blue "📊 現在のコンテナ状態:"
            docker ps -a --filter "name=voice_" --filter "name=voicevox_" --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
            
            # 停止したコンテナのログを表示
            print_color yellow "📋 停止したコンテナのログ:"
            for container in $(docker ps -a --filter "name=voice_" --filter "name=voicevox_" --filter "status=exited" -q); do
                CONTAINER_NAME=$(docker inspect --format='{{.Name}}' $container | sed 's/^\///')
                print_color yellow "--- $CONTAINER_NAME のログ ---"
                docker logs --tail 20 $container
            done
            break
        fi
        
        # ヘルスチェック
        HEALTH_STATUS="✅"
        
        if ! curl -s "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
            print_color yellow "⚠️  バックエンドのヘルスチェックに失敗"
            HEALTH_STATUS="⚠️"
        fi
        
        if ! curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
            print_color yellow "⚠️  フロントエンドのヘルスチェックに失敗"
            HEALTH_STATUS="⚠️"
        fi
        
        if ! curl -s "http://localhost:$VOICEVOX_PORT/" >/dev/null 2>&1; then
            print_color yellow "⚠️  VOICEVOXのヘルスチェックに失敗"
            HEALTH_STATUS="⚠️"
        fi
        
        # 正常時は定期的に状態を表示
        if [[ "$HEALTH_STATUS" == "✅" ]]; then
            # 5分ごとに正常メッセージを表示
            if [[ $(date +%s) -ge ${NEXT_STATUS_TIME:-0} ]]; then
                print_color green "✅ 全てのサービスが正常に動作中です ($(date '+%H:%M:%S'))"
                NEXT_STATUS_TIME=$(($(date +%s) + 300))
            fi
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    print_color red "🛑 プロセス監視を終了します"
    
    # 監視終了時の選択
    read -p "コンテナを停止しますか？ (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_color blue "🛑 コンテナを停止中..."
        docker-compose down
        print_color green "✅ コンテナを停止しました"
    fi
else
    print_color green "✅ 起動スクリプト完了。バックグラウンドでサービスが実行中です。"
fi