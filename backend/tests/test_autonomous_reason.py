from autonomous.read import ProcurementRead
from autonomous.reason import reason_about_procurement
from fastapi.testclient import TestClient

from main import app


def make_intake() -> ProcurementRead:

    return ProcurementRead(
        intake_id="INT-TEST123",
        source_type="manual",
        product_name="Industrial Servo Motors",
        quantity=1000,
        delivery_days=30,
        payment_days=60,
        sla_uptime=98.0,
        sla_penalty=2.0,
        currency="INR",
        requirements=[
            "Must include ISO 9001 compliance.",
            "Quality documentation required.",
            "Preferred standard packaging.",
        ],
        source_urls=[],
        raw_text=(
            "Product: Industrial Servo Motors. "
            "Quantity: 1000 units. "
            "Delivery within 30 days. "
            "Payment: Net 60. "
            "Uptime SLA: 98%. "
            "Penalty: 2%. "
            "Must include ISO 9001 compliance."
        ),
    )


def test_reasoning_builds_procurement_objective():

    intake = make_intake()

    result = reason_about_procurement(
        intake
    )

    assert (
        result.reasoning_id.startswith(
            "RSN-"
        )
    )

    assert result.intake_id == "INT-TEST123"

    assert (
        result.product_name
        == "Industrial Servo Motors"
    )

    assert result.quantity == 1000

    assert (
        result.target_delivery_days
        == 30
    )

    assert (
        result.target_payment_days
        == 60
    )


def test_reasoning_separates_constraints_and_preferences():

    intake = make_intake()

    result = reason_about_procurement(
        intake
    )

    hard_fields = [
        item.field
        for item in result.hard_constraints
    ]

    soft_fields = [
        item.field
        for item in result.soft_preferences
    ]

    assert "quantity" in hard_fields

    assert "delivery_days" in hard_fields

    assert "sla_uptime" in hard_fields

    assert "payment_days" in soft_fields

    assert "sla_penalty" in soft_fields

    assert any(
        item.priority == "critical"
        and "ISO 9001" in item.value
        for item in result.hard_constraints
    )


def test_reasoning_detects_missing_information():

    intake = ProcurementRead(
        intake_id="INT-MISSING",
        source_type="manual",
        product_name="Controllers",
        quantity=None,
        delivery_days=None,
        payment_days=None,
        sla_uptime=None,
        sla_penalty=None,
        currency=None,
        requirements=[],
        source_urls=[],
        raw_text="We need controllers.",
    )

    result = reason_about_procurement(
        intake
    )

    assert (
        "Required quantity"
        in result.missing_information
    )

    assert (
        "Required delivery timeline"
        in result.missing_information
    )

    assert (
        "Expected payment terms"
        in result.missing_information
    )

    assert result.confidence < 1.0

    assert len(result.risks) > 0


def test_reason_endpoint_returns_reasoning():

    client = TestClient(app)

    intake = make_intake()

    response = client.post(
        "/api/autonomous/reason",
        json={
            "intake": intake.model_dump()
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "reasoning" in data

    reasoning = data["reasoning"]

    assert (
        reasoning["intake_id"]
        == "INT-TEST123"
    )

    assert (
        reasoning["objective"]
    )

    assert (
        reasoning["negotiation_brief"]
    )

    assert (
        0.0
        <= reasoning["confidence"]
        <= 1.0
    )