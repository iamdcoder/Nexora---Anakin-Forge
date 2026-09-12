from autonomous import procure as procure_module

from autonomous.procure import (
    AutonomousProcurementRequest,
    ProcurementSupplier,
)

from autonomous.reason import ProcurementReasoning

from autonomous.act import ActResponse

from autonomous.verify import VerificationResult


def buyer_policy():
    return {
        "price": {
            "target": 110000,
            "minimum": 100000,
            "maximum": 120000,
        },
        "delivery": {
            "target_days": 30,
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


def supplier(
    name,
    price_target,
    delivery_target,
    delivery_maximum,
):
    policy = buyer_policy()

    policy["price"]["target"] = price_target

    policy["price"]["minimum"] = (
        price_target - 5000
    )

    policy["price"]["maximum"] = (
        price_target + 5000
    )

    policy["delivery"]["target_days"] = (
        delivery_target
    )

    policy["delivery"]["maximum_days"] = (
        delivery_maximum
    )

    policy["batna"] = (
        "Alternative supplier"
    )

    return ProcurementSupplier(
        name=name,
        source_url=(
            "https://example.com/supplier"
        ),
        policy=policy,
        description=(
            "Recovery integrity test supplier"
        ),
    )


def initial_reasoning():
    return ProcurementReasoning(
        reasoning_id="RSN-INITIAL",
        intake_id="INT-RECOVERY",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=20,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[
            "delivery",
            "price",
            "sla",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief=(
            "Initial recovery test."
        ),
        confidence=0.95,
        reasoning_source="deterministic",
    )


def recovery_reasoning():
    return ProcurementReasoning(
        reasoning_id="RSN-RECOVERY",
        intake_id="INT-RECOVERY",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[
            "delivery",
            "sla",
            "price",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[
            "Previous supplier failed verification."
        ],
        negotiation_brief=(
            "Recovery must preserve hard "
            "delivery requirements."
        ),
        confidence=0.95,
        reasoning_source="deterministic",
    )


def request():
    return AutonomousProcurementRequest(
        text=(
            "Need 1000 servo motors with a "
            "30 day delivery requirement."
        ),
        suppliers=[
            supplier(
                "Supplier A",
                108000,
                20,
                30,
            ),
            supplier(
                "Supplier B",
                109000,
                25,
                25,
            ),
            supplier(
                "Supplier C",
                112000,
                30,
                40,
            ),
        ],
        buyer=buyer_policy(),
        max_attempts=3,
        execution_mode="simulation",
    )


def action_for_supplier(req):
    return ActResponse(
        action_id=(
            f"ACT-{req.supplier_name}"
        ),
        decision="AGREED",
        reason="test",
        reasoning_id=(
            req.reasoning.reasoning_id
        ),
        negotiation_id=(
            f"NEG-{req.supplier_name}"
        ),
        negotiation={
            "status": "AGREED"
        },
    )


def verification_result(
    passed,
):
    return VerificationResult(
        verification_id="VER-RECOVERY",
        action_id="ACT-RECOVERY",
        negotiation_id="NEG-RECOVERY",
        status=(
            "verified"
            if passed
            else "rejected"
        ),
        verified=passed,
        checks=[],
        violations=(
            []
            if passed
            else [
                (
                    "Previous supplier failed "
                    "verification."
                )
            ]
        ),
        verified_contract=(
            {
                "contract_hash": "test"
            }
            if passed
            else None
        ),
    )


def test_recovery_does_not_reintroduce_newly_infeasible_supplier(
    monkeypatch,
):
    reasoning_calls = []

    action_calls = []

    def fake_reason(
        intake,
        **kwargs,
    ):
        failure_context = kwargs.get(
            "failure_context"
        )

        reasoning_calls.append(
            failure_context
        )

        if failure_context:
            return recovery_reasoning()

        return initial_reasoning()

    def fake_act(req):
        action_calls.append(
            req.supplier_name
        )

        return action_for_supplier(
            req
        )

    verification_calls = []

    def fake_verify(req):
        verification_calls.append(
            req.supplier
        )

        if len(
            verification_calls
        ) == 1:
            return verification_result(
                False
            )

        return verification_result(
            True
        )

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        fake_reason,
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        fake_act,
    )

    monkeypatch.setattr(
        procure_module,
        "verify_autonomous_action",
        fake_verify,
    )

    result = (
        procure_module.procure(
            request()
        )
    )

    assert (
        result.verified
        is True
    )

    assert (
        action_calls[0]
        == "Supplier A"
    )

    assert (
        action_calls[1]
        == "Supplier C"
    )

    assert (
        "Supplier B"
        not in action_calls
    )

    assert (
        len(action_calls)
        == 2
    )

    assert (
        len(reasoning_calls)
        == 2
    )

    recovery = (
        result.reasoning_history[-1]
    )

    assert (
        recovery["reasoning_id"]
        == "RSN-RECOVERY"
    )

    ranked_names = [
        item["supplier"]["name"]
        for item in result.supplier_ranking
    ]

    assert (
        "Supplier B"
        in ranked_names
    )

    b_entry = next(
        item
        for item
        in result.supplier_ranking
        if (
            item["supplier"]["name"]
            == "Supplier B"
        )
    )

    assert (
        b_entry["compatibility_score"]
        == 0.0
    )

    assert (
        b_entry["recommendation"]
        == "ineligible"
    )

    assert any(
        "delivery"
        in flag.lower()
        for flag
        in b_entry["risk_flags"]
    )

    assert (
        result.attempts[0].verified
        is False
    )

    assert (
        result.attempts[1].verified
        is True
    )