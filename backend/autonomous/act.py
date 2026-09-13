from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from autonomous.reason import ProcurementReasoning


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class ActRequest(BaseModel):
    
    reasoning: ProcurementReasoning

    buyer: dict[str, Any]

    supplier: dict[str, Any]

    buyer_name: str = "Buyer Corp"

    supplier_name: str = "Supplier Corp"

    product_name: str | None = None

    quantity: int | None = None

    minimum_confidence: float = 0.50

    require_complete_intake: bool = False

    execution_mode: Literal[
        "auto",
        "simulation",
        "lyzr",
    ] = "auto"


class ActResponse(BaseModel):
    action_id: str

    decision: str

    reason: str

    reasoning_id: str

    negotiation_id: str | None = None

    negotiation: dict[str, Any] | None = None


def _has_critical_missing_information(
    reasoning: ProcurementReasoning,
) -> list[str]:

    critical_missing = []

    critical_patterns = (
        "product",
        "quantity",
        "delivery",
    )

    for item in reasoning.missing_information:

        lowered = item.lower()

        if any(
            pattern in lowered
            for pattern in critical_patterns
        ):

            critical_missing.append(
                item
            )

    return critical_missing


def _resolve_product_name(
    request: ActRequest,
) -> str:

    if request.product_name:

        return request.product_name

    if request.reasoning.product_name:

        return request.reasoning.product_name

    return "Industrial Components"


def _resolve_quantity(
    request: ActRequest,
) -> int:

    if request.quantity is not None:

        return request.quantity

    if request.reasoning.quantity is not None:

        return request.reasoning.quantity

    return 1000


def _validate_action_request(
    request: ActRequest,
) -> None:

    if not 0.0 <= request.minimum_confidence <= 1.0:

        raise HTTPException(
            status_code=400,
            detail=(
                "minimum_confidence must be "
                "between 0 and 1."
            ),
        )

    if (
        request.reasoning.confidence
        < request.minimum_confidence
    ):

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Reasoning confidence is below "
                    "the minimum confidence required "
                    "for autonomous execution."
                ),
                "confidence": (
                    request.reasoning.confidence
                ),
                "minimum_confidence": (
                    request.minimum_confidence
                ),
            },
        )

    if not isinstance(request.buyer, dict):
        raise HTTPException(
            status_code=422,
            detail="Buyer policy must be a JSON object.",
        )

    if not isinstance(request.supplier, dict):
        raise HTTPException(
            status_code=422,
            detail="Supplier policy must be a JSON object.",
        )

    if request.reasoning.reasoning_id == "":
        raise HTTPException(
            status_code=422,
            detail="Reasoning ID is required for autonomous execution.",
        )

    missing = _has_critical_missing_information(
        request.reasoning
    )

    if (
        request.require_complete_intake
        and missing
    ):

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Autonomous execution requires "
                    "a complete procurement intake."
                ),
                "missing_information": missing,
            },
        )


def _build_negotiation_request(
    request: ActRequest,
) -> Any:

    
    
    
    from main import NegotiationRequest

    return NegotiationRequest(
        buyer=request.buyer,
        supplier=request.supplier,
        buyer_name=request.buyer_name,
        supplier_name=request.supplier_name,
        product_name=_resolve_product_name(
            request
        ),
        quantity=_resolve_quantity(
            request
        ),
        negotiation_context=(
            _build_strategy_context(
                request.reasoning
            )
        ),
        execution_mode=(
            request.execution_mode
        ),
    )


def _build_strategy_context(
    reasoning: ProcurementReasoning,
) -> str:
    """Convert procurement reasoning into non-sensitive negotiation guidance."""

    lines = [
        f"Reasoning ID: {reasoning.reasoning_id}",
    ]

    if reasoning.recommended_strategy:
        lines.append(
            f"Recommended strategy: {reasoning.recommended_strategy}"
        )

    if reasoning.priorities:
        lines.append(
            "Priority order: "
            + "; ".join(reasoning.priorities[:8])
        )

    if reasoning.supplier_evaluation_factors:
        lines.append(
            "Supplier evaluation factors: "
            + "; ".join(
                reasoning.supplier_evaluation_factors[:8]
            )
        )

    if reasoning.hard_constraints:
        lines.append(
            "Hard constraints to preserve: "
            + "; ".join(
                f"{item.field}={item.value}"
                for item in reasoning.hard_constraints[:8]
            )
        )

    if reasoning.soft_preferences:
        lines.append(
            "Soft preferences: "
            + "; ".join(
                f"{item.field}={item.value}"
                for item in reasoning.soft_preferences[:8]
            )
        )

    if reasoning.risks:
        lines.append(
            "Known procurement risks: "
            + "; ".join(reasoning.risks[:8])
        )

    return "\n".join(lines)


def _execute_existing_negotiation(
    request: ActRequest,
) -> dict[str, Any]:

    from main import start_negotiation

    negotiation_request = (
        _build_negotiation_request(
            request
        )
    )

    result = start_negotiation(
        negotiation_request
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "Existing negotiation API returned an unexpected response."
        )

    negotiation_id = result.get("negotiation_id")
    status = result.get("status")

    if not negotiation_id:
        raise RuntimeError(
            "Negotiation execution returned no negotiation_id."
        )

    if status is None:
        raise RuntimeError(
            "Negotiation execution returned no status."
        )

    return result


@router.post(
    "/act",
    response_model=ActResponse,
)
def act_on_procurement(
    request: ActRequest,
) -> ActResponse:

    _validate_action_request(
        request
    )

    action_id = (
        f"ACT-{uuid4().hex[:10].upper()}"
    )

    reasoning = request.reasoning

    action_reason = (
        "Reasoning passed the autonomous "
        "execution checks. Nexora is starting "
        "the existing Buyer/Supplier negotiation."
    )

    try:

        negotiation = (
            _execute_existing_negotiation(
                request
            )
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Autonomous negotiation execution failed."
                ),
                "error": str(exc),
                "action_id": action_id,
            },
        ) from exc

    negotiation_id = (
        negotiation.get(
            "negotiation_id"
        )
    )

    status = (
        negotiation.get(
            "status"
        )
    )

    return ActResponse(
        action_id=action_id,
        decision="executed",
        reason=(
            action_reason
            + f" Negotiation status: {status}."
        ),
        reasoning_id=reasoning.reasoning_id,
        negotiation_id=negotiation_id,
        negotiation=negotiation,
    )