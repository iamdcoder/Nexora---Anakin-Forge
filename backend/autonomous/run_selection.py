from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.act import (
    ActRequest,
    act_on_procurement,
)

from autonomous.discover import (
    SupplierCandidate,
    rank_suppliers,
)

from autonomous.read import (
    ReadRequest,
    read_procurement_input,
)

from autonomous.reason import (
    reason_about_procurement,
)

from autonomous.verify import (
    VerifyRequest,
    verify_autonomous_action,
)

from models.policy import PartyPolicy


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class AutonomousSelectionRunRequest(BaseModel):

    text: str = ""

    sources: list[str] = Field(
        default_factory=list
    )

    suppliers: list[SupplierCandidate]

    buyer: dict[str, Any]

    buyer_name: str = "Buyer Corp"

    minimum_confidence: float = 0.50

    minimum_supplier_score: float = 0.50

    require_complete_intake: bool = False


class AutonomousSelectionRunResponse(BaseModel):

    workflow_id: str

    status: str

    verified: bool

    selected_supplier: dict[str, Any] | None

    ranking: list[dict[str, Any]]

    intake: dict[str, Any]

    reasoning: dict[str, Any]

    action: dict[str, Any]

    verification: dict[str, Any]

    failure_stage: str | None = None

    failure_reason: str | None = None


def _build_buyer_policy(
    buyer: dict[str, Any],
) -> PartyPolicy:

    try:

        return PartyPolicy.model_validate(
            buyer
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid buyer policy.",
                "error": str(exc),
            },
        ) from exc


def _select_supplier(
    reasoning,
    suppliers: list[SupplierCandidate],
    buyer: PartyPolicy,
    minimum_score: float,
):

    ranked = rank_suppliers(
        reasoning=reasoning,
        suppliers=suppliers,
        buyer=buyer,
    )

    if not ranked:

        raise HTTPException(
            status_code=422,
            detail=(
                "No supplier candidates "
                "were provided."
            ),
        )

    selected = ranked[0]

    if (
        selected.compatibility_score
        < minimum_score
    ):

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "No supplier meets the "
                    "minimum compatibility score."
                ),
                "minimum_supplier_score": (
                    minimum_score
                ),
                "best_score": (
                    selected.compatibility_score
                ),
                "best_supplier": (
                    selected.supplier.name
                ),
            },
        )

    return selected, ranked


def run_selection_workflow(
    request: AutonomousSelectionRunRequest,
) -> AutonomousSelectionRunResponse:

    workflow_id = (
        f"WF-{uuid.uuid4().hex[:10].upper()}"
    )

    
    
    

    try:

        read_result = read_procurement_input(
            ReadRequest(
                text=request.text,
                sources=request.sources,
            )
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "READ stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    
    
    

    try:

        reasoning = reason_about_procurement(
            read_result.intake
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "REASON stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    
    
    

    buyer_policy = _build_buyer_policy(
        request.buyer
    )

    try:

        selected, ranked = _select_supplier(
            reasoning=reasoning,
            suppliers=request.suppliers,
            buyer=buyer_policy,
            minimum_score=(
                request.minimum_supplier_score
            ),
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "SUPPLIER SELECTION stage failed."
                ),
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    supplier_policy = selected.supplier.policy

    
    
    

    try:

        action_result = act_on_procurement(
            ActRequest(
                reasoning=reasoning,
                buyer=request.buyer,
                supplier=supplier_policy,
                buyer_name=request.buyer_name,
                supplier_name=(
                    selected.supplier.name
                ),
                product_name=(
                    reasoning.product_name
                ),
                quantity=(
                    reasoning.quantity
                ),
                minimum_confidence=(
                    request.minimum_confidence
                ),
                require_complete_intake=(
                    request.require_complete_intake
                ),
            )
        )

    except HTTPException as exc:

        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": "ACT stage failed.",
                "workflow_id": workflow_id,
                "selected_supplier": (
                    selected.model_dump()
                ),
                "stage_detail": exc.detail,
            },
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "ACT stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    
    
    

    supplier_policy_model = PartyPolicy.model_validate(
        supplier_policy
    )

    try:

        verification = verify_autonomous_action(
            VerifyRequest(
                action=action_result,
                reasoning=reasoning,
                buyer=buyer_policy,
                supplier=supplier_policy_model,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "VERIFY stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    ranking = [
        item.model_dump()
        for item in ranked
    ]

    result = AutonomousSelectionRunResponse(
        workflow_id=workflow_id,
        status=(
            "verified"
            if verification.verified
            else "rejected"
        ),
        verified=verification.verified,
        selected_supplier=(
            selected.model_dump()
        ),
        ranking=ranking,
        intake=(
            read_result.intake.model_dump()
        ),
        reasoning=(
            reasoning.model_dump()
        ),
        action=(
            action_result.model_dump()
        ),
        verification=(
            verification.model_dump()
        ),
    )

    if not verification.verified:

        result.failure_stage = "VERIFY"

        result.failure_reason = (
            "; ".join(
                verification.violations
            )
            if verification.violations
            else "Verification failed."
        )

    return result


@router.post(
    "/run-with-selection",
    response_model=AutonomousSelectionRunResponse,
)
def run_with_selection(
    request: AutonomousSelectionRunRequest,
) -> AutonomousSelectionRunResponse:

    if (
        not request.text.strip()
        and not request.sources
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Provide procurement text "
                "or at least one source URL."
            ),
        )

    if not request.suppliers:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one supplier "
                "candidate is required."
            ),
        )

    if not (
        0.0
        <= request.minimum_confidence
        <= 1.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "minimum_confidence must "
                "be between 0 and 1."
            ),
        )

    if not (
        0.0
        <= request.minimum_supplier_score
        <= 1.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "minimum_supplier_score "
                "must be between 0 and 1."
            ),
        )

    return run_selection_workflow(
        request
    )