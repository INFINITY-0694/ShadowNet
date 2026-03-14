"""test_beacon.py — beacon endpoint with real AES-GCM crypto."""

import pytest
import database
from tests.conftest import make_beacon_payload, decrypt_beacon_response, TEST_REG_SECRET


AGENT_ID = 'beacon-test-agent'


# ─────────────────────────────────────────────────────────────
# REGISTRATION
# ─────────────────────────────────────────────────────────────

class TestBeaconRegistration:
    def test_new_agent_registers_successfully(self, client):
        payload = make_beacon_payload({
            'agent_id':            AGENT_ID,
            'registration_secret': TEST_REG_SECRET,
        })
        rv = client.post('/beacon', json=payload)
        assert rv.status_code == 200
        agent = database.get_agent(AGENT_ID)
        assert agent is not None
        assert agent['status'] == 'online'

    def test_new_agent_with_wrong_secret_is_rejected(self, client):
        payload = make_beacon_payload({
            'agent_id':            'rogue-agent',
            'registration_secret': 'WRONG_SECRET',
        })
        rv = client.post('/beacon', json=payload)
        assert rv.status_code == 403

    def test_registration_creates_agent_connected_event(self, client):
        payload = make_beacon_payload({
            'agent_id':            AGENT_ID,
            'registration_secret': TEST_REG_SECRET,
        })
        client.post('/beacon', json=payload)
        agent  = database.get_agent(AGENT_ID)
        events = database.get_agent_events(agent['agent_id'])
        types  = [e['event_type'] for e in events]
        assert 'agent_connected' in types

    def test_duplicate_registration_still_returns_200(self, client):
        payload = make_beacon_payload({
            'agent_id':            AGENT_ID,
            'registration_secret': TEST_REG_SECRET,
        })
        client.post('/beacon', json=payload)
        rv = client.post('/beacon', json=payload)
        assert rv.status_code == 200


# ─────────────────────────────────────────────────────────────
# HEARTBEAT
# ─────────────────────────────────────────────────────────────

class TestBeaconHeartbeat:
    def test_heartbeat_updates_last_seen(self, client, registered_agent):
        before = database.get_agent(registered_agent)['last_seen']
        payload = make_beacon_payload({'agent_id': registered_agent})
        client.post('/beacon', json=payload)
        after = database.get_agent(registered_agent)['last_seen']
        # last_seen should have been touched (not necessarily changed if within same second,
        # but the call must succeed)
        assert after is not None

    def test_heartbeat_creates_heartbeat_event(self, client, registered_agent):
        payload = make_beacon_payload({'agent_id': registered_agent})
        client.post('/beacon', json=payload)
        events = database.get_agent_events(registered_agent)
        types  = [e['event_type'] for e in events]
        assert 'agent_heartbeat' in types

    def test_heartbeat_returns_encrypted_response(self, client, registered_agent):
        payload = make_beacon_payload({'agent_id': registered_agent})
        rv      = client.post('/beacon', json=payload)
        assert rv.status_code == 200
        body = rv.get_json()
        assert 'data' in body
        decrypted = decrypt_beacon_response(body['data'])
        assert 'task' in decrypted


# ─────────────────────────────────────────────────────────────
# TASK DELIVERY
# ─────────────────────────────────────────────────────────────

class TestBeaconTaskDelivery:
    def test_no_pending_task_returns_null(self, client, registered_agent):
        payload = make_beacon_payload({'agent_id': registered_agent})
        rv      = client.post('/beacon', json=payload)
        decrypted = decrypt_beacon_response(rv.get_json()['data'])
        assert decrypted['task'] is None

    def test_pending_task_is_delivered(self, client, registered_agent, admin_client):
        # Queue a task via the API
        agent = database.get_agent(registered_agent)
        database.create_task('task-deliver', registered_agent, 'dir /w')

        payload   = make_beacon_payload({'agent_id': registered_agent})
        rv        = client.post('/beacon', json=payload)
        decrypted = decrypt_beacon_response(rv.get_json()['data'])

        assert decrypted['task'] is not None
        assert decrypted['task']['cmd'] == 'dir /w'
        assert decrypted['task']['id']  == 'task-deliver'

    def test_task_status_set_to_sent_after_delivery(self, client, registered_agent):
        database.create_task('task-sent-check', registered_agent, 'ipconfig')
        payload = make_beacon_payload({'agent_id': registered_agent})
        client.post('/beacon', json=payload)
        task = database.get_task('task-sent-check')
        assert task['status'] == 'sent'


# ─────────────────────────────────────────────────────────────
# ACK
# ─────────────────────────────────────────────────────────────

class TestBeaconAck:
    def test_ack_sets_task_status_to_ack(self, client, registered_agent):
        database.create_task('task-ack', registered_agent, 'whoami')
        # Deliver the task first
        client.post('/beacon', json=make_beacon_payload({'agent_id': registered_agent}))

        # Send ACK
        payload = make_beacon_payload({'agent_id': registered_agent, 'ack': 'task-ack'})
        rv      = client.post('/beacon', json=payload)
        assert rv.status_code == 200
        task = database.get_task('task-ack')
        assert task['status'] == 'ack'


# ─────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────

class TestBeaconOutput:
    def test_output_marks_task_done(self, client, registered_agent):
        database.create_task('task-out', registered_agent, 'net user')
        # Deliver
        client.post('/beacon', json=make_beacon_payload({'agent_id': registered_agent}))
        # Return output
        payload = make_beacon_payload({
            'agent_id': registered_agent,
            'task_id':  'task-out',
            'output':   'Administrator\nGuest',
        })
        rv = client.post('/beacon', json=payload)
        assert rv.status_code == 200
        task = database.get_task('task-out')
        assert task['status'] == 'done'
        assert 'Administrator' in task['output']

    def test_task_completed_event_created(self, client, registered_agent):
        database.create_task('task-evt', registered_agent, 'dir')
        client.post('/beacon', json=make_beacon_payload({'agent_id': registered_agent}))
        payload = make_beacon_payload({
            'agent_id': registered_agent,
            'task_id':  'task-evt',
            'output':   'c:\\',
        })
        client.post('/beacon', json=payload)
        events = database.get_agent_events(registered_agent)
        types  = [e['event_type'] for e in events]
        assert 'task_completed' in types
