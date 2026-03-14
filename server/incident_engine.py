import time
import uuid
import threading
import database

# =========================
# CONFIGURATION
# =========================

HEARTBEAT_TIMEOUT   = 30
CHECK_INTERVAL      = 5
FAILURE_THRESHOLD   = 3
TASK_BURST_COUNT    = 5
TASK_BURST_WINDOW   = 20   # seconds
JITTER_THRESHOLD    = 15   # heartbeat delta > expected + this = anomaly

SUSPICIOUS_COMMANDS = [
    "net user",       # user enumeration
    "net localgroup", # group enumeration
    "mimikatz",       # credential dumping tool
    "procdump",       # credential dumping via LSASS
    "wce.exe",        # Windows Credential Editor
    "gsecdump",       # credential dumping
    "vssadmin delete", # shadow copy deletion (ransomware pattern)
    "bcdedit /set",   # boot config tampering
    "wbadmin delete", # backup deletion
]

# =========================
# INCIDENT HELPERS
# =========================

def create_incident(agent_alias, incident_type, severity):
    """Create incident in database"""
    agents = database.get_all_agents()
    for agent in agents:
        if agent['alias'] == agent_alias:
            incident_id = str(uuid.uuid4())
            return database.create_incident(
                incident_id, agent['agent_id'],
                agent_alias, incident_type, severity
            )
    return False

def resolve_incident(agent_alias, incident_type):
    """Resolve open incident by agent_alias and type"""
    for incident in database.get_all_incidents():
        if (incident['agent_alias'] == agent_alias and
            incident['type']        == incident_type and
            incident['status']      == 'open'):
            database.resolve_incident(incident['incident_id'])
            return True
    return False

# =========================
# AGENT STATE HELPERS
# ✅ CHANGED: State now loaded from DB and saved back to DB
#            Previously used in-memory dict — lost on every restart
# =========================

def _get_agent_id_from_alias(alias):
    """Helper to get agent_id from alias"""
    for agent in database.get_all_agents():
        if agent['alias'] == alias:
            return agent['agent_id']
    return None

def _load_state(agent_id):
    """
    Load agent behavioral state from DB.
    Returns fresh defaults if agent has no state yet.
    State includes: failure_count, last_heartbeat,
    heartbeat_history (list), task_timestamps (list)
    """
    return database.get_agent_state(agent_id)

def _save_state(agent_id, state):
    """
    Persist agent behavioral state to DB.
    Called after every state mutation so nothing is lost on restart.
    """
    database.save_agent_state(agent_id, state)

# =========================
# EVENT PROCESSING
# =========================

def process_event(event):
    """
    Process an incoming event and update behavioral state.
    State is loaded from DB at start and saved back at end —
    survives server restarts unlike the old in-memory dict.
    """
    alias      = event["agent_alias"]
    agent_id   = event["agent_id"]
    event_type = event["event_type"]
    details    = event.get("details", {})

    # ✅ CHANGED: Load state from DB instead of in-memory dict
    state = _load_state(agent_id)

    # -------------------------
    # Heartbeat Handling
    # -------------------------
    if event_type == "agent_heartbeat":
        now = time.time()

        if state["last_heartbeat"]:
            delta = now - state["last_heartbeat"]

            # Keep only last 5 intervals
            state["heartbeat_history"].append(delta)
            if len(state["heartbeat_history"]) > 5:
                state["heartbeat_history"] = state["heartbeat_history"][-5:]

            # Jitter detection — beacon arrived much later than expected
            if delta > JITTER_THRESHOLD:
                create_incident(alias, "Beacon Jitter Anomaly", "MEDIUM")

        state["last_heartbeat"] = now

        # ✅ CHANGED: Save updated state back to DB
        _save_state(agent_id, state)

        resolve_incident(alias, "Agent Unresponsive")
        return

    # -------------------------
    # Task Sent — burst detection
    # -------------------------
    if event_type == "task_sent":
        now = time.time()

        # Add current timestamp
        state["task_timestamps"].append(now)

        # Remove timestamps outside the burst window
        state["task_timestamps"] = [
            t for t in state["task_timestamps"]
            if now - t <= TASK_BURST_WINDOW
        ]

        if len(state["task_timestamps"]) >= TASK_BURST_COUNT:
            create_incident(alias, "Excessive Task Activity", "MEDIUM")

        # Suspicious command detection
        cmd = details.get("cmd", "")
        for keyword in SUSPICIOUS_COMMANDS:
            if keyword.lower() in cmd.lower():
                create_incident(alias, "Suspicious Command Pattern", "LOW")
                break

        # ✅ CHANGED: Save updated state back to DB
        _save_state(agent_id, state)

    # -------------------------
    # Task Completed — failure tracking
    # -------------------------
    if event_type == "task_completed":
        output = details.get("output", "")

        if "error" in output.lower() or "not recognized" in output.lower():
            state["failure_count"] += 1
            create_incident(alias, "Task Execution Failure", "MEDIUM")

            if state["failure_count"] >= FAILURE_THRESHOLD:
                create_incident(alias, "Repeated Task Failures", "HIGH")
        else:
            state["failure_count"] = 0
            resolve_incident(alias, "Task Execution Failure")
            resolve_incident(alias, "Repeated Task Failures")

        # ✅ CHANGED: Save updated state back to DB
        _save_state(agent_id, state)

# =========================
# HEARTBEAT MONITOR
# Runs in background thread — checks for unresponsive agents
# =========================

def heartbeat_monitor():
    while True:
        now = time.time()

        try:
            agents = database.get_all_agents()
            for agent in agents:
                last_seen = agent['last_seen']
                if last_seen:
                    try:
                        last_seen_time = time.mktime(
                            time.strptime(last_seen, "%Y-%m-%d %H:%M:%S.%f")
                        )
                    except:
                        try:
                            last_seen_time = time.mktime(
                                time.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
                            )
                        except:
                            continue

                    if now - last_seen_time > HEARTBEAT_TIMEOUT:
                        create_incident(agent['alias'], "Agent Unresponsive", "HIGH")

        except Exception as e:
            print(f"[ERROR] heartbeat_monitor: {e}")

        time.sleep(CHECK_INTERVAL)


# Start heartbeat monitor in background
threading.Thread(target=heartbeat_monitor, daemon=True).start()

# =========================
# PUBLIC API
# =========================

def get_all_incidents():
    return database.get_all_incidents()

def get_open_incidents():
    return database.get_open_incidents()

def get_agent_incidents(agent_id):
    return database.get_agent_incidents(agent_id)

SEVERITY_WEIGHTS = {
    "LOW":      10,
    "MEDIUM":   25,
    "HIGH":     50,
    "CRITICAL": 80
}

def calculate_agent_risk(agent_alias, incidents):
    """
    Calculate risk score based on open incidents.
    Score accumulates by severity weight.
    Returns (score, level) tuple.
    """
    score = 0
    for incident in incidents:
        if incident['status'] == 'open':
            score += SEVERITY_WEIGHTS.get(incident['severity'], 0)

    if score >= 100:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    elif score > 0:
        level = "LOW"
    else:
        level = "SAFE"

    return score, level