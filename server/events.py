# events.py
import time
import uuid


AGENT_CONNECTED  = "agent_connected"
AGENT_HEARTBEAT  = "agent_heartbeat"
AGENT_DELAYED    = "agent_delayed"

TASK_QUEUED      = "task_queued"
TASK_SENT        = "task_sent"
TASK_ACK         = "task_ack"
TASK_COMPLETED   = "task_completed"


def create_event(event_type, agent_id, agent_alias, details=None):
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "event_type": event_type,
        "agent_id": agent_id,
        "agent_alias": agent_alias,
        "details": details or {}
    }
