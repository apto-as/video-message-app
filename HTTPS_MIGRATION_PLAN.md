# HTTPS移行実装ガイド

## 推奨: Let's Encrypt + Nginx 実装

### 前提条件
- ドメイン名を所有している
- EC2インスタンスへのSSHアクセス

### Step 1: ドメイン設定

#### 1.1 Route 53でホストゾーン作成
```bash
# AWS Route 53でドメインのホストゾーンを作成
# 例: video-app.yourdomain.com
```

#### 1.2 Aレコード設定
```
Type: A
Name: video-app.yourdomain.com
Value: 3.115.141.166
TTL: 300
```

### Step 2: EC2でNginx設定

```bash
# SSHでEC2に接続
ssh -i ~/.ssh/video-app-key.pem ubuntu@3.115.141.166

# Nginxインストール
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Nginx設定ファイル作成
sudo nano /etc/nginx/sites-available/video-app
```

#### Nginx設定内容:
```nginx
server {
    listen 80;
    server_name video-app.yourdomain.com;

    # フロントエンド
    location / {
        proxy_pass http://localhost:55434;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # バックエンドAPI
    location /api/ {
        proxy_pass http://localhost:55433/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # VOICEVOX
    location /voicevox/ {
        proxy_pass http://localhost:50021/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

### Step 3: SSL証明書取得

```bash
# サイト有効化
sudo ln -s /etc/nginx/sites-available/video-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Let's Encrypt証明書取得
sudo certbot --nginx -d video-app.yourdomain.com

# 自動更新設定
sudo systemctl enable certbot.timer
```

### Step 4: フロントエンド環境変数更新

```bash
cd ~/video-message-app/video-message-app

# 環境変数をHTTPSに更新
cat > frontend/.env << EOF
REACT_APP_API_URL=https://video-app.yourdomain.com
EOF

# Docker再ビルド
sudo docker-compose down
sudo docker-compose up -d --build frontend
```

### Step 5: セキュリティグループ更新

```bash
# AWS ConsoleまたはCLIで以下のポートを開放:
# - 443 (HTTPS)
# - 80 (HTTP - Let's Encrypt更新用)
```

## 代替案: CloudFlare実装（最速）

### Step 1: CloudFlareアカウント作成
1. https://www.cloudflare.com でアカウント作成
2. ドメインを追加
3. DNSをCloudFlareに変更

### Step 2: DNS設定
```
Type: A
Name: video-app
Content: 3.115.141.166
Proxy status: Proxied (オレンジ色の雲)
```

### Step 3: SSL/TLS設定
1. CloudFlareダッシュボード → SSL/TLS
2. 暗号化モード: "Flexible"
3. Always Use HTTPS: ON

### Step 4: ページルール設定
```
URL: http://video-app.yourdomain.com/*
設定: Always Use HTTPS
```

## コスト比較

| 方法 | 初期費用 | 月額費用 | 設定時間 |
|------|---------|---------|----------|
| Let's Encrypt + Nginx | $0 | $0 | 30分 |
| AWS ALB + ACM | $0 | $20-30 | 1時間 |
| CloudFlare | $0 | $0 | 15分 |

## 移行後のメリット

✅ **録音機能が利用可能**  
✅ **SEO向上**  
✅ **ユーザー信頼性向上**  
✅ **ブラウザ警告の解消**  
✅ **PWA対応可能**

## Terraformでの自動化

```hcl
# terraform/https/main.tf
resource "aws_route53_zone" "main" {
  name = "yourdomain.com"
}

resource "aws_route53_record" "video_app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "video-app.yourdomain.com"
  type    = "A"
  ttl     = "300"
  records = [aws_instance.app_server.public_ip]
}
```