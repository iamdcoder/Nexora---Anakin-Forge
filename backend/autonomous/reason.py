from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.ai_reasoner import (
    AIReasoningDraft,
    run_ai_reasoning,
)
from autonomous.read import ProcurementRead
from models.policy import PartyPolicy


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


Priority = Literal[
    "critical",
    "high",
    "medium",
    "low",
]


class ReasonRequest(BaseModel):
    intake: ProcurementRead

    buyer_policy: dict | None = None

    use_ai: bool = True


class ProcurementConstraint(BaseModel):
    field: str

    value: str

    source: str

    priority: Priority


class ProcurementReasoning(BaseModel):
    reasoning_id: str

    intake_id: str

    objective: str

    product_name: str | None = None

    quantity: int | None = None

    target_delivery_days: int | None = None

    target_payment_days: int | None = None

    target_sla_uptime: float | None = None

    target_sla_penalty: float | None = None

    currency: str | None = None

    priorities: list[str] = Field(
        default_factory=list
    )

    hard_constraints: list[
        ProcurementConstraint
    ] = Field(
        default_factory=list
    )

    soft_preferences: list[
        ProcurementConstraint
    ] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    negotiation_brief: str

    confidence: float

    
    reasoning_source: str = "deterministic"

    ai_reasoning_run_id: str | None = None

    ai_summary: str | None = None

    recommended_strategy: str | None = None

    decision_rationale: str | None = None

    supplier_evaluation_factors: list[str] = Field(
        default_factory=list
    )

    ai_confidence: float | None = None


class ReasonResponse(BaseModel):
    reasoning: ProcurementReasoning


def _contains_any(
    text: str,
    words: tuple[str, ...],
) -> bool:
    text = text.lower()

    return any(
        word in text
        for word in words
    )


def _unique(
    values: list[str],
) -> list[str]:
    result: list[str] = []

    seen: set[str] = set()

    for value in values:
        normalized = value.strip()

        if not normalized:
            continue

        key = normalized.casefold()

        if key in seen:
            continue

        seen.add(key)

        result.append(normalized)

    return result


def _priority_from_text(
    requirement: str,
) -> Priority:
    text = requirement.lower()

    if _contains_any(
        text,
        (
            "must",
            "mandatory",
            "required",
            "shall",
            "compliance",
            "non-negotiable",
        ),
    ):
        return "critical"

    if _contains_any(
        text,
        (
            "preferred",
            "ideally",
            "prefer",
            "desired",
        ),
    ):
        return "medium"

    return "high"


def _build_constraints(
    intake: ProcurementRead,
) -> tuple[
    list[ProcurementConstraint],
    list[ProcurementConstraint],
]:

    hard: list[ProcurementConstraint] = []

    soft: list[ProcurementConstraint] = []

    for requirement in intake.requirements:

        constraint = ProcurementConstraint(
            field="requirement",
            value=requirement,
            source="rfq_or_source",
            priority=_priority_from_text(
                requirement
            ),
        )

        if constraint.priority == "critical":
            hard.append(constraint)
        else:
            soft.append(constraint)

    if intake.quantity is not None:

        hard.append(
            ProcurementConstraint(
                field="quantity",
                value=str(
                    intake.quantity
                ),
                source="structured_extraction",
                priority="critical",
            )
        )

    if intake.delivery_days is not None:

        hard.append(
            ProcurementConstraint(
                field="delivery_days",
                value=str(
                    intake.delivery_days
                ),
                source="structured_extraction",
                priority="high",
            )
        )

    if intake.sla_uptime is not None:

        hard.append(
            ProcurementConstraint(
                field="sla_uptime",
                value=str(
                    intake.sla_uptime
                ),
                source="structured_extraction",
                priority="critical",
            )
        )

    if intake.sla_penalty is not None:

        soft.append(
            ProcurementConstraint(
                field="sla_penalty",
                value=str(
                    intake.sla_penalty
                ),
                source="structured_extraction",
                priority="high",
            )
        )

    if intake.payment_days is not None:

        soft.append(
            ProcurementConstraint(
                field="payment_days",
                value=str(
                    intake.payment_days
                ),
                source="structured_extraction",
                priority="medium",
            )
        )

    return hard, soft


def _constraints_from_ai(
    items: list[str],
) -> list[ProcurementConstraint]:

    result: list[
        ProcurementConstraint
    ] = []

    for item in items:

        text = item.strip()

        if not text:
            continue

        priority: Priority = "critical"

        lowered = text.casefold()

        if any(
            word in lowered
            for word in (
                "prefer",
                "preferred",
                "ideally",
                "desired",
            )
        ):
            priority = "medium"

        result.append(
            ProcurementConstraint(
                field="ai_assessment",
                value=text,
                source="ai_reasoning",
                priority=priority,
            )
        )

    return result


def _build_missing_information(
    intake: ProcurementRead,
) -> list[str]:

    missing: list[str] = []

    if not intake.product_name:
        missing.append(
            "Exact product or service name/specification"
        )

    if intake.quantity is None:
        missing.append(
            "Required quantity"
        )

    if intake.delivery_days is None:
        missing.append(
            "Required delivery timeline"
        )

    if intake.payment_days is None:
        missing.append(
            "Expected payment terms"
        )

    if intake.sla_uptime is None:
        missing.append(
            "Required SLA uptime or availability"
        )

    if intake.currency is None:
        missing.append(
            "Transaction currency"
        )

    if not intake.source_urls:
        missing.append(
            "External supplier/source evidence"
        )

    return missing


def _build_risks(
    intake: ProcurementRead,
    missing: list[str],
) -> list[str]:

    risks: list[str] = []

    if intake.delivery_days is not None:

        if intake.delivery_days <= 7:
            risks.append(
                "Aggressive delivery requirement may reduce supplier availability."
            )

        elif intake.delivery_days >= 90:
            risks.append(
                "Long delivery window may indicate a non-standard procurement cycle."
            )

    if (
        intake.sla_uptime is not None
        and intake.sla_uptime >= 99.9
    ):
        risks.append(
            "Very high SLA target may materially restrict supplier options."
        )

    if (
        intake.sla_penalty is not None
        and intake.sla_penalty >= 5
    ):
        risks.append(
            "High SLA penalty may materially affect supplier acceptance."
        )

    if not intake.source_urls:
        risks.append(
            "No external supplier/source evidence was provided."
        )

    if missing:
        risks.append(
            f"{len(missing)} procurement inputs are missing."
        )

    return _unique(risks)


def _build_priorities(
    intake: ProcurementRead,
) -> list[str]:

    priorities: list[str] = []

    if intake.product_name:
        priorities.append(
            "Meet the requested product/service requirement"
        )

    if intake.quantity is not None:
        priorities.append(
            "Secure the full required quantity"
        )

    if intake.delivery_days is not None:
        priorities.append(
            "Meet the required delivery timeline"
        )

    if intake.sla_uptime is not None:
        priorities.append(
            "Maintain the required SLA availability"
        )

    if intake.sla_penalty is not None:
        priorities.append(
            "Preserve meaningful SLA protection"
        )

    if intake.payment_days is not None:
        priorities.append(
            "Preserve acceptable payment terms"
        )

    if intake.currency:
        priorities.append(
            f"Transact in {intake.currency}"
        )

    return priorities


def _build_objective(
    intake: ProcurementRead,
) -> str:

    product = (
        intake.product_name
        or "the requested procurement item"
    )

    quantity = (
        f"{intake.quantity} units"
        if intake.quantity is not None
        else "the required quantity"
    )

    return (
        f"Secure {quantity} of {product} "
        "under acceptable commercial, delivery, "
        "payment, and SLA conditions."
    )


def _build_negotiation_brief(
    intake: ProcurementRead,
    priorities: list[str],
    hard_constraints: list[
        ProcurementConstraint
    ],
    soft_preferences: list[
        ProcurementConstraint
    ],
    missing: list[str],
    risks: list[str],
    ai: AIReasoningDraft | None = None,
    
) -> str:

    lines: list[str] = [
        "NEXORA PROCUREMENT REASONING BRIEF"
    ]

    lines.append(
        f"Objective: {_build_objective(intake)}"
    )

    if priorities:

        lines.append(
            "Priorities: "
            + "; ".join(
                priorities
            )
        )

    if hard_constraints:

        lines.append(
            "Hard constraints: "
            + "; ".join(
                f"{item.field}={item.value}"
                for item in hard_constraints
            )
        )

    if soft_preferences:

        lines.append(
            "Soft preferences: "
            + "; ".join(
                f"{item.field}={item.value}"
                for item in soft_preferences
            )
        )

    if ai is not None:

        lines.append(
            f"AI assessment: {ai.summary}"
        )

        lines.append(
            f"AI strategy: {ai.recommended_strategy}"
        )

        lines.append(
            "AI decision rationale: "
            + ai.decision_rationale
        )

    if missing:

        lines.append(
            "Missing information: "
            + "; ".join(
                missing
            )
        )

    if risks:

        lines.append(
            "Risks: "
            + "; ".join(
                risks
            )
        )

    lines.append(
        "Negotiation rule: satisfy hard constraints first; "
        "use soft preferences to rank trade-offs."
    )

    return "\n".join(lines)


def _calculate_confidence(
    intake: ProcurementRead,
    missing: list[str],
) -> float:

    score = 1.0

    total_fields = 6

    present = sum(
        value is not None
        for value in (
            intake.product_name,
            intake.quantity,
            intake.delivery_days,
            intake.payment_days,
            intake.sla_uptime,
            intake.currency,
        )
    )

    score *= (
        present / total_fields
    )

    if intake.requirements:
        score += 0.10

    if intake.source_urls:
        score += 0.10

    if not intake.raw_text.strip():
        score -= 0.20

    if missing:
        score -= min(
            0.20,
            len(missing) * 0.025,
        )

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


def _policy_from_dict(
    value: dict | None,
) -> PartyPolicy | None:

    if value is None:
        return None

    try:

        return PartyPolicy.model_validate(
            value
        )

    except Exception:
        return None


def reason_about_procurement(
    intake: ProcurementRead,
    *,
    use_ai: bool = True,
    buyer_policy: dict | None = None,
    failure_context: str | None = None,
) -> ProcurementReasoning:

    hard_constraints, soft_preferences = (
        _build_constraints(
            intake
        )
    )

    missing = (
        _build_missing_information(
            intake
        )
    )

    risks = _build_risks(
        intake,
        missing,
    )

    priorities = (
        _build_priorities(
            intake
        )
    )

    ai: AIReasoningDraft | None = None
    if failure_context and failure_context.strip():
    
        risks.append(
            "Recovery context: "
            + failure_context.strip()[:500]
        )
    
        risks = _unique(
            risks
        )

    if use_ai:

        try:

            ai = run_ai_reasoning(
                intake,
                _policy_from_dict(buyer_policy),
                failure_context=failure_context,
            )

        except Exception as exc:

            
            
            
            risks.append(
                "AI reasoning unavailable; "
                "deterministic fallback used: "
                f"{exc}"
            )

            risks = _unique(
                risks
            )

    if ai is not None:

        if ai.priority_order:

            priorities = (
                ai.priority_order
                + [
                    item
                    for item in priorities
                    if item
                    not in ai.priority_order
                ]
            )

        ai_hard = (
            _constraints_from_ai(
                ai.hard_constraints
            )
        )

        ai_soft = (
            _constraints_from_ai(
                ai.soft_preferences
            )
        )

        hard_constraints.extend(
            ai_hard
        )

        soft_preferences.extend(
            ai_soft
        )

        missing = _unique(
            missing
            + ai.missing_information
        )

        risks = _unique(
            risks
            + ai.risks
        )

    brief = _build_negotiation_brief(
        intake=intake,
        priorities=priorities,
        hard_constraints=hard_constraints,
        soft_preferences=soft_preferences,
        missing=missing,
        risks=risks,
        ai=ai,
    )

    deterministic_confidence = (
        _calculate_confidence(
            intake,
            missing,
        )
    )

    confidence = (
        round(
            (
                deterministic_confidence
                * 0.45
            )
            + (
                ai.confidence
                * 0.55
            ),
            2,
        )
        if ai is not None
        else deterministic_confidence
    )

    return ProcurementReasoning(
        reasoning_id=(
            f"RSN-{uuid4().hex[:10].upper()}"
        ),
        intake_id=intake.intake_id,
        objective=_build_objective(
            intake
        ),
        product_name=intake.product_name,
        quantity=intake.quantity,
        target_delivery_days=(
            intake.delivery_days
        ),
        target_payment_days=(
            intake.payment_days
        ),
        target_sla_uptime=(
            intake.sla_uptime
        ),
        target_sla_penalty=(
            intake.sla_penalty
        ),
        currency=intake.currency,
        priorities=_unique(
            priorities
        ),
        hard_constraints=(
            hard_constraints
        ),
        soft_preferences=(
            soft_preferences
        ),
        missing_information=(
            missing
        ),
        risks=(
            risks
        ),
        negotiation_brief=brief,
        confidence=confidence,
        reasoning_source=(
            ai.reasoning_source
            if ai is not None
            else "deterministic"
        ),
        ai_reasoning_run_id=(
            ai.reasoning_run_id
            if ai is not None
            else None
        ),
        ai_summary=(
            ai.summary
            if ai is not None
            else None
        ),
        recommended_strategy=(
            ai.recommended_strategy
            if ai is not None
            else None
        ),
        decision_rationale=(
            ai.decision_rationale
            if ai is not None
            else None
        ),
        supplier_evaluation_factors=(
            ai.supplier_evaluation_factors
            if ai is not None
            else []
        ),
        ai_confidence=(
            ai.confidence
            if ai is not None
            else None
        ),
    )


@router.post(
    "/reason",
    response_model=ReasonResponse,
)
def reason_procurement(
    request: ReasonRequest,
) -> ReasonResponse:

    if not request.intake.raw_text.strip():

        raise HTTPException(
            status_code=400,
            detail="Procurement intake is empty.",
        )

    reasoning = reason_about_procurement(
        request.intake,
        use_ai=request.use_ai,
        buyer_policy=request.buyer_policy,
    )

    return ReasonResponse(
        reasoning=reasoning
    )