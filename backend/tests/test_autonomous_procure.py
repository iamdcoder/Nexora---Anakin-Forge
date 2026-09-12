from autonomous.procure import (
    AutonomousProcurementRequest,
    ProcurementSupplier,
)


def buyer():

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


def supplier_policy():

    return {
        "price": {
            "target": 115000,
            "minimum": 105000,
            "maximum": 125000,
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
    }


def test_request_supports_autonomous_procurement():

    request = AutonomousProcurementRequest(
        text=(
            "Product: Industrial Servo Motors. "
            "Quantity: 1000 units. "
            "Delivery within 30 days."
        ),
        buyer=buyer(),
        suppliers=[
            ProcurementSupplier(
                name="Supplier Alpha",
                source_url="https://example.com",
                policy=supplier_policy(),
                description=(
                    "Industrial automation supplier"
                ),
            )
        ],
    )

    assert request.text

    assert request.suppliers[0].name == (
        "Supplier Alpha"
    )

    assert request.max_attempts == 3


def test_supplier_defaults_are_safe():

    supplier = ProcurementSupplier(
        name="Supplier Alpha",
        source_url="https://example.com",
        policy=supplier_policy(),
    )

    assert supplier.description == ""


def test_max_attempts_is_bounded():

    request = AutonomousProcurementRequest(
        buyer=buyer(),
        suppliers=[
            ProcurementSupplier(
                name="Supplier Alpha",
                source_url="https://example.com",
                policy=supplier_policy(),
            )
        ],
        max_attempts=5,
    )

    assert 1 <= request.max_attempts <= 10