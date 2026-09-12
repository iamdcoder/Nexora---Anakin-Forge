from autonomous.discover import (
    SupplierCandidate,
)

from autonomous.reason import (
    ProcurementReasoning,
)

from autonomous.run_selection import (
    AutonomousSelectionRunRequest,
    _build_buyer_policy,
    _select_supplier,
)


def buyer_policy():

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
        "batna": "No-deal",
        "max_rounds": 8,
    }


def reasoning():

    return ProcurementReasoning(
        reasoning_id="RSN-TEST",
        intake_id="INT-TEST",
        objective="Secure industrial motors.",
        product_name="Industrial Servo Motors",
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
        confidence=0.90,
    )


def supplier(
    name,
    price_min,
    price_target,
    price_max,
    delivery,
):

    return SupplierCandidate(
        name=name,
        policy={
            "price": {
                "target": price_target,
                "minimum": price_min,
                "maximum": price_max,
            },
            "delivery": {
                "target_days": delivery,
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
        },
        evidence=[
            "Supplier website",
            "Product documentation",
        ],
    )


def test_buyer_policy_is_constructed():

    result = _build_buyer_policy(
        buyer_policy()
    )

    assert (
        result.price.target
        == 110000
    )


def test_selection_returns_best_supplier():

    buyer = _build_buyer_policy(
        buyer_policy()
    )

    suppliers = [
        supplier(
            "Supplier A",
            130000,
            140000,
            150000,
            30,
        ),
        supplier(
            "Supplier B",
            100000,
            110000,
            120000,
            30,
        ),
    ]

    selected, ranked = _select_supplier(
        reasoning(),
        suppliers,
        buyer,
        0.5,
    )

    assert (
        selected.supplier.name
        == "Supplier B"
    )

    assert len(ranked) == 2


def test_selection_run_request_accepts_candidates():

    request = (
        AutonomousSelectionRunRequest(
            text="Need 1000 servo motors.",
            suppliers=[
                supplier(
                    "Supplier A",
                    100000,
                    110000,
                    120000,
                    30,
                )
            ],
            buyer=buyer_policy(),
        )
    )

    assert len(
        request.suppliers
    ) == 1

    assert (
        request.suppliers[0].name
        == "Supplier A"
    )