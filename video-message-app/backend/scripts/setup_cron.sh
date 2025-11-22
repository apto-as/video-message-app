#!/bin/bash
# Cron設定スクリプト - 一時ファイル自動クリーンアップ

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Cron設定を追加
(crontab -l 2>/dev/null || true; echo "# Video Message App - Temp Files Cleanup") | crontab -
(crontab -l 2>/dev/null; echo "0 * * * * cd $PROJECT_ROOT && python3 scripts/cleanup_temp_files.py >> /tmp/cleanup.log 2>&1") | crontab -

echo "✅ Cron job added: Hourly cleanup at minute 0"
echo "View with: crontab -l"
echo "Logs: /tmp/cleanup.log"
