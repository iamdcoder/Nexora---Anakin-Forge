from autonomous.discover import (
    SupplierCandidate,
    rank_suppliers,
)

from autonomous.evidence import (
    EvidenceFinding,
    SupplierEvidenceAssessment,
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
        reasoning_id="RSN-WEB",
        intake_id="INT-WEB",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="test",
        confidence=0.9,
    )


def policy():

    return {
        "price": {
            "target": 110000,
            "minimum": 100000,
            "maximum": 120000,
        },
        "delivery": {
            "target_days": 30,
            "minimum_days": 20,
            "maximum_days": 40,
        },
        "payment": {
            "preferred_days": 60,
            "minimum_days": 30,
            "maximum_days": 90,
        },
        "sla": {
            "minimum_uptime": 98,
            "maximum_uptime": 99.9,
            "minimum_penalty": 1,
            "maximum_penalty": 5,
        },
        "batna": "Other customer",
        "max_rounds": 8,
    }


def assessment(
    conflict: bool,
):

    claim = EvidenceFinding(
        field="delivery_days",
        observed_value=(
            "45"
            if conflict
            else "25"
        ),
        required_value="30",
        status=(
            "conflict"
            if conflict
            else "compatible"
        ),
        severity=(
            "high"
            if conflict
            else "low"
        ),
        source_url=(
            "https://supplier.example"
        ),
        explanation="test",
    )

    return SupplierEvidenceAssessment(
        source_status="read",
        source_url=(
            "https://supplier.example"
        ),
        claims=[claim],
        risk_flags=(
            ["delivery conflict"]
            if conflict
            else []
        ),
        evidence_score=(
            0.30
            if conflict
            else 0.65
        ),
        summary="test",
    )


def test_web_evidence_changes_supplier_ranking():

    good = SupplierCandidate(
        name="Supplier A",
        policy=policy(),
        evidence=["website"],
        evidence_assessment=assessment(
            False
        ),
    )

    conflicted = SupplierCandidate(
        name="Supplier B",
        policy=policy(),
        evidence=["website"],
        evidence_assessment=assessment(
            True
        ),
    )

    ranked = rank_suppliers(
        reasoning(),
        [
            conflicted,
            good,
        ],
        buyer(),
    )

    assert (
        ranked[0].supplier.name
        == "Supplier A"
    )

    assert (
        ranked[1].supplier.name
        == "Supplier B"
    )

    assert any(
        "delivery conflict"
        in flag.lower()
        for flag
        in ranked[1].risk_flags
    )