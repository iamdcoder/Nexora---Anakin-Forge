from autonomous.ai_reasoner import (
    _extract_json,
    run_ai_reasoning,
)
from autonomous.read import ProcurementRead


def intake():

    return ProcurementRead(
        intake_id="INT-AI-001",
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
            "Preferred standard packaging.",
        ],
        source_urls=[
            "https://example.com/supplier"
        ],
        raw_text=(
            "Product: Industrial Servo Motors. "
            "Quantity: 1000 units. "
            "Delivery within 30 days. "
            "Payment: Net 60. "
            "Uptime SLA: 98%."
        ),
    )


def test_extract_json_accepts_plain_json():

    result = _extract_json(
        '{"summary":"ok","confidence":0.9}'
    )

    assert result["summary"] == "ok"

    assert result["confidence"] == 0.9


def test_extract_json_accepts_markdown_fence():

    result = _extract_json(
        '```json\n{"summary":"ok"}\n```'
    )

    assert result["summary"] == "ok"


def test_ai_reasoning_is_optional_without_configuration(
    monkeypatch,
):

    monkeypatch.delenv(
        "LYZR_API_KEY",
        raising=False,
    )

    monkeypatch.delenv(
        "LYZR_REASONING_AGENT_ID",
        raising=False,
    )

    monkeypatch.setenv(
        "LYZR_AI_REASONING_ENABLED",
        "1",
    )

    assert (
        run_ai_reasoning(
            intake()
        )
        is None
    )