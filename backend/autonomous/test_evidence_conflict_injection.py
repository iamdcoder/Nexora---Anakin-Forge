from autonomous.evidence import assess_supplier_evidence
from autonomous.read import SourceRead
from autonomous.reason import ProcurementReasoning
from models.policy import (
    DeliveryPolicy,
    PartyPolicy,
    PaymentPolicy,
    PricePolicy,
    SLAPolicy,
)


def buyer():
    return PartyPolicy(
        price=PricePolicy(
            target=110000,
            minimum=100000,
            maximum=120000,
        ),
        delivery=DeliveryPolicy(
            target_days=30,
            maximum_days=40,
        ),
        payment=PaymentPolicy(
            preferred_days=60,
            minimum_days=30,
        ),
        sla=SLAPolicy(
            minimum_uptime=98,
            minimum_penalty=1,
            maximum_penalty=5,
        ),
        batna="No-deal",
        max_rounds=8,
    )


def reasoning():
    return ProcurementReasoning(
        reasoning_id=(
            "RSN-CONFLICT-INJECTION"
        ),
        intake_id="INT-CONFLICT",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[
            "delivery",
            "sla",
            "price",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="test",
        confidence=0.95,
    )


def test_conflicting_claims_inside_one_supplier_page_are_not_hidden_by_first_match():

    source = SourceRead(
        url=(
            "https://supplier.example/"
            "malicious"
        ),
        status="read",
        provider="anakin",
        source_mode="LIVE",
        text=(
            "Official delivery: 30 days. "
            "Enterprise delivery: 90 days. "
            "Uptime: 99.9%. "
            "Fallback SLA: 95% uptime. "
            "Net 60 payment terms. "
            "Special enterprise payment: Net 15."
        ),
        claims={},
    )

    result = assess_supplier_evidence(
        source=source,
        reasoning=reasoning(),
        buyer=buyer(),
    )

    assert (
        result.evidence_score
        < 0.5
    )

    assert any(
        claim.field
        == "delivery_days"
        and claim.status
        == "conflict"
        for claim in result.claims
    )

    assert any(
        claim.field
        == "sla_uptime"
        and claim.status
        == "conflict"
        for claim in result.claims
    )

    assert any(
        claim.field
        == "payment_days"
        and claim.status
        == "conflict"
        for claim in result.claims
    )

    assert any(
        "conflicting delivery"
        in flag.lower()
        for flag
        in result.risk_flags
    )