# 📡 ShadowNet API Reference

> Complete API documentation for ShadowNet server endpoints

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Agent Endpoints](#agent-endpoints)
- [Command Endpoints](#command-endpoints)
- [Incident Endpoints](#incident-endpoints)
- [Event Endpoints](#event-endpoints)
- [Beacon Endpoints](#beacon-endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

**Base URL:** `http://localhost:5000`  
**Protocol:** HTTP/HTTPS  
**Format:** JSON  
**Authentication:** Session-based cookies

### API Versioning

Current Version: **v1** (implicit in URLs)

Future versions will use: `/api/v2/...`

### Common Headers

```http
Content-Type: application/json
Accept: application/json
Cookie: session=<session_token>
```

## Authentication

### POST /login

Authenticate user and create session.

**Request:**
```http
POST /login HTTP/1.1
Content-Type: application/json

{
  "username": "admin",
  "password": "secure_password"
}
```

**Response (Success):**
```http
HTTP/1.1 200 OK
Set-Cookie: session=abc123...; HttpOnly; Secure
Content-Type: application/json

{
  "status": "success",
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

**Response (Failure):**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "status": "error",
  "message": "Invalid credentials"
}
```

---

### POST /logout

End user session.

**Request:**
```http
POST /logout HTTP/1.1
Cookie: session=abc123...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Logged out successfully"
}
```

---

### GET /auth/status

Check authentication status.

**Request:**
```http
GET /auth/status HTTP/1.1
Cookie: session=abc123...
```

**Response (Authenticated):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "authenticated": true,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

**Response (Not Authenticated):**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "authenticated": false
}
```

## Agent Endpoints

### GET /api/agents

List all registered agents.

**Request:**
```http
GET /api/agents HTTP/1.1
Cookie: session=abc123...
```

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `inactive`, `offline`)
- `limit` (optional): Number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```http
GET /api/agents?status=active&limit=50 HTTP/1.1
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "count": 2,
  "agents": [
    {
      "id": "agent-abc123",
      "hostname": "web-server-01",
      "ip_address": "192.168.1.100",
      "os": "Linux",
      "os_version": "Ubuntu 22.04",
      "architecture": "x86_64",
      "status": "active",
      "last_seen": "2026-03-05T10:30:00Z",
      "risk_score": 15,
      "created_at": "2026-03-01T08:00:00Z"
    },
    {
      "id": "agent-xyz789",
      "hostname": "db-server-02",
      "ip_address": "192.168.1.101",
      "os": "Windows",
      "os_version": "Windows Server 2022",
      "architecture": "x86_64",
      "status": "active",
      "last_seen": "2026-03-05T10:29:45Z",
      "risk_score": 5,
      "created_at": "2026-03-02T09:15:00Z"
    }
  ]
}
```

---

### GET /api/agent/<agent_id>

Get detailed information about a specific agent.

**Request:**
```http
GET /api/agent/agent-abc123 HTTP/1.1
Cookie: session=abc123...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "agent": {
    "id": "agent-abc123",
    "hostname": "web-server-01",
    "ip_address": "192.168.1.100",
    "os": "Linux",
    "os_version": "Ubuntu 22.04",
    "architecture": "x86_64",
    "status": "active",
    "last_seen": "2026-03-05T10:30:00Z",
    "risk_score": 15,
    "created_at": "2026-03-01T08:00:00Z",
    "metrics": {
      "cpu_usage": 45.2,
      "memory_usage": 62.8,
      "disk_usage": 78.5,
      "network_rx": 1024000,
      "network_tx": 512000
    },
    "recent_incidents": [
      {
        "id": 42,
        "type": "jitter_anomaly",
        "severity": "medium",
        "created_at": "2026-03-05T09:15:00Z"
      }
    ],
    "command_history": [
      {
        "task_id": "task-001",
        "command": "whoami",
        "status": "completed",
        "created_at": "2026-03-05T10:00:00Z"
      }
    ]
  }
}
```

**Response (Not Found):**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "status": "error",
  "message": "Agent not found"
}
```

---

### DELETE /api/agent/<agent_id>

Remove an agent from the system.

**Request:**
```http
DELETE /api/agent/agent-abc123 HTTP/1.1
Cookie: session=abc123...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Agent removed successfully"
}
```

---

### PUT /api/agent/<agent_id>/status

Manually update agent status.

**Request:**
```http
PUT /api/agent/agent-abc123/status HTTP/1.1
Cookie: session=abc123...
Content-Type: application/json

{
  "status": "offline"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Agent status updated"
}
```

## Command Endpoints

### POST /api/command

Send a command to an agent.

**Request:**
```http
POST /api/command HTTP/1.1
Cookie: session=abc123...
Content-Type: application/json

{
  "agent_id": "agent-abc123",
  "command": "whoami",
  "command_type": "shell"
}
```

**Command Types:**
- `shell`: Execute shell command
- `script`: Execute script
- `file_upload`: Upload file to agent
- `file_download`: Download file from agent
- `config_update`: Update agent configuration

**Response:**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "status": "success",
  "message": "Command queued",
  "task": {
    "task_id": "task-xyz789",
    "agent_id": "agent-abc123",
    "command": "whoami",
    "status": "pending",
    "created_at": "2026-03-05T10:35:00Z"
  }
}
```

---

### GET /api/commands/<agent_id>

Get command history for a specific agent.

**Request:**
```http
GET /api/commands/agent-abc123 HTTP/1.1
Cookie: session=abc123...
```

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Number of results
- `offset` (optional): Pagination offset

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "count": 3,
  "commands": [
    {
      "task_id": "task-003",
      "command": "ls -la",
      "command_type": "shell",
      "status": "completed",
      "result": "total 48\ndrwxr-xr-x  6 user user  4096 Mar  5 10:30 .\n...",
      "created_at": "2026-03-05T10:30:00Z",
      "completed_at": "2026-03-05T10:30:02Z"
    },
    {
      "task_id": "task-002",
      "command": "whoami",
      "command_type": "shell",
      "status": "completed",
      "result": "root",
      "created_at": "2026-03-05T10:25:00Z",
      "completed_at": "2026-03-05T10:25:01Z"
    },
    {
      "task_id": "task-001",
      "command": "uptime",
      "command_type": "shell",
      "status": "failed",
      "error_message": "Command timeout",
      "created_at": "2026-03-05T10:20:00Z"
    }
  ]
}
```

---

### GET /api/command/<task_id>

Get status and result of a specific command.

**Request:**
```http
GET /api/command/task-xyz789 HTTP/1.1
Cookie: session=abc123...
```

**Response (Completed):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "task": {
    "task_id": "task-xyz789",
    "agent_id": "agent-abc123",
    "command": "whoami",
    "command_type": "shell",
    "status": "completed",
    "result": "root",
    "created_at": "2026-03-05T10:35:00Z",
    "completed_at": "2026-03-05T10:35:02Z"
  }
}
```

**Response (Pending):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "task": {
    "task_id": "task-xyz789",
    "agent_id": "agent-abc123",
    "command": "whoami",
    "command_type": "shell",
    "status": "pending",
    "created_at": "2026-03-05T10:35:00Z"
  }
}
```

---

### DELETE /api/command/<task_id>

Cancel a pending command.

**Request:**
```http
DELETE /api/command/task-xyz789 HTTP/1.1
Cookie: session=abc123...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Command cancelled"
}
```

## Incident Endpoints

### GET /api/incidents

List all incidents.

**Request:**
```http
GET /api/incidents HTTP/1.1
Cookie: session=abc123...
```

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `status` (optional): Filter by status (`open`, `investigating`, `resolved`)
- `severity` (optional): Filter by severity (`low`, `medium`, `high`, `critical`)
- `limit` (optional): Number of results
- `offset` (optional): Pagination offset

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "count": 2,
  "incidents": [
    {
      "id": 42,
      "agent_id": "agent-abc123",
      "incident_type": "burst_detection",
      "severity": "high",
      "description": "Burst of 5 failures detected in 60 seconds",
      "details": {
        "failure_count": 5,
        "time_window": 60,
        "first_failure": "2026-03-05T10:15:00Z",
        "last_failure": "2026-03-05T10:16:00Z"
      },
      "status": "open",
      "created_at": "2026-03-05T10:16:05Z"
    },
    {
      "id": 41,
      "agent_id": "agent-xyz789",
      "incident_type": "jitter_anomaly",
      "severity": "medium",
      "description": "Jitter exceeded normal range",
      "details": {
        "expected_jitter": 15,
        "actual_jitter": 145,
        "deviation": 130
      },
      "status": "investigating",
      "created_at": "2026-03-05T09:45:00Z"
    }
  ]
}
```

---

### GET /api/incident/<incident_id>

Get detailed information about a specific incident.

**Request:**
```http
GET /api/incident/42 HTTP/1.1
Cookie: session=abc123...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "incident": {
    "id": 42,
    "agent_id": "agent-abc123",
    "agent_hostname": "web-server-01",
    "incident_type": "burst_detection",
    "severity": "high",
    "description": "Burst of 5 failures detected in 60 seconds",
    "details": {
      "failure_count": 5,
      "time_window": 60,
      "first_failure": "2026-03-05T10:15:00Z",
      "last_failure": "2026-03-05T10:16:00Z",
      "failure_types": ["connection_timeout", "http_500", "http_500"]
    },
    "status": "open",
    "created_at": "2026-03-05T10:16:05Z",
    "timeline": [
      {
        "timestamp": "2026-03-05T10:16:05Z",
        "action": "incident_created",
        "user": "system"
      }
    ]
  }
}
```

---

### PUT /api/incident/<incident_id>/resolve

Mark an incident as resolved.

**Request:**
```http
PUT /api/incident/42/resolve HTTP/1.1
Cookie: session=abc123...
Content-Type: application/json

{
  "resolution_notes": "False positive, server was restarting"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Incident resolved",
  "incident": {
    "id": 42,
    "status": "resolved",
    "resolved_at": "2026-03-05T10:45:00Z",
    "resolved_by": "admin"
  }
}
```

---

### POST /api/incident/acknowledge

Acknowledge an incident (change status to 'investigating').

**Request:**
```http
POST /api/incident/acknowledge HTTP/1.1
Cookie: session=abc123...
Content-Type: application/json

{
  "incident_id": 42,
  "notes": "Investigating the root cause"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Incident acknowledged"
}
```

## Event Endpoints

### GET /api/events

List system events.

**Request:**
```http
GET /api/events HTTP/1.1
Cookie: session=abc123...
```

**Query Parameters:**
- `agent_id` (optional): Filter by agent
- `event_type` (optional): Filter by type
- `start_time` (optional): Start time (ISO 8601)
- `end_time` (optional): End time (ISO 8601)
- `limit` (optional): Number of results
- `offset` (optional): Pagination offset

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "count": 3,
  "events": [
    {
      "id": 1001,
      "event_type": "agent_connected",
      "agent_id": "agent-abc123",
      "data": {
        "hostname": "web-server-01",
        "ip_address": "192.168.1.100"
      },
      "timestamp": "2026-03-05T10:30:00Z"
    },
    {
      "id": 1000,
      "event_type": "command_executed",
      "agent_id": "agent-abc123",
      "data": {
        "task_id": "task-xyz789",
        "command": "whoami",
        "status": "completed"
      },
      "timestamp": "2026-03-05T10:29:00Z"
    },
    {
      "id": 999,
      "event_type": "incident_created",
      "agent_id": "agent-abc123",
      "data": {
        "incident_id": 42,
        "type": "burst_detection",
        "severity": "high"
      },
      "timestamp": "2026-03-05T10:16:05Z"
    }
  ]
}
```

---

### GET /api/events/<agent_id>

Get events for a specific agent.

**Request:**
```http
GET /api/events/agent-abc123 HTTP/1.1
Cookie: session=abc123...
```

**Response:** Same format as `/api/events` but filtered by agent.

---

### GET /api/events/stream

Server-Sent Events (SSE) stream for real-time event updates.

**Request:**
```http
GET /api/events/stream HTTP/1.1
Cookie: session=abc123...
Accept: text/event-stream
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: agent_connected
data: {"agent_id":"agent-abc123","hostname":"web-server-01"}

event: command_executed
data: {"task_id":"task-xyz789","status":"completed"}

event: incident_created
data: {"incident_id":43,"type":"jitter_anomaly","severity":"medium"}
```

## Beacon Endpoints

*These endpoints are used by agents for check-in and reporting.*

### POST /beacon

Agent check-in endpoint.

**Request:**
```http
POST /beacon HTTP/1.1
Content-Type: application/json

{
  "agent_id": "agent-abc123",
  "hostname": "web-server-01",
  "ip_address": "192.168.1.100",
  "os": "Linux",
  "os_version": "Ubuntu 22.04",
  "architecture": "x86_64",
  "status": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 78.5
  },
  "jitter": 15,
  "timestamp": "2026-03-05T10:30:00Z"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "commands": [
    {
      "task_id": "task-xyz789",
      "command": "whoami",
      "command_type": "shell"
    }
  ],
  "next_beacon": 60,
  "config_update": null
}
```

---

### POST /result

Report command execution results.

**Request:**
```http
POST /result HTTP/1.1
Content-Type: application/json

{
  "task_id": "task-xyz789",
  "agent_id": "agent-abc123",
  "status": "completed",
  "result": "root",
  "execution_time": 0.15,
  "timestamp": "2026-03-05T10:30:02Z"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "message": "Result received"
}
```

## Error Handling

### Standard Error Response Format

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful GET, PUT, DELETE |
| `201` | Created | Successful POST (resource created) |
| `400` | Bad Request | Invalid request data |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Server overloaded/maintenance |

### Error Examples

**400 Bad Request**
```json
{
  "status": "error",
  "message": "Invalid request data",
  "error_code": "INVALID_INPUT",
  "details": {
    "command": "Command is required"
  }
}
```

**401 Unauthorized**
```json
{
  "status": "error",
  "message": "Authentication required",
  "error_code": "UNAUTHORIZED"
}
```

**404 Not Found**
```json
{
  "status": "error",
  "message": "Agent not found",
  "error_code": "NOT_FOUND"
}
```

**429 Too Many Requests**
```json
{
  "status": "error",
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

## Rate Limiting

### Current Limits

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Authentication | 5 requests | 1 minute |
| Agent Management | 100 requests | 1 minute |
| Commands | 50 requests | 1 minute |
| Events | 200 requests | 1 minute |
| Beacon (per agent) | Unlimited | - |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1709640000
```

---

## Code Examples

### Python

```python
import requests

# Login
session = requests.Session()
login_response = session.post(
    'http://localhost:5000/login',
    json={'username': 'admin', 'password': 'password'}
)

# List agents
agents_response = session.get('http://localhost:5000/api/agents')
agents = agents_response.json()['agents']

# Send command
command_response = session.post(
    'http://localhost:5000/api/command',
    json={
        'agent_id': agents[0]['id'],
        'command': 'whoami',
        'command_type': 'shell'
    }
)
task_id = command_response.json()['task']['task_id']

# Check command status
import time
while True:
    status_response = session.get(f'http://localhost:5000/api/command/{task_id}')
    task = status_response.json()['task']
    if task['status'] == 'completed':
        print(f"Result: {task['result']}")
        break
    time.sleep(2)
```

### cURL

```bash
# Login
curl -c cookies.txt -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# List agents
curl -b cookies.txt http://localhost:5000/api/agents

# Send command
curl -b cookies.txt -X POST http://localhost:5000/api/command \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"agent-abc123","command":"whoami","command_type":"shell"}'

# Get command result
curl -b cookies.txt http://localhost:5000/api/command/task-xyz789
```

### JavaScript

```javascript
// Login
const loginResponse = await fetch('http://localhost:5000/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    username: 'admin',
    password: 'password'
  })
});

// List agents
const agentsResponse = await fetch('http://localhost:5000/api/agents', {
  credentials: 'include'
});
const { agents } = await agentsResponse.json();

// Send command
const commandResponse = await fetch('http://localhost:5000/api/command', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    agent_id: agents[0].id,
    command: 'whoami',
    command_type: 'shell'
  })
});
const { task } = await commandResponse.json();

// Poll for result
const checkStatus = async () => {
  const response = await fetch(`http://localhost:5000/api/command/${task.task_id}`, {
    credentials: 'include'
  });
  const { task: updatedTask } = await response.json();
  
  if (updatedTask.status === 'completed') {
    console.log('Result:', updatedTask.result);
  } else {
    setTimeout(checkStatus, 2000);
  }
};
checkStatus();
```

---

**Last Updated:** March 5, 2026  
**API Version:** 1.0