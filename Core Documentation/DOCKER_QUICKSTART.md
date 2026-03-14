# Docker Deployment Quick Reference

> **Purpose**: Deploy ShadowNet on any PC/laptop via Docker

## What's Changed

✅ **Agent (main.go)**
- Windows persistence now optional (disabled in Docker via `SHADOWNET_ENABLE_PERSISTENCE=false`)
- All config via environment variables

✅ **Server (server_with_event.py)**
- Env file loading now uses `SHADOWNET_ENV_FILE` variable (Docker-compatible)
- Database path configurable via `SHADOWNET_DB_PATH`

✅ **Configuration**
- `.env.docker` - Example environment file
- `Dockerfile` - Multi-stage Python image
- `docker-compose.yml` - Full stack (server + optional Traefik)
- `DOCKER_DEPLOYMENT.md` - Complete deployment guide

---

## Quick 5-Minute Setup

### 1. Generate Keys
```bash
python -c "import secrets; print('AES:', secrets.token_hex(32)); print('Secret:', secrets.token_hex(16))"
```

### 2. Create `.env`
```bash
cp .env.docker .env
# Edit .env with your generated keys
```

### 3. Start Server
```bash
docker-compose up -d
```

### 4. Access Web UI
```
http://localhost:5000
Login: admin / <your password from .env>
```

### 5. Build & Run Agent
```bash
export SHADOWNET_SERVER_URL=http://localhost:5000/beacon
export SHADOWNET_AES_KEY=<from .env>
export SHADOWNET_REGISTRATION_SECRET=<from .env>
export SHADOWNET_ENABLE_PERSISTENCE=false

cd agent
go run main.go
```

---

## Multi-PC Setup

**Server PC** (run once):
```bash
docker-compose up -d
ip addr show  # Get server IP (e.g., 192.168.1.100)
```

**Agent PCs** (on different machines):
```bash
export SHADOWNET_SERVER_URL=http://192.168.1.100:5000/beacon
export SHADOWNET_AES_KEY=<same key as server>
export SHADOWNET_REGISTRATION_SECRET=<same as server>
export SHADOWNET_ENABLE_PERSISTENCE=false

cd agent
go run main.go
```

---

## Custom Domain (HTTPS)

Update `.env`:
```env
CUSTOM_DOMAIN=c2.example.com
LETSENCRYPT_EMAIL=you@example.com
```

Then:
```bash
docker-compose up -d
# Wait for certificate, then access https://c2.example.com
```

---

## Useful Commands

```bash
# Start server
docker-compose up -d

# View logs
docker-compose logs -f server

# Stop server
docker-compose down

# Remove data (CAREFUL!)
docker-compose down -v

# Check running containers
docker-compose ps

# Database backup
cp data/shadownet.db data/shadownet.db.backup
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Connection refused** | Check server IP: `docker-compose logs server` |
| **Port 5000 in use** | Change `SERVER_PORT=8080` in .env |
| **DB lock error** | Restart: `docker-compose restart server` |
| **Agent won't connect** | Check `SHADOWNET_AES_KEY` matches |
| **Missing .env** | Run: `cp .env.docker .env` |

---

## Files Added/Modified

```
e:\shadowNet\
├── Dockerfile                    # New - Python container image
├── docker-compose.yml            # New - Service orchestration
├── .env.docker                   # New - Example configuration
├── .gitignore                    # Updated - Ignore .env and data/
├── DOCKER_DEPLOYMENT.md          # New - Full deployment guide
│
├── agent/main.go                 # Modified - Configurable persistence
├── server/server_with_event.py   # Modified - Configurable env path
├── server/database.py            # Modified - Configurable DB path
│
└── data/                         # New filesystem (created at runtime)
    ├── shadownet.db              # Database file
    └── agent.env                 # Optional .env file
```

---

## Environment Variable Reference

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `SHADOWNET_AES_KEY` | YES | `a1b2c3d4...` | Must be exactly 64 hex chars |
| `SHADOWNET_FLASK_SECRET` | YES | `f1e2d3c4...` | Min 32 bytes |
| `SHADOWNET_REGISTRATION_SECRET` | YES | `1a2b3c4d...` | Used by agents to register |
| `SHADOWNET_ADMIN_PASSWORD` | NO | `ChangeMe123!` | Default: admin123 |
| `SERVER_PORT` | NO | `5000` | HTTP listen port |
| `SHADOWNET_DB_PATH` | NO | `/app/data/shadownet.db` | Database location |
| `CUSTOM_DOMAIN` | NO | `c2.example.com` | For HTTPS setup |
| `LETSENCRYPT_EMAIL` | NO | `admin@example.com` | For HTTPS certs |

---

## Next Steps

1. **Read full guide**: See `DOCKER_DEPLOYMENT.md`
2. **Deploy**: Follow "Quick 5-Minute Setup" above
3. **Agents**: Build agents with server credentials
4. **Scale**: Run agents on multiple PCs

---

**Status**: ✅ Ready for production Docker deployment on any PC/laptop
