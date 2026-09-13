from models.proposal import (
    NegotiationProposal,
    ProposalAction,
)

from guardrails.legal_validator import LegalValidator

def make_proposal(**overrides):

    data = {
        "round_number": 1,
        "price": 100,
        "delivery_days": 30,
        "payment_days": 30,
        "sla_penalty": 2,
        "sla_uptime": 98,
        "action": ProposalAction.COUNTER,
    }

    data.update(overrides)

    return NegotiationProposal(**data)

def test_valid_proposal_passes():

    result = LegalValidator.validate(
        make_proposal()
    )

    assert result.status.value == "allowed"

def test_low_sla_uptime_is_blocked():

    result = LegalValidator.validate(
        make_proposal(
            sla_uptime=90
        )
    )

    assert result.status.value == "blocked"

def test_excessive_payment_period_is_blocked():

    result = LegalValidator.validate(
        make_proposal(
            payment_days=500
        )
    )

    assert result.status.value == "blocked"

def test_excessive_delivery_period_is_blocked():

    result = LegalValidator.validate(
        make_proposal(
            delivery_days=4000
        )
    )

    assert result.status.value == "blocked"