"""
SERVER — Stage 01 (Basic Beacon Receiver)

Matches: agent/stages/stage01_basic_beacon.go

What this does:
- Minimal Flask server
- Single /beacon route
- Receives JSON POST and prints it
- Returns a simple OK response
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/beacon", methods=["POST"])
def beacon():
    data = request.get_json()
    print(f"[+] Beacon received: {data}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("[*] Stage 01 server started on http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
