from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from guardrails.guardrail_engine import GuardrailEngine
from models.policy import PartyPolicy
from models.proposal import NegotiationProposal


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class GovernanceDemoRequest(BaseModel):
    buyer: dict[str, Any]

    supplier: dict[str, Any] | None = None

    ai_proposal: dict[str, Any] | None = None


class GovernanceDemoResponse(BaseModel):
    demo_id: str

    ai_proposal: dict[str, Any]

    ai_decision: dict[str, Any]

    corrected_proposal: dict[str, Any]

    corrected_decision: dict[str, Any]

    lesson: str


def _default_ai_proposal(
    buyer: PartyPolicy,
) -> dict[str, Any]:

    target = buyer.price.target

    maximum = buyer.price.maximum

    if maximum is None:
        maximum = target

    unsafe_price = round(
        float(maximum)
        + max(
            1000.0,
            float(maximum) * 0.03,
        ),
        2,
    )

    return {
        "round_number": 1,
        "price": unsafe_price,
        "delivery_days": (
            buyer.delivery.target_days
        ),
        "payment_days": (
            buyer.payment.preferred_days
        ),
        "sla_penalty": (
            buyer.sla.maximum_penalty
        ),
        "sla_uptime": (
            buyer.sla.minimum_uptime
        ),
        "action": "offer",
        "accepted_offer": None,
        "rationale": (
            "AI demo proposal intentionally "
            "exceeds the buyer price ceiling."
        ),
    }


def _proposal(
    value: dict[str, Any],
) -> NegotiationProposal:

    return NegotiationProposal.model_validate(
        value
    )


def _decision_payload(
    result,
) -> dict[str, Any]:

    return {
        "allowed": (
            result.status.value
            == "allowed"
        ),
        "status": (
            result.status.value
        ),
        "reason": result.reason,
        "violations": result.violations,
        "validator": result.validator,
        "severity": result.severity,
    }


def _correct_proposal(
    ai: NegotiationProposal,
    buyer: PartyPolicy,
) -> dict[str, Any]:

    price_ceiling = (
        buyer.price.maximum
    )

    corrected_price = ai.price

    if price_ceiling is not None:

        corrected_price = float(
            price_ceiling
        )

    corrected_delivery = min(
        ai.delivery_days,
        buyer.delivery.maximum_days,
    )

    corrected_payment = max(
        ai.payment_days,
        buyer.payment.minimum_days,
    )

    corrected_penalty = max(
        buyer.sla.minimum_penalty,
        min(
            ai.sla_penalty,
            buyer.sla.maximum_penalty,
        ),
    )

    corrected_uptime = max(
        ai.sla_uptime,
        buyer.sla.minimum_uptime,
    )

    return {
        "round_number": (
            ai.round_number + 1
        ),
        "price": corrected_price,
        "delivery_days": corrected_delivery,
        "payment_days": corrected_payment,
        "sla_penalty": corrected_penalty,
        "sla_uptime": corrected_uptime,
        "action": "counter",
        "accepted_offer": None,
        "rationale": (
            "AI proposal was blocked by governance; "
            "Nexora corrected the proposal to the "
            "buyer's permitted policy boundary."
        ),
    }


@router.post(
    "/governance-demo",
    response_model=GovernanceDemoResponse,
)
def governance_demo(
    request: GovernanceDemoRequest,
) -> GovernanceDemoResponse:

    try:

        buyer = PartyPolicy.model_validate(
            request.buyer
        )

        ai_payload = (
            request.ai_proposal
            or _default_ai_proposal(
                buyer
            )
        )

        ai_proposal = _proposal(
            ai_payload
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Invalid governance demo input."
                ),
                "error": str(exc),
            },
        ) from exc

    ai_result = (
        GuardrailEngine.validate(
            proposal=ai_proposal,
            policy=buyer,
            role="buyer",
        )
    )

    corrected_payload = (
        _correct_proposal(
            ai_proposal,
            buyer,
        )
    )

    corrected = _proposal(
        corrected_payload
    )

    corrected_result = (
        GuardrailEngine.validate(
            proposal=corrected,
            policy=buyer,
            role="buyer",
        )
    )

    return GovernanceDemoResponse(
        demo_id=(
            f"GOV-{uuid4().hex[:10].upper()}"
        ),
        ai_proposal=(
            ai_proposal.model_dump()
        ),
        ai_decision=(
            _decision_payload(
                ai_result
            )
        ),
        corrected_proposal=(
            corrected.model_dump()
        ),
        corrected_decision=(
            _decision_payload(
                corrected_result
            )
        ),
        lesson=(
            "AI can recommend a commercial action, "
            "but deterministic governance remains "
            "authoritative and can block unsafe or "
            "out-of-policy actions."
        ),
    )