from __future__ import annotations

import json
import os
import re
from typing import Any
from uuid import uuid4

from agents.lyzr_client import LyzrClient
from autonomous.read import ProcurementRead
from models.policy import PartyPolicy


class AIReasoningDraft:
    """Validated, non-authoritative reasoning produced by a Lyzr agent."""

    def __init__(
        self,
        *,
        summary: str,
        priority_order: list[str],
        hard_constraints: list[str],
        soft_preferences: list[str],
        recommended_strategy: str,
        supplier_evaluation_factors: list[str],
        risks: list[str],
        missing_information: list[str],
        confidence: float,
        decision_rationale: str,
    ) -> None:
        self.summary = summary
        self.priority_order = priority_order
        self.hard_constraints = hard_constraints
        self.soft_preferences = soft_preferences
        self.recommended_strategy = recommended_strategy
        self.supplier_evaluation_factors = supplier_evaluation_factors
        self.risks = risks
        self.missing_information = missing_information
        self.confidence = confidence
        self.decision_rationale = decision_rationale
        self.reasoning_source = "lyzr"
        self.reasoning_run_id = (
            f"AIR-{uuid4().hex[:10].upper()}"
        )


def _clean_list(
    value: Any,
    maximum: int = 12,
) -> list[str]:

    if not isinstance(value, list):
        return []

    result: list[str] = []

    seen: set[str] = set()

    for item in value:

        text = str(item).strip()

        if not text:
            continue

        key = text.casefold()

        if key in seen:
            continue

        seen.add(key)

        result.append(text)

        if len(result) >= maximum:
            break

    return result


def _clean_text(
    value: Any,
    default: str,
    maximum: int = 800,
) -> str:

    text = (
        str(value).strip()
        if value is not None
        else ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    if not text:
        return default

    return text[:maximum]


def _safe_confidence(
    value: Any,
    default: float = 0.70,
) -> float:

    try:

        score = float(value)

    except (
        TypeError,
        ValueError,
    ):

        score = default

    if score > 1:
        score /= 100

    return round(
        max(
            0.0,
            min(
                1.0,
                score,
            ),
        ),
        2,
    )


def _extract_json(
    text: str,
) -> dict[str, Any]:

    cleaned = text.strip()

    if cleaned.startswith("```"):

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

    try:

        parsed = json.loads(
            cleaned
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\{.*\}",
        cleaned,
        flags=re.DOTALL,
    )

    if not match:

        raise ValueError(
            "AI reasoning response did not contain a JSON object."
        )

    parsed = json.loads(
        match.group(0)
    )

    if not isinstance(
        parsed,
        dict,
    ):

        raise ValueError(
            "AI reasoning response JSON was not an object."
        )

    return parsed


def _policy_summary(
    policy: PartyPolicy | None,
) -> str:

    if policy is None:

        return (
            "No private party policy supplied "
            "to the reasoning agent."
        )

    
    return (
        "Buyer-side guardrails available for reasoning only: "
        f"target price={policy.price.target}; "
        f"maximum price={policy.price.maximum}; "
        f"target delivery={policy.delivery.target_days} days; "
        f"maximum delivery={policy.delivery.maximum_days} days; "
        f"preferred payment=Net {policy.payment.preferred_days}; "
        f"minimum SLA uptime={policy.sla.minimum_uptime}%; "
        f"maximum SLA penalty={policy.sla.maximum_penalty}%."
    )


def _build_prompt(
    intake: ProcurementRead,
    buyer_policy: PartyPolicy | None = None,
    failure_context: str | None = None,
) -> str:

    source_text = intake.raw_text[:14_000]

    recovery_section = (
        failure_context.strip()
        if failure_context
        and failure_context.strip()
        else (
            "No previous execution failure is available. "
            "This is the initial procurement reasoning pass."
        )
    )

    return f"""
You are NEXORA's PROCUREMENT REASONING AGENT.

Your job is to interpret procurement requirements and turn them into a safe,
structured procurement strategy for another system to execute.

You MUST NOT negotiate, invent supplier facts, reveal secrets, or directly
approve a contract. Your output is advisory. Deterministic governance and
validators remain authoritative.

PROCUREMENT INTAKE
Product: {intake.product_name or "unknown"}
Quantity: {
        intake.quantity
        if intake.quantity is not None
        else "unknown"
    }
Delivery days: {
        intake.delivery_days
        if intake.delivery_days is not None
        else "unknown"
    }
Payment days: {
        intake.payment_days
        if intake.payment_days is not None
        else "unknown"
    }
SLA uptime: {
        intake.sla_uptime
        if intake.sla_uptime is not None
        else "unknown"
    }%
SLA penalty: {
        intake.sla_penalty
        if intake.sla_penalty is not None
        else "unknown"
    }%
Currency: {intake.currency or "unknown"}
Explicit requirements: {
        json.dumps(
            intake.requirements[:20]
        )
    }
External source URLs: {
        json.dumps(
            intake.source_urls[:5]
        )
    }

RECOVERY / EXECUTION FEEDBACK
{recovery_section}

Raw intake text:
{source_text}

{_policy_summary(buyer_policy)}

REASONING RULES
1. Separate hard constraints from soft preferences.
2. Put safety/compliance, required quantity, maximum delivery, and minimum SLA
   requirements ahead of negotiable commercial preferences.
3. Do not treat a preference as a hard constraint unless the intake clearly
   says must/required/mandatory/non-negotiable.
4. Identify missing information that could materially affect supplier choice.
5. Explain the trade-off logic in plain language.
6. Never claim facts about a supplier that are not present in the intake.
7. When recovery feedback is present, explicitly account for it in the
   recommended strategy, risks, and decision rationale.
8. Keep the output concise and operational.
9. Return ONLY valid JSON.

RETURN EXACTLY THIS SHAPE:
{{
  "summary": "one or two sentence assessment",
  "priority_order": ["delivery", "sla", "compliance", "price", "payment"],
  "hard_constraints": ["short plain-language constraint"],
  "soft_preferences": ["short plain-language preference"],
  "recommended_strategy": "specific negotiation strategy",
  "supplier_evaluation_factors": ["factor used to rank suppliers"],
  "risks": ["specific procurement risk"],
  "missing_information": ["missing item"],
  "confidence": 0.0,
  "decision_rationale": "why this strategy follows from the requirements"
}}
""".strip()


def run_ai_reasoning(
    intake: ProcurementRead,
    buyer_policy: PartyPolicy | None = None,
    failure_context: str | None = None,
) -> AIReasoningDraft | None:
    """Run a separate Lyzr reasoning agent when explicitly configured.

    Returns None when AI reasoning is disabled or not configured so the
    existing deterministic reasoning path remains the safe fallback.
    """

    enabled = (
        os.getenv(
            "LYZR_AI_REASONING_ENABLED",
            "1",
        ).strip()
        == "1"
    )

    agent_id = os.getenv(
        "LYZR_REASONING_AGENT_ID",
        "",
    ).strip()

    api_key = os.getenv(
        "LYZR_API_KEY",
        "",
    ).strip()

    if (
        not enabled
        or not agent_id
        or not api_key
    ):
        return None

    client = LyzrClient()

    session_id = (
        f"reasoning-"
        f"{int.from_bytes(os.urandom(4), 'big'):08x}"
    )

    user_id = os.getenv(
        "LYZR_USER_ID",
        "nexora-system",
    )

    response = client.chat(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        message=_build_prompt(
            intake,
            buyer_policy,
            failure_context,
        ),
    )

    payload = (
        response
        if isinstance(
            response,
            dict,
        )
        else _extract_json(
            str(response)
        )
    )

    return AIReasoningDraft(
        summary=_clean_text(
            payload.get("summary"),
            (
                "AI reasoning completed from "
                "the procurement intake."
            ),
        ),
        priority_order=_clean_list(
            payload.get(
                "priority_order"
            ),
            10,
        ),
        hard_constraints=_clean_list(
            payload.get(
                "hard_constraints"
            ),
            20,
        ),
        soft_preferences=_clean_list(
            payload.get(
                "soft_preferences"
            ),
            20,
        ),
        recommended_strategy=_clean_text(
            payload.get(
                "recommended_strategy"
            ),
            (
                "Satisfy hard constraints first "
                "and optimize soft preferences second."
            ),
        ),
        supplier_evaluation_factors=_clean_list(
            payload.get(
                "supplier_evaluation_factors"
            )
        ),
        risks=_clean_list(
            payload.get(
                "risks"
            )
        ),
        missing_information=_clean_list(
            payload.get(
                "missing_information"
            )
        ),
        confidence=_safe_confidence(
            payload.get(
                "confidence"
            )
        ),
        decision_rationale=_clean_text(
            payload.get(
                "decision_rationale"
            ),
            (
                "The recommended strategy follows "
                "the stated procurement constraints."
            ),
        ),
    )