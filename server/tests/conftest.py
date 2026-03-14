"""
conftest.py — ShadowNet pytest fixtures

Boot-order is critical:
1. Set required env vars (before any import of server_with_event)
2. Patch database.DB_FILE to a temp file (before server module runs init_database)
3. Import server_with_event (triggers init_database + admin user creation)
4. Each test gets a FRESH temp DB via the reset_db fixture (no lock contention)
"""

import os
import json
import base64
import tempfile
import pytest
import bcrypt

# ── 1. Environment vars must be set before server_with_event is imported ─────
TEST_AES_KEY          = b'12345678901234567890123456789012'  # exactly 32 bytes
TEST_FLASK_SECRET     = b'testsecret1234567890123456789012'
TEST_REG_SECRET       = 'TEST_REG_SECRET'
TEST_ADMIN_PASSWORD   = 'adminpass'

os.environ['SHADOWNET_AES_KEY']             = TEST_AES_KEY.decode()
os.environ['SHADOWNET_FLASK_SECRET']        = TEST_FLASK_SECRET.decode()
os.environ['SHADOWNET_REGISTRATION_SECRET'] = TEST_REG_SECRET
os.environ['SHADOWNET_ADMIN_PASSWORD']      = TEST_ADMIN_PASSWORD

# ── 2. Patch DB_FILE to a bootstrap temp file before server_with_event import ─
import database
import sqlite3 as _sqlite3

_boot_db_fd, _boot_db_path = tempfile.mkstemp(suffix='_boot.db')
os.close(_boot_db_fd)
database.DB_FILE = _boot_db_path
database.init_database()

# ── 3. Now it is safe to import the Flask app ─────────────────────────────────
import server_with_event as srv

# ── 4. Silence the heartbeat monitor's background DB writes so it never holds
#       a write lock that could race with per-test fixture writes.
import incident_engine as _ie
_ie.create_incident = lambda *a, **kw: False   # background thread write = no-op

# ── Crypto helper ─────────────────────────────────────────────────────────────
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def make_beacon_payload(data: dict) -> dict:
    """Encrypt a dict with the test AES key and return {"data": "<b64>"}."""
    aes   = AESGCM(TEST_AES_KEY)
    nonce = os.urandom(12)
    ct    = aes.encrypt(nonce, json.dumps(data).encode(), None)
    return {"data": base64.b64encode(nonce + ct).decode()}


def decrypt_beacon_response(b64: str) -> dict:
    """Decrypt a beacon response (base64 nonce+ct) with the test AES key."""
    raw         = base64.b64decode(b64)
    nonce, ct   = raw[:12], raw[12:]
    aes         = AESGCM(TEST_AES_KEY)
    return json.loads(aes.decrypt(nonce, ct, None).decode())


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def flask_app():
    srv.app.config['TESTING']          = True
    srv.app.config['WTF_CSRF_ENABLED'] = False
    srv.app.config['SECRET_KEY']       = TEST_FLASK_SECRET
    return srv.app


@pytest.fixture(autouse=True)
def reset_db():
    """Give each test a fresh, isolated SQLite DB — no lock contention."""
    # Create a new temp file for this test
    fd, path = tempfile.mkstemp(suffix='_test.db')
    os.close(fd)
    database.DB_FILE = path
    # Enable WAL mode on the fresh file so any concurrent reads are safe
    _conn = _sqlite3.connect(path, timeout=15)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.close()
    # Initialise schema + seed command templates
    database.init_database()
    # Create admin user
    admin_hash = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    database.create_user('admin', admin_hash, 'admin')
    # Reset in-memory access control settings
    srv.access_control_settings['enabled']   = False
    srv.access_control_settings['whitelist'] = ['127.0.0.1', '::1']
    yield
    # Cleanup temp file after test
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def admin_client(flask_app):
    c = flask_app.test_client()
    c.post('/login', json={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
    return c


def _create_and_login(flask_app, username, role):
    pw_hash = bcrypt.hashpw(b'pass1234', bcrypt.gensalt(rounds=4)).decode()
    database.create_user(username, pw_hash, role)
    c = flask_app.test_client()
    c.post('/login', json={'username': username, 'password': 'pass1234'})
    return c


@pytest.fixture
def operator_client(flask_app):
    return _create_and_login(flask_app, 'op_user', 'operator')


@pytest.fixture
def developer_client(flask_app):
    return _create_and_login(flask_app, 'dev_user', 'developer')


@pytest.fixture
def viewer_client(flask_app):
    return _create_and_login(flask_app, 'view_user', 'viewer')


@pytest.fixture
def registered_agent(client):
    """Register a fresh agent via the beacon endpoint and return its agent_id."""
    agent_id = 'test-agent-001'
    payload  = make_beacon_payload({
        'agent_id':            agent_id,
        'registration_secret': TEST_REG_SECRET,
    })
    client.post('/beacon', json=payload)
    return agent_id

