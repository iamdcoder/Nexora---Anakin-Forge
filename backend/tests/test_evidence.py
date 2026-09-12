from autonomous.evidence import (
    assess_supplier_evidence,
)

from autonomous.read import (
    ProcurementRead,
    SourceRead,
)

from autonomous.reason import (
    ProcurementReasoning,
)

from models.policy import (
    DeliveryPolicy,
    PartyPolicy,
    PaymentPolicy,
    PricePolicy,
    SLAPolicy,
)


def make_buyer():

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


def make_reasoning():

    return ProcurementReasoning(
        reasoning_id="RSN-EVIDENCE",
        intake_id="INT-EVIDENCE",
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
            "payment",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="test",
        confidence=0.9,
    )


def test_conflicting_website_claim_is_detected():

    source = SourceRead(
        url="https://supplier.example",
        status="read",
        title="Supplier",
        text=(
            "Standard delivery is 45 days. "
            "SLA uptime is 97%. "
            "Net 30 payment terms."
        ),
        content_hash="hash",
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    assert (
        assessment.evidence_score
        < 0.5
    )

    assert len(
        assessment.claims
    ) == 2

    assert any(
        claim.field == "delivery_days"
        and claim.status == "conflict"
        for claim
        in assessment.claims
    )

    assert any(
        "delivery"
        in flag.lower()
        for flag
        in assessment.risk_flags
    )


def test_compatible_website_claim_is_detected():

    source = SourceRead(
        url="https://supplier.example",
        status="read",
        title="Supplier",
        text=(
            "Delivery in 25 days. "
            "99.5% uptime. "
            "Net 60 payment terms."
        ),
        content_hash="hash",
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    assert (
        assessment.evidence_score
        == 0.80
    )

    assert all(
        claim.status == "compatible"
        for claim
        in assessment.claims
    )

    assert (
        assessment.risk_flags
        == []
    )