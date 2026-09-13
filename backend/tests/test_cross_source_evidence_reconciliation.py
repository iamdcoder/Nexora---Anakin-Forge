from autonomous.evidence_reconcile import reconcile_supplier_sources
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
        price=PricePolicy(target=110000, minimum=100000, maximum=120000),
        delivery=DeliveryPolicy(target_days=30, maximum_days=40),
        payment=PaymentPolicy(preferred_days=60, minimum_days=30),
        sla=SLAPolicy(minimum_uptime=98, minimum_penalty=1, maximum_penalty=5),
        batna="No-deal",
        max_rounds=8,
    )


def reasoning():
    return ProcurementReasoning(
        reasoning_id="RSN-CROSS-SOURCE",
        intake_id="INT-CROSS-SOURCE",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=["delivery", "sla", "price"],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="test",
        confidence=0.95,
    )


def test_cross_source_conflicts_are_reconciled():
    sources = [
        SourceRead(
            url="https://supplier.example/products",
            status="read",
            provider="anakin",
            source_mode="LIVE",
            text=(
                "Servo Motors. Delivery 30 days. Net 60. Uptime 99.9%."
            ),
        ),
        SourceRead(
            url="https://supplier.example/enterprise-terms",
            status="read",
            provider="anakin",
            source_mode="LIVE",
            text=(
                "Enterprise terms: Delivery 90 days. Net 15. Uptime 95%."
            ),
        ),
    ]

    result = reconcile_supplier_sources(
        sources=sources,
        reasoning=reasoning(),
        buyer=buyer(),
    )

    assert result.extracted_attributes["source_count"] == 2
    assert result.evidence_score < 0.5
    assert len(result.extracted_attributes["source_urls"]) == 2

    conflicts = {
        claim.field
        for claim in result.claims
        if claim.status == "conflict"
    }
    assert {"delivery_days", "payment_days", "sla_uptime"} <= conflicts
    assert any("conflicting delivery" in flag.lower() for flag in result.risk_flags)
