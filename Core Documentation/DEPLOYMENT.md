# Production Deployment Guide

This guide covers deploying ShadowNet C2 in a production or controlled testing environment with proper security configurations.

## ⚠️ Security Warning

**CRITICAL**: Only deploy this in:
- Isolated lab environments
- Authorized red team infrastructure
- Controlled testing environments with proper authorization

**NEVER deploy on public networks without proper isolation and legal authorization.**

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Server Hardening](#server-hardening)
3. [HTTPS Configuration](#https-configuration)
4. [Environment Configuration](#environment-configuration)
5. [Firewall Setup](#firewall-setup)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup Strategy](#backup-strategy)
8. [Maintenance](#maintenance)

---

## Pre-Deployment Checklist

Before deploying to production:

- [ ] **Change default credentials** (admin/admin123)
- [ ] **Generate strong encryption key** (32 random bytes)
- [ ] **Configure HTTPS** with valid SSL certificates
- [ ] **Set up firewall rules**
- [ ] **Review security settings**
- [ ] **Configure proper logging**
- [ ] **Set up backup procedures**
- [ ] **Test in isolated environment first**
- [ ] **Document your configuration**
- [ ] **Obtain proper authorization**

---

## Server Hardening

### 1. Operating System Hardening

#### Linux (Recommended)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install fail2ban for brute force protection
sudo apt install fail2ban -y

# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 443/tcp  # HTTPS only
sudo ufw enable

# Create dedicated user
sudo useradd -r -s /bin/false shadownet
sudo mkdir -p /opt/shadownet
sudo chown shadownet:shadownet /opt/shadownet
```

#### Windows Server

```powershell
# Enable Windows Firewall
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# Allow only HTTPS
New-NetFirewallRule -DisplayName "ShadowNet HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow

# Create dedicated service account
New-LocalUser -Name "shadownet" -NoPassword -UserMayNotChangePassword
```

### 2. Python Environment

```bash
# Use virtual environment
python3 -m venv /opt/shadownet/venv
source /opt/shadownet/venv/bin/activate

# Install with specific versions
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# Set proper permissions
chmod 700 /opt/shadownet
chmod 600 /opt/shadownet/server/*.py
```

### 3. Secure Configuration

Create production config file:

```python
# /opt/shadownet/config.py
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SHADOWNET_SECRET_KEY')
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    
    # Security headers
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # Database
    DATABASE_PATH = '/opt/shadownet/data/shadownet.db'
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/shadownet/server.log'
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per hour"
```

---

## HTTPS Configuration

### Option 1: Self-Signed Certificate (Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365 \
  -subj "/CN=shadownet.local"

# Set permissions
chmod 600 key.pem
chmod 644 cert.pem
```

### Option 2: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot -y

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Option 3: Private CA Certificate

```bash
# Create private CA (for isolated networks)
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem

# Generate server certificate
openssl genrsa -out server-key.pem 4096
openssl req -new -key server-key.pem -out server-req.pem
openssl x509 -req -in server-req.pem -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365
```

### Update Server for HTTPS

Modify `server_with_event.py`:

```python
if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    app.run(
        host='0.0.0.0',
        port=443,
        ssl_context=context,
        debug=False
    )
```

---

## Environment Configuration

### 1. Generate Strong Encryption Key

```python
# generate_key.py
import secrets

# Generate cryptographically secure 32-byte key
key = secrets.token_hex(16)  # 16 bytes = 32 hex chars
print(f"SHADOWNET_SECRET_KEY={key}")
```

### 2. Environment Variables

Create `/opt/shadownet/.env`:

```bash
# Server Configuration
SHADOWNET_SECRET_KEY=<your-32-byte-key-here>
FLASK_ENV=production
FLASK_APP=server_with_event.py

# Database
DATABASE_PATH=/opt/shadownet/data/shadownet.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/shadownet/server.log

# Security
SESSION_TIMEOUT=1800
MAX_CONTENT_LENGTH=10485760  # 10MB

# Network
SERVER_HOST=0.0.0.0
SERVER_PORT=443
```

Load environment:

```bash
# Add to systemd service or startup script
set -a
source /opt/shadownet/.env
set +a
```

### 3. Change Default Credentials

```python
# change_password.py
import database
import hashlib

def change_admin_password():
    new_password = input("Enter new admin password: ")
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    database.update_user_password('admin', password_hash)
    print("Password updated successfully!")

if __name__ == '__main__':
    change_admin_password()
```

---

## Firewall Setup

### Linux (UFW)

```bash
# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow HTTPS only
sudo ufw allow 443/tcp comment 'ShadowNet HTTPS'

# Allow SSH (for management)
sudo ufw allow 22/tcp comment 'SSH'

# Enable
sudo ufw enable
sudo ufw status verbose
```

### Linux (iptables)

```bash
# Flush existing rules
sudo iptables -F

# Default policies
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow HTTPS
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow SSH (management)
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### Windows Firewall

```powershell
# Remove default rules
Remove-NetFirewallRule -DisplayName "ShadowNet*"

# Add HTTPS rule
New-NetFirewallRule -DisplayName "ShadowNet HTTPS" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 443 `
    -Action Allow `
    -Profile Domain,Private

# Block all other incoming by default
Set-NetFirewallProfile -DefaultInboundAction Block
```

---

## Systemd Service (Linux)

Create `/etc/systemd/system/shadownet.service`:

```ini
[Unit]
Description=ShadowNet C2 Server
After=network.target

[Service]
Type=simple
User=shadownet
Group=shadownet
WorkingDirectory=/opt/shadownet/server
Environment="SHADOWNET_SECRET_KEY=your-key-here"
ExecStart=/opt/shadownet/venv/bin/python server_with_event.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=shadownet

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/shadownet/data /var/log/shadownet

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable shadownet
sudo systemctl start shadownet
sudo systemctl status shadownet
```

---

## Monitoring & Logging

### 1. Application Logging

Update server code to log to file:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    '/var/log/shadownet/server.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
```

### 2. System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Monitor server process
htop -p $(pgrep -f shadownet)

# Monitor network connections
sudo nethogs

# Check logs
sudo journalctl -u shadownet -f
```

### 3. Log Rotation

Create `/etc/logrotate.d/shadownet`:

```
/var/log/shadownet/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 shadownet shadownet
    sharedscripts
    postrotate
        systemctl reload shadownet > /dev/null 2>&1 || true
    endscript
}
```

---

## Backup Strategy

### 1. Database Backup Script

```bash
#!/bin/bash
# /opt/shadownet/scripts/backup.sh

BACKUP_DIR="/opt/shadownet/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/opt/shadownet/data/shadownet.db"

# Create backup
mkdir -p $BACKUP_DIR
sqlite3 $DB_PATH ".backup '$BACKUP_DIR/shadownet_$DATE.db'"

# Compress
gzip "$BACKUP_DIR/shadownet_$DATE.db"

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

# Log
echo "[$DATE] Backup completed: shadownet_$DATE.db.gz"
```

### 2. Automated Backups

```bash
# Add to crontab
crontab -e

# Run daily at 2 AM
0 2 * * * /opt/shadownet/scripts/backup.sh >> /var/log/shadownet/backup.log 2>&1
```

### 3. Configuration Backup

```bash
#!/bin/bash
# Backup configuration files

tar -czf /opt/shadownet/backups/config_$(date +%Y%m%d).tar.gz \
    /opt/shadownet/.env \
    /opt/shadownet/config.py \
    /etc/systemd/system/shadownet.service
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor logs for errors
- Check agent connectivity
- Review incident reports

**Weekly:**
- Review access logs
- Update dependencies
- Check disk space
- Verify backups

**Monthly:**
- Update system packages
- Rotate logs
- Review and archive old data
- Update SSL certificates (if needed)
- Security audit

### Update Procedure

```bash
# Stop service
sudo systemctl stop shadownet

# Backup current version
sudo cp -r /opt/shadownet /opt/shadownet.backup

# Update code
cd /opt/shadownet
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Test configuration
python -m py_compile server_with_event.py

# Start service
sudo systemctl start shadownet

# Check status
sudo systemctl status shadownet
sudo journalctl -u shadownet -n 50
```

### Disaster Recovery

```bash
# Restore from backup
sudo systemctl stop shadownet
sudo cp /opt/shadownet/backups/shadownet_YYYYMMDD.db.gz .
gunzip shadownet_YYYYMMDD.db.gz
sudo cp shadownet_YYYYMMDD.db /opt/shadownet/data/shadownet.db
sudo chown shadownet:shadownet /opt/shadownet/data/shadownet.db
sudo systemctl start shadownet
```

---

## Security Checklist

**Before Going Live:**

- [ ] Default credentials changed
- [ ] Strong encryption key generated
- [ ] HTTPS configured with valid certificates
- [ ] Firewall rules configured
- [ ] Unnecessary ports closed
- [ ] Logging enabled and tested
- [ ] Backup automation configured
- [ ] System updates applied
- [ ] SELinux/AppArmor configured (Linux)
- [ ] Service running as non-root user
- [ ] Database file permissions set correctly (600)
- [ ] Environment variables secured
- [ ] Rate limiting enabled
- [ ] Session timeout configured
- [ ] Documentation updated

**Post-Deployment:**

- [ ] Monitor logs regularly
- [ ] Test backups weekly
- [ ] Review access patterns
- [ ] Keep software updated
- [ ] Conduct security audits
- [ ] Document any changes
- [ ] Maintain incident response plan

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u shadownet -xe

# Check permissions
ls -la /opt/shadownet/

# Check port availability
sudo netstat -tulpn | grep 443

# Test manually
sudo -u shadownet /opt/shadownet/venv/bin/python /opt/shadownet/server/server_with_event.py
```

### Certificate Issues

```bash
# Verify certificate
openssl x509 -in cert.pem -text -noout

# Check certificate expiration
openssl x509 -in cert.pem -noout -dates

# Test HTTPS connection
curl -v https://your-domain.com
```

### Performance Issues

```bash
# Check resource usage
htop
df -h
free -h

# Check database size
du -sh /opt/shadownet/data/shadownet.db

# Vacuum database
sqlite3 /opt/shadownet/data/shadownet.db "VACUUM;"
```

---

## Contact

For deployment support:
- GitHub Issues: [Report deployment issues](https://github.com/yourusername/shadownet-c2/issues)
- Security: Use secure reporting for vulnerabilities

---

**Remember**: This is a security testing tool. Use responsibly and only on authorized systems.
