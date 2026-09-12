from autonomous.discover import (
    SupplierCandidate,
    rank_suppliers,
)

from autonomous.reason import (
    ProcurementConstraint,
    ProcurementReasoning,
)

from autonomous.evidence import (
    SupplierEvidenceAssessment,
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
        reasoning_id="RSN-HARD-CONSTRAINT",
        intake_id="INT-HARD-CONSTRAINT",
        objective=(
            "Procure industrial servo motors."
        ),
        product_name="Industrial Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[
            "evidence",
            "price",
            "delivery",
        ],
        hard_constraints=[
            ProcurementConstraint(
                field="budget",
                value="120000",
                source="buyer_policy",
                priority="critical",
            ),
            ProcurementConstraint(
                field="delivery_days",
                value="30",
                source="buyer_requirement",
                priority="critical",
            ),
            ProcurementConstraint(
                field="sla_uptime",
                value="98",
                source="buyer_requirement",
                priority="critical",
            ),
        ],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief=(
            "Evaluate supplier feasibility before "
            "considering evidence quality."
        ),
        confidence=0.95,
    )


def make_supplier(
    name: str,
    *,
    price_minimum: float = 100000,
    price_target: float = 110000,
    price_maximum: float = 120000,
    delivery_target: int = 30,
    delivery_maximum: int = 40,
    payment_preferred: int = 60,
    payment_minimum: int = 30,
    sla_uptime: float = 98,
):

    return SupplierCandidate(
        name=name,
        policy={
            "price": {
                "target": price_target,
                "minimum": price_minimum,
                "maximum": price_maximum,
            },
            "delivery": {
                "target_days": delivery_target,
                "minimum_days": 20,
                "maximum_days": delivery_maximum,
            },
            "payment": {
                "preferred_days": payment_preferred,
                "minimum_days": payment_minimum,
                "maximum_days": 90,
            },
            "sla": {
                "minimum_uptime": sla_uptime,
                "maximum_uptime": 99.9,
                "minimum_penalty": 1,
                "maximum_penalty": 5,
            },
            "batna": "Alternative customer",
            "max_rounds": 8,
        },
        evidence=[
            "Live supplier page",
            "Product specification",
        ],
    )


def perfect_anakin_evidence():

    return SupplierEvidenceAssessment(
        source_status="read",
        source_url=(
            "https://supplier.example/live"
        ),
        source_provider="anakin",
        source_mode="LIVE",
        content_hash="sha256-perfect",
        request_id="REQ-ANAKIN-TEST",
        source_duration_ms=420,
        source_authenticated=True,
        extracted_attributes={
            "product": "Industrial Servo Motors",
            "delivery_days": 30,
            "payment_days": 60,
            "sla_uptime": 99.9,
            "warranty_months": 24,
            "availability": "Currently in stock",
            "certification": "ISO 9001",
        },
        evidence_snippets=[
            "Industrial Servo Motors",
            "Delivery in 30 days",
            "Net 60",
            "99.9% uptime",
            "24 month warranty",
            "Currently in stock",
            "ISO 9001 certified",
        ],
        claims=[],
        risk_flags=[],
        evidence_score=1.0,
        summary=(
            "Excellent live supplier evidence."
        ),
    )


def test_perfect_anakin_evidence_cannot_override_delivery_constraint():

    buyer = make_buyer()

    reasoning = make_reasoning()

    supplier = make_supplier(
        "Perfect Evidence / Slow Supplier",
        delivery_target=60,
        delivery_maximum=60,
    )

    supplier.evidence_assessment = (
        perfect_anakin_evidence()
    )

    ranked = rank_suppliers(
        reasoning,
        [supplier],
        buyer,
    )

    result = ranked[0]

    assert (
        result.evidence_score
        == 1.0
    )

    assert (
        result.delivery_score
        == 0.0
    )

    assert (
        result.compatibility_score
        == 0.0
    )

    assert (
        result.recommendation
        == "ineligible"
    )

    assert any(
        "hard procurement constraint failed"
        in flag.lower()
        for flag in result.risk_flags
    )


def test_perfect_anakin_evidence_cannot_override_budget_constraint():

    buyer = make_buyer()

    reasoning = make_reasoning()

    supplier = make_supplier(
        "Perfect Evidence / Over Budget",
        price_minimum=140000,
        price_target=145000,
        price_maximum=150000,
    )

    supplier.evidence_assessment = (
        perfect_anakin_evidence()
    )

    ranked = rank_suppliers(
        reasoning,
        [supplier],
        buyer,
    )

    result = ranked[0]

    assert (
        result.evidence_score
        == 1.0
    )

    assert (
        result.price_score
        == 0.0
    )

    assert (
        result.compatibility_score
        == 0.0
    )

    assert (
        result.recommendation
        == "ineligible"
    )


def test_feasible_supplier_can_still_use_anakin_evidence_score():

    buyer = make_buyer()

    reasoning = make_reasoning()

    supplier = make_supplier(
        "Feasible Supplier",
        price_minimum=100000,
        price_target=108000,
        price_maximum=115000,
        delivery_target=30,
        delivery_maximum=35,
        payment_preferred=60,
        payment_minimum=30,
        sla_uptime=98,
    )

    supplier.evidence_assessment = (
        perfect_anakin_evidence()
    )

    ranked = rank_suppliers(
        reasoning,
        [supplier],
        buyer,
    )

    result = ranked[0]

    assert (
        result.price_score
        > 0
    )

    assert (
        result.delivery_score
        > 0
    )

    assert (
        result.payment_score
        > 0
    )

    assert (
        result.sla_score
        > 0
    )

    assert (
        result.evidence_score
        == 1.0
    )

    assert (
        result.compatibility_score
        > 0
    )

    assert (
        result.recommendation
        in {
            "candidate",
            "strong_candidate",
        }
    )


def test_ineligible_supplier_loses_to_feasible_supplier_even_with_better_evidence():

    buyer = make_buyer()

    reasoning = make_reasoning()

    infeasible = make_supplier(
        "Infeasible Perfect Evidence",
        price_minimum=150000,
        price_target=155000,
        price_maximum=160000,
        delivery_target=60,
        delivery_maximum=60,
        sla_uptime=99.9,
    )

    infeasible.evidence_assessment = (
        perfect_anakin_evidence()
    )

    feasible = make_supplier(
        "Feasible Supplier",
        price_minimum=100000,
        price_target=110000,
        price_maximum=120000,
        delivery_target=30,
        delivery_maximum=40,
        sla_uptime=98,
    )

    feasible.evidence_assessment = (
        SupplierEvidenceAssessment(
            source_status="read",
            source_url=(
                "https://supplier.example/feasible"
            ),
            source_provider="anakin",
            source_mode="LIVE",
            content_hash="sha256-feasible",
            request_id="REQ-FEASIBLE",
            source_duration_ms=300,
            source_authenticated=True,
            extracted_attributes={
                "product": "Industrial Servo Motors",
                "delivery_days": 30,
                "payment_days": 60,
                "sla_uptime": 98,
            },
            evidence_snippets=[
                "Industrial Servo Motors",
                "Delivery in 30 days",
                "Net 60",
                "98% uptime",
            ],
            claims=[],
            risk_flags=[],
            evidence_score=0.75,
            summary=(
                "Good supplier evidence."
            ),
        )
    )

    ranked = rank_suppliers(
        reasoning,
        [
            infeasible,
            feasible,
        ],
        buyer,
    )

    assert (
        ranked[0].supplier.name
        == "Feasible Supplier"
    )

    assert (
        ranked[1].supplier.name
        == "Infeasible Perfect Evidence"
    )

    assert (
        ranked[1].compatibility_score
        == 0.0
    )

    assert (
        ranked[1].recommendation
        == "ineligible"
    )


def test_hard_constraints_are_not_softened_by_reasoning_priorities():

    buyer = make_buyer()

    reasoning = make_reasoning()

    reasoning.priorities = [
        "evidence",
        "quality",
        "documentation",
    ]

    supplier = make_supplier(
        "Evidence Heavy But Infeasible",
        price_minimum=145000,
        price_target=150000,
        price_maximum=160000,
        delivery_target=55,
        delivery_maximum=60,
        sla_uptime=99.9,
    )

    supplier.evidence_assessment = (
        perfect_anakin_evidence()
    )

    ranked = rank_suppliers(
        reasoning,
        [supplier],
        buyer,
    )

    result = ranked[0]

    assert (
        result.evidence_score
        == 1.0
    )

    assert (
        result.compatibility_score
        == 0.0
    )

    assert (
        result.recommendation
        == "ineligible"
    )

    assert (
        "Hard procurement constraint failed"
        in " ".join(
            result.risk_flags
        )
    )