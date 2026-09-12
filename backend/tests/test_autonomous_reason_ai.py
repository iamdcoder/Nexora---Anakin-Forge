from autonomous.ai_reasoner import (
    AIReasoningDraft,
)
from autonomous.read import ProcurementRead
import autonomous.reason as reason_module


def test_reasoning_merges_ai_strategy_without_removing_deterministic_constraints(
    monkeypatch,
):

    intake = ProcurementRead(
        intake_id="INT-AI-MERGE",
        source_type="manual",
        product_name="Servo Motors",
        quantity=1000,
        delivery_days=30,
        payment_days=60,
        sla_uptime=98,
        sla_penalty=2,
        currency="INR",
        requirements=[
            "Must include ISO 9001 compliance."
        ],
        source_urls=[],
        raw_text=(
            "Servo Motors, 1000 units, "
            "delivery within 30 days."
        ),
    )

    draft = AIReasoningDraft(
        summary=(
            "Delivery is the dominant constraint."
        ),
        priority_order=[
            "delivery",
            "sla",
            "price",
            "payment",
        ],
        hard_constraints=[
            "Delivery must be 30 days or less."
        ],
        soft_preferences=[
            "Prefer Net 60 payment."
        ],
        recommended_strategy=(
            "Protect delivery first and trade price second."
        ),
        supplier_evaluation_factors=[
            "delivery fit",
            "SLA fit",
        ],
        risks=[
            "Limited supplier pool."
        ],
        missing_information=[],
        confidence=0.92,
        decision_rationale=(
            "Missing delivery would make the purchase unusable."
        ),
    )

    monkeypatch.setattr(
        reason_module,
        "run_ai_reasoning",
        lambda *args, **kwargs: draft,
    )

    result = (
        reason_module.reason_about_procurement(
            intake
        )
    )

    assert (
        result.reasoning_source
        == "lyzr"
    )

    assert result.ai_reasoning_run_id

    assert (
        result.ai_summary
        == draft.summary
    )

    assert (
        result.recommended_strategy
        == draft.recommended_strategy
    )

    assert (
        result.ai_confidence
        == 0.92
    )

    assert any(
        item.field == "quantity"
        for item
        in result.hard_constraints
    )

    assert not any(
        item.source == "ai_reasoning"
        for item
        in result.hard_constraints
    )

    assert any(
        "AI-suggested hard constraint is advisory only"
        in risk
        for risk
        in result.risks
    )

    assert (
        "AI strategy:"
        in result.negotiation_brief
    )