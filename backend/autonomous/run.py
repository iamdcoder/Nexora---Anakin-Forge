from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.read import (
    ReadRequest,
    read_procurement_input,
)

from autonomous.reason import (
    ReasonRequest,
    reason_about_procurement,
)

from autonomous.act import (
    ActRequest,
    act_on_procurement,
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


class AutonomousRunRequest(BaseModel):

    text: str = ""

    sources: list[str] = Field(
        default_factory=list
    )

    buyer: dict[str, Any]

    supplier: dict[str, Any]

    buyer_name: str = "Buyer Corp"

    supplier_name: str = "Supplier Corp"

    product_name: str | None = None

    quantity: int | None = None

    minimum_confidence: float = 0.50

    require_complete_intake: bool = False


class AutonomousRunResponse(BaseModel):

    workflow_id: str

    status: str

    verified: bool

    intake: dict[str, Any]

    reasoning: dict[str, Any]

    action: dict[str, Any]

    verification: dict[str, Any]

    failure_stage: str | None = None

    failure_reason: str | None = None


def _policy_from_dict(
    value: dict[str, Any],
) -> PartyPolicy:

    try:

        return PartyPolicy.model_validate(
            value
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid party policy.",
                "error": str(exc),
            },
        ) from exc


def run_autonomous_workflow(
    request: AutonomousRunRequest,
) -> AutonomousRunResponse:

    import uuid

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

    
    
    

    try:

        action_result = act_on_procurement(
            ActRequest(
                reasoning=reasoning,
                buyer=request.buyer,
                supplier=request.supplier,
                buyer_name=request.buyer_name,
                supplier_name=request.supplier_name,
                product_name=request.product_name,
                quantity=request.quantity,
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

    
    
    

    buyer_policy = _policy_from_dict(
        request.buyer
    )

    supplier_policy = _policy_from_dict(
        request.supplier
    )

    try:

        verification = verify_autonomous_action(
            VerifyRequest(
                action=action_result,
                reasoning=reasoning,
                buyer=buyer_policy,
                supplier=supplier_policy,
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

    if verification.verified:

        return AutonomousRunResponse(
            workflow_id=workflow_id,
            status="verified",
            verified=True,
            intake=read_result.intake.model_dump(),
            reasoning=reasoning.model_dump(),
            action=action_result.model_dump(),
            verification=verification.model_dump(),
        )

    return AutonomousRunResponse(
        workflow_id=workflow_id,
        status="rejected",
        verified=False,
        intake=read_result.intake.model_dump(),
        reasoning=reasoning.model_dump(),
        action=action_result.model_dump(),
        verification=verification.model_dump(),
        failure_stage="VERIFY",
        failure_reason=(
            "; ".join(
                verification.violations
            )
            if verification.violations
            else "Verification failed."
        ),
    )


@router.post(
    "/run",
    response_model=AutonomousRunResponse,
)
def run_autonomous(
    request: AutonomousRunRequest,
) -> AutonomousRunResponse:

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

    return run_autonomous_workflow(
        request
    )