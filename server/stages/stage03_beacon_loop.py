"""
SERVER — Stage 03 (Beacon Loop — Track Last Seen)

Matches: agent/stages/stage03_beacon_loop.go

What this adds:
- Tracks last_seen timestamp per agent
- Shows how many beacons received
- Returns OK every time
"""

from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

agents = {}

@app.route("/beacon", methods=["POST"])
def beacon():
    data = request.get_json()
    agent_id = data.get("agent", "unknown")

    if agent_id not in agents:
        agents[agent_id] = {"count": 0, "hostname": data.get("hostname", "?"),
                             "os": data.get("os", "?")}

    agents[agent_id]["count"] += 1
    agents[agent_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agents[agent_id]["status"] = data.get("status", "unknown")

    print(f"[+] Beacon #{agents[agent_id]['count']} from {agent_id} "
          f"({agents[agent_id]['hostname']}) at {agents[agent_id]['last_seen']}")

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("[*] Stage 03 server started on http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
