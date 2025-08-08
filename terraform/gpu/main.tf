# GPU対応 AWS Infrastructure for Video Message App
# アプリケーションサーバー + GPUサーバーの2インスタンス構成

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "video-app"
}

# ========================================
# Variables
# ========================================

variable "aws_region" {
  description = "AWS Region"
  default     = "ap-northeast-1"
}

variable "app_name" {
  description = "Application name"
  default     = "video-message-app"
}

variable "environment" {
  description = "Environment"
  default     = "dev"
}

variable "key_name" {
  description = "EC2 Key Pair name"
  type        = string
}

variable "app_instance_type" {
  description = "Instance type for application server"
  default     = "t3.large"
}

variable "gpu_instance_type" {
  description = "Instance type for GPU server"
  default     = "g4dn.xlarge"
}

variable "enable_gpu_instance" {
  description = "Enable GPU instance creation"
  default     = true
  type        = bool
}

variable "use_spot_for_gpu" {
  description = "Use spot instance for GPU"
  default     = false
  type        = bool
}

variable "spot_max_price" {
  description = "Maximum price for spot instance"
  default     = "0.30"
}

# ========================================
# Data Sources
# ========================================

# Ubuntu AMI for app server
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Deep Learning AMI for GPU server (fallback to Ubuntu for now)
data "aws_ami" "deep_learning" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ========================================
# Network
# ========================================

# VPC (既存のデフォルトVPCを使用するか、新規作成)
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.app_name}-${var.environment}-vpc"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.app_name}-${var.environment}-igw"
    Environment = var.environment
  }
}

# Public Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.app_name}-${var.environment}-public"
    Environment = var.environment
  }
}

# Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-public-rt"
    Environment = var.environment
  }
}

# Route Table Association
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

data "aws_availability_zones" "available" {
  state = "available"
}

# ========================================
# Security Groups
# ========================================

# Application Server Security Group
resource "aws_security_group" "app_sg" {
  name        = "${var.app_name}-${var.environment}-app-sg"
  description = "Security group for application server"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Backend API"
    from_port   = 55433
    to_port     = 55433
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Frontend"
    from_port   = 55434
    to_port     = 55434
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "VOICEVOX"
    from_port   = 50021
    to_port     = 50021
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-app-sg"
    Environment = var.environment
  }
}

# GPU Server Security Group
resource "aws_security_group" "gpu_sg" {
  name        = "${var.app_name}-${var.environment}-gpu-sg"
  description = "Security group for GPU server"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description     = "OpenVoice from App Server"
    from_port       = 8001
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-gpu-sg"
    Environment = var.environment
  }
}

# ========================================
# EFS (Shared Storage)
# ========================================

resource "aws_efs_file_system" "shared" {
  creation_token = "${var.app_name}-${var.environment}-efs"
  encrypted      = true

  tags = {
    Name        = "${var.app_name}-${var.environment}-efs"
    Environment = var.environment
  }
}

resource "aws_efs_mount_target" "shared" {
  file_system_id  = aws_efs_file_system.shared.id
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_security_group" "efs_sg" {
  name        = "${var.app_name}-${var.environment}-efs-sg"
  description = "Security group for EFS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from App Server"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  ingress {
    description     = "NFS from GPU Server"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.gpu_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-efs-sg"
    Environment = var.environment
  }
}

# ========================================
# EC2 Instances
# ========================================

# Application Server
resource "aws_instance" "app_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.app_instance_type
  key_name      = var.key_name
  subnet_id     = aws_subnet.public.id

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  root_block_device {
    volume_type = "gp3"
    volume_size = 100
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data_app.sh", {
    efs_id = aws_efs_file_system.shared.id
    region = var.aws_region
  }))

  tags = {
    Name        = "${var.app_name}-${var.environment}-app"
    Environment = var.environment
    Type        = "Application"
    AutoStop    = "true"
  }
}

# GPU Server (Optional)
resource "aws_instance" "gpu_server" {
  count = var.enable_gpu_instance ? 1 : 0

  ami           = data.aws_ami.deep_learning.id
  instance_type = var.gpu_instance_type
  key_name      = var.key_name
  subnet_id     = aws_subnet.public.id

  vpc_security_group_ids = [aws_security_group.gpu_sg.id]

  root_block_device {
    volume_type = "gp3"
    volume_size = 200
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data_gpu.sh", {
    efs_id = aws_efs_file_system.shared.id
    region = var.aws_region
  }))

  tags = {
    Name        = "${var.app_name}-${var.environment}-gpu"
    Environment = var.environment
    Type        = "GPU"
    AutoStop    = "true"
  }
}

# Elastic IPs
resource "aws_eip" "app_eip" {
  instance = aws_instance.app_server.id
  domain   = "vpc"

  tags = {
    Name        = "${var.app_name}-${var.environment}-app-eip"
    Environment = var.environment
  }
}

resource "aws_eip" "gpu_eip" {
  count    = var.enable_gpu_instance ? 1 : 0
  instance = aws_instance.gpu_server[0].id
  domain   = "vpc"

  tags = {
    Name        = "${var.app_name}-${var.environment}-gpu-eip"
    Environment = var.environment
  }
}

# ========================================
# S3 Bucket for Backups
# ========================================

resource "aws_s3_bucket" "backup" {
  bucket = "${var.app_name}-${var.environment}-backups-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "${var.app_name}-${var.environment}-backups"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

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

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# ========================================
# IAM Roles
# ========================================

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
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "${var.app_name}-${var.environment}-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*"
        ]
        Resource = [
          aws_s3_bucket.backup.arn,
          "${aws_s3_bucket.backup.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:*"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.app_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ========================================
# Outputs
# ========================================

output "app_server_public_ip" {
  description = "Public IP of the application server"
  value       = aws_eip.app_eip.public_ip
}

output "gpu_server_public_ip" {
  description = "Public IP of the GPU server"
  value       = var.enable_gpu_instance ? aws_eip.gpu_eip[0].public_ip : "Not created"
}

output "app_server_private_ip" {
  description = "Private IP of the application server"
  value       = aws_instance.app_server.private_ip
}

output "gpu_server_private_ip" {
  description = "Private IP of the GPU server"
  value       = var.enable_gpu_instance ? aws_instance.gpu_server[0].private_ip : "Not created"
}

output "efs_dns_name" {
  description = "DNS name of the EFS file system"
  value       = aws_efs_file_system.shared.dns_name
}

output "s3_bucket_name" {
  description = "Name of the S3 backup bucket"
  value       = aws_s3_bucket.backup.id
}

output "ssh_commands" {
  description = "SSH commands to connect to servers"
  value = {
    app = "ssh -i ${var.key_name}.pem ubuntu@${aws_eip.app_eip.public_ip}"
    gpu = var.enable_gpu_instance ? "ssh -i ${var.key_name}.pem ubuntu@${aws_eip.gpu_eip[0].public_ip}" : "Not created"
  }
}

output "app_urls" {
  description = "Application URLs"
  value = {
    frontend = "http://${aws_eip.app_eip.public_ip}:55434"
    backend  = "http://${aws_eip.app_eip.public_ip}:55433"
    voicevox = "http://${aws_eip.app_eip.public_ip}:50021"
    openvoice = var.enable_gpu_instance ? "http://${aws_instance.gpu_server[0].private_ip}:8001" : "Not created"
  }
}

output "instance_ids" {
  description = "Instance IDs for management"
  value = {
    app = aws_instance.app_server.id
    gpu = var.enable_gpu_instance ? aws_instance.gpu_server[0].id : "Not created"
  }
}