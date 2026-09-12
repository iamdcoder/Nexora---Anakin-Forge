from datetime import datetime
from enum import Enum

from pydantic import BaseModel

class AuditEventType(str, Enum):

    NEGOTIATION_STARTED = (
        "negotiation_started"
    )

    PROPOSAL_GENERATED = (
        "proposal_generated"
    )

    PROPOSAL_GENERATION_ATTEMPT = (
        "proposal_generation_attempt"
    )

    PROPOSAL_PARSE_ERROR = (
        "proposal_parse_error"
    )

    POLICY_CHECK = (
        "policy_check"
    )

    LEGAL_CHECK = (
        "legal_check"
    )

    PROPOSAL_APPROVED = (
        "proposal_approved"
    )

    PROPOSAL_BLOCKED = (
        "proposal_blocked"
    )

    PROPOSAL_REVISED = (
        "proposal_revised"
    )

    AGREEMENT_VALIDATION = (
        "agreement_validation"
    )

    AGREEMENT_REACHED = (
        "agreement_reached"
    )

    DEADLOCK = (
        "deadlock"
    )

    CONTRACT_GENERATED = (
        "contract_generated"
    )

    GOVERNANCE_EVENT = (
        "governance_event"
    )

class AuditEvent(BaseModel):

    event_id: str

    negotiation_id: str

    timestamp: datetime

    round_number: int | None = None

    event_type: AuditEventType

    actor: str

    status: str

    details: dict