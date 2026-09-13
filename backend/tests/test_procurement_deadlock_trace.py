from autonomous.procure import (
    AutonomousProcurementRequest,
    procure,
)


BUYER = {
    "price": {
        "target": 95000,
        "minimum": 85000,
        "maximum": 115000,
    },
    "delivery": {
        "target_days": 25,
        "minimum_days": 20,
        "maximum_days": 40,
    },
    "payment": {
        "preferred_days": 60,
        "minimum_days": 30,
        "maximum_days": 90,
    },
    "sla": {
        "minimum_uptime": 99,
        "maximum_uptime": 100,
        "minimum_penalty": 2,
        "maximum_penalty": 7,
    },
    "batna": "No-deal",
    "max_rounds": 8,
}


SUPPLIER = {
    "price": {
        "target": 130000,
        "minimum": 120000,
        "maximum": 135000,
    },
    "delivery": {
        "target_days": 35,
        "minimum_days": 30,
        "maximum_days": 50,
    },
    "payment": {
        "preferred_days": 30,
        "minimum_days": 15,
        "maximum_days": 60,
    },
    "sla": {
        "minimum_uptime": 98,
        "maximum_uptime": 100,
        "minimum_penalty": 1,
        "maximum_penalty": 6,
    },
    "batna": "Other customer offer",
    "max_rounds": 8,
}


def test_incompatible_supplier_is_reported_as_deadlock():
    result = procure(
        AutonomousProcurementRequest(
            text=(
                "Product: Industrial Servo Motors. "
                "Quantity: 1000 units. "
                "Budget ceiling ₹115000. "
                "Delivery target 25 days. "
                "Net 60 payment. Required uptime 99%."
            ),
            suppliers=[
                {
                    "name": "Edited Supplier",
                    "source_url": "https://example.com/edited-supplier",
                    "policy": SUPPLIER,
                    "description": "Edited supplier policy for deadlock test.",
                }
            ],
            buyer=BUYER,
            buyer_name="Acme Corp",
            max_attempts=3,
            minimum_confidence=0.4,
            minimum_supplier_score=0.3,
            execution_mode="simulation",
        )
    )

    assert result.status == "deadlock"
    assert result.verified is False
    assert result.failure_code == "SELECTION_ERROR"
    assert result.failure_provenance
    assert result.failure_provenance[0].stage == "SUPPLIER_SELECTION"
    assert result.failure_provenance[0].recoverable is False
    assert result.stages["read"] == "complete"
    assert result.stages["reason"] == "complete"
    assert result.stages["supplier_selection"] == "failed"
    assert result.stages["act"] == "blocked"
    assert result.stages["verify"] == "blocked"
    assert result.final_action is None
    assert result.final_verification is None
    assert result.selected_supplier is not None
    assert result.selected_supplier["compatibility_score"] < 0.3
