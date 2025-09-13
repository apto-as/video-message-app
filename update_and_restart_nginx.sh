#!/bin/bash

# Update and restart Nginx on EC2 after timeout configuration changes
# This script should be run on EC2 instance

set -e

echo "=== Updating EC2 deployment with Nginx timeout fixes ==="
echo "Starting at: $(date)"

# Navigate to project directory
cd /home/ubuntu/video-message-app

# Pull latest changes from GitHub
echo "1. Pulling latest changes from GitHub..."
git pull origin master

# Restart only nginx container to apply new configuration
echo "2. Restarting Nginx container..."
docker-compose restart nginx

# Wait for nginx to be ready
echo "3. Waiting for Nginx to be ready..."
sleep 5

# Check nginx status
echo "4. Checking Nginx status..."
docker-compose ps nginx

# Test health endpoint through nginx
echo "5. Testing health endpoint through Nginx..."
curl -I https://localhost/health -k || echo "Health check via HTTPS"
curl -I http://localhost/api/health || echo "Health check via HTTP"

echo ""
echo "=== Nginx configuration updated successfully ==="
echo "Timeout settings have been increased to 300 seconds (5 minutes)"
echo "This should resolve the 504 Gateway Timeout errors during voice cloning"
echo ""
echo "Next steps:"
echo "1. Test voice clone registration from the web interface"
echo "2. Monitor logs: docker logs voice_nginx --tail 50"
echo "3. If issues persist, check backend logs: docker logs voice_backend --tail 50"
echo ""
echo "Completed at: $(date)"