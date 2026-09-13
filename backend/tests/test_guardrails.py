from models.policy import (
    PartyPolicy,
    PricePolicy,
    DeliveryPolicy,
    PaymentPolicy,
    SLAPolicy,
)

from models.proposal import (
    NegotiationProposal,
    ProposalAction,
)

from guardrails.policy_validator import PolicyValidator
from guardrails.guardrail_engine import GuardrailEngine
def test_legal_validator_blocks_negative_price():

    proposal = NegotiationProposal(
        round_number=1,
        price=-10,
        delivery_days=30,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    policy = make_buyer_policy()

    result = GuardrailEngine.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
def make_buyer_policy():
    return PartyPolicy(
        price=PricePolicy(
            target=100,
            maximum=110,
        ),
        delivery=DeliveryPolicy(
            target_days=30,
            maximum_days=45,
        ),
        payment=PaymentPolicy(
            preferred_days=60,
            minimum_days=30,
        ),
        sla=SLAPolicy(
            minimum_uptime=98,
            minimum_penalty=2,
            maximum_penalty=5,
        ),
        batna="Existing supplier",
        max_rounds=10,
    )
def test_sla_penalty_below_minimum_is_blocked():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=35,
        payment_days=45,
        sla_penalty=0,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
    assert any(
        "below minimum" in violation
        for violation in result.violations
    )

def test_legal_validator_blocks_invalid_uptime():

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=30,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=101,
        action=ProposalAction.COUNTER,
    )

    policy = make_buyer_policy()

    result = GuardrailEngine.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
def test_sla_penalty_above_maximum_is_blocked():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=35,
        payment_days=45,
        sla_penalty=10,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"

def test_guardrail_result_identifies_validator():

    proposal = NegotiationProposal(
        round_number=1,
        price=500,
        delivery_days=30,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    policy = make_buyer_policy()

    result = GuardrailEngine.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
    assert result.validator == "policy"
def test_sla_uptime_below_policy_is_blocked():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=35,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=90,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"

def test_unknown_role_is_blocked():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=35,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "attacker",
    )

    assert result.status.value == "blocked"

def test_multiple_policy_violations_are_reported():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=500,
        delivery_days=100,
        payment_days=10,
        sla_penalty=10,
        sla_uptime=80,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
    assert len(result.violations) >= 4

def test_valid_proposal_passes():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=35,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "allowed"

def test_price_above_buyer_limit_is_blocked():

    policy = make_buyer_policy()

    proposal = NegotiationProposal(
        round_number=1,
        price=500,
        delivery_days=35,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )

    result = PolicyValidator.validate(
        proposal,
        policy,
        "buyer",
    )

    assert result.status.value == "blocked"
    assert len(result.violations) > 0