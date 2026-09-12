from autonomous.discover import SupplierCandidate, rank_suppliers
from autonomous.reason import ProcurementReasoning
from models.policy import DeliveryPolicy, PartyPolicy, PaymentPolicy, PricePolicy, SLAPolicy
from autonomous.evidence import assess_supplier_evidence
from autonomous.read import SourceRead


def make_buyer():
    return PartyPolicy(
        price=PricePolicy(target=110000, minimum=100000, maximum=120000),
        delivery=DeliveryPolicy(target_days=30, maximum_days=40),
        payment=PaymentPolicy(preferred_days=60, minimum_days=30),
        sla=SLAPolicy(minimum_uptime=98, minimum_penalty=1, maximum_penalty=5),
        batna="No-deal",
        max_rounds=8,
    )


def make_reasoning():
    return ProcurementReasoning(
        reasoning_id="RSN-ANAKIN-IMPACT",
        intake_id="INT-ANAKIN-IMPACT",
        objective="Procure industrial servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=["evidence", "delivery", "price"],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="Use supplier web evidence during selection.",
        confidence=0.9,
    )


def make_supplier(name, evidence_assessment=None):
    return SupplierCandidate(
        name=name,
        policy={
            "price": {"target": 110000, "minimum": 100000, "maximum": 120000},
            "delivery": {"target_days": 30, "minimum_days": 20, "maximum_days": 40},
            "payment": {"preferred_days": 60, "minimum_days": 30, "maximum_days": 90},
            "sla": {"minimum_uptime": 98, "maximum_uptime": 99.9, "minimum_penalty": 1, "maximum_penalty": 5},
            "batna": "Other customer",
            "max_rounds": 8,
        },
        evidence=["Supplier page read by Anakin."],
        source_url=f"https://example.com/{name.lower().replace(' ', '-')}",
        evidence_assessment=evidence_assessment,
    )


def test_anakin_evidence_can_change_supplier_ranking():
    buyer = make_buyer()
    reasoning = make_reasoning()

    strong_source = SourceRead(
        url="https://example.com/strong",
        status="read",
        provider="anakin",
        source_mode="LIVE",
        title="Servo Motors",
        text=(
            "Product: Servo Motors. Delivery in 30 days. "
            "Net 60 payment terms. 99.5% uptime. "
            "24 month warranty. Currently in stock. ISO 9001 certified."
        ),
        claims={
            "product": "Servo Motors",
            "delivery_days": 30,
            "payment_days": 60,
            "sla_uptime": 99.5,
            "warranty_months": 24,
            "availability": "Currently in stock",
            "certification": "ISO 9001",
        },
        content_hash="strong-hash",
        request_id="REQ-STRONG",
        duration_ms=100,
        authenticated=True,
    )

    weak_source = SourceRead(
        url="https://example.com/weak",
        status="read",
        provider="anakin",
        source_mode="LIVE",
        title="Servo Motors",
        text="Product: Servo Motors. Delivery in 45 days. Out of stock.",
        claims={
            "product": "Servo Motors",
            "delivery_days": 45,
            "availability": "Out of stock",
        },
        content_hash="weak-hash",
        request_id="REQ-WEAK",
        duration_ms=100,
        authenticated=True,
    )

    strong_assessment = assess_supplier_evidence(strong_source, reasoning, buyer)
    weak_assessment = assess_supplier_evidence(weak_source, reasoning, buyer)

    ranked = rank_suppliers(
        reasoning,
        [
            make_supplier("Strong Evidence Supplier", strong_assessment),
            make_supplier("Weak Evidence Supplier", weak_assessment),
        ],
        buyer,
    )

    assert ranked[0].supplier.name == "Strong Evidence Supplier"
    assert ranked[0].evidence_score > ranked[1].evidence_score


def test_anakin_provenance_survives_into_assessment():
    buyer = make_buyer()
    reasoning = make_reasoning()

    source = SourceRead(
        url="https://example.com/provenance",
        status="read",
        provider="anakin",
        source_mode="LIVE",
        title="Servo Motors",
        text="Delivery in 30 days. Net 60. 99.5% uptime.",
        claims={"delivery_days": 30, "payment_days": 60, "sla_uptime": 99.5},
        content_hash="abc123",
        request_id="REQ-PROV",
        duration_ms=321,
        authenticated=True,
    )

    assessment = assess_supplier_evidence(source, reasoning, buyer)

    assert assessment.source_provider == "anakin"
    assert assessment.source_mode == "LIVE"
    assert assessment.content_hash == "abc123"
    assert assessment.request_id == "REQ-PROV"
    assert assessment.source_authenticated is True
    assert assessment.source_duration_ms == 321


def test_anakin_conflict_evidence_lowers_selection_score():
    buyer = make_buyer()
    reasoning = make_reasoning()

    clean = SourceRead(
        url="https://example.com/clean",
        status="read",
        provider="anakin",
        source_mode="LIVE",
        title="Servo Motors",
        text="Delivery in 30 days. Net 60. 99.5% uptime.",
        claims={"delivery_days": 30, "payment_days": 60, "sla_uptime": 99.5},
    )

    conflict = SourceRead(
        url="https://example.com/conflict",
        status="read",
        provider="anakin",
        source_mode="LIVE",
        title="Servo Motors",
        text="Delivery in 45 days. 97% uptime. Out of stock.",
        claims={"delivery_days": 45, "sla_uptime": 97, "availability": "Out of stock"},
    )

    clean_assessment = assess_supplier_evidence(clean, reasoning, buyer)
    conflict_assessment = assess_supplier_evidence(conflict, reasoning, buyer)

    assert conflict_assessment.evidence_score < clean_assessment.evidence_score
    assert conflict_assessment.risk_flags
