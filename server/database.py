import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

# Register datetime adapters (fixes Python 3.12+ deprecation)
def adapt_datetime(dt):
    """Convert datetime to ISO format string for SQLite"""
    return dt.isoformat()

def convert_datetime(s):
    """Convert ISO format string back to datetime"""
    return datetime.fromisoformat(s.decode())

# Register the adapters
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

# ✅ Database location - configurable via environment variable, defaults to server root
_db_default = str(Path(__file__).parent.parent / "shadownet.db")
DB_FILE = os.environ.get('SHADOWNET_DB_PATH', _db_default)

# ===========================
# DATABASE CONNECTION
# ===========================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("[*] Initializing database...")
    print(f"[*] Database location: {DB_FILE}")
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'operator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Agents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE NOT NULL,
            alias TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            auth_token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'offline',
            last_seen TIMESTAMP,
            hostname TEXT,
            ip_address TEXT,
            os_info TEXT,
            agent_user TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    # Migration: add new columns to existing databases
    for col, coltype in [('hostname', 'TEXT'), ('ip_address', 'TEXT'), ('os_info', 'TEXT'), ('agent_user', 'TEXT')]:
        try:
            cursor.execute(f'ALTER TABLE agents ADD COLUMN {col} {coltype}')
        except Exception:
            pass  # column already exists
    
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            agent_id TEXT NOT NULL,
            command TEXT NOT NULL,
            status TEXT DEFAULT 'queued',
            output TEXT,
            queued_at TIMESTAMP,
            sent_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    # Incidents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE NOT NULL,
            agent_id TEXT NOT NULL,
            agent_alias TEXT NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            start_time TIMESTAMP,
            resolved_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    # Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            agent_id TEXT NOT NULL,
            agent_alias TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    # Command Templates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            os_type TEXT DEFAULT 'all',
            usage_count INTEGER DEFAULT 0,
            is_favorite BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ✅ NEW: Agent state table — persists behavioral tracking across restarts
    # Replaces the in-memory AGENT_STATE dict in incident_engine.py
    # Each row = one agent's behavioral state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_state (
            agent_id          TEXT PRIMARY KEY,
            failure_count     INTEGER DEFAULT 0,
            last_heartbeat    REAL,
            heartbeat_history TEXT DEFAULT '[]',
            task_timestamps   TEXT DEFAULT '[]',
            updated_at        TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    conn.commit()
    
    # Seed default command templates if table is empty
    cursor.execute('SELECT COUNT(*) as count FROM command_templates')
    if cursor.fetchone()['count'] == 0:
        seed_command_templates(conn)
    
    conn.close()
    print("[+] Database initialized successfully!")

def seed_command_templates(conn):
    """Seed default command templates"""
    cursor = conn.cursor()
    
    default_commands = [
        # Reconnaissance
        ('System Info', 'systeminfo', 'reconnaissance', 'Get detailed system information', 'windows', 0, 1),
        ('Network Config', 'ipconfig /all', 'reconnaissance', 'Display network configuration', 'windows', 0, 1),
        ('Network Config (Linux)', 'ifconfig -a', 'reconnaissance', 'Display network configuration', 'linux', 0, 1),
        ('Running Processes', 'tasklist', 'reconnaissance', 'List all running processes', 'windows', 0, 1),
        ('Running Processes (Linux)', 'ps aux', 'reconnaissance', 'List all running processes', 'linux', 0, 1),
        ('Whoami', 'whoami /all', 'reconnaissance', 'Display current user privileges', 'windows', 0, 1),
        ('Network Connections', 'netstat -ano', 'reconnaissance', 'Show network connections', 'windows', 0, 1),
        ('List Users', 'net user', 'reconnaissance', 'List local users', 'windows', 0, 0),
        ('Check Admin Rights', 'net localgroup administrators', 'reconnaissance', 'List admin group members', 'windows', 0, 0),
        
        # File Operations
        ('List Directory', 'dir', 'file_ops', 'List current directory contents', 'windows', 0, 1),
        ('List Directory (Linux)', 'ls -la', 'file_ops', 'List current directory contents', 'linux', 0, 1),
        ('Current Directory', 'cd', 'file_ops', 'Show current directory', 'all', 0, 1),
        ('Find Files', 'dir /s /b *.txt', 'file_ops', 'Search for .txt files recursively', 'windows', 0, 0),
        ('Disk Usage', 'wmic logicaldisk get caption,freespace,size', 'file_ops', 'Check disk space', 'windows', 0, 0),
        
        # Persistence
        ('List Startup Programs', 'wmic startup list brief', 'persistence', 'List startup programs', 'windows', 0, 0),
        ('Check Scheduled Tasks', 'schtasks /query', 'persistence', 'List scheduled tasks', 'windows', 0, 0),
        ('List Services', 'sc query', 'persistence', 'List Windows services', 'windows', 0, 0),
        
        # Network
        ('Ping Test', 'ping -n 4 google.com', 'network', 'Test network connectivity', 'windows', 0, 0),
        ('Trace Route', 'tracert google.com', 'network', 'Trace network route', 'windows', 0, 0),
        ('DNS Lookup', 'nslookup google.com', 'network', 'DNS query', 'all', 0, 0),
        ('ARP Cache', 'arp -a', 'network', 'Display ARP cache', 'windows', 0, 0),
        
        # System
        ('Environment Variables', 'set', 'system', 'Display environment variables', 'windows', 0, 0),
        ('Installed Software', 'wmic product get name,version', 'system', 'List installed programs', 'windows', 0, 0),
        ('System Uptime', 'systeminfo | find "System Boot Time"', 'system', 'Check system uptime', 'windows', 0, 0),
        ('Check Antivirus', 'wmic /namespace:\\\\root\\SecurityCenter2 path AntiVirusProduct get displayName', 'system', 'List installed antivirus', 'windows', 0, 0),
    ]
    
    cursor.executemany('''
        INSERT INTO command_templates (name, command, category, description, os_type, usage_count, is_favorite)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', default_commands)
    
    conn.commit()
    print(f"[+] Seeded {len(default_commands)} default command templates")

# ===========================
# USER FUNCTIONS
# ===========================

def create_user(username, password_hash, role='operator'):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, password_hash, role)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def verify_user(username, password_hash):
    user = get_user(username)
    if user and user['password_hash'] == password_hash:
        return True
    return False

def update_user_password(username, new_password_hash):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE username = ?',
            (new_password_hash, username)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update password: {e}")
        return False

# ===========================
# AGENT FUNCTIONS
# ===========================

def register_agent(agent_id, alias, username, auth_token,
                   hostname=None, ip_address=None, os_info=None, agent_user=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO agents (agent_id, alias, username, auth_token, status, last_seen,
                                   hostname, ip_address, os_info, agent_user)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (agent_id, alias, username, auth_token, 'online', datetime.now(),
             hostname, ip_address, os_info, agent_user)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_agent(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
    agent = cursor.fetchone()
    conn.close()
    return dict(agent) if agent else None

def get_agent_by_alias(alias):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agents WHERE alias = ?', (alias,))
    agent = cursor.fetchone()
    conn.close()
    return dict(agent) if agent else None

def get_all_agents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agents')
    agents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return agents

def update_agent_identity(agent_id, hostname=None, ip_address=None, os_info=None, agent_user=None):
    """Backfill identity columns whenever the beacon carries them."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE agents
           SET hostname   = COALESCE(?, hostname),
               ip_address = COALESCE(?, ip_address),
               os_info    = COALESCE(?, os_info),
               agent_user = COALESCE(?, agent_user)
           WHERE agent_id = ?''',
        (hostname, ip_address, os_info, agent_user, agent_id)
    )
    conn.commit()
    conn.close()

def update_agent_status(agent_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE agents SET status = ?, last_seen = ? WHERE agent_id = ?',
        (status, datetime.now(), agent_id)
    )
    conn.commit()
    conn.close()

def update_agent_last_seen(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE agents SET last_seen = ?, status = ? WHERE agent_id = ?',
        (datetime.now(), 'online', agent_id)
    )
    conn.commit()
    conn.close()

# ===========================
# AGENT STATE FUNCTIONS (NEW)
# ✅ Replaces in-memory AGENT_STATE dict in incident_engine.py
# State survives server restarts, crashes, and deployments
# ===========================

def get_agent_state(agent_id):
    """
    Load behavioral state for an agent from the database.
    Returns a dict with failure_count, last_heartbeat,
    heartbeat_history, and task_timestamps.
    If no state exists yet, returns a fresh default state.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agent_state WHERE agent_id = ?', (agent_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "failure_count":     row['failure_count'],
            "last_heartbeat":    row['last_heartbeat'],
            # heartbeat_history and task_timestamps stored as JSON arrays
            "heartbeat_history": json.loads(row['heartbeat_history']),
            "task_timestamps":   json.loads(row['task_timestamps']),
        }

    # No state found — return clean defaults
    return {
        "failure_count":     0,
        "last_heartbeat":    None,
        "heartbeat_history": [],
        "task_timestamps":   [],
    }

def save_agent_state(agent_id, state):
    """
    Persist behavioral state for an agent to the database.
    Uses INSERT OR REPLACE so first call creates the row,
    subsequent calls update it.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Keep only last 5 heartbeat intervals (match deque maxlen=5)
    heartbeat_history = state.get("heartbeat_history", [])
    if len(heartbeat_history) > 5:
        heartbeat_history = heartbeat_history[-5:]

    # Keep only task timestamps within burst window (last 60 seconds max)
    task_timestamps = state.get("task_timestamps", [])

    cursor.execute('''
        INSERT OR REPLACE INTO agent_state 
            (agent_id, failure_count, last_heartbeat, heartbeat_history, task_timestamps, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        agent_id,
        state.get("failure_count", 0),
        state.get("last_heartbeat"),
        json.dumps(heartbeat_history),
        json.dumps(task_timestamps),
        datetime.now()
    ))

    conn.commit()
    conn.close()

def reset_agent_state(agent_id):
    """Reset behavioral state for an agent — used when agent reconnects"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM agent_state WHERE agent_id = ?', (agent_id,))
    conn.commit()
    conn.close()

# ===========================
# TASK FUNCTIONS
# ===========================

def create_task(task_id, agent_id, command):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO tasks (task_id, agent_id, command, status, queued_at) 
           VALUES (?, ?, ?, ?, ?)''',
        (task_id, agent_id, command, 'queued', datetime.now())
    )
    conn.commit()
    conn.close()

def get_task(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return dict(task) if task else None

# ✅ Batch fetch — used by list_agents() to avoid N+1 queries
def get_all_tasks():
    """Get all tasks across all agents"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def get_agent_tasks(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE agent_id = ? ORDER BY created_at DESC', (agent_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def get_pending_tasks(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM tasks WHERE agent_id = ? AND status = ? ORDER BY queued_at ASC LIMIT 1',
        (agent_id, 'queued')
    )
    task = cursor.fetchone()
    conn.close()
    return dict(task) if task else None

def update_task_status(task_id, status, output=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status == 'sent':
        cursor.execute(
            'UPDATE tasks SET status = ?, sent_at = ? WHERE task_id = ?',
            (status, datetime.now(), task_id)
        )
    elif status == 'done':
        cursor.execute(
            'UPDATE tasks SET status = ?, output = ?, completed_at = ? WHERE task_id = ?',
            (status, output, datetime.now(), task_id)
        )
    else:
        cursor.execute(
            'UPDATE tasks SET status = ? WHERE task_id = ?',
            (status, task_id)
        )
    
    conn.commit()
    conn.close()

# ===========================
# INCIDENT FUNCTIONS
# ===========================

def create_incident(incident_id, agent_id, agent_alias, incident_type, severity):
    """Create incident — deduplicates open incidents of same type"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''SELECT * FROM incidents 
           WHERE agent_id = ? AND type = ? AND status = ?''',
        (agent_id, incident_type, 'open')
    )
    
    if cursor.fetchone():
        conn.close()
        return False
    
    cursor.execute(
        '''INSERT INTO incidents (incident_id, agent_id, agent_alias, type, severity, status, start_time) 
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (incident_id, agent_id, agent_alias, incident_type, severity, 'open', datetime.now())
    )
    conn.commit()
    conn.close()
    return True

def get_incident(incident_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents WHERE incident_id = ?', (incident_id,))
    incident = cursor.fetchone()
    conn.close()
    return dict(incident) if incident else None

def get_all_incidents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents ORDER BY start_time DESC')
    incidents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return incidents

def get_open_incidents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE status = 'open' ORDER BY start_time DESC")
    incidents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return incidents

def get_agent_incidents(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents WHERE agent_id = ? ORDER BY start_time DESC', (agent_id,))
    incidents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return incidents

def resolve_incident(incident_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE incidents SET status = ?, resolved_time = ? WHERE incident_id = ?',
        ('resolved', datetime.now(), incident_id)
    )
    conn.commit()
    conn.close()

# ===========================
# EVENT FUNCTIONS
# ===========================

def create_event(event_id, agent_id, agent_alias, event_type, details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    details_json = json.dumps(details) if details else None
    cursor.execute(
        '''INSERT INTO events (event_id, agent_id, agent_alias, event_type, details, timestamp) 
           VALUES (?, ?, ?, ?, ?, ?)''',
        (event_id, agent_id, agent_alias, event_type, details_json, datetime.now())
    )
    conn.commit()
    conn.close()

def get_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
    event = cursor.fetchone()
    conn.close()
    return dict(event) if event else None

def get_all_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events ORDER BY timestamp DESC')
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events

def get_agent_events(agent_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE agent_id = ? ORDER BY timestamp DESC', (agent_id,))
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events

# ===========================
# COMMAND TEMPLATE FUNCTIONS
# ===========================

def get_all_command_templates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM command_templates ORDER BY category, name')
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return templates

def get_command_templates_by_category(category):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM command_templates WHERE category = ? ORDER BY name', (category,))
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return templates

def get_favorite_commands():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM command_templates WHERE is_favorite = 1 ORDER BY usage_count DESC')
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return templates

def get_popular_commands(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM command_templates ORDER BY usage_count DESC LIMIT ?', (limit,))
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return templates

def increment_command_usage(template_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE command_templates SET usage_count = usage_count + 1 WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()

def toggle_favorite_command(template_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE command_templates SET is_favorite = NOT is_favorite WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()

def create_command_template(name, command, category, description='', os_type='all'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO command_templates (name, command, category, description, os_type) 
           VALUES (?, ?, ?, ?, ?)''',
        (name, command, category, description, os_type)
    )
    conn.commit()
    conn.close()

def delete_command_template(template_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM command_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()

def get_command_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM command_templates ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_os_types():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT os_type FROM command_templates WHERE os_type != "all" ORDER BY os_type')
    os_types = [row['os_type'] for row in cursor.fetchall()]
    conn.close()
    return os_types

def get_command_templates_by_os(os_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM command_templates WHERE os_type = ? OR os_type = "all" ORDER BY name',
        (os_type,)
    )
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return templates

# ===========================
# UTILITY FUNCTIONS
# ===========================

def clear_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM events')
    cursor.execute('DELETE FROM incidents')
    cursor.execute('DELETE FROM tasks')
    cursor.execute('DELETE FROM agent_state')
    cursor.execute('DELETE FROM agents')
    cursor.execute('DELETE FROM users')
    conn.commit()
    conn.close()
    print("[!] Database cleared!")

def clear_events():
    """Clear all events from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM events')
    conn.commit()
    conn.close()
    print("[!] Events cleared!")

def clear_completed_tasks():
    """Clear only completed tasks from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE status = 'done'")
    conn.commit()
    conn.close()
    print("[!] Completed tasks cleared!")

def reset_database():
    """Reset entire database (drop all tables)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop all tables
    tables = ['events', 'incidents', 'tasks', 'agent_state', 'agents', 'command_templates', 'users']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    conn.commit()
    conn.close()
    print("[!] Database reset!")

def get_db_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}
    for table in ['users', 'agents', 'tasks', 'incidents', 'events', 'command_templates', 'agent_state']:
        cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
        stats[table] = cursor.fetchone()['count']
    conn.close()
    return stats