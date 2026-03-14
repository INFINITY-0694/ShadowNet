<div align="center">

# >_ ShadowNet C2

### Command & Control Framework

[![Go](https://img.shields.io/badge/Agent-Go%201.22-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/Server-Python%203.11-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?logo=docker&logoColor=white)](https://docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A full-stack Command & Control framework built for cybersecurity education and research.**

AES-256-GCM encrypted communications · Role-Based Access Control · Behavioral anomaly detection · Web dashboard

---

⚠️ **EDUCATIONAL USE ONLY** — See [DISCLAIMER.md](DISCLAIMER.md) before using this software.

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Development Stages](#development-stages)
- [Testing](#testing)
- [Security Design](#security-design)
- [Configuration Reference](#configuration-reference)
- [License](#license)

---

## Overview

ShadowNet is a modular Command & Control (C2) framework developed as a Semester 6 cybersecurity engineering project. It demonstrates real-world C2 architecture patterns used in red-team operations, penetration testing, and adversary simulation — all within a controlled, ethical, and educational context.

The system consists of two components:

- **Agent** — A lightweight Go binary that runs on target systems, beacons home periodically, executes tasked commands, and reports results over encrypted channels.
- **Server** — A Python/Flask application that manages connected agents, queues tasks, detects behavioral anomalies, and provides operators with a modern web dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OPERATOR (Browser)                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Dashboard   │  │  Admin Panel │  │   Command Library        │  │
│  │   (agents,    │  │  (users,     │  │   (templates,            │  │
│  │    tasks,     │  │   RBAC,      │  │    favorites,            │  │
│  │    incidents) │  │   settings)  │  │    usage tracking)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         └─────────────────┼──────────────────────┘                  │
│                           │ HTTPS                                   │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────────┐
│                    SERVER (Python/Flask)                             │
│                           │                                         │
│  ┌────────────┐  ┌───────▼────────┐  ┌─────────────────────┐       │
│  │   RBAC     │  │  Beacon Route  │  │  Incident Engine    │       │
│  │ Decorators │  │  /beacon POST  │  │  (jitter anomaly,   │       │
│  │ (viewer,   │  │  AES-GCM      │  │   task burst,       │       │
│  │  operator, │  │  decrypt/      │  │   suspicious cmd,   │       │
│  │  admin)    │  │  encrypt       │  │   agent offline)    │       │
│  └────────────┘  └───────┬────────┘  └─────────┬───────────┘       │
│                          │                      │                   │
│                  ┌───────▼──────────────────────▼───────────┐       │
│                  │              SQLite Database              │       │
│                  │  users · agents · tasks · incidents ·    │       │
│                  │  events · command_templates · agent_state │       │
│                  └──────────────────────────────────────────┘       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ AES-256-GCM
                            │ Encrypted Beacons
┌───────────────────────────┼─────────────────────────────────────────┐
│                     AGENT (Go Binary)                               │
│                           │                                         │
│  ┌────────────┐  ┌───────▼────────┐  ┌──────────────────┐          │
│  │ Persistent │  │  Beacon Loop   │  │ Command Executor │          │
│  │ Agent ID   │  │  (jitter ±2s)  │  │ (cmd/sh, cd,     │          │
│  │ (.agent_id)│  │  AES-GCM       │  │  working dir)    │          │
│  └────────────┘  │  encrypt/      │  └──────────────────┘          │
│                  │  decrypt       │  ┌──────────────────┐          │
│  ┌────────────┐  └────────────────┘  │ Task ACK +       │          │
│  │ Persistence│                      │ Dedup (task_id)  │          │
│  │ (Windows   │                      └──────────────────┘          │
│  │  Registry) │                                                     │
│  └────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Features

### 🔐 Encryption & Security

- **AES-256-GCM** end-to-end encrypted agent-server communication
- **Timing-safe** secret comparison (`secrets.compare_digest`) — prevents timing attacks
- **bcrypt** password hashing with dummy-hash on unknown users — prevents user enumeration
- **Parameterized SQL queries** throughout — zero SQL injection surface
- **Command safety filter** — regex blocklist prevents agents from executing self-destructive commands (`taskkill`, `rm -rf`, `del /f`, etc.)
- **Startup guard** — agent binary refuses to run if secrets are still default sentinels

### 🎛️ Agent Management

- Auto-registration with shared secret
- Persistent agent identity (`.agent_id` file survives reboots)
- System info collection (hostname, OS, architecture, IP, username)
- Real-time status tracking (online/offline/stale)
- Agent alias system (A1, A2, A3…) for easy identification

### 📡 Task System

- Reliable delivery with **ACK on receipt** and **exactly-once execution**
- Task lifecycle tracking: `queued → sent → ack → completed`
- Command output reporting with full stdout/stderr capture
- Task history per agent with timestamps

### 🕵️ Behavioral Incident Engine

- **Beacon Jitter Anomaly** — detects irregular heartbeat intervals
- **Excessive Task Activity** — flags task bursts (5+ in 30 seconds)
- **Suspicious Command Pattern** — matches known offensive tool keywords
- **Repeated Task Failures** — tracks consecutive failed executions
- **Agent Unresponsive** — background heartbeat monitor flags silent agents
- Risk scoring per agent based on open incident count and severity

### 👥 Role-Based Access Control (RBAC)

| Role | Permissions |
|------|------------|
| `viewer` | View dashboard, agents, tasks (read-only) |
| `operator` | All viewer permissions + execute commands, manage tasks |
| `developer` | All operator permissions + API access, command templates |
| `admin` | Full access — user management, DB reset, access control |

### 🖥️ Web Dashboard

- Modern dark-themed UI with real-time agent status
- Agent detail view with task history and identity info
- Command template library with favorites and usage tracking
- Security incident timeline with severity indicators
- Admin panel for user management and system configuration
- IP-based access control with whitelist management

### 🐋 Deployment

- Multi-stage Docker build (Python 3.11-slim)
- Render.com deployment with custom domain support
- Docker Compose for local development
- Environment-based configuration (no hardcoded secrets)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Agent** | Go 1.22 — single static binary, cross-platform |
| **Server** | Python 3.11, Flask 3.1, Werkzeug 3.1 |
| **Database** | SQLite 3 with WAL mode |
| **Encryption** | AES-256-GCM (Go `crypto/cipher` + Python `cryptography`) |
| **Auth** | bcrypt, Flask sessions |
| **Frontend** | Bootstrap 5, Jinja2 templates, vanilla JS |
| **Deployment** | Docker, Render.com |
| **Testing** | pytest (116 tests), isolated temp-DB per test |

---

## Project Structure

```
shadowNet/
├── agent/                          # Go agent
│   ├── main.go                     # Production agent (475 lines)
│   ├── go.mod / go.sum             # Go module dependencies
│   └── stages/                     # 14 development stage snapshots
│       ├── stage01_basic_beacon.go
│       ├── stage02_sysinfo.go
│       ├── ...
│       └── stage18_Behavioral_stealth.go
│
├── server/                         # Python/Flask server
│   ├── server_with_event.py        # Main server application (1240 lines)
│   ├── database.py                 # SQLite data access layer
│   ├── incident_engine.py          # Behavioral anomaly detection
│   ├── events.py                   # Event handling
│   ├── requirements.txt            # Python dependencies
│   ├── Frontend/
│   │   ├── templates/              # Jinja2 HTML templates
│   │   │   ├── login.html
│   │   │   ├── dashboard.html
│   │   │   ├── admin_panel.html
│   │   │   ├── agent_detail.html
│   │   │   ├── commands_library.html
│   │   │   └── ...
│   │   └── static/                 # CSS, JS, images
│   │       ├── style.css
│   │       ├── modern-theme.css
│   │       ├── app.js
│   │       └── logo.png
│   ├── stages/                     # 13 server development stage snapshots
│   │   ├── stage01_basic_beacon.py
│   │   ├── ...
│   │   └── stage18_behavioral_stealth.py
│   └── tests/                      # pytest test suite (116 tests)
│       ├── conftest.py
│       ├── test_database.py
│       ├── test_auth.py
│       ├── test_api.py
│       ├── test_admin.py
│       └── test_beacon.py
│
├── Core Documentation/             # Detailed project documentation
│   ├── Project_overview.md
│   ├── architecture.md
│   ├── RBAC.md
│   ├── server_documentation.md
│   └── ...  (20+ files)
│
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Local dev with Traefik
├── render.yaml                     # Render.com deployment blueprint
├── .dockerignore
├── .gitignore
├── LICENSE
├── DISCLAIMER.md
└── README.md                       # ← You are here
```

---

## Quick Start

### Prerequisites

- **Python 3.11+** and `pip`
- **Go 1.22+** (for building the agent)
- **Docker** (optional, for containerized deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/shadowNet.git
cd shadowNet
```

### 2. Configure Secrets

```bash
# Create the agent config file
cp agent/agent.env.example agent/agent.env
```

Edit `agent/agent.env` with your values:

```env
SHADOWNET_AES_KEY=your_32_character_aes_key_here!!
SHADOWNET_REGISTRATION_SECRET=your_registration_secret
SHADOWNET_SERVER_URL=http://127.0.0.1:8080/beacon
```

### 3. Start the Server

```bash
cd server
pip install -r requirements.txt

# Set environment variables
export SHADOWNET_AES_KEY="your_32_character_aes_key_here!!"
export SHADOWNET_FLASK_SECRET="your_flask_secret_key"
export SHADOWNET_REGISTRATION_SECRET="your_registration_secret"
export SHADOWNET_ADMIN_PASSWORD="your_admin_password"

python server_with_event.py
```

Server starts at `http://127.0.0.1:8080`. Login with `admin` / your configured password.

### 4. Run the Agent

```bash
cd agent
go run main.go
```

The agent loads secrets from `agent.env`, registers with the server, and begins beaconing.

### 5. Build a Production Agent Binary

```bash
cd agent
go build -ldflags="-X main.serverURL=https://your-server.com/beacon \
                    -X main.registrationSecret=YOUR_SECRET \
                    -X main.aesKeyStr=YOUR_32_BYTE_AES_KEY" \
         -o agent.exe main.go
```

---

## Docker Deployment

### Local (Docker Compose)

```bash
# Create .env from template
cp .env.docker .env
# Edit .env with your secrets

docker-compose up -d
```

### Production (Render.com via Docker Hub)

```bash
# Build and push
docker build -t yourdockerhub/shadownet:latest .
docker push yourdockerhub/shadownet:latest
```

Then on [Render Dashboard](https://dashboard.render.com):
1. **New → Web Service → Existing Docker Image**
2. Image: `docker.io/yourdockerhub/shadownet:latest`
3. Set environment variables (AES key, Flask secret, registration secret, admin password)
4. Add custom domain under Settings → Custom Domains

---

## Development Stages

ShadowNet was built incrementally across **18 development stages**, each introducing a new capability. Both agent and server stage snapshots are preserved in `agent/stages/` and `server/stages/`.

| Stage | Agent Feature | Server Feature |
|-------|--------------|----------------|
| 01 | Basic HTTP POST | Receive JSON beacon |
| 02 | System info collection | Store hostname/OS/arch |
| 03 | Beacon loop (10s interval) | Track last_seen timestamp |
| 04 | Command execution + output | Task queue + output display |
| 05 | Jitter-based sleep | Beacon interval monitoring |
| 06 | — | HTTP command dispatch routes |
| 07 | AES-256-GCM encryption | Encrypted request/response |
| 10 | Persistent UUID agent_id | Agent identity + registration |
| 13 | State machine (IDLE/TASK/REPORT) | Task lifecycle tracking |
| 16 | Task ACK + exactly-once execution | Reliable delivery + SQLite |
| 17 | — | Offline detection + registration secret |
| 17b | Windows persistence (registry) | bcrypt auth + login sessions |
| 18 | Behavioral stealth awareness | Incident engine + event stream |

---

## Testing

The server includes a comprehensive pytest suite with **116 automated tests**:

```bash
cd server
python -m pytest tests/ -v
```

### Test Coverage

| Module | Tests | Covers |
|--------|-------|--------|
| `test_database.py` | DB schema, CRUD operations, agent state persistence |
| `test_auth.py` | Login, logout, session handling, RBAC enforcement |
| `test_api.py` | Task creation, agent listing, command templates |
| `test_admin.py` | User management, DB reset, access control |
| `test_beacon.py` | Encrypted beacon flow, registration, heartbeat |

### Test Architecture

- Each test gets an **isolated SQLite temp database** (no cross-test contamination)
- WAL mode enabled for concurrent read safety
- Background heartbeat monitor muted during tests (prevents lock contention)
- Crypto helpers (`make_beacon_payload`, `decrypt_beacon_response`) for testing encrypted flows

---

## Security Design

### Encryption Protocol

```
Agent                                    Server
  │                                        │
  │  1. JSON payload                       │
  │  2. AES-256-GCM encrypt (random nonce) │
  │  3. base64(nonce + ciphertext)         │
  │  4. POST /beacon {data: "..."}         │
  │ ─────────────────────────────────────► │
  │                                        │
  │  5. Decrypt with shared key            │
  │  6. Process beacon                     │
  │  7. Encrypt response (new nonce)       │
  │  8. Return {data: "..."}              │
  │ ◄───────────────────────────────────── │
```

### Defense-in-Depth

| Layer | Mechanism |
|-------|-----------|
| Transport | AES-256-GCM (12-byte nonce, authenticated encryption) |
| Authentication | Shared registration secret (timing-safe compare) |
| Password Storage | bcrypt with per-user salt |
| User Enumeration | Dummy bcrypt hash computed on unknown usernames |
| SQL Injection | 100% parameterized queries |
| Session Security | Signed Flask cookies with `SECRET_KEY` |
| Command Safety | Regex blocklist prevents self-destructive agent commands |
| Access Control | RBAC enforced at decorator level on every route |

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SHADOWNET_AES_KEY` | ✅ | 32-character AES encryption key (must match agent) |
| `SHADOWNET_FLASK_SECRET` | ✅ | Flask session signing key (any length) |
| `SHADOWNET_REGISTRATION_SECRET` | ✅ | Agent registration shared secret (must match agent) |
| `SHADOWNET_ADMIN_PASSWORD` | ✅ | Initial admin user password |
| `SHADOWNET_DB_PATH` | ❌ | SQLite database path (default: `./shadownet.db`) |
| `PORT` | ❌ | Server port (default: `8080`, auto-set by Render) |

### Generate Secure Keys

```bash
# AES key (32 characters)
python -c "import os; print(os.urandom(32).hex()[:32])"

# Flask secret
python -c "import secrets; print(secrets.token_hex(32))"

# Registration secret
python -c "import secrets; print(secrets.token_hex(16))"
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This software is developed **strictly for educational and authorized security research purposes**. Unauthorized use of this tool against systems you do not own or have explicit permission to test is **illegal** and **unethical**. The developers are not responsible for any misuse. See [DISCLAIMER.md](DISCLAIMER.md) for the full ethical use policy.

---

<div align="center">

**Built with 🔐 by Divy Soni**

*Semester 6 — Cybersecurity Engineering*

</div>
