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
        for item in result.hard_constraints
    )

    assert any(
        "AI-suggested hard constraint is advisory only"
        in risk
        for risk in result.risks
    )

    assert (
        "AI strategy:"
        in result.negotiation_brief
    )

def test_ai_reasoning_provider_failure_falls_back(monkeypatch):
    intake = ProcurementRead(
        intake_id="INT-AI-FAIL",
        source_type="manual",
        product_name="Controllers",
        quantity=100,
        delivery_days=20,
        payment_days=60,
        sla_uptime=98,
        sla_penalty=2,
        currency="INR",
        requirements=[],
        source_urls=[],
        raw_text="100 controllers within 20 days.",
    )

    monkeypatch.setenv(
        "LYZR_AI_REASONING_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "LYZR_REASONING_AGENT_ID",
        "agent-test",
    )
    monkeypatch.setenv(
        "LYZR_API_KEY",
        "key-test",
    )

    class FailingClient:
        def chat(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "autonomous.ai_reasoner.LyzrClient",
        lambda: FailingClient(),
    )

    result = reason_module.reason_about_procurement(
        intake,
        use_ai=True,
    )

    assert result.reasoning_source == "deterministic"
    assert result.ai_reasoning_run_id is None


def test_ai_prompt_does_not_expose_private_numeric_policy(monkeypatch):
    from autonomous.ai_reasoner import _build_prompt
    from models.policy import PartyPolicy

    intake = ProcurementRead(
        intake_id="INT-AI-PRIVACY",
        source_type="manual",
        product_name="Controllers",
        quantity=100,
        delivery_days=20,
        payment_days=60,
        sla_uptime=98,
        sla_penalty=2,
        currency="INR",
        requirements=[],
        source_urls=[],
        raw_text="100 controllers within 20 days.",
    )

    policy = PartyPolicy(
        price={
            "target": 111111,
            "maximum": 122222,
        },
        delivery={
            "target_days": 20,
            "maximum_days": 25,
        },
        payment={
            "preferred_days": 60,
            "minimum_days": 45,
        },
        sla={
            "minimum_uptime": 98,
            "minimum_penalty": 1,
            "maximum_penalty": 5,
        },
        batna="private",
        max_rounds=6,
    )

    prompt = _build_prompt(
        intake,
        policy,
    )

    assert "111111" not in prompt
    assert "122222" not in prompt
    assert "private" not in prompt.lower().replace("private numeric negotiation thresholds", "")
