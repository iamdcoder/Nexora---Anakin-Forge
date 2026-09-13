from autonomous.governance_demo import (
    GovernanceDemoRequest,
    governance_demo,
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
        "batna": "No deal",
        "max_rounds": 8,
    }


def test_governance_demo_blocks_bad_ai_proposal_and_allows_correction():

    result = governance_demo(
        GovernanceDemoRequest(
            buyer=buyer_policy(),
            ai_proposal={
                "round_number": 1,
                "price": 130000,
                "delivery_days": 30,
                "payment_days": 60,
                "sla_penalty": 2,
                "sla_uptime": 98,
                "action": "offer",
                "accepted_offer": None,
                "rationale": (
                    "intentional demo violation"
                ),
            },
        )
    )

    assert (
        result.ai_decision["allowed"]
        is False
    )

    assert (
        result.ai_decision["status"]
        == "blocked"
    )

    assert any(
        "exceeds buyer maximum"
        in violation
        for violation
        in result.ai_decision[
            "violations"
        ]
    )

    assert (
        result.corrected_decision[
            "allowed"
        ]
        is True
    )

    assert (
        result.corrected_decision[
            "status"
        ]
        == "allowed"
    )