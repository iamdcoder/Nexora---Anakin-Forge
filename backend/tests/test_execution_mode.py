from autonomous.act import ActRequest


def make_reasoning():

    from autonomous.reason import (
        ProcurementReasoning,
    )

    return ProcurementReasoning(
        reasoning_id="RSN-MODE",
        intake_id="INT-MODE",
        objective="Test execution mode.",
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


def test_act_defaults_to_auto():

    request = ActRequest(
        reasoning=make_reasoning(),
        buyer={},
        supplier={},
    )

    assert (
        request.execution_mode
        == "auto"
    )


def test_act_supports_simulation_mode():

    request = ActRequest(
        reasoning=make_reasoning(),
        buyer={},
        supplier={},
        execution_mode="simulation",
    )

    assert (
        request.execution_mode
        == "simulation"
    )


def test_act_supports_lyzr_mode():

    request = ActRequest(
        reasoning=make_reasoning(),
        buyer={},
        supplier={},
        execution_mode="lyzr",
    )

    assert (
        request.execution_mode
        == "lyzr"
    )


def test_act_rejects_unknown_mode():

    from pydantic import ValidationError

    try:

        ActRequest(
            reasoning=make_reasoning(),
            buyer={},
            supplier={},
            execution_mode="invalid",
        )

    except ValidationError:

        return

    raise AssertionError(
        "Invalid execution mode was accepted."
    )