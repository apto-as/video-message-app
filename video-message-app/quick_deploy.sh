#!/bin/bash

# クイックデプロイスクリプト
# SSHキーを環境変数で指定して実行

echo "🚀 Quick Deploy to EC2"
echo "======================"

# SSHキーパスを設定（必要に応じて変更）
export SSH_KEY_PATH="$HOME/.ssh/id_rsa"

# もし引数でキーが指定されたら使用
if [ -n "$1" ]; then
    export SSH_KEY_PATH="$1"
fi

# デプロイスクリプトを実行
./deploy_to_ec2.sh