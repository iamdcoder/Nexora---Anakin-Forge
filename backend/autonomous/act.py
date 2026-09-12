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
        execution_mode=(
            request.execution_mode
        ),
    )


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
            "Existing negotiation API returned "
            "an unexpected response."
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