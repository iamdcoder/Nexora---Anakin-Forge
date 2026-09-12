from fastapi.testclient import TestClient

from main import app
from autonomous.read import (
    _HTMLTextParser,
    _validate_url,
)


def test_read_endpoint_extracts_procurement_fields():

    client = TestClient(app)

    response = client.post(
        "/api/autonomous/read",
        json={
            "text": (
                "Product: Industrial Servo Motors. "
                "Quantity: 1000 units. "
                "Delivery within 30 days. "
                "Payment: Net 60. "
                "Uptime SLA: 98%. "
                "Penalty: 2%. "
                "Must include ISO 9001 compliance."
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    intake = data["intake"]

    assert intake["source_type"] == "manual"

    assert (
        intake["product_name"]
        == "Industrial Servo Motors"
    )

    assert intake["quantity"] == 1000

    assert intake["delivery_days"] == 30

    assert intake["payment_days"] == 60

    assert intake["sla_uptime"] == 98.0

    assert intake["sla_penalty"] == 2.0

    assert (
        "ISO 9001 compliance"
        in intake["requirements"][0]
    )

    assert intake["intake_id"].startswith(
        "INT-"
    )


def test_read_endpoint_requires_input():

    client = TestClient(app)

    response = client.post(
        "/api/autonomous/read",
        json={},
    )

    assert response.status_code == 400


def test_private_urls_are_rejected():

    try:

        _validate_url(
            "http://127.0.0.1:8000/internal"
        )

    except ValueError as exc:

        assert (
            "Private or local"
            in str(exc)
        )

    else:

        raise AssertionError(
            "Private URL was not rejected"
        )


def test_html_parser_removes_non_content_sections():

    parser = _HTMLTextParser()

    parser.feed(
        "<html>"
        "<head>"
        "<title>Supplier</title>"
        "<script>ignore()</script>"
        "</head>"
        "<body>"
        "<p>Offer 100 units.</p>"
        "</body>"
        "</html>"
    )

    assert parser.title == "Supplier"

    assert (
        "Offer 100 units."
        in " ".join(parser.parts)
    )

    assert (
        "ignore"
        not in " ".join(parser.parts)
    )