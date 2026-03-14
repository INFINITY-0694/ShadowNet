# ShadowNet Docker Deployment Guide

> **Last Updated**: March 14, 2026

This guide explains how to deploy ShadowNet (Agent + Server) on Docker to work on any PC or laptop.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Environment Variables](#environment-variables)
4. [Deployment Options](#deployment-options)
5. [Multi-PC Setup](#multi-pc-setup)
6. [Custom Domain Setup](#custom-domain-setup)
7. [Troubleshooting](#troubleshooting)
8. [Code Changes for Docker](#code-changes-for-docker)

---

## Quick Start

### 1. Generate Security Keys

```bash
# Generate random keys (requires Python 3)
python -c "
import secrets
print('AES_KEY (32 bytes hex):', secrets.token_hex(32))
print('FLASK_SECRET:', secrets.token_hex(32))
print('REGISTRATION_SECRET:', secrets.token_hex(16))
"
```

Example output:
```
AES_KEY: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
FLASK_SECRET: f1e2d3c4b5a69f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5
REGISTRATION_SECRET: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
```

### 2. Create `.env` File

```bash
# Copy the example configuration
cp .env.docker .env

# Edit .env with your values
nano .env  # or use your favorite editor
```

### 3. Start the Server

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f server

# Check system status
docker-compose ps
```

### 4. Access the Server

- **Web Interface**: http://localhost:5000
- **Default Login**: admin / (password from SHADOWNET_ADMIN_PASSWORD)
- **Database**: Automatically created in `./data/shadownet.db`

---

## System Requirements

### For Docker Host (Server PC)

- **Docker Engine**: 20.10+ (or Docker Desktop for Windows/Mac)
- **Docker Compose**: 2.0+
- **Disk Space**: 500MB minimum (Python image + data)
- **Memory**: 512MB minimum (1GB recommended)
- **Network**: Port 5000 (or custom) must be accessible

### For Agent PC

- **Go**: 1.16+ (for building agents)
- **Network**: Must reach server IP:PORT
- **OS**: Windows, Linux, macOS (agent auto-detects)

### Installation

**Windows (Docker Desktop)**:
```bash
# Download Docker Desktop: https://www.docker.com/products/docker-desktop
# Or via chocolatey:
choco install docker-desktop
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

**macOS**:
```bash
# Via Homebrew:
brew install --cask docker
brew install docker-compose
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SHADOWNET_AES_KEY` | 32-byte hex encryption key | `a1b2c3d4...` (64 chars) |
| `SHADOWNET_FLASK_SECRET` | Flask session secret | `f1e2d3c4...` (64+ chars) |
| `SHADOWNET_REGISTRATION_SECRET` | Agent registration secret | `1a2b3c4d...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SHADOWNET_ADMIN_PASSWORD` | `admin123` | Admin user password |
| `SERVER_PORT` | `5000` | HTTP port for server |
| `SHADOWNET_DB_PATH` | `/app/data/shadownet.db` | Database file location |
| `FLASK_ENV` | `production` | Flask environment |
| `FLASK_DEBUG` | `0` | Debug mode (0=off, 1=on) |

### Custom Domain Variables (Traefik)

| Variable | Required | Description |
|----------|----------|-------------|
| `CUSTOM_DOMAIN` | Optional | Domain name (e.g., c2.example.com) |
| `LETSENCRYPT_EMAIL` | If using domain | Email for SSL certificates |
| `TRAEFIK_USER` | Optional | Traefik dashboard username |
| `TRAEFIK_PASSWORD` | Optional | Traefik dashboard password |

---

## Deployment Options

### Option 1: Local Development (Single PC)

```bash
# Start server
docker-compose up -d server

# Agent runs locally (same machine)
export SHADOWNET_SERVER_URL=http://localhost:5000/beacon
export SHADOWNET_AES_KEY=your_aes_key
export SHADOWNET_REGISTRATION_SECRET=your_reg_secret
export SHADOWNET_ENABLE_PERSISTENCE=false  # Disable Windows persistence

go run main.go
```

### Option 2: Server on One PC, Agent on Another

```bash
# On Server PC:
docker-compose up -d

# On Agent PC:
# Get server IP
ipconfig getifaddr en0  # macOS
hostname -I             # Linux
ipconfig                # Windows - look for IPv4 Address

# Build and run agent
export SHADOWNET_SERVER_URL=http://SERVER_IP:5000/beacon
export SHADOWNET_AES_KEY=your_aes_key
export SHADOWNET_REGISTRATION_SECRET=your_reg_secret
export SHADOWNET_ENABLE_PERSISTENCE=false

go run main.go
```

### Option 3: Docker Compose Network (Both in Containers)

**docker-compose.yml snippet** (for agents):
```yaml
agent1:
  image: golang:1.19
  container_name: shadownet-agent-1
  volumes:
    - ./agent:/workspace
  working_dir: /workspace
  environment:
    SHADOWNET_SERVER_URL: http://server:5000/beacon
    SHADOWNET_AES_KEY: ${SHADOWNET_AES_KEY}
    SHADOWNET_REGISTRATION_SECRET: ${SHADOWNET_REGISTRATION_SECRET}
    SHADOWNET_ENABLE_PERSISTENCE: "false"
  networks:
    - shadownet-network
  command: go run main.go
```

Then: `docker-compose up -d`

---

## Multi-PC Setup

### Scenario: Server on PC-A, Multiple Agents on PC-B, PC-C, etc.

#### Step 1: Deploy Server

**On PC-A:**
```bash
# Clone/copy ShadowNet
git clone https://github.com/yourrepo/shadownet.git
cd shadownet

# Create .env
cp .env.docker .env
nano .env  # Fill in secrets

# Start server
docker-compose up -d

# Get PC-A's IP address
hostname -I | awk '{print $1}'  # Example: 192.168.1.100
```

#### Step 2: Build Agents

**On PC-B, PC-C, etc:**
```bash
# Copy agent code
cd shadownet/agent

# Build agent with server address
export SHADOWNET_SERVER_URL=http://192.168.1.100:5000/beacon
export SHADOWNET_AES_KEY=<value from PC-A .env>
export SHADOWNET_REGISTRATION_SECRET=<value from PC-A .env>
export SHADOWNET_ENABLE_PERSISTENCE=false  # For non-Windows or testing

go build -o agent main.go
./agent

# Or run directly (no build):
go run main.go
```

#### Step 3: Verify Connection

Visit: http://192.168.1.100:5000 (on any PC on the network)
- Login: admin / <your admin password>
- Check "Agents" page
- You should see registered agents

---

## Custom Domain Setup

Deploy with automatic HTTPS using Let's Encrypt.

### Prerequisites

- Domain name (e.g., c2.example.com)
- DNS records pointing to your server IP
- Open ports: 80 (HTTP) and 443 (HTTPS)

### Steps

1. **Update DNS**:
   ```
   Type: A
   Name: c2.example.com
   Value: YOUR_SERVER_IP
   ```

2. **Update .env**:
   ```env
   CUSTOM_DOMAIN=c2.example.com
   LETSENCRYPT_EMAIL=your-email@example.com
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Wait for certificate**:
   ```bash
   # Check Traefik logs
   docker-compose logs -f reverse-proxy
   # Look for "Certificate Obtained Successfully"
   ```

5. **Access via HTTPS**:
   ```
   https://c2.example.com
   ```

6. **Agent configuration**:
   ```bash
   export SHADOWNET_SERVER_URL=https://c2.example.com/beacon
   go run main.go
   ```

---

## Troubleshooting

### Issue: Docker Compose fails to start

```bash
# Check syntax
docker-compose config

# View error logs
docker-compose logs server

# Common fixes:
# 1. Ensure .env file exists:
ls -la .env

# 2. Check SHADOWNET_AES_KEY is exactly 32 bytes (64 hex chars)
# 3. Verify Docker daemon is running:
docker ps
```

### Issue: Agent cannot connect to server

```bash
# On Agent PC, test connectivity:
# Windows:
Test-NetConnection -ComputerName SERVER_IP -Port 5000

# Linux/Mac:
nc -zv SERVER_IP 5000
curl http://SERVER_IP:5000/

# Check agent logs for error:
# Look for connection errors in console output
```

### Issue: Database file grows too large

```bash
# Database is in ./data/ directory
ls -lah ./data/shadownet.db

# Optional: cleanup old events from database
docker-compose exec server python -c "
import database
conn = database.get_db_connection()
# Add cleanup logic as needed
"
```

### Issue: Port 5000 already in use

```bash
# Change in .env:
SERVER_PORT=8080

# Or kill existing process:
# Windows:
netstat -ano | findstr :5000
taskkill /PID <pid> /F

# Linux/Mac:
lsof -i :5000
kill -9 <pid>
```

### Issue: Certificate renewal failing (Traefik)

```bash
# Check Traefik logs
docker-compose logs -f reverse-proxy

# Verify DNS is correctly set:
nslookup c2.example.com

# Manually renew:
docker-compose exec reverse-proxy \
  /traefik --api.insecure=true
```

---

## Code Changes for Docker

### Changes Made

All code has been updated for cross-platform Docker compatibility:

#### 1. **Agent (main.go)**

**Windows Persistence - Now Disabled in Docker**:
```go
// Before: Always checked GOOS
if runtime.GOOS != "windows" {
    return
}

// After: Can be disabled via environment variable
if enablePersistence := os.Getenv("SHADOWNET_ENABLE_PERSISTENCE"); enablePersistence == "false" {
    return  // Skip persistence in Docker
}
```

**Set in Docker containers**:
```bash
SHADOWNET_ENABLE_PERSISTENCE=false
```

#### 2. **Server (server_with_event.py)**

**Env File Loading - Now Configurable**:
```python
# Before: Hardcoded relative path
env_path = Path(__file__).parent.parent / 'agent' / 'agent.env'
load_dotenv(env_path)

# After: Uses environment variable or fallback
env_path = os.environ.get('SHADOWNET_ENV_FILE')
if env_path and Path(env_path).exists():
    load_dotenv(env_path)
# Falls back to default if not found
```

#### 3. **Database (database.py)**

**DB Path - Now Configurable**:
```python
# Before: Hardcoded path
DB_FILE = str(Path(__file__).parent.parent / "shadownet.db")

# After: Uses environment variable
_db_default = str(Path(__file__).parent.parent / "shadownet.db")
DB_FILE = os.environ.get('SHADOWNET_DB_PATH', _db_default)
```

### Environment Variables Used

| Component | Variable | Purpose |
|-----------|----------|---------|
| Agent | `SHADOWNET_SERVER_URL` | Server beacon endpoint |
| Agent | `SHADOWNET_ENABLE_PERSISTENCE` | Disable Windows persistence |
| Agent | `SHADOWNET_AES_KEY` | Encryption key |
| Agent | `SHADOWNET_REGISTRATION_SECRET` | Registration secret |
| Server | `SHADOWNET_DB_PATH` | Database file location |
| Server | `SHADOWNET_ENV_FILE` | Path to .env file |
| Server | Etc. | See [Environment Variables](#environment-variables) |

---

## Advanced Configuration

### Custom Ports

```env
# Override in .env
SERVER_PORT=8080
```

Then access at: http://localhost:8080

### Volume Mounts (Backup/Restore)

```bash
# Backup database
docker-compose exec server cp /app/data/shadownet.db /app/data/shadownet.db.backup

# Access data directory
ls -la ./data/

# Restore from backup
docker-compose exec server bash -c "cp /app/data/shadownet.db.backup /app/data/shadownet.db"
```

### Performance Tuning

```yaml
# In docker-compose.yml under 'server':
resources:
  limits:
    cpus: '2.0'
    memory: 2G
  reservations:
    cpus: '1.0'
    memory: 1G
```

### Multi-Instance Deployment

```bash
# Run multiple servers with different ports
docker-compose up -d -p instance1
docker-compose up -d -p instance2

# Access via:
# http://localhost:5000 (instance1)
# http://localhost:5001 (instance2)
```

---

## Next Steps

1. ✅ **Deploy Server**: Follow Quick Start above
2. ✅ **Build Agents**: Use environment variables from .env
3. ✅ **Test Connection**: Visit http://server:5000
4. ✅ **Setup Domain**: (Optional) Follow Custom Domain Setup
5. 📚 **Scale**: Run agents on multiple PCs

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting)
2. View logs: `docker-compose logs -f`
3. Check Docker: `docker ps` and `docker-compose config`
4. Review [Code Changes](#code-changes-for-docker) section

---

**Key Takeaway**: With the changes made, ShadowNet now:
- ✅ Runs on Docker (any OS)
- ✅ Works on any PC/laptop
- ✅ Uses environment variables (no hardcoded paths)
- ✅ Supports custom domains with HTTPS
- ✅ Disables platform-specific persistence in Docker
