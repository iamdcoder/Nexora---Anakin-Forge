from enum import Enum

from pydantic import BaseModel, Field, model_validator

class ProposalAction(str, Enum):
    OFFER = "offer"
    COUNTER = "counter"
    ACCEPT = "accept"
    WALK_AWAY = "walk_away"

class NegotiationProposal(BaseModel):

    round_number: int = Field(gt=0)
    price: float
    delivery_days: int
    payment_days: int
    sla_penalty: float
    sla_uptime: float
    action: ProposalAction
    accepted_offer: str | None = None
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_acceptance(self):
        if self.action == ProposalAction.ACCEPT:
            if self.accepted_offer not in (None, "buyer", "supplier"):
                raise ValueError("accepted_offer must be buyer, supplier, or null")
        if self.action != ProposalAction.ACCEPT and self.accepted_offer is not None:
            raise ValueError("accepted_offer is only valid for accept actions")
        return self
