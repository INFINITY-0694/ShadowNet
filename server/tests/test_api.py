"""test_api.py — REST API endpoint tests."""

import pytest
import database
from tests.conftest import TEST_REG_SECRET, make_beacon_payload


def _register_agent(client, agent_id='api-test-agent'):
    payload = make_beacon_payload({
        'agent_id':            agent_id,
        'registration_secret': TEST_REG_SECRET,
    })
    client.post('/beacon', json=payload)
    return agent_id


# ─────────────────────────────────────────────────────────────
# /agents
# ─────────────────────────────────────────────────────────────

class TestAgentsEndpoint:
    def test_returns_empty_list_when_no_agents(self, admin_client):
        rv = admin_client.get('/agents')
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_returns_registered_agents(self, admin_client, registered_agent):
        rv   = admin_client.get('/agents')
        data = rv.get_json()
        assert len(data) == 1
        agent = data[0]
        assert 'alias'      in agent
        assert 'status'     in agent
        assert 'risk_level' in agent

    def test_requires_login(self, client):
        rv = client.get('/agents')
        assert rv.status_code == 302


# ─────────────────────────────────────────────────────────────
# /events
# ─────────────────────────────────────────────────────────────

class TestEventsEndpoint:
    def test_returns_empty_list_initially(self, admin_client):
        rv = admin_client.get('/events')
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_events_appear_after_beacon(self, admin_client, registered_agent):
        rv    = admin_client.get('/events')
        types = [e['event_type'] for e in rv.get_json()]
        assert 'agent_connected' in types

    def test_requires_login(self, client):
        rv = client.get('/events')
        assert rv.status_code == 302


# ─────────────────────────────────────────────────────────────
# /incidents
# ─────────────────────────────────────────────────────────────

class TestIncidentsEndpoint:
    def test_returns_empty_list_initially(self, admin_client):
        rv = admin_client.get('/incidents')
        assert rv.status_code == 200
        assert rv.get_json() == []


# ─────────────────────────────────────────────────────────────
# /api/agent/<alias>
# ─────────────────────────────────────────────────────────────

class TestAgentDetail:
    def test_404_for_unknown_alias(self, admin_client):
        rv = admin_client.get('/api/agent/NoSuchAlias')
        assert rv.status_code == 404

    def test_returns_correct_structure(self, admin_client, registered_agent):
        agent = database.get_agent(registered_agent)
        alias = agent['alias']
        rv    = admin_client.get(f'/api/agent/{alias}')
        assert rv.status_code == 200
        data  = rv.get_json()
        for key in ('alias', 'status', 'tasks', 'events', 'heartbeat_sessions',
                    'task_event_groups', 'incidents'):
            assert key in data

    def test_tasks_list_is_populated(self, admin_client, registered_agent):
        database.create_task('task-detail', registered_agent, 'ver')
        agent = database.get_agent(registered_agent)
        rv    = admin_client.get(f'/api/agent/{agent["alias"]}')
        tasks = rv.get_json()['tasks']
        assert any(t['task_id'] == 'task-detail' for t in tasks)


# ─────────────────────────────────────────────────────────────
# /api/dashboard/stats
# ─────────────────────────────────────────────────────────────

class TestDashboardStats:
    def test_all_keys_present(self, admin_client):
        rv   = admin_client.get('/api/dashboard/stats')
        assert rv.status_code == 200
        data = rv.get_json()
        for key in ('active_agents', 'total_agents', 'open_incidents',
                    'total_incidents', 'completed_tasks', 'total_tasks',
                    'pending_tasks', 'recent_events'):
            assert key in data

    def test_total_agents_matches_db(self, admin_client, registered_agent):
        rv   = admin_client.get('/api/dashboard/stats')
        data = rv.get_json()
        assert data['total_agents'] == len(database.get_all_agents())

    def test_requires_login(self, client):
        rv = client.get('/api/dashboard/stats')
        assert rv.status_code == 302


# ─────────────────────────────────────────────────────────────
# /api/task
# ─────────────────────────────────────────────────────────────

class TestTaskCreate:
    def test_create_task_successfully(self, operator_client, registered_agent):
        agent = database.get_agent(registered_agent)
        rv    = operator_client.post('/api/task', json={
            'agent_alias': agent['alias'],
            'command':     'whoami',
        })
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'task_id' in data
        assert data['agent'] == agent['alias']

    def test_missing_agent_alias_returns_400(self, operator_client):
        rv = operator_client.post('/api/task', json={'command': 'whoami'})
        assert rv.status_code == 400

    def test_missing_command_returns_400(self, operator_client, registered_agent):
        agent = database.get_agent(registered_agent)
        rv    = operator_client.post('/api/task', json={'agent_alias': agent['alias']})
        assert rv.status_code == 400

    def test_unknown_agent_alias_returns_404(self, operator_client):
        rv = operator_client.post('/api/task', json={
            'agent_alias': 'NoSuchAgent',
            'command':     'whoami',
        })
        assert rv.status_code == 404

    def test_task_appears_in_db(self, operator_client, registered_agent):
        agent = database.get_agent(registered_agent)
        operator_client.post('/api/task', json={
            'agent_alias': agent['alias'],
            'command':     'ipconfig',
        })
        tasks = database.get_agent_tasks(registered_agent)
        cmds  = [t['command'] for t in tasks]
        assert 'ipconfig' in cmds

    def test_viewer_cannot_create_task(self, viewer_client, registered_agent):
        agent = database.get_agent(registered_agent)
        rv    = viewer_client.post('/api/task', json={
            'agent_alias': agent['alias'],
            'command':     'dir',
        })
        assert rv.status_code == 403


# ─────────────────────────────────────────────────────────────
# /api/commands
# ─────────────────────────────────────────────────────────────

class TestCommandsAPI:
    def test_get_all_commands(self, admin_client):
        rv = admin_client.get('/api/commands')
        assert rv.status_code == 200
        assert len(rv.get_json()) > 0

    def test_get_categories_includes_reconnaissance(self, admin_client):
        rv   = admin_client.get('/api/commands/categories')
        cats = rv.get_json()
        assert 'reconnaissance' in cats

    def test_get_os_types(self, admin_client):
        rv      = admin_client.get('/api/commands/os-types')
        os_list = rv.get_json()
        assert 'windows' in os_list

    def test_get_commands_by_os_windows(self, admin_client):
        rv = admin_client.get('/api/commands/by-os/windows')
        assert rv.status_code == 200
        for t in rv.get_json():
            assert t['os_type'] in ('windows', 'all')

    def test_toggle_favorite(self, admin_client):
        templates   = database.get_all_command_templates()
        template_id = templates[0]['id']
        rv          = admin_client.post(f'/api/commands/{template_id}/favorite')
        assert rv.status_code == 200
        assert rv.get_json()['success'] is True

    def test_favorites_endpoint(self, admin_client):
        rv = admin_client.get('/api/commands/favorites')
        assert rv.status_code == 200
        assert isinstance(rv.get_json(), list)


# ─────────────────────────────────────────────────────────────
# /api/incident/<id>
# ─────────────────────────────────────────────────────────────

class TestIncidentDetail:
    def _create_incident(self, registered_agent):
        database.create_incident('inc-det', registered_agent, 'A1', 'Test', 'LOW')

    def test_404_for_missing_incident(self, admin_client):
        rv = admin_client.get('/api/incident/no-such-id')
        assert rv.status_code == 404

    def test_get_incident_returns_structure(self, admin_client, registered_agent):
        database.create_incident('inc-d2', registered_agent, 'A1', 'TestType', 'MEDIUM')
        rv   = admin_client.get('/api/incident/inc-d2')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'incident' in data
        assert 'events'   in data
        assert 'tasks'    in data

    def test_patch_resolves_incident(self, admin_client, registered_agent):
        database.create_incident('inc-res', registered_agent, 'A1', 'PatchType', 'LOW')
        rv = admin_client.patch('/api/incident/inc-res')
        assert rv.status_code == 200
        inc = database.get_incident('inc-res')
        assert inc['status'] == 'resolved'
