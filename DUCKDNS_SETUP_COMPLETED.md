# DuckDNS Setup - Ready for Token
## Video Message App Domain Configuration

**Status**: ✅ All scripts prepared and ready
**Domain**: video-message-trinitas.duckdns.org
**Current**: Waiting for DuckDNS token

## Completed Steps
1. ✅ Configuration files updated for new domain
2. ✅ nginx configured for video-message-trinitas.duckdns.org
3. ✅ Docker compose environment variables updated
4. ✅ DuckDNS update script created
5. ✅ Let's Encrypt installation script created

## Next Steps (User Action Required)

### 1. Get Your DuckDNS Token
1. Open: https://www.duckdns.org
2. Sign in with GitHub/Google/Reddit
3. Copy the token shown at the top of the page

### 2. Add Subdomain in DuckDNS
- Enter: `video-message-trinitas` in the subdomain field
- Click "add domain"

### 3. Run Commands
```bash
ssh -p 22 -i ~/.ssh/video-app-key.pem ec2-user@3.115.141.166
cd ~/video-message-app
./duckdns_update.sh YOUR_TOKEN_HERE
sudo ./install_letsencrypt.sh
```

## Files Created on EC2
- `/home/ec2-user/video-message-app/update_for_domain.sh` - Domain configuration updater
- `/home/ec2-user/video-message-app/duckdns_update.sh` - DuckDNS DNS updater
- `/home/ec2-user/video-message-app/install_letsencrypt.sh` - Let's Encrypt installer

## After Completion
Your app will be available at:
**https://video-message-trinitas.duckdns.org**

With:
- ✅ Valid SSL certificate (Let's Encrypt)
- ✅ No browser warnings
- ✅ Professional domain name
- ✅ Completely free