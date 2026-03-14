# ShadowNet — Project Overview

> A full-stack Command & Control (C2) framework built as a Semester 6 cybersecurity engineering project.  
> Designed for authorized red-team simulation and educational study of C2 architecture, behavioral detection, and secure communications.

---

## What Is ShadowNet?

ShadowNet is a self-contained C2 platform consisting of:

- A **Go agent** that runs on a target machine, beacons home on a jittered timer, and executes commands sent by the server
- A **Python/Flask server** that manages agents, queues tasks, processes events, detects behavioral anomalies, and serves a web dashboard
- A **role-based web UI** for operators, administrators, and developers

The entire communication channel is encrypted with **AES-256-GCM**. All operator actions require authentication. Every significant event is logged, correlated, and fed into an automated incident detection engine.

---

## Key Features

| Feature | Detail |
|---|---|
| AES-256-GCM encryption | All beacon traffic encrypted; nonce prepended, base64 transported |
| Agent auto-registration | First beacon registers using a shared secret; subsequent beacons are lean |
| Jitter-based beaconing | Random sleep interval ± 30 % to avoid timing pattern detection |
| Persistent agent identity | Hostname, IP, OS, username captured on registration and stored |
| Task queue | Server queues commands; agent ACKs receipt and reports output |
| Event stream | Every agent action produces a typed event (connected, heartbeat, task_queued, task_sent, task_ack, task_completed) |
| Behavioral incident engine | Detects jitter anomalies, task bursts, and suspicious command patterns; raises severity-graded incidents |
| RBAC — 4 roles | `viewer` → `operator` → `developer` → `admin`, enforced by Flask decorators on every route |
| Session grouping | Heartbeat events are grouped into logical sessions for clean timeline display |
| Admin panel | User management, DB operations, IP whitelist access control (persisted to JSON), system stats |
| 116 automated tests | pytest suite covering auth, RBAC, beacon crypto, task lifecycle, and database operations |

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Agent | Go 1.25 | Small static binary, no runtime dependency, cross-compile to any OS |
| Server | Python 3.12 / Flask 3.1 | Rapid development, rich security libraries |
| Encryption | `cryptography.hazmat` AESGCM + Go `crypto/aes` | Industry-standard AES-256-GCM, not a toy cipher |
| Auth | bcrypt (cost 12) | Slow hash resistant to brute force |
| Database | SQLite 3 | Zero-dependency, sufficient for lab scale |
| Frontend | Bootstrap 5 + vanilla JS | No build toolchain needed |
| Testing | pytest + pytest-flask | Full HTTP-layer tests with real crypto |

---

## Project Structure

```
shadowNet/
├── agent/
│   ├── main.go              # Agent entry point — beacon loop, task execution
│   ├── agent/               # Modular sub-package (beacon, system info, types)
│   └── stages/              # 14 iterative development stages (history of the build)
│
└── server/
    ├── server_with_event.py # Flask application — all routes and business logic
    ├── database.py          # SQLite data access layer
    ├── events.py            # Event type constants and factory
    ├── incident_engine.py   # Behavioral anomaly detection and incident lifecycle
    ├── tests/               # pytest suite (116 tests)
    └── Frontend/
        ├── templates/       # Jinja2 HTML pages
        └── static/          # CSS, JS, theme
```

---

## Security Design Decisions

1. **Timing-safe secret comparison** — `secrets.compare_digest` used for registration secret check, preventing timing oracle attacks
2. **Constant-time login** — dummy bcrypt check on unknown usernames prevents user enumeration via response timing
3. **Role enforcement at the decorator level** — no route can be accidentally left unprotected; access control is explicit and centralized
4. **IP whitelist validation** — Python `ipaddress` module rejects non-IP strings before they enter the whitelist
5. **Agent defaults refused at startup** — Go agent refuses to run with hardcoded development credentials; must be rebuilt with `-ldflags`
6. **No raw SQL string formatting** — all database queries use parameterized statements (`?` placeholders)

---

## Development Journey

The `stages/` directory preserves 14 snapshots from the first working beacon (Stage 01) through to behavioral stealth (Stage 18):

```
Stage 01 → Basic HTTP beacon
Stage 02 → System info collection
Stage 03 → Beacon loop with sleep
Stage 04 → Task result reporting
Stage 05 → Jitter-based timing
Stage 06 → Server-side command input
Stage 07 → AES-GCM encryption
Stage 10 → Agent identity & persistence
Stage 13 → State machine
Stage 16 → Reliable delivery (ACK)
Stage 17 → Supervisor / crash recovery
Stage 17b → Persistence across restarts
Stage 18 → Behavioral stealth patterns
```

Each stage is a self-contained, runnable file that demonstrates one concept added to the design.

---

## Ethical Use

ShadowNet is an **educational project** built for authorized lab use only.  
Run agents only on machines you own or have explicit written permission to access.  
This codebase must not be used against systems without authorization.
