import json

from audit.logger import AuditLogger
from audit.models import AuditEventType

def test_audit_event_is_logged(tmp_path):

    log_path = tmp_path / "audit.jsonl"

    logger = AuditLogger(
        path=str(log_path)
    )

    event = logger.log(
        negotiation_id="NEG-001",
        event_type=AuditEventType.NEGOTIATION_STARTED,
        actor="negotiation_engine",
        status="success",
        details={
            "buyer": "Buyer Corp",
            "supplier": "Supplier Corp",
        },
    )

    assert event.negotiation_id == "NEG-001"
    assert event.event_type == AuditEventType.NEGOTIATION_STARTED

    assert log_path.exists()

    lines = log_path.read_text(
        encoding="utf-8"
    ).strip().splitlines()

    assert len(lines) == 1

    saved_event = json.loads(lines[0])

    assert saved_event["negotiation_id"] == "NEG-001"
    assert saved_event["event_type"] == "negotiation_started"
    assert saved_event["actor"] == "negotiation_engine"
    assert saved_event["status"] == "success"

def test_multiple_audit_events_are_appended(tmp_path):

    log_path = tmp_path / "audit.jsonl"

    logger = AuditLogger(
        path=str(log_path)
    )

    logger.log(
        negotiation_id="NEG-002",
        event_type=AuditEventType.NEGOTIATION_STARTED,
        actor="negotiation_engine",
        status="success",
        details={},
    )

    logger.log(
        negotiation_id="NEG-002",
        event_type=AuditEventType.PROPOSAL_GENERATED,
        actor="buyer_agent",
        status="success",
        details={
            "price": 50000,
        },
        round_number=1,
    )

    lines = log_path.read_text(
        encoding="utf-8"
    ).strip().splitlines()

    assert len(lines) == 2