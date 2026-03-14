<div align="center">

# >_ ShadowNet

### Command & Control Framework

[![Go](https://img.shields.io/badge/Agent-Go%201.22-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/Server-Python%203.11-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?logo=docker&logoColor=white)](https://docker.com/)
[![Tests](https://img.shields.io/badge/Tests-116%20passed-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A full-stack Command & Control framework built for cybersecurity research and adversary simulation.**

AES-256-GCM encrypted communications · Role-Based Access Control · Behavioral anomaly detection · Web-based operator dashboard

---

⚠️ **FOR AUTHORIZED USE ONLY** — See [DISCLAIMER.md](DISCLAIMER.md) before using this software.

</div>

---

## 📋 Table of Contents

- [Why I Built This](#why-i-built-this)
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Features](#features)
- [Security Design](#security-design)
- [Challenges & Design Decisions](#challenges--design-decisions)
- [Known Limitations & Future Scope](#known-limitations--future-scope)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Docker Deployment](#docker-deployment)
- [Development Journey](#development-journey)
- [Testing](#testing)
- [Configuration Reference](#configuration-reference)
- [License](#license)

---

## Why I Built This

I wanted to understand how real-world adversaries operate — not from textbooks, but by building the tools from scratch. Most cybersecurity courses teach you how to use existing frameworks (Metasploit, Cobalt Strike), but they rarely explain the engineering behind them: How does an agent hide its traffic? How does a server track hundreds of implants? How do you detect behavioral anomalies in beacon patterns?

I chose to build a **full C2 framework from the ground up** to answer these questions. The goal was to learn:

- **Network-level cryptography** — implementing AES-256-GCM in both Go and Python, not just calling an API
- **Protocol design** — designing a beacon protocol that handles registration, task delivery, ACK, and output reporting over a single encrypted channel
- **Defensive detection** — building the behavioral anomaly engine that defenders would use to catch exactly this kind of tool
- **Full-stack engineering** — writing production-quality code across two languages, with a database layer, test suite, web UI, and Docker deployment

Every line of code in this project was written with the mindset of understanding both the offensive and defensive perspective.

---

## Project Overview

ShadowNet is a modular Command & Control system with two components:

**Agent (Go)** — A lightweight binary that runs on target systems. It beacons home at randomized intervals, executes tasked commands, and reports results — all over AES-256-GCM encrypted HTTPS. It persists across reboots using OS-native mechanisms (Windows Registry) and maintains a unique identity stored on disk.

**Server (Python/Flask)** — A web application that manages connected agents, queues tasks, tracks incident telemetry, and provides operators with a real-time dashboard. It enforces role-based access control across four privilege levels and runs a background behavioral analysis engine that flags anomalous agent behavior — the same kind of detection that a SOC analyst or EDR would perform.

The system is deployed via Docker on Render with a custom domain and automatic TLS.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        OPERATOR (Browser)                          │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Dashboard  │  │  Admin Panel │  │   Command Library        │  │
│  │  (agents,    │  │  (users,     │  │   (templates,            │  │
│  │   tasks,     │  │   RBAC,      │  │    favorites,            │  │
│  │   incidents) │  │   settings)  │  │    usage tracking)       │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘  │
│         └─────────────────┼──────────────────────┘                 │
│                           │ HTTPS                                  │
└───────────────────────────┼────────────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────────────┐
│                    SERVER (Python / Flask)                         │
│                           │                                        │
│  ┌────────────┐  ┌───────▼────────┐  ┌─────────────────────┐       │
│  │   RBAC     │  │  Beacon Route  │  │  Incident Engine    │       │
│  │ Decorators │  │  /beacon POST  │  │  (jitter anomaly,   │       │
│  │ (viewer,   │  │  AES-GCM       │  │   task burst,       │       │
│  │  operator, │  │  decrypt →     │  │   suspicious cmd,   │       │
│  │  admin)    │  │  process →     │  │   agent offline)    │       │
│  │            │  │  encrypt       │  │                     │       │
│  └────────────┘  └───────┬────────┘  └─────────┬───────────┘       │
│                          │                     │                   │
│                  ┌───────▼──────────────────────▼───────────┐      │
│                  │              SQLite Database             │      │
│                  │  users · agents · tasks · incidents ·    │      │
│                  │  events · command_templates · agent_stat │      │
│                  └──────────────────────────────────────────┘      │
└───────────────────────────┬────────────────────────────────────────┘
                            │ AES-256-GCM Encrypted
                            │ Beacon Traffic (HTTPS)
┌───────────────────────────┼────────────────────────────────────────┐
│                     AGENT (Go Binary)                              │
│                           │                                        │
│  ┌────────────┐  ┌───────▼────────┐  ┌──────────────────┐          │
│  │ Persistent │  │  Beacon Loop   │  │ Command Executor │          │
│  │ Agent ID   │  │  (jitter ±2s)  │  │ (cmd/sh, cd,     │          │
│  │ (.agent_id)│  │  encrypt →     │  │  working dir)    │          │
│  │            │  │  POST →        │  │                  │          │
│  └────────────┘  │  decrypt       │  └──────────────────┘          │
│                  └────────────────┘  ┌──────────────────┐          │
│  ┌────────────┐                      │ Reliable Task    │          │
│  │ Windows    │                      │ ACK + Dedup      │          │
│  │ Persistence│                      │ (exactly-once)   │          │
│  │ (Registry) │                      └──────────────────┘          │
│  └────────────┘                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Features

### 🔐 Encryption

- **AES-256-GCM** end-to-end encryption on all agent-server traffic
- Random 12-byte nonce per message — no nonce reuse
- Shared key configured at build time or via environment variables
- Encrypted payload transported as base64 over JSON/HTTPS

### 🎛️ Agent Capabilities

- Auto-registration with shared secret verification
- Persistent agent identity (survives reboots — UUID stored on disk)
- System fingerprinting (hostname, OS, architecture, IP, username)
- Jitter-based beacon interval (base ± 2s) to evade static timing analysis
- Cross-platform command execution (`cmd /C` on Windows, `sh -c` on Linux)
- Persistent working directory across commands (supports `cd`)
- Windows startup persistence (binary copy + Registry Run key)
- Startup guard — refuses to run if secrets are still default values

### 📡 Task System

- Reliable delivery: agent ACKs on receipt, server tracks lifecycle
- Exactly-once execution via task_id deduplication
- Task states: `queued → sent → ack → completed`
- Full stdout/stderr capture in output reports

### 🕵️ Behavioral Incident Engine

The server includes a detection engine — the same type of analysis a defender or EDR would run:

| Detection | What It Catches |
|-----------|----------------|
| Beacon Jitter Anomaly | Irregular heartbeat intervals (network issues, agent tampering) |
| Excessive Task Activity | Burst of 5+ tasks in 30 seconds (possible automation/scripting) |
| Suspicious Command Pattern | Known offensive tool keywords (`mimikatz`, `procdump`, `net user`, etc.) |
| Repeated Task Failures | Consecutive failed command executions |
| Agent Unresponsive | Silent agents that stop beaconing (crash, kill, network loss) |

Each agent gets a computed **risk score** based on open incident count and severity.

### 👥 Role-Based Access Control

| Role | Permissions |
|------|------------|
| `viewer` | Read-only access to dashboard, agents, tasks |
| `operator` | Execute commands, manage tasks |
| `developer` | API access, command template management |
| `admin` | Full control — user management, DB operations, access control |

Enforced at the decorator level — every route is protected, no route left unguarded.

### 🖥️ Web Dashboard

- Real-time agent status with online/offline/stale indicators
- Agent detail view (identity, task history, system info)
- Command template library with favorites and usage tracking
- Security incident timeline with severity and status
- Admin panel for user CRUD, system diagnostics, and DB management
- IP-based access control with configurable whitelist

---

## Security Design

### Encryption Protocol Flow

```
Agent                                    Server
  │                                        │
  │  1. Build JSON payload                 │
  │  2. AES-256-GCM encrypt (random nonce) │
  │  3. base64(nonce + ciphertext)         │
  │  4. POST /beacon {"data": "..."}       │
  │ ─────────────────────────────────────► │
  │                                        │  5. Decrypt with shared key
  │                                        │  6. Process + queue response
  │                                        │  7. Encrypt response (new nonce)
  │  8. Parse + decrypt response           │
  │ ◄───────────────────────────────────── │
```

### Defense-in-Depth Summary

| Layer | Implementation |
|-------|---------------|
| Transport Encryption | AES-256-GCM with 12-byte random nonce per message |
| Authentication | `secrets.compare_digest` for registration (timing-safe) |
| Password Storage | bcrypt with per-user salt; dummy hash on unknown users (prevents enumeration) |
| SQL Injection | 100% parameterized queries — zero string concatenation near SQL |
| Session Security | Signed Flask cookies with cryptographic `SECRET_KEY` |
| Command Safety | Regex blocklist prevents self-destructive agent commands (`taskkill`, `rm -rf`, etc.) |
| Access Control | RBAC enforced via decorators on every route |
| Agent Startup | Binary refuses to run if secrets match compiled-in sentinel values |

---

## Challenges & Design Decisions

### 1. AES-GCM Interoperability (Go ↔ Python)

The hardest part early on was getting Go's `crypto/cipher` and Python's `cryptography` library to produce compatible ciphertext. The nonce prepending order, base64 encoding, and associated data handling had to be byte-identical on both sides. I spent two days debugging a single-byte offset in the nonce slice.

**Decision:** Nonce is always prepended (not appended) to the ciphertext before base64 encoding. No associated data (AAD). This convention is documented and enforced by tests.

### 2. Agent State Persistence Across Server Restarts

Initially, the incident engine stored per-agent behavioral state (heartbeat history, task timestamps, failure counts) in an in-memory Python dictionary. Every server restart lost all state, causing false-positive "new agent" incidents.

**Decision:** Added an `agent_state` table to SQLite that serializes the behavioral state as JSON. The incident engine loads state from DB on first access and writes it back after every update.

### 3. Task Reliability — ACK and Exactly-Once Execution

In early stages, tasks would get lost if the agent crashed between receiving a task and reporting output. The server had no way to know if a task was actually executed.

**Decision:** Implemented a three-phase protocol:
1. Server sends task → marks it `sent`
2. Agent immediately ACKs with `task_id` → server marks `ack`
3. Agent executes and reports output → server marks `completed`

Plus a client-side `executedTasks` map that prevents re-execution if the same task is received again.

### 4. Concurrent SQLite Access Under Load

SQLite doesn't handle concurrent writes well. The background heartbeat monitor thread was competing with Flask request handlers for write locks, causing `database is locked` errors during tests.

**Decision:** Enabled WAL (Write-Ahead Logging) mode, increased connection timeout to 15s, and in the test suite, the heartbeat monitor's `create_incident` is replaced with a no-op to eliminate write contention entirely.

### 5. Test Isolation

Early tests were flaky because they shared a single database file. One test's admin user creation would interfere with another test's auth check.

**Decision:** Each test gets its own temporary SQLite file via the `reset_db` fixture in `conftest.py`. The file is created with `tempfile.mkstemp`, initialized with the full schema, and cleaned up after. Zero cross-test contamination.

---

## Known Limitations & Future Scope

| Area | Current State | What Could Be Added |
|------|--------------|-------------------|
| **Transport** | AES-256-GCM over HTTPS | Domain fronting, DNS-over-HTTPS beaconing, certificate pinning |
| **Agent Evasion** | Basic jitter + persistence | Process injection, syscall-level execution, AMSI bypass |
| **DDoS Protection** | Not implemented | Rate limiting, connection throttling, IP reputation scoring |
| **Database** | SQLite (single-file) | PostgreSQL or Redis for horizontal scaling |
| **Dashboard** | Server-rendered Jinja2 | WebSocket-based real-time updates, React/Vue SPA |
| **Agent Platforms** | Windows primary, Linux basic | macOS persistence, mobile agents |
| **Logging** | Print statements | Structured logging (JSON), log aggregation (ELK/Loki) |
| **Multi-tenancy** | Single-team | Namespaced agent groups, team-scoped access |

> These limitations are intentional scoping decisions, not oversights. The project was built to demonstrate core C2 concepts deeply rather than cover every feature superficially.

---

## Tech Stack

| Component | Technology | Why This Choice |
|-----------|-----------|----------------|
| **Agent** | Go 1.22 | Compiles to a single static binary, cross-platform, fast startup |
| **Server** | Python 3.11 / Flask 3.1 | Rapid development, rich crypto library ecosystem |
| **Database** | SQLite 3 (WAL mode) | Zero-config, embedded, sufficient for single-server C2 |
| **Encryption** | AES-256-GCM | Industry standard authenticated encryption; Go + Python both support it natively |
| **Auth** | bcrypt | Slow-by-design hash resists GPU brute-force |
| **Frontend** | Bootstrap 5 / Jinja2 | Server-rendered, no build step needed |
| **Deployment** | Docker / Render.com | Reproducible builds, free-tier cloud hosting |
| **Testing** | pytest (116 tests) | Isolated temp-DB per test, full API coverage |

---

## Project Structure

```
ShadowNet/
├── agent/                          # Go agent
│   ├── main.go                     # Production agent (475 lines)
│   ├── go.mod / go.sum             # Go module dependencies
│   └── stages/                     # Development stage snapshots (14 files)
│
├── server/                         # Python/Flask server
│   ├── server_with_event.py        # Main server application (1240+ lines)
│   ├── database.py                 # SQLite data access layer
│   ├── incident_engine.py          # Behavioral anomaly detection engine
│   ├── events.py                   # Event handling
│   ├── requirements.txt            # Python dependencies
│   ├── Frontend/
│   │   ├── templates/              # 12 Jinja2 HTML templates
│   │   └── static/                 # CSS, JS, logo
│   ├── stages/                     # Server development stage snapshots (13 files)
│   └── tests/                      # pytest suite (116 tests)
│       ├── conftest.py             # Fixtures: isolated DB, crypto helpers
│       ├── test_database.py
│       ├── test_auth.py
│       ├── test_api.py
│       ├── test_admin.py
│       └── test_beacon.py
│
├── Core Documentation/             # 20+ detailed design documents
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Local development setup
├── render.yaml                     # Render.com deployment blueprint
├── .dockerignore / .gitignore
├── LICENSE                         # MIT
├── DISCLAIMER.md                   # Ethical use policy
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+ and pip
- Go 1.22+ (for building the agent)
- Docker (optional, for containerized deployment)

### 1. Clone & Configure

```bash
git clone https://github.com/INFINITY-0694/ShadowNet.git
cd ShadowNet
```

Create `agent/agent.env` (not committed — contains secrets):

```env
SHADOWNET_AES_KEY=your_32_character_key_here______
SHADOWNET_REGISTRATION_SECRET=your_secret_here
SHADOWNET_SERVER_URL=http://127.0.0.1:8080/beacon
```

### 2. Start the Server

```bash
cd server
pip install -r requirements.txt

# Set environment variables (or create a root .env file)
export SHADOWNET_AES_KEY="your_32_character_key_here______"
export SHADOWNET_FLASK_SECRET="your_flask_secret_key"
export SHADOWNET_REGISTRATION_SECRET="your_secret_here"
export SHADOWNET_ADMIN_PASSWORD="your_admin_password"

python server_with_event.py
```

Server runs at `http://127.0.0.1:8080`. Login: `admin` / your configured password.

### 3. Run the Agent

```bash
cd agent
go run main.go
```

Agent loads config from `agent.env`, registers with the server, and starts beaconing.

### 4. Build a Standalone Agent Binary

```bash
go build -ldflags="-X main.serverURL=https://your-server.com/beacon \
                    -X main.registrationSecret=YOUR_SECRET \
                    -X main.aesKeyStr=YOUR_32_BYTE_KEY" \
         -o agent.exe main.go
```

---

## Docker Deployment

### Local

```bash
cp .env.docker .env   # Edit with your secrets
docker-compose up -d
```

### Production (Docker Hub → Render)

```bash
docker build -t yourdockerhub/shadownet:latest .
docker push yourdockerhub/shadownet:latest
```

On Render: **New → Web Service → Existing Docker Image** → set environment variables → deploy.

Custom domain + auto-TLS configured via `render.yaml`.

---

## Development Journey

ShadowNet was built incrementally across **18 stages**. Each stage introduced one new capability, and both agent and server snapshots are preserved in `agent/stages/` and `server/stages/`.

| Stage | What Was Added |
|-------|---------------|
| 01 | Basic beacon — agent sends JSON, server receives it |
| 02 | System info collection (hostname, OS, arch) |
| 03 | Beacon loop with 10-second interval |
| 04 | Command execution and output reporting |
| 05 | Jitter-based randomized sleep |
| 06 | HTTP-based operator command dispatch |
| 07 | **AES-256-GCM encryption** on all traffic |
| 10 | Persistent UUID agent identity |
| 13 | Agent state machine (IDLE → TASK → REPORT) |
| 16 | **Reliable delivery** — ACK + exactly-once execution + SQLite |
| 17 | Agent offline detection + registration secret enforcement |
| 17b | **User authentication** — bcrypt login, sessions, Windows persistence |
| 18 | **Behavioral incident engine** — jitter anomaly, task burst, suspicious commands |

*Stages 8–9, 11–12, 14–15 were incremental refactors absorbed into the next major stage.*

---

## Testing

```bash
cd server
python -m pytest tests/ -v
```

**116 tests** across 5 modules:

| Module | Coverage |
|--------|----------|
| `test_database.py` | Schema creation, CRUD, agent state persistence, edge cases |
| `test_auth.py` | Login, logout, RBAC enforcement, session handling |
| `test_api.py` | Task API, agent listing, command templates, favorites |
| `test_admin.py` | User management, DB reset, access control settings |
| `test_beacon.py` | Encrypted beacon flow, registration, heartbeat, task delivery |

**Test architecture:** Each test gets an isolated temporary SQLite database. WAL mode enabled. Background threads are mocked. Crypto helpers (`make_beacon_payload`, `decrypt_beacon_response`) test the full encryption pipeline.

---

## Configuration Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SHADOWNET_AES_KEY` | ✅ | 32-character AES key (must match agent and server) |
| `SHADOWNET_FLASK_SECRET` | ✅ | Flask session signing key |
| `SHADOWNET_REGISTRATION_SECRET` | ✅ | Agent registration shared secret |
| `SHADOWNET_ADMIN_PASSWORD` | ✅ | Initial admin user password |
| `SHADOWNET_DB_PATH` | ❌ | SQLite path (default: `./shadownet.db`) |
| `PORT` | ❌ | Server port (default: `8080`, auto-set by Render) |

### Generate Secure Keys

```bash
python -c "import os; print(os.urandom(32).hex()[:32])"           # AES key
python -c "import secrets; print(secrets.token_hex(32))"           # Flask secret
python -c "import secrets; print(secrets.token_hex(16))"           # Registration secret
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This software is built for **educational and authorized security research only**. Unauthorized use against systems you do not own or have explicit permission to test is illegal and unethical. The author is not responsible for any misuse. See [DISCLAIMER.md](DISCLAIMER.md) for the full policy.

---

<div align="center">

**Built by [Divy Soni](https://github.com/INFINITY-0694)**

</div>
