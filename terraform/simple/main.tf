# Simple AWS Infrastructure for Video Message App
# 開発環境用の最小構成

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Provider設定
provider "aws" {
  region = var.aws_region
}

# 変数定義
variable "aws_region" {
  description = "AWS Region"
  default     = "ap-northeast-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.large"
}

variable "app_name" {
  description = "Application name"
  default     = "video-message-app"
}

variable "environment" {
  description = "Environment name"
  default     = "dev"
}

# 最新のUbuntu AMIを取得
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# キーペア（既存のものを使用するか、事前に作成）
variable "key_name" {
  description = "EC2 Key Pair name"
  type        = string
}

# セキュリティグループ
resource "aws_security_group" "app_sg" {
  name        = "${var.app_name}-${var.environment}-sg"
  description = "Security group for Video Message App"

  # SSH
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # 本番環境では制限すること
  }

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Backend API
  ingress {
    description = "Backend API"
    from_port   = 55433
    to_port     = 55433
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Frontend
  ingress {
    description = "Frontend"
    from_port   = 55434
    to_port     = 55434
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # VOICEVOX
  ingress {
    description = "VOICEVOX Engine"
    from_port   = 50021
    to_port     = 50021
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # OpenVoice
  ingress {
    description = "OpenVoice Service"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound - すべて許可
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-sg"
    Environment = var.environment
  }
}

# EC2インスタンス
resource "aws_instance" "app_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  # ルートボリューム
  root_block_device {
    volume_type = "gp3"
    volume_size = 100
    encrypted   = true
    
    tags = {
      Name = "${var.app_name}-${var.environment}-root"
    }
  }

  # ユーザーデータ（初期セットアップ）
  user_data = <<-EOF
    #!/bin/bash
    # ログ出力
    exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
    
    # システム更新
    apt-get update
    apt-get upgrade -y
    
    # Dockerインストール
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker ubuntu
    
    # Docker Composeインストール
    apt-get install -y docker-compose-plugin
    
    # 必要なツールインストール
    apt-get install -y git htop ncdu
    
    # スワップ追加（メモリ不足対策）
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
    
    # AWS CLIインストール（バックアップ用）
    apt-get install -y awscli
    
    # 完了メッセージ
    echo "Initial setup completed at $(date)" > /home/ubuntu/setup_complete.txt
    chown ubuntu:ubuntu /home/ubuntu/setup_complete.txt
  EOF

  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
    AutoStop    = "true" # 自動停止スクリプト用タグ
  }
}

# Elastic IP
resource "aws_eip" "app_eip" {
  instance = aws_instance.app_server.id
  domain   = "vpc"

  tags = {
    Name        = "${var.app_name}-${var.environment}-eip"
    Environment = var.environment
  }
}

# S3バケット（バックアップ用）
resource "aws_s3_bucket" "backup" {
  bucket = "${var.app_name}-${var.environment}-backups-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "${var.app_name}-${var.environment}-backups"
    Environment = var.environment
  }
}

# S3バケットのバージョニング
resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# S3バケットのライフサイクル（30日後に削除）
resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id

  rule {
    id     = "delete-old-backups"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# ランダム文字列（S3バケット名用）
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# IAMロール（EC2用）
resource "aws_iam_role" "ec2_role" {
  name = "${var.app_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-${var.environment}-ec2-role"
    Environment = var.environment
  }
}

# IAMポリシー（S3アクセス用）
resource "aws_iam_role_policy" "ec2_s3_policy" {
  name = "${var.app_name}-${var.environment}-s3-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.backup.arn,
          "${aws_s3_bucket.backup.arn}/*"
        ]
      }
    ]
  })
}

# インスタンスプロファイル
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.app_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# EC2インスタンスにIAMロールをアタッチ
resource "aws_instance" "app_server_with_role" {
  count = 0 # 既存のインスタンスがある場合はこちらを使用

  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  # 他の設定は上記と同じ
}

# CloudWatch アラーム（オプション - 無料枠内）
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.app_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "CPUUtilization"
  namespace          = "AWS/EC2"
  period             = "300"
  statistic          = "Average"
  threshold          = "80"
  alarm_description  = "This metric monitors ec2 cpu utilization"

  dimensions = {
    InstanceId = aws_instance.app_server.id
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-high-cpu-alarm"
    Environment = var.environment
  }
}

# 出力
output "instance_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_eip.app_eip.public_ip
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.app_server.id
}

output "s3_bucket_name" {
  description = "Name of the S3 backup bucket"
  value       = aws_s3_bucket.backup.id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ${var.key_name}.pem ubuntu@${aws_eip.app_eip.public_ip}"
}

output "app_urls" {
  description = "Application URLs"
  value = {
    frontend = "http://${aws_eip.app_eip.public_ip}:55434"
    backend  = "http://${aws_eip.app_eip.public_ip}:55433"
    voicevox = "http://${aws_eip.app_eip.public_ip}:50021"
  }
}