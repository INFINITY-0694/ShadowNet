# 🕸️ ShadowNet

> A sophisticated Command & Control (C2) framework for distributed system monitoring and management

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![Go Version](https://img.shields.io/badge/go-1.x%2B-00ADD8.svg)](https://golang.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](./server/tests/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Testing](#testing)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

**ShadowNet** is a full-featured Command & Control framework built with **Go** agents and a **Python** server. It provides real-time monitoring, incident detection, and remote management capabilities for distributed systems.

### Key Capabilities

- 🤖 **Lightweight Go Agents** - Cross-platform, low-footprint monitoring agents
- 🖥️ **Centralized Python Server** - Flask-based C2 server with web dashboard
- 🔐 **Encrypted Communications** - Secure agent-server communications
- 🚨 **Incident Detection** - Automated anomaly and failure detection
- 📊 **Real-time Dashboard** - Web-based monitoring and control interface
- 🎭 **Stealth Features** - Jitter, behavioral stealth, and evasion capabilities
- 🔄 **Reliability** - State machine architecture with persistence

## ✨ Features

### Agent Features (Go)
- ✅ System information collection
- ✅ Heartbeat/beacon mechanism
- ✅ Remote command execution
- ✅ AES-256 encryption
- ✅ Jitter for traffic randomization
- ✅ Persistence mechanisms
- ✅ Supervisor/watchdog process
- ✅ State machine architecture
- ✅ Behavioral stealth

### Server Features (Python)
- ✅ RESTful API endpoints
- ✅ Web dashboard (HTML/CSS/JS)
- ✅ SQLite database
- ✅ Incident detection engine
- ✅ Event processing system
- ✅ Secure task queue
- ✅ User authentication
- ✅ Real-time agent monitoring
- ✅ Command library
- ✅ Agent health tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SHADOWNET SYSTEM                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐                    ┌──────────────────┐
│   Go Agents      │ ◄──── HTTPS ─────► │  Python Server   │
│  (Distributed)   │                    │   (Centralized)  │
└──────────────────┘                    └──────────────────┘
       │                                         │
       ├─ Sys Info Collection                   ├─ Command & Control
       ├─ Beacon/Heartbeat                      ├─ Agent Management
       ├─ Command Execution                     ├─ Task Queuing
       ├─ Encrypted Comms                       ├─ Incident Detection
       ├─ Jitter/Stealth                        ├─ Event Processing
       └─ Persistence                           └─ Web Dashboard
```

### Component Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Agent** | Go 1.x+ | Lightweight client-side monitoring |
| **Server** | Python 3.14+, Flask | Centralized C2 backend |
| **Database** | SQLite | Agent & incident data storage |
| **Frontend** | HTML5, CSS3, JavaScript | Web dashboard |
| **Protocol** | HTTPS, JSON | Secure communication |

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+** (for server)
- **Go 1.x+** (for agent)
- **SQLite** (bundled with Python)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/shadowNet.git
cd shadowNet
```

### 2. Start Server

```bash
cd server
pip install -r requirements.txt
python server_with_event.py
```

Server will start on `http://localhost:5000`

### 3. Build & Run Agent

```bash
cd agent
go build -o agent main.go
./agent
```

### 4. Access Dashboard

Open browser and navigate to:
```
http://localhost:5000
```

**Default Credentials:**
- Username: `admin`
- Password: `password` (change this!)

## 📦 Installation

### Detailed Server Setup

```bash
# Navigate to server directory
cd server

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py

# Start server
python server_with_event.py
```

### Detailed Agent Setup

```bash
# Navigate to agent directory
cd agent

# Install dependencies
go mod download

# Build for current platform
go build -o agent main.go

# Build for specific platforms
# Windows
GOOS=windows GOARCH=amd64 go build -o agent.exe main.go

# Linux
GOOS=linux GOARCH=amd64 go build -o agent-linux main.go

# macOS
GOOS=darwin GOARCH=amd64 go build -o agent-mac main.go
```

### Configuration

#### Server Configuration

Edit `server/key.env`:
```bash
# Encryption key
ENCRYPTION_KEY=your-32-byte-key-here

# Server settings
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
DEBUG=False
```

#### Agent Configuration

Edit `agent/agent.env`:
```bash
# Server connection
SERVER_URL=http://localhost:5000
BEACON_INTERVAL=60

# Encryption
ENCRYPTION_KEY=your-32-byte-key-here

# Jitter settings
JITTER_MIN=30
JITTER_MAX=90
```

## 💻 Usage

### Managing Agents

#### Via Web Dashboard

1. Login to dashboard at `http://localhost:5000`
2. View all connected agents
3. Click agent to see details
4. Send commands via command interface

#### Via API

```python
import requests

# List all agents
response = requests.get('http://localhost:5000/api/agents')
agents = response.json()

# Send command to agent
command_data = {
    'agent_id': 'agent-123',
    'command': 'whoami'
}
response = requests.post('http://localhost:5000/api/command', json=command_data)
```

### Incident Detection

The incident engine automatically detects:

- **Burst Detection**: Rapid failure spikes
- **Repeated Failures**: Persistent errors
- **Jitter Anomalies**: Communication irregularities
- **Risk Score Calculation**: Aggregate risk assessment

View incidents in dashboard or via API:
```python
response = requests.get('http://localhost:5000/api/incidents')
incidents = response.json()
```

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design deep dive
- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API documentation
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide
- **[SECURITY.md](./SECURITY.md)** - Security best practices
- **[FAQ.md](./FAQ.md)** - Frequently asked questions
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute

## 🧪 Testing

### Run All Tests

```bash
cd server
python -m pytest --rootdir=. -v
```

### Run Specific Test Suite

```bash
# Incident engine tests
python -m pytest --rootdir=. -v server/tests/test_incident_engine.py

# Database tests
python -m pytest --rootdir=. -v server/test_db.py

# API tests
python -m pytest --rootdir=. -v server/test_commands_api.py
```

### Test Coverage

```bash
# Generate coverage report
python -m pytest --rootdir=. --cov=server --cov-report=html

# View report
# Open htmlcov/index.html in browser
```

### Current Test Status

- ✅ **Incident Engine**: 7/7 tests passing
- ✅ **Database Layer**: Comprehensive tests
- ✅ **API Endpoints**: Full coverage
- ✅ **Authentication**: Login tests

## 🔐 Security

### Important Security Notes

⚠️ **This is a Command & Control framework - Use responsibly and legally!**

- Only use on systems you own or have explicit permission to monitor
- Change default credentials immediately
- Use strong encryption keys
- Enable HTTPS in production
- Regularly update dependencies
- Review [SECURITY.md](./SECURITY.md) for best practices

### Security Features

- 🔒 AES-256 encryption for agent communications
- 🔑 Authentication and session management
- 🛡️ SQL injection prevention
- 🚫 Rate limiting
- 📝 Audit logging
- 🔐 Environment-based secrets

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/shadowNet.git
cd shadowNet

# Install dev dependencies
pip install -r server/requirements.txt
pip install pytest pytest-cov black flake8

# Run tests before committing
python -m pytest --rootdir=. -v

# Format code
black server/
```

### Code Style

- **Python**: Follow PEP 8, use `black` for formatting
- **Go**: Follow Go conventions, use `gofmt`
- **Commits**: Use conventional commits format

## 🗺️ Roadmap

### Current Version: 1.0.0

- [x] Basic agent-server communication
- [x] Incident detection engine
- [x] Web dashboard
- [x] Encryption
- [x] Test suite

### Future Plans

- [ ] Multi-user support
- [ ] PostgreSQL support
- [ ] Docker deployment
- [ ] Kubernetes orchestration
- [ ] Advanced analytics
- [ ] Plugin system
- [ ] Mobile app

## 📊 Project Structure

```
shadowNet/
├── agent/              # Go agent source code
│   ├── agent/         # Core agent logic
│   └── stages/        # Development iterations
├── server/            # Python server source code
│   ├── static/        # CSS, JS assets
│   ├── templates/     # HTML templates
│   └── tests/         # Test suites
├── docs/              # Additional documentation
└── scripts/           # Utility scripts
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 👥 Authors

- **Your Name** - *Initial work* - [@yourusername](https://github.com/yourusername)

See also the list of [contributors](./CONTRIBUTORS.md) who participated in this project.

## 🙏 Acknowledgments

- Flask framework for the server
- Go standard library for agent
- SQLite for database
- All contributors and testers

## 📞 Support

- 📧 Email: support@shadownet.example
- 💬 Discord: [Join our server](https://discord.gg/example)
- 📖 Wiki: [GitHub Wiki](https://github.com/yourusername/shadowNet/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/shadowNet/issues)

## ⚖️ Legal Disclaimer

**ShadowNet** is designed for legitimate system administration and monitoring purposes. Users are responsible for ensuring their use complies with all applicable laws and regulations. Unauthorized access to computer systems is illegal. The developers assume no liability for misuse of this software.

---

**Made with ❤️ by the ShadowNet Team**

*Star ⭐ this repo if you find it useful!*