#!/bin/bash

# AWS環境セットアップチェックスクリプト
# Terraform実行前の環境確認用

set -e

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   AWS Environment Setup Checker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# チェック結果を保存
CHECKS_PASSED=0
CHECKS_FAILED=0

# 関数定義
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 is installed${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ $1 is not installed${NC}"
        echo -e "   Install guide: $2"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $1 exists${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${YELLOW}⚠️  $1 not found${NC}"
        echo -e "   $2"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        return 1
    fi
}

# 1. 必須コマンドチェック
echo -e "${YELLOW}1. Checking required commands...${NC}"
check_command "aws" "brew install awscli"
check_command "terraform" "brew install terraform"
check_command "git" "brew install git"
check_command "docker" "https://docs.docker.com/get-docker/"
echo ""

# 2. AWS CLI設定チェック
echo -e "${YELLOW}2. Checking AWS CLI configuration...${NC}"
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}✅ AWS credentials configured${NC}"
    
    # アカウント情報表示
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    REGION=$(aws configure get region)
    
    echo -e "   Account ID: ${BLUE}$ACCOUNT_ID${NC}"
    echo -e "   User ARN:   ${BLUE}$USER_ARN${NC}"
    echo -e "   Region:     ${BLUE}$REGION${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo -e "   Run: aws configure"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi
echo ""

# 3. リージョンチェック
echo -e "${YELLOW}3. Checking AWS region...${NC}"
CURRENT_REGION=$(aws configure get region)
if [ "$CURRENT_REGION" = "ap-northeast-1" ]; then
    echo -e "${GREEN}✅ Region is set to Tokyo (ap-northeast-1)${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️  Region is set to $CURRENT_REGION${NC}"
    echo -e "   Recommended: ap-northeast-1 (Tokyo)"
    echo -e "   Change with: aws configure set region ap-northeast-1"
fi
echo ""

# 4. IAM権限チェック（基本的な権限のみ確認）
echo -e "${YELLOW}4. Checking IAM permissions...${NC}"
PERMISSIONS_OK=true

# EC2権限チェック
if aws ec2 describe-instances --max-results 1 &> /dev/null; then
    echo -e "${GREEN}✅ EC2 permissions OK${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌ EC2 permissions missing${NC}"
    PERMISSIONS_OK=false
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

# S3権限チェック
if aws s3 ls &> /dev/null; then
    echo -e "${GREEN}✅ S3 permissions OK${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌ S3 permissions missing${NC}"
    PERMISSIONS_OK=false
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

# IAM権限チェック
if aws iam list-roles --max-items 1 &> /dev/null; then
    echo -e "${GREEN}✅ IAM permissions OK${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌ IAM permissions missing${NC}"
    PERMISSIONS_OK=false
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

if [ "$PERMISSIONS_OK" = false ]; then
    echo -e "${YELLOW}   → IAMポリシーの確認が必要です${NC}"
fi
echo ""

# 5. EC2キーペアチェック
echo -e "${YELLOW}5. Checking EC2 Key Pairs...${NC}"
KEY_PAIRS=$(aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName' --output text 2>/dev/null || echo "")
if [ -n "$KEY_PAIRS" ]; then
    echo -e "${GREEN}✅ EC2 Key Pairs found:${NC}"
    for key in $KEY_PAIRS; do
        echo -e "   - $key"
    done
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${YELLOW}⚠️  No EC2 Key Pairs found${NC}"
    echo -e "   Create with: aws ec2 create-key-pair --key-name my-app-key"
fi
echo ""

# 6. Terraform設定チェック
echo -e "${YELLOW}6. Checking Terraform configuration...${NC}"
if [ -d "terraform/gpu" ] || [ -d "terraform/simple" ]; then
    echo -e "${GREEN}✅ Terraform directories found${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
    
    # terraform.tfvarsチェック
    if [ -f "terraform/gpu/terraform.tfvars" ]; then
        echo -e "${GREEN}✅ terraform/gpu/terraform.tfvars exists${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    elif [ -f "terraform/simple/terraform.tfvars" ]; then
        echo -e "${GREEN}✅ terraform/simple/terraform.tfvars exists${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${YELLOW}⚠️  terraform.tfvars not found${NC}"
        echo -e "   Copy from: cp terraform/gpu/terraform.tfvars.example terraform/gpu/terraform.tfvars"
    fi
else
    echo -e "${RED}❌ Terraform directories not found${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi
echo ""

# 7. コスト確認
echo -e "${YELLOW}7. Cost estimation...${NC}"
echo -e "${BLUE}Simple configuration (terraform/simple):${NC}"
echo -e "  - t3.large: ~\$70/month (24/7) or ~\$20/month (8h/day)"
echo -e "  - Storage: ~\$15/month"
echo -e "  ${GREEN}Total: \$35-85/month${NC}"
echo ""
echo -e "${BLUE}GPU configuration (terraform/gpu):${NC}"
echo -e "  - t3.large: ~\$20/month (8h/day)"
echo -e "  - g4dn.xlarge: ~\$0.71/hour (use only when needed)"
echo -e "  - Storage: ~\$20/month"
echo -e "  ${GREEN}Total: \$40-60/month (with 20h GPU usage)${NC}"
echo ""

# 8. セキュリティチェック
echo -e "${YELLOW}8. Security check...${NC}"
check_file ".gitignore" "Create .gitignore to prevent credential leaks"

if [ -f ".gitignore" ]; then
    # 重要なパターンが含まれているか確認
    PATTERNS=("*.pem" "*.tfstate" "terraform.tfvars" ".env")
    for pattern in "${PATTERNS[@]}"; do
        if grep -q "$pattern" .gitignore; then
            echo -e "${GREEN}✅ .gitignore contains $pattern${NC}"
        else
            echo -e "${YELLOW}⚠️  Add '$pattern' to .gitignore${NC}"
        fi
    done
fi
echo ""

# 結果サマリー
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           Check Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Checks passed: ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Checks failed: ${RED}$CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Ready to deploy.${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. cd terraform/gpu  (or terraform/simple)"
    echo "2. terraform init"
    echo "3. terraform plan"
    echo "4. terraform apply"
else
    echo -e "${RED}⚠️  Some checks failed. Please fix the issues above.${NC}"
    echo ""
    echo -e "${YELLOW}Quick fixes:${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo "• Install AWS CLI: brew install awscli"
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "• Configure AWS: aws configure"
    fi
    
    if ! command -v terraform &> /dev/null; then
        echo "• Install Terraform: brew install terraform"
    fi
fi

echo ""
echo -e "${BLUE}Need help? Check AWS_IAM_SETUP_GUIDE.md${NC}"