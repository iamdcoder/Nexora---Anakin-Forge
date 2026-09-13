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


class RecoveryRunRequest(BaseModel):

    text: str = ""

    sources: list[str] = Field(
        default_factory=list
    )

    suppliers: list[SupplierCandidate]

    buyer: dict[str, Any]

    buyer_name: str = "Buyer Corp"

    minimum_confidence: float = 0.50

    minimum_supplier_score: float = 0.50

    max_attempts: int = 3

    require_complete_intake: bool = False


class RecoveryAttempt(BaseModel):

    attempt: int

    supplier_name: str

    supplier_score: float

    decision: str

    negotiation_id: str | None = None

    verified: bool

    violations: list[str] = Field(
        default_factory=list
    )


class RecoveryRunResponse(BaseModel):

    workflow_id: str

    status: str

    verified: bool

    attempts_used: int

    selected_supplier: dict[str, Any] | None

    attempts: list[RecoveryAttempt]

    intake: dict[str, Any]

    reasoning: dict[str, Any]

    final_action: dict[str, Any] | None

    final_verification: dict[str, Any] | None

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


def _run_attempt(
    reasoning,
    buyer: dict[str, Any],
    supplier: SupplierCandidate,
    buyer_name: str,
    minimum_confidence: float,
    require_complete_intake: bool,
):

    action = act_on_procurement(
        ActRequest(
            reasoning=reasoning,
            buyer=buyer,
            supplier=supplier.policy,
            buyer_name=buyer_name,
            supplier_name=supplier.name,
            product_name=reasoning.product_name,
            quantity=reasoning.quantity,
            minimum_confidence=minimum_confidence,
            require_complete_intake=require_complete_intake,
        )
    )

    buyer_policy = PartyPolicy.model_validate(
        buyer
    )

    supplier_policy = PartyPolicy.model_validate(
        supplier.policy
    )

    verification = verify_autonomous_action(
        VerifyRequest(
            action=action,
            reasoning=reasoning,
            buyer=buyer_policy,
            supplier=supplier_policy,
        )
    )

    return action, verification


@router.post(
    "/recover",
    response_model=RecoveryRunResponse,
)
def run_recovery_workflow(
    request: RecoveryRunRequest,
) -> RecoveryRunResponse:

    workflow_id = (
        f"WF-{uuid.uuid4().hex[:10].upper()}"
    )

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
        1
        <= request.max_attempts
        <= 10
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "max_attempts must be between 1 and 10."
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

    if (
        reasoning.confidence
        < request.minimum_confidence
    ):

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Reasoning confidence is below "
                    "the autonomous execution threshold."
                ),
                "confidence": reasoning.confidence,
                "minimum_confidence": (
                    request.minimum_confidence
                ),
                "workflow_id": workflow_id,
            },
        )

    
    
    

    buyer_policy = _build_buyer_policy(
        request.buyer
    )

    try:

        ranked = rank_suppliers(
            reasoning=reasoning,
            suppliers=request.suppliers,
            buyer=buyer_policy,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Supplier ranking failed."
                ),
                "workflow_id": workflow_id,
                "error": str(exc),
            },
        ) from exc

    if not ranked:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "No supplier candidates "
                    "were available."
                ),
                "workflow_id": workflow_id,
            },
        )

    attempts: list[RecoveryAttempt] = []

    final_action = None

    final_verification = None

    selected_supplier = None

    suppliers_tried = 0

    
    
    

    for index, supplier_score in enumerate(
        ranked[
            : request.max_attempts
        ],
        start=1,
    ):

        suppliers_tried = index

        supplier = (
            supplier_score.supplier
        )

        if (
            supplier_score.compatibility_score
            < request.minimum_supplier_score
        ):

            attempts.append(
                RecoveryAttempt(
                    attempt=index,
                    supplier_name=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="skipped",
                    negotiation_id=None,
                    verified=False,
                    violations=[
                        (
                            "Supplier compatibility score "
                            "is below the minimum threshold."
                        )
                    ],
                )
            )

            continue

        selected_supplier = (
            supplier_score.model_dump()
        )

        try:

            action, verification = (
                _run_attempt(
                    reasoning=reasoning,
                    buyer=request.buyer,
                    supplier=supplier,
                    buyer_name=request.buyer_name,
                    minimum_confidence=(
                        request.minimum_confidence
                    ),
                    require_complete_intake=(
                        request.require_complete_intake
                    ),
                )
            )

        except HTTPException as exc:

            attempts.append(
                RecoveryAttempt(
                    attempt=index,
                    supplier_name=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="execution_failed",
                    negotiation_id=None,
                    verified=False,
                    violations=[
                        str(exc.detail)
                    ],
                )
            )

            continue

        except Exception as exc:

            attempts.append(
                RecoveryAttempt(
                    attempt=index,
                    supplier_name=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="execution_failed",
                    negotiation_id=None,
                    verified=False,
                    violations=[
                        str(exc)
                    ],
                )
            )

            continue

        final_action = action.model_dump()

        final_verification = (
            verification.model_dump()
        )

        if verification.verified:

            attempts.append(
                RecoveryAttempt(
                    attempt=index,
                    supplier_name=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="verified",
                    negotiation_id=(
                        action.negotiation_id
                    ),
                    verified=True,
                    violations=[],
                )
            )

            return RecoveryRunResponse(
                workflow_id=workflow_id,
                status="verified",
                verified=True,
                attempts_used=suppliers_tried,
                selected_supplier=(
                    selected_supplier
                ),
                attempts=attempts,
                intake=(
                    read_result.intake.model_dump()
                ),
                reasoning=(
                    reasoning.model_dump()
                ),
                final_action=final_action,
                final_verification=(
                    final_verification
                ),
            )

        attempts.append(
            RecoveryAttempt(
                attempt=index,
                supplier_name=supplier.name,
                supplier_score=(
                    supplier_score.compatibility_score
                ),
                decision="verification_failed",
                negotiation_id=(
                    action.negotiation_id
                ),
                verified=False,
                violations=(
                    verification.violations
                ),
            )
        )

        
        
        

        if verification.violations:

            
            
            
            continue

    return RecoveryRunResponse(
        workflow_id=workflow_id,
        status="recovery_exhausted",
        verified=False,
        attempts_used=suppliers_tried,
        selected_supplier=(
            selected_supplier
        ),
        attempts=attempts,
        intake=(
            read_result.intake.model_dump()
        ),
        reasoning=(
            reasoning.model_dump()
        ),
        final_action=final_action,
        final_verification=(
            final_verification
        ),
        failure_reason=(
            "Autonomous recovery exhausted "
            "its bounded supplier attempts "
            "without producing a verified result."
        ),
    )