# Quick Start - Cleanup Script

## 基本コマンド

```bash
# 場所
cd ~/workspace/github.com/apto-as/prototype-app/video-message-app/backend/scripts

# ドライラン（確認のみ）
python cleanup_temp_files.py --dry-run

# 実行（24時間以上経過したファイル削除）
python cleanup_temp_files.py

# 1時間以上経過したファイル削除
python cleanup_temp_files.py --max-age-hours 1

# 即座に削除（テスト用）
python cleanup_temp_files.py --max-age-hours 0
```

## ヘルプ

```bash
python cleanup_temp_files.py --help
```

## 削除対象

- `openvoice_*` - OpenVoice一時ディレクトリ
- `tmp*.wav` - 一時音声ファイル

## 詳細ドキュメント

- README_CLEANUP.md - 詳細な使用方法
- PHASE1_IMPLEMENTATION_SUMMARY.md - 実装詳細
