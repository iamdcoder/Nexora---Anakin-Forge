import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from audit.models import AuditEvent, AuditEventType

class AuditLogger:
    """Append-only local audit log with a tamper-evident hash chain."""

    def __init__(self, path: str = "data/audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _previous_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return "GENESIS"
        try:
            return json.loads(lines[-1]).get("event_hash", "GENESIS")
        except json.JSONDecodeError:
            return "GENESIS"

    @staticmethod
    def _hash_event(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def log(
        self,
        negotiation_id: str,
        event_type: AuditEventType,
        actor: str,
        status: str,
        details: dict,
        round_number: int | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            negotiation_id=negotiation_id,
            timestamp=datetime.now(timezone.utc),
            round_number=round_number,
            event_type=event_type,
            actor=actor,
            status=status,
            details=details,
        )
        record = event.model_dump(mode="json")
        record["previous_hash"] = self._previous_hash()
        record["event_hash"] = self._hash_event(record)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True) + "\n")
        return event

    def verify(self) -> dict:
        if not self.path.exists():
            return {"valid": True, "events": 0, "broken_at": None}
        previous = "GENESIS"
        events = 0
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            expected_previous = record.get("previous_hash")
            if expected_previous != previous:
                return {"valid": False, "events": events, "broken_at": index}
            supplied_hash = record.get("event_hash")
            payload = dict(record)
            payload.pop("event_hash", None)
            computed_hash = self._hash_event(payload)
            if supplied_hash != computed_hash:
                return {"valid": False, "events": events, "broken_at": index}
            previous = supplied_hash
            events += 1
        return {"valid": True, "events": events, "broken_at": None}
