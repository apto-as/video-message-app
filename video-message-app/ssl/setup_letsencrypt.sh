#!/bin/bash
# Let's Encrypt SSL Certificate Setup for Video Message App
# Trinitas-Core Emergency SSL Recovery Script

set -e

DOMAIN="3.115.141.166"
EMAIL="admin@trinitas-core.com"
WEBROOT="/var/www/certbot"

echo "🔐 Trinitas-Core SSL Certificate Recovery"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"

# Create webroot directory for certbot challenges
sudo mkdir -p $WEBROOT

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Stop nginx temporarily
echo "Stopping nginx..."
sudo docker-compose -f /home/ubuntu/video-message-app/docker-compose.yml down nginx 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# Request certificate using standalone mode (since nginx is down)
echo "Requesting SSL certificate..."
sudo certbot certonly \
    --standalone \
    --agree-tos \
    --no-eff-email \
    --email $EMAIL \
    -d $DOMAIN \
    --non-interactive

# Copy certificates to application directory
echo "Copying certificates..."
APP_DIR="/home/ubuntu/video-message-app"
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $APP_DIR/ssl/server.crt
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $APP_DIR/ssl/server.key

# Set correct permissions
sudo chown ubuntu:ubuntu $APP_DIR/ssl/server.crt $APP_DIR/ssl/server.key
sudo chmod 644 $APP_DIR/ssl/server.crt
sudo chmod 600 $APP_DIR/ssl/server.key

# Setup auto-renewal
echo "Setting up auto-renewal..."
sudo crontab -l 2>/dev/null | grep -q "certbot renew" || {
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'cd /home/ubuntu/video-message-app && docker-compose restart nginx'") | sudo crontab -
}

# Restart services
echo "Restarting services..."
cd $APP_DIR
sudo docker-compose up -d

echo "✅ SSL Certificate successfully installed!"
echo "🌐 Your application is now available at: https://$DOMAIN"
echo "🔄 Auto-renewal configured via crontab"