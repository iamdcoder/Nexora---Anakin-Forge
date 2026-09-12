from autonomous.run import (
    AutonomousRunRequest,
    _policy_from_dict,
)


def make_policy():

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


def test_policy_conversion():

    result = _policy_from_dict(
        make_policy()
    )

    assert result.price.target == 110000

    assert (
        result.delivery.target_days
        == 30
    )

    assert (
        result.payment.preferred_days
        == 60
    )


def test_autonomous_request_contains_all_stages():

    request = AutonomousRunRequest(
        text=(
            "Product: Industrial Servo Motors. "
            "Quantity: 1000 units. "
            "Delivery within 30 days."
        ),
        buyer=make_policy(),
        supplier=make_policy(),
        buyer_name="Buyer Corp",
        supplier_name="Supplier Corp",
    )

    assert request.text

    assert request.buyer

    assert request.supplier

    assert (
        request.buyer_name
        == "Buyer Corp"
    )


def test_autonomous_request_supports_web_sources():

    request = AutonomousRunRequest(
        sources=[
            "https://example.com"
        ],
        buyer=make_policy(),
        supplier=make_policy(),
    )

    assert len(
        request.sources
    ) == 1