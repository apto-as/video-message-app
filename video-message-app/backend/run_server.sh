#!/bin/bash
# バックエンドサーバー起動スクリプト

echo "🚀 バックエンドサーバーを起動します..."
cd "$(dirname "$0")"
uvicorn main:app --reload --port 55433