"""Private-memory boundary for the Buyer and Supplier agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from governance.lyzr_governance import build_redaction_snapshot

@dataclass
class AgentEnvironment:
    actor: str
    private_policy: Any
    session_id: str
    shared_context: dict[str, Any] = field(default_factory=dict)

    def private_snapshot(self) -> dict[str, Any]:
        return build_redaction_snapshot(self.private_policy)

    def visible_context(self) -> dict[str, Any]:
        """Context intentionally excludes reservation prices, BATNA and raw policy."""
        return {
            "actor": self.actor,
            "session_id": self.session_id,
            "shared_context": self.shared_context,
            "private_policy": self.private_snapshot(),
        }

    def allowed_shared_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return only fields safe to expose outside the actor's private context."""
        forbidden = {
            "batna",
            "minimum_price",
            "maximum_price",
            "reservation_price",
            "raw_policy",
            "private_policy",
            "walk_away_price",
        }
        return {
            key: value
            for key, value in payload.items()
            if key not in forbidden
        }

    def can_read(self, field_name: str) -> bool:
        forbidden = {
            "batna",
            "minimum_price",
            "maximum_price",
            "reservation_price",
            "raw_policy",
        }
        return field_name not in forbidden
