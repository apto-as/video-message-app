#!/bin/bash

# Video Message App - デプロイスクリプト
# ローカル → EC2へのデプロイを自動化

set -e  # エラー時に停止

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
EC2_HOST="3.115.141.166"
EC2_USER="ec2-user"
EC2_KEY="$HOME/.ssh/video-app-key.pem"
EC2_PATH="/home/ec2-user/video-message-app/video-message-app"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

# 除外パターン
RSYNC_EXCLUDE="--exclude='.git' \
               --exclude='__pycache__' \
               --exclude='*.pyc' \
               --exclude='node_modules' \
               --exclude='venv' \
               --exclude='*.egg-info' \
               --exclude='data/' \
               --exclude='.DS_Store' \
               --exclude='.env.local' \
               --exclude='*.log'"

# ヘルプ表示
show_help() {
    cat << EOF
使い方: $0 [COMMAND] [OPTIONS]

COMMANDS:
    sync        - ソースコードをEC2に同期（デフォルト）
    deploy      - sync + Docker再起動
    rollback    - 前回のバックアップに戻す
    status      - EC2の状態を確認
    logs        - サービスログを表示
    ssh         - EC2にSSH接続

OPTIONS:
    --dry-run   - 実際の変更を行わずにシミュレーション
    --backup    - デプロイ前にバックアップを作成（デフォルト）
    --no-backup - バックアップをスキップ
    --service   - 再起動するサービス（backend, frontend, nginx, all）

EXAMPLES:
    $0 deploy                    # 全サービスをデプロイ
    $0 deploy --service=backend  # バックエンドのみデプロイ
    $0 sync --dry-run            # 変更内容を確認
    $0 rollback                  # ロールバック
    $0 logs backend              # バックエンドのログ表示

EOF
}

# ログ出力
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# SSH接続確認
check_ssh() {
    log_step "SSH接続を確認中..."
    if ssh -i "$EC2_KEY" -p 22 -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo 'Connected'" &>/dev/null; then
        log_info "SSH接続成功"
        return 0
    else
        log_error "SSH接続失敗"
        return 1
    fi
}

# バックアップ作成
create_backup() {
    log_step "バックアップを作成中..."
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"

    ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" << EOF
        cd $EC2_PATH
        mkdir -p ../backups
        tar -czf ../backups/$BACKUP_NAME.tar.gz \
            --exclude='data' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='venv' \
            .
        echo "$BACKUP_NAME" > ../backups/latest.txt
EOF

    log_info "バックアップ作成完了: $BACKUP_NAME"
}

# ソースコード同期
sync_code() {
    local DRY_RUN=""
    if [ "$1" == "--dry-run" ]; then
        DRY_RUN="--dry-run"
        log_warn "DRY RUN モード（実際の変更は行いません）"
    fi

    log_step "ソースコードを同期中..."

    rsync -avz --progress $DRY_RUN $RSYNC_EXCLUDE \
        -e "ssh -i $EC2_KEY -p 22" \
        --exclude='.env' \
        "$LOCAL_PATH/" \
        "$EC2_USER@$EC2_HOST:$EC2_PATH/"

    if [ -z "$DRY_RUN" ]; then
        log_info "同期完了"
    fi
}

# Dockerサービス再起動
restart_services() {
    local SERVICE="${1:-all}"

    log_step "Dockerサービスを再起動中: $SERVICE"

    if [ "$SERVICE" == "all" ]; then
        ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" \
            "cd $EC2_PATH && docker-compose restart"
    else
        ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" \
            "cd $EC2_PATH && docker-compose restart $SERVICE"
    fi

    log_info "再起動完了"
}

# ロールバック
rollback() {
    log_step "ロールバック中..."

    # 最新のバックアップを取得
    BACKUP_NAME=$(ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" \
        "cat $EC2_PATH/../backups/latest.txt")

    if [ -z "$BACKUP_NAME" ]; then
        log_error "バックアップが見つかりません"
        exit 1
    fi

    log_info "バックアップを復元中: $BACKUP_NAME"

    ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" << EOF
        cd $EC2_PATH
        tar -xzf ../backups/$BACKUP_NAME.tar.gz
EOF

    restart_services "all"
    log_info "ロールバック完了"
}

# ステータス確認
check_status() {
    log_step "EC2ステータスを確認中..."

    ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" << 'EOF'
        echo "=== システム情報 ==="
        uptime
        echo ""
        echo "=== ディスク使用量 ==="
        df -h / | tail -1
        echo ""
        echo "=== メモリ使用量 ==="
        free -h | grep Mem
        echo ""
        echo "=== Dockerサービス ==="
        cd /home/ec2-user/video-message-app/video-message-app
        docker-compose ps
        echo ""
        echo "=== OpenVoice Service ==="
        sudo systemctl status openvoice --no-pager -l | head -20
EOF
}

# ログ表示
show_logs() {
    local SERVICE="${1:-backend}"
    local LINES="${2:-50}"

    log_step "ログを表示中: $SERVICE"

    ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST" \
        "cd $EC2_PATH && docker-compose logs --tail=$LINES $SERVICE"
}

# メイン処理
main() {
    local COMMAND="${1:-deploy}"
    local DRY_RUN=""
    local CREATE_BACKUP=true
    local SERVICE="all"

    # オプション解析
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run)
                DRY_RUN="--dry-run"
                ;;
            --no-backup)
                CREATE_BACKUP=false
                ;;
            --service=*)
                SERVICE="${1#*=}"
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    # SSH接続確認
    if ! check_ssh; then
        log_error "EC2に接続できません"
        exit 1
    fi

    # コマンド実行
    case "$COMMAND" in
        sync)
            sync_code $DRY_RUN
            ;;
        deploy)
            if [ "$CREATE_BACKUP" = true ] && [ -z "$DRY_RUN" ]; then
                create_backup
            fi
            sync_code $DRY_RUN
            if [ -z "$DRY_RUN" ]; then
                restart_services "$SERVICE"
            fi
            log_info "デプロイ完了！"
            ;;
        rollback)
            rollback
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs "$SERVICE" "${2:-50}"
            ;;
        ssh)
            ssh -i "$EC2_KEY" -p 22 "$EC2_USER@$EC2_HOST"
            ;;
        *)
            log_error "不明なコマンド: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
