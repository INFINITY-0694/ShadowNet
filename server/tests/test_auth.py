"""test_auth.py — authentication routes and RBAC decorators."""

import pytest
from tests.conftest import TEST_ADMIN_PASSWORD
import database
import bcrypt


def _make_user(role):
    """Helper: create a user with the given role and return (username, 'pass1234')."""
    username = f'{role}_tester'
    pw_hash  = bcrypt.hashpw(b'pass1234', bcrypt.gensalt(rounds=4)).decode()
    database.create_user(username, pw_hash, role)
    return username, 'pass1234'


# ─────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────

class TestLogin:
    def test_successful_admin_login(self, client):
        rv = client.post('/login', json={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        data = rv.get_json()
        assert rv.status_code == 200
        assert data['success'] is True
        assert data['role']    == 'admin'

    def test_wrong_password_returns_401(self, client):
        rv = client.post('/login', json={'username': 'admin', 'password': 'wrongpass'})
        assert rv.status_code == 401
        assert 'error' in rv.get_json()

    def test_unknown_user_returns_401(self, client):
        rv = client.post('/login', json={'username': 'nobody', 'password': 'x'})
        assert rv.status_code == 401

    def test_missing_username_returns_400(self, client):
        rv = client.post('/login', json={'password': 'x'})
        assert rv.status_code == 400

    def test_missing_password_returns_400(self, client):
        rv = client.post('/login', json={'username': 'admin'})
        assert rv.status_code == 400

    def test_login_with_operator_role(self, client):
        username, pw = _make_user('operator')
        rv = client.post('/login', json={'username': username, 'password': pw})
        data = rv.get_json()
        assert rv.status_code == 200
        assert data['role'] == 'operator'


# ─────────────────────────────────────────────────────────────
# SESSION CHECK
# ─────────────────────────────────────────────────────────────

class TestSessionCheck:
    def test_unauthenticated_returns_logged_in_false(self, client):
        rv   = client.get('/api/session')
        data = rv.get_json()
        assert data['logged_in'] is False

    def test_authenticated_returns_username_and_role(self, admin_client):
        rv   = admin_client.get('/api/session')
        data = rv.get_json()
        assert data['logged_in'] is True
        assert data['username']  == 'admin'
        assert data['role']      == 'admin'


# ─────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_session(self, admin_client):
        # Verify logged in
        rv = admin_client.get('/api/session')
        assert rv.get_json()['logged_in'] is True

        # Logout
        rv = admin_client.post('/logout')
        assert rv.status_code == 200
        assert rv.get_json()['success'] is True

        # Session should be cleared
        rv = admin_client.get('/api/session')
        assert rv.get_json()['logged_in'] is False


# ─────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────

class TestChangePassword:
    def test_successful_password_change(self, admin_client):
        rv = admin_client.post('/api/change-password', json={
            'old_password': TEST_ADMIN_PASSWORD,
            'new_password': 'newadminpass'
        })
        assert rv.status_code == 200
        assert rv.get_json()['success'] is True
        # Verify new password works
        user = database.get_user('admin')
        stored = user['password_hash']
        if isinstance(stored, str):
            stored = stored.encode()
        assert bcrypt.checkpw(b'newadminpass', stored)

    def test_wrong_old_password_returns_401(self, admin_client):
        rv = admin_client.post('/api/change-password', json={
            'old_password': 'wrongoldpass',
            'new_password': 'newpass'
        })
        assert rv.status_code == 401

    def test_unauthenticated_redirects(self, client):
        rv = client.post('/api/change-password', json={
            'old_password': 'a',
            'new_password': 'b'
        })
        assert rv.status_code == 302


# ─────────────────────────────────────────────────────────────
# RBAC — admin_required
# ─────────────────────────────────────────────────────────────

class TestAdminRequired:
    def test_admin_can_access_user_list(self, admin_client):
        rv = admin_client.get('/api/admin/users')
        assert rv.status_code == 200

    def test_operator_gets_403_on_admin_endpoint(self, operator_client):
        rv = operator_client.get('/api/admin/users')
        assert rv.status_code == 403

    def test_viewer_gets_403_on_admin_endpoint(self, viewer_client):
        rv = viewer_client.get('/api/admin/users')
        assert rv.status_code == 403

    def test_unauthenticated_page_redirects(self, client):
        # /settings is admin_required page route → redirect to login
        rv = client.get('/settings')
        assert rv.status_code == 302


# ─────────────────────────────────────────────────────────────
# RBAC — operator_required
# ─────────────────────────────────────────────────────────────

class TestOperatorRequired:
    def test_viewer_gets_403_on_task_create(self, viewer_client):
        rv = viewer_client.post('/api/task', json={
            'agent_alias': 'X',
            'command':     'whoami'
        })
        assert rv.status_code == 403

    def test_operator_can_reach_task_endpoint(self, operator_client, registered_agent):
        rv = operator_client.post('/api/task', json={
            'agent_alias': 'A1',
            'command':     'whoami'
        })
        # Either 200 (task created) or 404 (agent alias mismatch) — not 403
        assert rv.status_code != 403

    def test_unauthenticated_redirects_on_dashboard(self, client):
        rv = client.get('/')
        assert rv.status_code == 302
