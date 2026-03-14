Architecture · MD# 🏗️ ShadowNet Architecture

> Detailed technical architecture and design documentation

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [API Design](#api-design)
- [Security Architecture](#security-architecture)
- [Scalability](#scalability)

## System Overview

ShadowNet implements a client-server architecture pattern with distributed Go agents communicating with a centralized Python server.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SHADOWNET ECOSYSTEM                          │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
    │   Agent 1   │         │   Agent 2   │         │   Agent N   │
    │   (Go)      │         │   (Go)      │         │   (Go)      │
    └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
           │                       │                       │
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                              HTTPS/JSON
                                   │
                    ┌──────────────▼──────────────┐
                    │     Load Balancer/Proxy      │
                    │      (Optional/Future)       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Flask Server (Python)   │
                    │  ┌───────────────────────┐  │
                    │  │  Web Dashboard        │  │
                    │  │  (HTML/CSS/JS)        │  │
                    │  └───────────────────────┘  │
                    │  ┌───────────────────────┐  │
                    │  │  REST API Endpoints   │  │
                    │  └───────────────────────┘  │
                    │  ┌───────────────────────┐  │
                    │  │  Business Logic       │  │
                    │  │  - Incident Engine    │  │
                    │  │  - Event Processor    │  │
                    │  │  - Task Queue         │  │
                    │  └───────────────────────┘  │
                    │  ┌───────────────────────┐  │
                    │  │  Database Layer       │  │
                    │  │  (database.py)        │  │
                    │  └───────────┬───────────┘  │
                    └──────────────┼──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    SQLite Database           │
                    │  - agents                    │
                    │  - commands/tasks            │
                    │  - incidents                 │
                    │  - events                    │
                    │  - users                     │
                    └─────────────────────────────┘
```

## Component Architecture

### 1. Agent (Go)

#### Core Components

```
agent/
├── main.go                  # Entry point, initialization
├── agent/
│   ├── beacon.go           # Heartbeat and check-in logic
│   ├── system.go           # System information collection
│   └── types.go            # Data structures and types
└── stages/                 # Evolutionary development stages
```

#### Agent State Machine

```
┌──────────────┐
│ Initialization│
└──────┬────────┘
       │
       ▼
┌──────────────┐     Failed     ┌──────────────┐
│   IDLE       │────────────────►│   ERROR      │
└──────┬────────┘                └──────┬────────┘
       │                                │
       │ Timer/Jitter                   │ Retry Logic
       ▼                                ▼
┌──────────────┐                ┌──────────────┐
│  BEACON      │                │  BACKOFF     │
└──────┬────────┘                └──────────────┘
       │
       │ Command Available?
       ▼
┌──────────────┐
│  EXECUTE     │
└──────┬────────┘
       │
       │ Send Results
       ▼
┌──────────────┐
│  REPORT      │
└──────┬────────┘
       │
       └────────► Back to IDLE
```

#### Key Agent Features

**1. Beacon System**
```go
// Pseudo-code
func beaconLoop() {
    for {
        // Add jitter to avoid detection
        jitter := calculateJitter()
        sleep(beaconInterval + jitter)
        
        // Send heartbeat
        status := collectSystemInfo()
        sendBeacon(status)
        
        // Check for commands
        commands := fetchCommands()
        executeCommands(commands)
    }
}
```

**2. System Information Collection**
- OS details (name, version, architecture)
- Hostname and IP addresses
- CPU, memory, disk usage
- Network interfaces
- Running processes
- User information

**3. Command Execution**
- Receives commands from server
- Executes in isolated environment
- Captures stdout/stderr
- Reports results back to server
- Handles timeouts and errors

**4. Encryption**
- AES-256-GCM encryption
- Shared key with server
- All communications encrypted
- Key rotation support (future)

**5. Stealth Features**
- **Jitter**: Randomizes beacon timing
- **Behavioral Stealth**: Mimics normal traffic patterns
- **Process Disguise**: Can masquerade as legitimate process

**6. Persistence**
- Auto-restart on crash (supervisor)
- Registry/cron/systemd integration
- Watchdog process

### 2. Server (Python/Flask)

#### Core Modules

```
server/
├── database.py              # Database abstraction layer
├── incident_engine.py       # Anomaly detection
├── events.py                # Event processing
├── secure_queue.py          # Task queue management
├── diagnose.py              # System diagnostics
├── server_with_event.py     # Main server (current version)
├── static/                  # CSS, JS assets
├── templates/               # HTML templates
└── tests/                   # Test suites
```

#### Server Layers

**1. Presentation Layer** (Templates + Static Files)
```
templates/
├── login.html              # Authentication page
├── dashboard.html          # Main dashboard
├── agent_detail.html       # Individual agent view
├── incident_detail.html    # Incident details
└── commands_library.html   # Command templates
```

**2. Application Layer** (Flask Routes)
```python
# Route structure
@app.route('/')                      # Dashboard
@app.route('/login', POST)           # Authentication
@app.route('/api/agents', GET)       # List agents
@app.route('/api/agent/<id>', GET)   # Agent details
@app.route('/api/command', POST)     # Send command
@app.route('/api/incidents', GET)    # List incidents
@app.route('/beacon', POST)          # Agent check-in
```

**3. Business Logic Layer**

**Incident Engine**
```python
class IncidentEngine:
    def __init__(self, db):
        self.db = db
        self.detectors = [
            BurstDetector(),
            RepeatedFailureDetector(),
            JitterAnomalyDetector()
        ]
    
    def process_beacon(self, agent_id, data):
        # Check for anomalies
        for detector in self.detectors:
            if detector.detect(agent_id, data):
                self.create_incident(detector.type, agent_id)
        
        # Calculate risk score
        risk = self.calculate_risk_score(agent_id)
        self.update_agent_risk(agent_id, risk)
```

**Event Processor**
```python
class EventProcessor:
    def process_event(self, event_type, data):
        # Log event
        self.log_event(event_type, data)
        
        # Trigger handlers
        for handler in self.handlers[event_type]:
            handler.handle(data)
        
        # Update metrics
        self.update_metrics(event_type)
```

**Secure Task Queue**
```python
class SecureTaskQueue:
    def enqueue_task(self, agent_id, command):
        task_id = generate_task_id()
        encrypted_command = encrypt(command)
        
        self.db.insert_task({
            'id': task_id,
            'agent_id': agent_id,
            'command': encrypted_command,
            'status': 'pending',
            'created_at': now()
        })
        
        return task_id
    
    def get_pending_tasks(self, agent_id):
        tasks = self.db.get_tasks(agent_id, status='pending')
        return [decrypt(task) for task in tasks]
```

**4. Data Layer** (database.py)

Provides abstraction over SQLite operations:
- Connection management
- CRUD operations
- Transaction handling
- Query optimization

## Data Flow

### Agent Check-in Flow

```
Agent                          Server                        Database
  │                              │                              │
  │  1. Collect system info      │                              │
  ├──────────────────────────────┤                              │
  │                              │                              │
  │  2. POST /beacon             │                              │
  │    {agent_id, status, ...}   │                              │
  ├─────────────────────────────>│                              │
  │                              │                              │
  │                              │  3. Update agent status      │
  │                              ├─────────────────────────────>│
  │                              │                              │
  │                              │  4. Check for anomalies      │
  │                              │    (Incident Engine)         │
  │                              ├──────────────────────────────┤
  │                              │                              │
  │                              │  5. Get pending commands     │
  │                              ├─────────────────────────────>│
  │                              │                              │
  │                              │  6. Return commands          │
  │                              │<─────────────────────────────┤
  │                              │                              │
  │  7. Response with commands   │                              │
  │<─────────────────────────────┤                              │
  │                              │                              │
  │  8. Execute commands         │                              │
  ├──────────────────────────────┤                              │
  │                              │                              │
  │  9. POST /result             │                              │
  │    {task_id, output}         │                              │
  ├─────────────────────────────>│                              │
  │                              │                              │
  │                              │  10. Store results           │
  │                              ├─────────────────────────────>│
  │                              │                              │
```

### Command Execution Flow

```
Dashboard                      Server                        Agent
    │                            │                              │
    │  1. User enters command    │                              │
    ├────────────────────────────┤                              │
    │                            │                              │
    │  2. POST /api/command      │                              │
    │    {agent_id, cmd}         │                              │
    ├───────────────────────────>│                              │
    │                            │                              │
    │                            │  3. Validate & encrypt       │
    │                            ├──────────────────────────────┤
    │                            │                              │
    │                            │  4. Store in task queue      │
    │                            ├───────────────────┐          │
    │                            │                   │          │
    │                            │<──────────────────┘          │
    │                            │                              │
    │  5. Return task_id         │                              │
    │<───────────────────────────┤                              │
    │                            │                              │
    │                            │  6. Agent checks in          │
    │                            │<─────────────────────────────┤
    │                            │                              │
    │                            │  7. Return pending tasks     │
    │                            ├─────────────────────────────>│
    │                            │                              │
    │                            │                              │  8. Decrypt
    │                            │                              │     & execute
    │                            │                              ├──────────────┐
    │                            │                              │              │
    │                            │                              │<─────────────┘
    │                            │                              │
    │                            │  9. POST results             │
    │                            │<─────────────────────────────┤
    │                            │                              │
    │  10. WebSocket update      │                              │
    │<───────────────────────────┤                              │
    │  (or polling)              │                              │
```

## Database Schema

### Tables

**1. agents**
```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    ip_address TEXT,
    os TEXT,
    os_version TEXT,
    architecture TEXT,
    last_seen TIMESTAMP,
    status TEXT CHECK(status IN ('active', 'inactive', 'offline')),
    risk_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_last_seen ON agents(last_seen);
```

**2. commands/tasks**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    command TEXT NOT NULL,
    command_type TEXT,
    status TEXT CHECK(status IN ('pending', 'sent', 'completed', 'failed')),
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

**3. incidents**
```sql
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    details JSON,
    status TEXT CHECK(status IN ('open', 'investigating', 'resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_incidents_agent_id ON incidents(agent_id);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_created_at ON incidents(created_at);
```

**4. events**
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    agent_id TEXT,
    data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_events_agent_id ON events(agent_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(event_type);
```

**5. users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    role TEXT CHECK(role IN ('admin', 'operator', 'viewer')),
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
```

**6. beacon_history**
```sql
CREATE TABLE beacon_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jitter_seconds INTEGER,
    status_data JSON,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_beacon_agent_id ON beacon_history(agent_id);
CREATE INDEX idx_beacon_timestamp ON beacon_history(timestamp);
```

### Entity Relationships

```
┌──────────┐       1:N      ┌──────────┐
│  agents  │────────────────│  tasks   │
└────┬─────┘                └──────────┘
     │
     │ 1:N
     │
┌────▼──────┐
│ incidents │
└───────────┘
     │
     │ 1:N
     │
┌────▼──────┐
│  events   │
└───────────┘
```

## API Design

### RESTful Endpoints

**Authentication**
```
POST   /login           # User login
POST   /logout          # User logout
GET    /auth/status     # Check auth status
```

**Agents**
```
GET    /api/agents                  # List all agents
GET    /api/agent/<id>              # Get agent details
DELETE /api/agent/<id>              # Remove agent
PUT    /api/agent/<id>/status       # Update agent status
```

**Commands**
```
POST   /api/command                 # Send command to agent
GET    /api/commands/<agent_id>     # Get command history
GET    /api/command/<task_id>       # Get command status
DELETE /api/command/<task_id>       # Cancel command
```

**Incidents**
```
GET    /api/incidents               # List all incidents
GET    /api/incident/<id>           # Get incident details
PUT    /api/incident/<id>/resolve   # Resolve incident
POST   /api/incident/acknowledge    # Acknowledge incident
```

**Events**
```
GET    /api/events                  # List events
GET    /api/events/<agent_id>       # Agent-specific events
GET    /api/events/stream           # SSE event stream
```

**Beacon (Agent-facing)**
```
POST   /beacon                      # Agent check-in
POST   /result                      # Report command results
```

### API Request/Response Examples

**Beacon Request**
```json
POST /beacon
{
  "agent_id": "agent-abc123",
  "hostname": "web-server-01",
  "ip_address": "192.168.1.100",
  "os": "Linux",
  "os_version": "Ubuntu 22.04",
  "architecture": "x86_64",
  "cpu_usage": 45.2,
  "memory_usage": 62.8,
  "disk_usage": 78.5,
  "jitter": 15,
  "timestamp": "2026-03-05T10:30:00Z"
}
```

**Beacon Response**
```json
{
  "status": "ok",
  "commands": [
    {
      "task_id": "task-xyz789",
      "command": "whoami",
      "command_type": "shell"
    }
  ],
  "next_beacon": 60
}
```

## Security Architecture

### Encryption

**Symmetric Encryption (AES-256-GCM)**
```
Agent                                    Server
  │                                        │
  │  Shared Key (Environment Variable)     │
  │  ────────────────────────────────────► │
  │                                        │
  │  Encrypt(Data, Key, Nonce)             │
  ├────────────────────────────────────────┤
  │                                        │
  │  Send: Nonce + Ciphertext              │
  ├───────────────────────────────────────>│
  │                                        │
  │                                        │  Decrypt(Ciphertext, Key, Nonce)
  │                                        ├──────────────────────────────────┐
  │                                        │                                  │
  │                                        │<─────────────────────────────────┘
```

### Authentication Flow

```
User                    Server                     Database
 │                        │                           │
 │  1. Enter credentials  │                           │
 ├───────────────────────>│                           │
 │                        │                           │
 │                        │  2. Check user exists     │
 │                        ├──────────────────────────>│
 │                        │                           │
 │                        │  3. Return user record    │
 │                        │<──────────────────────────┤
 │                        │                           │
 │                        │  4. Verify password hash  │
 │                        ├───────────────────────────┤
 │                        │                           │
 │                        │  5. Create session        │
 │                        ├───────────────────────────┤
 │                        │                           │
 │  6. Set session cookie │                           │
 │<───────────────────────┤                           │
```

### Security Best Practices Implemented

1. **Encrypted Communications**: All agent-server traffic encrypted
2. **Parameterized Queries**: SQL injection prevention
3. **Password Hashing**: bcrypt/argon2 for user passwords
4. **Session Management**: Secure session cookies
5. **Input Validation**: All user input validated
6. **Rate Limiting**: API rate limits (future)
7. **Audit Logging**: All actions logged

## Scalability

### Current Limitations

- **Database**: SQLite (single-file, not distributed)
- **Concurrency**: Limited by Python GIL
- **Session Storage**: In-memory (not distributed)

### Future Scalability Improvements

**1. Database Migration**
```
SQLite → PostgreSQL/MySQL
- Horizontal scaling
- Replication support
- Better concurrent writes
```

**2. Application Scaling**
```
Single Flask Instance → Multiple Instances
- Load balancer (nginx/HAProxy)
- Shared session storage (Redis)
- Message queue (RabbitMQ/Redis)
```

**3. Caching Layer**
```
Add Redis for:
- Session storage
- Task queue
- Real-time data
- Cache frequent queries
```

**4. Microservices (Future)**
```
Monolith → Microservices
- Agent Service
- Command Service
- Incident Service
- Event Service
```

### Estimated Capacity

**Current Architecture:**
- **Agents**: ~1,000 concurrent agents
- **Requests/sec**: ~100 requests/second
- **Database Size**: ~10GB before performance degradation

**With Improvements:**
- **Agents**: 10,000+ concurrent agents
- **Requests/sec**: 1,000+ requests/second
- **Database Size**: 100GB+ with proper indexing

## Conclusion

ShadowNet's architecture is designed for:
- ✅ **Simplicity**: Easy to understand and deploy
- ✅ **Security**: Encrypted, authenticated communications
- ✅ **Reliability**: State machine, persistence, error handling
- ✅ **Extensibility**: Modular design for easy additions
- ✅ **Maintainability**: Clear separation of concerns

For production deployments, consider the scalability improvements outlined above.