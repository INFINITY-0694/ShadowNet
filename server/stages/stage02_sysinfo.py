"""
SERVER — Stage 02 (System Info Storage)

Matches: agent/stages/stage02_sysinfo.go

What this adds:
- Stores agent hostname, OS, arch in memory
- Prints full system info on each beacon
- Returns OK
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

agents = {}  # in-memory agent store

@app.route("/beacon", methods=["POST"])
def beacon():
    data = request.get_json()

    agent_id = data.get("agent", "unknown")
    agents[agent_id] = {
        "hostname": data.get("hostname", "unknown"),
        "os":       data.get("os", "unknown"),
        "arch":     data.get("arch", "unknown"),
        "status":   data.get("status", "unknown"),
    }

    print(f"[+] Agent check-in: {agents[agent_id]}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("[*] Stage 02 server started on http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
