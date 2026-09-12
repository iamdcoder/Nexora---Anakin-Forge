from autonomous.discover import (
    SupplierCandidate,
    rank_suppliers,
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
        reasoning_id="RSN-TEST",
        intake_id="INT-TEST",
        objective=(
            "Secure industrial motors."
        ),
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
    minimum_price,
    target_price,
    maximum_price,
    delivery,
):

    return SupplierCandidate(
        name=name,
        policy={
            "price": {
                "target": target_price,
                "minimum": minimum_price,
                "maximum": maximum_price,
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
            "Supplier profile",
            "Product specification",
        ],
    )


def test_rank_suppliers_prefers_compatible_supplier():

    buyer = make_buyer()

    reasoning = make_reasoning()

    suppliers = [
        supplier(
            "Bad Supplier",
            130000,
            140000,
            150000,
            40,
        ),
        supplier(
            "Good Supplier",
            100000,
            110000,
            120000,
            30,
        ),
    ]

    ranked = rank_suppliers(
        reasoning,
        suppliers,
        buyer,
    )

    assert len(ranked) == 2

    assert (
        ranked[0].supplier.name
        == "Good Supplier"
    )

    assert (
        ranked[0].compatibility_score
        > ranked[1].compatibility_score
    )


def test_incompatible_price_is_flagged():

    buyer = make_buyer()

    reasoning = make_reasoning()

    suppliers = [
        supplier(
            "Expensive Supplier",
            130000,
            140000,
            150000,
            30,
        )
    ]

    ranked = rank_suppliers(
        reasoning,
        suppliers,
        buyer,
    )

    assert (
        ranked[0].price_score
        == 0.0
    )

    assert any(
        "price"
        in flag.lower()
        for flag in ranked[0].risk_flags
    )