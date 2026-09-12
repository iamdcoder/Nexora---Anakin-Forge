from autonomous.act import (
    ActRequest,
    _has_critical_missing_information,
    _resolve_product_name,
    _resolve_quantity,
)

from autonomous.reason import ProcurementReasoning


def make_reasoning():

    return ProcurementReasoning(
        reasoning_id="RSN-TEST123",
        intake_id="INT-TEST123",
        objective=(
            "Secure 1000 units of Industrial "
            "Servo Motors under acceptable terms."
        ),
        product_name="Industrial Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98.0,
        target_sla_penalty=2.0,
        currency="INR",
        priorities=[
            "Meet the requested product/service requirement",
            "Secure the full required quantity",
            "Meet the required delivery timeline",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief=(
            "NEXORA PROCUREMENT REASONING BRIEF"
        ),
        confidence=0.90,
    )


def make_request():

    return ActRequest(
        reasoning=make_reasoning(),
        buyer={
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
        },
        supplier={
            "price": {
                "target": 120000,
                "minimum": 100000,
                "maximum": 130000,
            },
            "delivery": {
                "target_days": 30,
                "minimum_days": 20,
                "maximum_days": 40,
            },
            "payment": {
                "preferred_days": 45,
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
    )


def test_critical_missing_information_is_detected():

    reasoning = make_reasoning()

    reasoning.missing_information = [
        "Required quantity",
        "Transaction currency",
    ]

    result = (
        _has_critical_missing_information(
            reasoning
        )
    )

    assert (
        "Required quantity"
        in result
    )

    assert (
        "Transaction currency"
        not in result
    )


def test_product_name_prefers_explicit_request():

    request = make_request()

    request.product_name = "Explicit Product"

    assert (
        _resolve_product_name(request)
        == "Explicit Product"
    )


def test_product_name_falls_back_to_reasoning():

    request = make_request()

    request.product_name = None

    assert (
        _resolve_product_name(request)
        == "Industrial Servo Motors"
    )


def test_quantity_falls_back_to_reasoning():

    request = make_request()

    request.quantity = None

    assert (
        _resolve_quantity(request)
        == 1000
    )


def test_act_request_contains_reasoning():

    request = make_request()

    assert (
        request.reasoning.reasoning_id
        == "RSN-TEST123"
    )

    assert request.reasoning.confidence == 0.90