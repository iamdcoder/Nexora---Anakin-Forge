from autonomous.evidence import (
    assess_supplier_evidence,
)

from autonomous.read import (
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

    assert assessment.evidence_score < 0.5

    assert len(assessment.claims) == 3

    assert any(
        claim.field == "delivery_days"
        and claim.status == "conflict"
        for claim in assessment.claims
    )

    assert any(
        "delivery" in flag.lower()
        for flag in assessment.risk_flags
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

    assert assessment.evidence_score == 0.95

    assert all(
        claim.status == "compatible"
        for claim in assessment.claims
    )

    assert assessment.risk_flags == []


def test_anakin_claims_and_provenance_are_preserved():
    source = SourceRead(
        url="https://supplier.example/anakin",
        status="read",
        title="Supplier Live Page",
        text=(
            "Delivery in 25 days. "
            "99.5% uptime. "
            "Net 60 payment terms."
        ),
        content_hash="sha256-example",
        provider="anakin",
        request_id="REQ-ANAKIN-123",
        duration_ms=842,
        credits_remaining=97,
        authenticated=True,
        source_mode="LIVE",
        claims={
            "delivery_days": 25,
            "payment_days": 60,
            "sla_uptime": 99.5,
            "warranty_months": 24,
        },
        evidence_snippets=[
            "Delivery in 25 days.",
            "99.5% uptime.",
        ],
        warnings=[],
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    assert assessment.source_provider == "anakin"
    assert assessment.source_mode == "LIVE"
    assert assessment.content_hash == "sha256-example"
    assert assessment.request_id == "REQ-ANAKIN-123"
    assert assessment.source_authenticated is True
    assert assessment.source_duration_ms == 842

    assert (
        assessment.extracted_attributes[
            "warranty_months"
        ]
        == 24
    )

    assert (
        assessment.extracted_attributes[
            "delivery_days"
        ]
        == 25
    )

    assert assessment.evidence_snippets


def test_procurement_attributes_are_extracted_from_supplier_evidence():
    source = SourceRead(
        url="https://supplier.example/product",
        status="read",
        title="Supplier Product Page",
        text=(
            "Product: Servo Motors. "
            "Delivery in 25 days. "
            "Net 60 payment terms. "
            "99.5% uptime. "
            "24 month warranty. "
            "Currently in stock. "
            "ISO 9001 certified."
        ),
        content_hash="hash-attributes",
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    attributes = assessment.extracted_attributes

    assert attributes["product"] == "Servo Motors"
    assert attributes["warranty_months"] == 24
    assert attributes["availability"] == "Currently in stock"
    assert attributes["certification"] == "ISO 9001"

    assert any(
        claim.field == "warranty_months"
        and claim.status == "observed"
        for claim in assessment.claims
    )

    assert any(
        claim.field == "availability"
        and claim.status == "compatible"
        for claim in assessment.claims
    )

    assert any(
        claim.field == "certification"
        and claim.status == "observed"
        for claim in assessment.claims
    )


def test_out_of_stock_becomes_a_risk_flag():
    source = SourceRead(
        url="https://supplier.example/inventory",
        status="read",
        title="Supplier Inventory",
        text=(
            "Product: Servo Motors. "
            "Currently out of stock. "
            "Estimated replenishment in 21 days."
        ),
        content_hash="hash-stock",
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    availability_claims = [
        claim
        for claim in assessment.claims
        if claim.field == "availability"
    ]

    assert availability_claims

    assert availability_claims[0].status == "conflict"
    assert availability_claims[0].severity == "high"

    assert any(
        "availability" in flag.lower()
        for flag in assessment.risk_flags
    )


def test_product_mismatch_is_detected_as_conflict():
    source = SourceRead(
        url="https://supplier.example/wrong-product",
        status="read",
        title="Supplier Product Page",
        text=(
            "Product: Industrial Pumps. "
            "Delivery in 20 days."
        ),
        content_hash="hash-product-mismatch",
    )

    assessment = assess_supplier_evidence(
        source=source,
        reasoning=make_reasoning(),
        buyer=make_buyer(),
    )

    assert any(
        claim.field == "product"
        and claim.status == "conflict"
        for claim in assessment.claims
    )

    assert any(
        "product" in flag.lower()
        for flag in assessment.risk_flags
    )