from autonomous.web_discover import (
    WebSupplierCandidate,
    _build_candidate,
)


def test_web_candidate_preserves_supplier_identity():

    candidate = WebSupplierCandidate(
        name="Supplier Alpha",
        source_url="https://example.com",
        policy={
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
    )

    result = _build_candidate(
        candidate
    )

    assert (
        result.name
        == "Supplier Alpha"
    )

    assert (
        result.source_url
        == "https://example.com"
    )

    assert result.policy

    assert len(
        result.evidence
    ) > 0


def test_web_candidate_records_read_failure():

    candidate = WebSupplierCandidate(
        name="Invalid Supplier",
        source_url=(
            "http://127.0.0.1:8000/internal"
        ),
        policy={
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
    )

    result = _build_candidate(
        candidate
    )

    assert any(
        "Website could not be read"
        in item
        for item in result.evidence
    )