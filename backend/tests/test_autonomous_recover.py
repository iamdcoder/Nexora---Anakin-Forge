from autonomous.discover import (
    SupplierCandidate,
    rank_suppliers,
)

from autonomous.reason import (
    ProcurementReasoning,
)

from autonomous.recover import (
    RecoveryRunRequest,
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


def make_supplier(
    name,
    price_min,
    price_target,
    price_max,
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
        },
        evidence=[
            "Supplier website",
        ],
    )


def make_reasoning():

    return ProcurementReasoning(
        reasoning_id="RSN-RECOVER",
        intake_id="INT-RECOVER",
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


def test_recovery_request_limits_attempts():

    request = RecoveryRunRequest(
        text="Need industrial motors.",
        suppliers=[
            make_supplier(
                "Supplier A",
                100000,
                110000,
                120000,
            )
        ],
        buyer=buyer_policy(),
        max_attempts=3,
    )

    assert request.max_attempts == 3

    assert 1 <= request.max_attempts <= 10


def test_ranked_suppliers_provide_recovery_order():

    from models.policy import PartyPolicy

    buyer = PartyPolicy.model_validate(
        buyer_policy()
    )

    suppliers = [
        make_supplier(
            "Supplier A",
            130000,
            140000,
            150000,
        ),
        make_supplier(
            "Supplier B",
            100000,
            110000,
            120000,
        ),
        make_supplier(
            "Supplier C",
            105000,
            115000,
            125000,
        ),
    ]

    ranked = rank_suppliers(
        make_reasoning(),
        suppliers,
        buyer,
    )

    assert len(ranked) == 3

    assert (
        ranked[0].supplier.name
        in {
            "Supplier B",
            "Supplier C",
        }
    )

    assert (
        ranked[-1].supplier.name
        == "Supplier A"
    )