# GPU対応構成の設定例

# AWSリージョン
aws_region = "ap-northeast-1"

# アプリケーション名
app_name = "video-message-app"

# 環境名
environment = "dev"

# EC2キーペア名（事前作成必要）
key_name = "video-app-key"

# インスタンスタイプ
app_instance_type = "t3.large"    # アプリサーバー（月$70 or $20 with auto-stop）
gpu_instance_type = "g4dn.xlarge" # GPUサーバー（時間$0.71）

# GPUインスタンス有効化
enable_gpu_instance = false

# スポットインスタンス使用（コスト70%削減）
use_spot_for_gpu = false
spot_max_price = "0.30"  # スポット価格上限