"""test_admin.py — admin API endpoints."""

import pytest
import database
import bcrypt
from tests.conftest import TEST_ADMIN_PASSWORD


# ─────────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────────

class TestUserManagement:
    def test_list_users_includes_admin(self, admin_client):
        rv   = admin_client.get('/api/admin/users')
        assert rv.status_code == 200
        users = rv.get_json()
        assert any(u['username'] == 'admin' for u in users)

    def test_create_user_success(self, admin_client):
        rv = admin_client.post('/api/admin/users', json={
            'username': 'newop',
            'password': 'secure123',
            'role':     'operator',
        })
        assert rv.status_code == 200
        assert database.get_user('newop') is not None

    def test_create_user_duplicate_returns_400(self, admin_client):
        admin_client.post('/api/admin/users', json={
            'username': 'dupuser',
            'password': 'pass1234',
            'role':     'viewer',
        })
        rv = admin_client.post('/api/admin/users', json={
            'username': 'dupuser',
            'password': 'pass1234',
            'role':     'viewer',
        })
        assert rv.status_code == 400

    def test_create_user_invalid_role_returns_400(self, admin_client):
        rv = admin_client.post('/api/admin/users', json={
            'username': 'badrole',
            'password': 'pass1234',
            'role':     'superuser',
        })
        assert rv.status_code == 400

    def test_create_user_short_password_returns_400(self, admin_client):
        rv = admin_client.post('/api/admin/users', json={
            'username': 'shortpw',
            'password': 'abc',
            'role':     'viewer',
        })
        assert rv.status_code == 400

    def test_delete_user_success(self, admin_client):
        admin_client.post('/api/admin/users', json={
            'username': 'todelete',
            'password': 'pass1234',
            'role':     'viewer',
        })
        rv = admin_client.delete('/api/admin/users/todelete')
        assert rv.status_code == 200
        assert database.get_user('todelete') is None

    def test_cannot_delete_admin_user(self, admin_client):
        rv = admin_client.delete('/api/admin/users/admin')
        assert rv.status_code == 403

    def test_delete_nonexistent_user_returns_404(self, admin_client):
        rv = admin_client.delete('/api/admin/users/ghostuser')
        assert rv.status_code == 404

    def test_non_admin_cannot_list_users(self, operator_client):
        rv = operator_client.get('/api/admin/users')
        assert rv.status_code == 403

    def test_non_admin_cannot_create_user(self, operator_client):
        rv = operator_client.post('/api/admin/users', json={
            'username': 'sneaky',
            'password': 'pass1234',
            'role':     'viewer',
        })
        assert rv.status_code == 403

    def test_non_admin_cannot_delete_user(self, operator_client):
        rv = operator_client.delete('/api/admin/users/admin')
        assert rv.status_code == 403


# ─────────────────────────────────────────────────────────────
# VERIFY ADMIN PASSWORD
# ─────────────────────────────────────────────────────────────

class TestVerifyAdminPassword:
    def test_correct_password_returns_verified(self, admin_client):
        rv = admin_client.post('/api/admin/verify-password',
                               json={'password': TEST_ADMIN_PASSWORD})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['verified'] is True

    def test_wrong_password_returns_401(self, admin_client):
        rv = admin_client.post('/api/admin/verify-password',
                               json={'password': 'wrongpassword'})
        assert rv.status_code == 401

    def test_non_admin_gets_403(self, operator_client):
        rv = operator_client.post('/api/admin/verify-password',
                                  json={'password': 'pass1234'})
        assert rv.status_code == 403


# ─────────────────────────────────────────────────────────────
# SYSTEM INFO
# ─────────────────────────────────────────────────────────────

class TestSystemInfo:
    def test_returns_expected_keys(self, admin_client):
        rv   = admin_client.get('/api/admin/system-info')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'db_size'      in data
        assert 'total_agents' in data
        assert 'total_events' in data

    def test_total_agents_is_integer(self, admin_client):
        rv   = admin_client.get('/api/admin/system-info')
        data = rv.get_json()
        assert isinstance(data['total_agents'], int)


# ─────────────────────────────────────────────────────────────
# CLEAR EVENTS / TASKS
# ─────────────────────────────────────────────────────────────

class TestClearOperations:
    def test_clear_events(self, admin_client, registered_agent):
        # Events exist after registration
        assert len(database.get_all_events()) > 0
        rv = admin_client.post('/api/admin/clear-events')
        assert rv.status_code == 200
        assert database.get_all_events() == []

    def test_clear_completed_tasks_keeps_queued(self, admin_client, registered_agent):
        database.create_task('task-queued',   registered_agent, 'a')
        database.create_task('task-finished', registered_agent, 'b')
        database.update_task_status('task-finished', 'done', output='ok')

        rv = admin_client.post('/api/admin/clear-tasks')
        assert rv.status_code == 200

        remaining = database.get_all_tasks()
        ids = [t['task_id'] for t in remaining]
        assert 'task-queued'   in ids
        assert 'task-finished' not in ids


# ─────────────────────────────────────────────────────────────
# ACCESS CONTROL
# ─────────────────────────────────────────────────────────────

class TestAccessControl:
    def test_get_returns_enabled_and_whitelist(self, admin_client):
        rv   = admin_client.get('/api/admin/access-control')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'enabled'   in data
        assert 'whitelist' in data

    def test_post_enables_access_control(self, admin_client):
        rv = admin_client.post('/api/admin/access-control', json={'enabled': True})
        assert rv.status_code == 200
        assert rv.get_json()['enabled'] is True

    def test_add_ip_to_whitelist(self, admin_client):
        rv = admin_client.post('/api/admin/access-control/add', json={'ip': '10.0.0.1'})
        assert rv.status_code == 200
        assert '10.0.0.1' in rv.get_json()['whitelist']

    def test_remove_ip_from_whitelist(self, admin_client):
        admin_client.post('/api/admin/access-control/add', json={'ip': '10.0.0.2'})
        rv = admin_client.post('/api/admin/access-control/remove', json={'ip': '10.0.0.2'})
        assert rv.status_code == 200
        assert '10.0.0.2' not in rv.get_json()['whitelist']

    def test_cannot_remove_localhost(self, admin_client):
        rv = admin_client.post('/api/admin/access-control/remove', json={'ip': '127.0.0.1'})
        assert rv.status_code == 400

    def test_add_empty_ip_returns_400(self, admin_client):
        rv = admin_client.post('/api/admin/access-control/add', json={'ip': ''})
        assert rv.status_code == 400
