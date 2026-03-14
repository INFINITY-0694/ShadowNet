"""test_database.py — unit tests for database.py functions."""

import pytest
import database


# ─────────────────────────────────────────────────────────────
# USER FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestUsers:
    def test_create_and_get_user(self):
        ok = database.create_user('alice', 'hash_abc', 'operator')
        assert ok is True
        user = database.get_user('alice')
        assert user is not None
        assert user['username'] == 'alice'
        assert user['role']     == 'operator'

    def test_create_duplicate_user_returns_false(self):
        database.create_user('bob', 'hash1', 'operator')
        assert database.create_user('bob', 'hash2', 'admin') is False

    def test_get_nonexistent_user_returns_none(self):
        assert database.get_user('ghost') is None

    def test_update_user_password(self):
        database.create_user('carol', 'oldhash', 'developer')
        database.update_user_password('carol', 'newhash')
        user = database.get_user('carol')
        assert user['password_hash'] == 'newhash'


# ─────────────────────────────────────────────────────────────
# AGENT FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestAgents:
    def test_register_and_get_agent(self):
        database.create_user('sys', 'h', 'operator')
        ok = database.register_agent('ag-1', 'Alpha', 'sys', 'tok-1')
        assert ok is True
        agent = database.get_agent('ag-1')
        assert agent['alias'] == 'Alpha'
        assert agent['status'] == 'online'

    def test_register_duplicate_returns_false(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-2', 'Beta', 'sys', 'tok-2')
        assert database.register_agent('ag-2', 'Beta2', 'sys', 'tok-2b') is False

    def test_get_agent_by_alias(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-3', 'Gamma', 'sys', 'tok-3')
        agent = database.get_agent_by_alias('Gamma')
        assert agent['agent_id'] == 'ag-3'

    def test_get_agent_by_alias_nonexistent(self):
        assert database.get_agent_by_alias('DoesNotExist') is None

    def test_get_all_agents(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-4', 'D1', 'sys', 'tok-4')
        database.register_agent('ag-5', 'D2', 'sys', 'tok-5')
        agents = database.get_all_agents()
        aliases = [a['alias'] for a in agents]
        assert 'D1' in aliases
        assert 'D2' in aliases

    def test_update_agent_last_seen(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-6', 'E1', 'sys', 'tok-6')
        database.update_agent_last_seen('ag-6')
        agent = database.get_agent('ag-6')
        assert agent['last_seen'] is not None
        assert agent['status'] == 'online'


# ─────────────────────────────────────────────────────────────
# TASK FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestTasks:
    def _setup_agent(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-t', 'TaskAgent', 'sys', 'tok-t')
        return 'ag-t'

    def test_create_and_get_task(self):
        aid = self._setup_agent()
        database.create_task('task-1', aid, 'whoami')
        task = database.get_task('task-1')
        assert task['command'] == 'whoami'
        assert task['status']  == 'queued'

    def test_pending_task_returns_oldest(self):
        aid = self._setup_agent()
        database.create_task('task-a', aid, 'cmd_a')
        database.create_task('task-b', aid, 'cmd_b')
        pending = database.get_pending_tasks(aid)
        assert pending['task_id'] == 'task-a'

    def test_update_task_status_sent(self):
        aid = self._setup_agent()
        database.create_task('task-s', aid, 'dir')
        database.update_task_status('task-s', 'sent')
        task = database.get_task('task-s')
        assert task['status']  == 'sent'
        assert task['sent_at'] is not None

    def test_update_task_status_done(self):
        aid = self._setup_agent()
        database.create_task('task-d', aid, 'dir')
        database.update_task_status('task-d', 'done', output='file.txt')
        task = database.get_task('task-d')
        assert task['status']       == 'done'
        assert task['output']       == 'file.txt'
        assert task['completed_at'] is not None

    def test_get_all_tasks(self):
        aid = self._setup_agent()
        database.create_task('task-all-1', aid, 'a')
        database.create_task('task-all-2', aid, 'b')
        tasks = database.get_all_tasks()
        ids = [t['task_id'] for t in tasks]
        assert 'task-all-1' in ids
        assert 'task-all-2' in ids

    def test_no_pending_after_sent(self):
        aid = self._setup_agent()
        database.create_task('task-np', aid, 'x')
        database.update_task_status('task-np', 'sent')
        assert database.get_pending_tasks(aid) is None


# ─────────────────────────────────────────────────────────────
# INCIDENT FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestIncidents:
    def _setup_agent(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-i', 'IncAgent', 'sys', 'tok-i')
        return 'ag-i'

    def test_create_incident(self):
        aid = self._setup_agent()
        ok = database.create_incident('inc-1', aid, 'IncAgent', 'Test Incident', 'HIGH')
        assert ok is True
        inc = database.get_incident('inc-1')
        assert inc['severity'] == 'HIGH'
        assert inc['status']   == 'open'

    def test_incident_deduplication(self):
        aid = self._setup_agent()
        database.create_incident('inc-2', aid, 'IncAgent', 'Dup Type', 'MEDIUM')
        # Same agent + same type + open → should return False (no duplicate)
        ok = database.create_incident('inc-3', aid, 'IncAgent', 'Dup Type', 'MEDIUM')
        assert ok is False

    def test_resolve_incident(self):
        aid = self._setup_agent()
        database.create_incident('inc-4', aid, 'IncAgent', 'Resolvable', 'LOW')
        database.resolve_incident('inc-4')
        inc = database.get_incident('inc-4')
        assert inc['status'] == 'resolved'

    def test_get_open_incidents_filters_resolved(self):
        aid = self._setup_agent()
        database.create_incident('inc-5', aid, 'IncAgent', 'Open One', 'LOW')
        database.create_incident('inc-6', aid, 'IncAgent', 'Closed One', 'LOW')
        database.resolve_incident('inc-6')
        open_incs = database.get_open_incidents()
        ids = [i['incident_id'] for i in open_incs]
        assert 'inc-5' in ids
        assert 'inc-6' not in ids


# ─────────────────────────────────────────────────────────────
# EVENT FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestEvents:
    def _setup_agent(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-e', 'EvtAgent', 'sys', 'tok-e')
        return 'ag-e'

    def test_create_and_retrieve_event(self):
        aid = self._setup_agent()
        database.create_event('evt-1', aid, 'EvtAgent', 'agent_heartbeat', {'ping': 1})
        events = database.get_agent_events(aid)
        assert len(events) == 1
        assert events[0]['event_type'] == 'agent_heartbeat'

    def test_get_all_events(self):
        aid = self._setup_agent()
        database.create_event('evt-2', aid, 'EvtAgent', 'agent_connected')
        all_evts = database.get_all_events()
        assert any(e['event_id'] == 'evt-2' for e in all_evts)


# ─────────────────────────────────────────────────────────────
# AGENT STATE FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestAgentState:
    def test_default_state_for_new_agent(self):
        state = database.get_agent_state('unknown-ag')
        assert state['failure_count']     == 0
        assert state['last_heartbeat']    is None
        assert state['heartbeat_history'] == []
        assert state['task_timestamps']   == []

    def test_save_and_load_state(self):
        state = {
            'failure_count':     3,
            'last_heartbeat':    1234567890.0,
            'heartbeat_history': [5.0, 6.0, 7.0],
            'task_timestamps':   [1234567800.0],
        }
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-st', 'StateAg', 'sys', 'tok-st')
        database.save_agent_state('ag-st', state)
        loaded = database.get_agent_state('ag-st')
        assert loaded['failure_count']  == 3
        assert loaded['last_heartbeat'] == 1234567890.0
        assert loaded['heartbeat_history'] == [5.0, 6.0, 7.0]

    def test_heartbeat_history_trimmed_to_five(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-trim', 'TrimAg', 'sys', 'tok-trim')
        state = {
            'failure_count':     0,
            'last_heartbeat':    1.0,
            'heartbeat_history': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            'task_timestamps':   [],
        }
        database.save_agent_state('ag-trim', state)
        loaded = database.get_agent_state('ag-trim')
        assert len(loaded['heartbeat_history']) == 5
        assert loaded['heartbeat_history'] == [3.0, 4.0, 5.0, 6.0, 7.0]


# ─────────────────────────────────────────────────────────────
# COMMAND TEMPLATE FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestCommandTemplates:
    def test_seeded_templates_exist_after_init(self):
        # init_database seeds templates on first run; reset_db clears users/agents
        # but NOT command_templates — they remain from conftest init.
        templates = database.get_all_command_templates()
        assert len(templates) > 0

    def test_toggle_favorite(self):
        templates    = database.get_all_command_templates()
        template_id  = templates[0]['id']
        original     = templates[0]['is_favorite']
        database.toggle_favorite_command(template_id)
        updated = database.get_all_command_templates()
        new_val = next(t for t in updated if t['id'] == template_id)['is_favorite']
        assert bool(new_val) != bool(original)

    def test_increment_command_usage(self):
        templates   = database.get_all_command_templates()
        template_id = templates[0]['id']
        before      = templates[0]['usage_count']
        database.increment_command_usage(template_id)
        after = next(t for t in database.get_all_command_templates() if t['id'] == template_id)
        assert after['usage_count'] == before + 1

    def test_get_command_categories(self):
        cats = database.get_command_categories()
        assert 'reconnaissance' in cats

    def test_get_templates_by_os(self):
        windows_templates = database.get_command_templates_by_os('windows')
        for t in windows_templates:
            assert t['os_type'] in ('windows', 'all')


# ─────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────

class TestUtility:
    def test_clear_database_removes_users_and_agents(self):
        database.create_user('sys', 'h', 'operator')
        database.register_agent('ag-c', 'ClearAg', 'sys', 'tok-c')
        database.clear_database()
        assert database.get_all_agents() == []
        assert database.get_user('sys') is None

    def test_get_db_stats_has_expected_keys(self):
        stats = database.get_db_stats()
        for key in ('users', 'agents', 'tasks', 'incidents', 'events', 'command_templates', 'agent_state'):
            assert key in stats
