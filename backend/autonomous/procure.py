from __future__ import annotations

import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.failure import (
    FailureCode,
    classify_failure,
)

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
    SourceRead,
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


class ProcurementSupplier(BaseModel):

    name: str

    source_url: str

    policy: dict[str, Any]

    description: str = ""


class AutonomousProcurementRequest(BaseModel):

    text: str = ""

    sources: list[str] = Field(
        default_factory=list
    )

    suppliers: list[ProcurementSupplier]

    buyer: dict[str, Any]

    buyer_name: str = "Buyer Corp"

    minimum_confidence: float = 0.50

    minimum_supplier_score: float = 0.50

    max_attempts: int = 3

    require_complete_intake: bool = False

    execution_mode: Literal[
        "auto",
        "simulation",
        "lyzr",
    ] = "auto"

    demo_fault: Literal[
        "none",
        "recovery_once",
    ] = "none"


class ProcurementAttempt(BaseModel):

    attempt: int

    supplier: str

    supplier_score: float

    decision: str

    negotiation_id: str | None = None

    verified: bool

    violations: list[str] = Field(
        default_factory=list
    )

    recovery_triggered: bool = False

    recovery_reason: str | None = None

    failure_code: FailureCode | None = None


class FailureProvenance(BaseModel):

    stage: str

    code: FailureCode

    attempt: int | None = None

    supplier: str | None = None

    message: str

    recoverable: bool


class AutonomousProcurementResponse(BaseModel):

    workflow_id: str

    anakin: dict[str, Any] = Field(default_factory=dict)

    status: str

    verified: bool

    stages: dict[str, str]

    intake: dict[str, Any]

    reasoning: dict[str, Any]

    reasoning_history: list[dict[str, Any]] = Field(
        default_factory=list
    )

    recovery_events: list[dict[str, Any]] = Field(
        default_factory=list
    )

    failure_provenance: list[FailureProvenance] = Field(
        default_factory=list
    )

    supplier_ranking: list[dict[str, Any]]

    selected_supplier: dict[str, Any] | None

    attempts: list[ProcurementAttempt]

    final_action: dict[str, Any] | None

    final_verification: dict[str, Any] | None

    failure_reason: str | None = None

    failure_code: FailureCode | None = None

    demo: dict[str, Any] = Field(
        default_factory=dict
    )


def _buyer_policy(
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
                "message": "Invalid buyer policy.",
                "error": str(exc),
            },
        ) from exc


def _read_supplier(
    supplier: ProcurementSupplier,
    source_by_url: dict[str, Any] | None = None,
    read_live_source: bool = True,
) -> SupplierCandidate:

    source = (source_by_url or {}).get(
        supplier.source_url
    )

    if source is None and read_live_source:
        from autonomous.read import _fetch_source
        source = _fetch_source(
            supplier.source_url
        )

    evidence: list[str] = []

    if source is None:
        source = SourceRead(
            url=supplier.source_url,
            status="read",
            title=supplier.name,
            text=supplier.description,
            provider="simulation",
            source_mode="SIMULATION",
            authenticated=False,
            evidence_snippets=(
                [supplier.description]
                if supplier.description
                else []
            ),
        )

    if source.status == "read":
        if source.title:
            evidence.append(
                f"Website title: {source.title}"
            )
        if source.text:
            evidence.append(
                "Website content: "
                + source.text[:1000]
            )
    else:
        evidence.append(
            "Website read failed: "
            + (
                source.error
                or source.status
            )
        )

    return SupplierCandidate(
        name=supplier.name,
        policy=supplier.policy,
        evidence=evidence,
        source_url=supplier.source_url,
        description=supplier.description,
    )


def _build_failure_context(
    *,
    attempt: int,
    supplier: str,
    stage: str,
    message: str,
    violations: list[str] | None = None,
) -> str:

    details = message.strip()

    if violations:

        details += (
            " Violations: "
            + "; ".join(
                violations
            )
            + "."
        )

    return (
        f"Attempt {attempt} failed for supplier "
        f"{supplier} during {stage}. "
        f"{details} "
        "Re-evaluate the remaining suppliers. "
        "Do not relax hard procurement constraints "
        "just to obtain a deal."
    )


def _failure_code(
    *,
    stage: str,
    error: Any = None,
    violations: list[str] | None = None,
) -> FailureCode:
    return classify_failure(
        stage=stage,
        error=error,
        violations=violations,
    )


def _record_failure(
    *,
    failure_provenance: list[FailureProvenance],
    stage: str,
    code: FailureCode,
    message: str,
    attempt: int | None = None,
    supplier: str | None = None,
    recoverable: bool = False,
) -> None:
    failure_provenance.append(
        FailureProvenance(
            stage=stage,
            code=code,
            attempt=attempt,
            supplier=supplier,
            message=message,
            recoverable=recoverable,
        )
    )


def _recover_and_rerank(
    *,
    intake,
    buyer: PartyPolicy,
    current_ranked: list,
    attempted_supplier_names: set[str],
    failure_context: str,
    recovery_events: list[dict[str, Any]],
    reasoning_history: list[dict[str, Any]],
    attempt: int,
    failed_supplier: str,
    stages: dict[str, str],
):

    recovery_events.append(
        {
            "attempt": attempt,
            "trigger": "REASON_AGAIN",
            "supplier": failed_supplier,
            "message": failure_context,
        }
    )

    new_reasoning = reason_about_procurement(
        intake,
        use_ai=True,
        buyer_policy=buyer.model_dump(),
        failure_context=failure_context,
    )

    reasoning_history.append(
        new_reasoning.model_dump()
    )

    remaining = [
        item
        for item in current_ranked
        if item.supplier.name
        not in attempted_supplier_names
    ]

    reranked = rank_suppliers(
        reasoning=new_reasoning,
        suppliers=[
            item.supplier
            for item in remaining
        ],
        buyer=buyer,
    )

    stages["reason"] = "complete"
    stages["supplier_selection"] = (
        "complete"
        if reranked
        else "failed"
    )
    stages["recovery"] = "complete"

    return (
        new_reasoning,
        reranked,
    )


def procure(
    request: AutonomousProcurementRequest,
) -> AutonomousProcurementResponse:

    workflow_id = (
        f"WF-{uuid.uuid4().hex[:10].upper()}"
    )

    stages = {
        "read": "pending",
        "reason": "pending",
        "supplier_selection": "pending",
        "act": "pending",
        "verify": "pending",
        "recovery": "not_needed",
    }

    anakin_sources_read = 0
    anakin_authenticated = False
    anakin_fallbacks = 0
    source_by_url: dict[str, Any] = {}

    try:

        read_result = read_procurement_input(
            ReadRequest(
                text=request.text,
                sources=request.sources,
            )
        )

        stages["read"] = "complete"

        source_by_url = {
            source.url: source
            for source in read_result.sources
        }

        for source in read_result.sources:
            if source.provider == "anakin" and source.status == "read":
                anakin_sources_read += 1
                anakin_authenticated = anakin_authenticated or source.authenticated
            if source.provider == "direct_http" and source.error and "Anakin unavailable" in source.error:
                anakin_fallbacks += 1

    except HTTPException:

        stages["read"] = "failed"

        raise

    except Exception as exc:

        stages["read"] = "failed"

        code = _failure_code(
            stage="READ",
            error=exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": "READ stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
                "failure_code": code,
            },
        ) from exc

    try:

        reasoning = reason_about_procurement(
            read_result.intake,
            use_ai=True,
            buyer_policy=request.buyer,
        )

        stages["reason"] = "complete"

    except Exception as exc:

        stages["reason"] = "failed"

        code = _failure_code(
            stage="REASON",
            error=exc,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": "REASON stage failed.",
                "workflow_id": workflow_id,
                "error": str(exc),
                "failure_code": code,
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
                    "Procurement reasoning confidence "
                    "is below the execution threshold."
                ),
                "workflow_id": workflow_id,
                "confidence": (
                    reasoning.confidence
                ),
                "minimum_confidence": (
                    request.minimum_confidence
                ),
            },
        )

    buyer = _buyer_policy(
        request.buyer
    )

    try:

        candidates = [
            _read_supplier(
                supplier,
                source_by_url=source_by_url,
                read_live_source=(
                    request.execution_mode
                    != "simulation"
                ),
            )
            for supplier in request.suppliers
        ]

        ranked = rank_suppliers(
            reasoning=reasoning,
            suppliers=candidates,
            buyer=buyer,
        )

        stages[
            "supplier_selection"
        ] = "complete"

    except Exception as exc:

        stages[
            "supplier_selection"
        ] = "failed"

        code = _failure_code(
            stage="SUPPLIER_SELECTION",
            error=exc,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Supplier selection stage failed."
                ),
                "workflow_id": workflow_id,
                "error": str(exc),
                "failure_code": code,
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

    ranked = [
        item
        for item in ranked
        if (
            item.compatibility_score
            >= request.minimum_supplier_score
        )
    ]

    if not ranked:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "No supplier met the minimum "
                    "compatibility score."
                ),
                "workflow_id": workflow_id,
                "minimum_supplier_score": (
                    request.minimum_supplier_score
                ),
            },
        )

    attempts: list[ProcurementAttempt] = []

    final_action = None

    final_verification = None

    selected_supplier = None

    reasoning_history = [
        reasoning.model_dump()
    ]

    recovery_events: list[
        dict[str, Any]
    ] = []

    failure_provenance: list[FailureProvenance] = []

    attempted_supplier_names: set[str] = set()

    max_attempts = min(
        request.max_attempts,
        len(ranked),
    )

    current_ranked = list(
        ranked
    )

    last_failure_code: FailureCode | None = None

    demo_fault_consumed = False

    for attempt_number in range(
        1,
        max_attempts + 1,
    ):

        available_ranked = [
            item
            for item in current_ranked
            if item.supplier.name
            not in attempted_supplier_names
        ]

        if not available_ranked:
            break

        supplier_score = (
            available_ranked[0]
        )

        supplier = (
            supplier_score.supplier
        )

        attempted_supplier_names.add(
            supplier.name
        )

        selected_supplier = (
            supplier_score.model_dump()
        )

        if (
            supplier_score.compatibility_score
            < request.minimum_supplier_score
        ):

            attempts.append(
                ProcurementAttempt(
                    attempt=attempt_number,
                    supplier=supplier.name,
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
                    recovery_triggered=(
                        attempt_number < max_attempts
                    ),
                    recovery_reason=(
                        "Supplier rejected by minimum "
                        "compatibility threshold."
                        if attempt_number < max_attempts
                        else None
                    ),
                    failure_code="SELECTION_ERROR",
                )
            )

            if attempt_number < max_attempts:

                failure_context = _build_failure_context(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    stage="SUPPLIER_SELECTION",
                    message=(
                        "The supplier was below the "
                        "minimum compatibility threshold."
                    ),
                )

                try:

                    (
                        reasoning,
                        current_ranked,
                    ) = _recover_and_rerank(
                        intake=read_result.intake,
                        buyer=buyer,
                        current_ranked=current_ranked,
                        attempted_supplier_names=(
                            attempted_supplier_names
                        ),
                        failure_context=failure_context,
                        recovery_events=recovery_events,
                        reasoning_history=(
                            reasoning_history
                        ),
                        attempt=attempt_number,
                        failed_supplier=supplier.name,
                        stages=stages,
                    )

                except Exception as exc:

                    stages["recovery"] = "failed"

                    last_failure_code = _failure_code(
                        stage="RECOVERY",
                        error=exc,
                    )

                    _record_failure(
                        failure_provenance=failure_provenance,
                        stage="RECOVERY",
                        code=last_failure_code,
                        message=str(exc),
                        attempt=attempt_number,
                        supplier=supplier.name,
                        recoverable=False,
                    )

                    recovery_events.append(
                        {
                            "attempt": attempt_number,
                            "trigger": (
                                "RECOVERY_REASONING_FAILURE"
                            ),
                            "supplier": supplier.name,
                            "message": str(exc),
                            "failure_code": last_failure_code,
                        }
                    )

            continue

        if (
            request.demo_fault == "recovery_once"
            and not demo_fault_consumed
        ):

            demo_fault_consumed = True
            stages["act"] = "failed"

            demo_fault_message = (
                "Controlled flagship demo fault injection: "
                "the first supplier attempt is intentionally blocked "
                "so Nexora must autonomously recover. No fake negotiation "
                "result is produced; the next attempt runs through the "
                "normal ACT and VERIFY stages."
            )

            failure_context = _build_failure_context(
                attempt=attempt_number,
                supplier=supplier.name,
                stage="ACT",
                message=demo_fault_message,
            )

            last_failure_code = "DEMO_FAULT"

            _record_failure(
                failure_provenance=failure_provenance,
                stage="ACT",
                code=last_failure_code,
                message=demo_fault_message,
                attempt=attempt_number,
                supplier=supplier.name,
                recoverable=(
                    attempt_number < max_attempts
                ),
            )

            attempts.append(
                ProcurementAttempt(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="demo_fault_injected",
                    negotiation_id=None,
                    verified=False,
                    violations=[demo_fault_message],
                    recovery_triggered=(
                        attempt_number < max_attempts
                    ),
                    recovery_reason=(
                        "Controlled demo fault triggered; "
                        "Nexora will re-rank remaining suppliers."
                        if attempt_number < max_attempts
                        else None
                    ),
                    failure_code=last_failure_code,
                )
            )

            if attempt_number < max_attempts:

                try:

                    (
                        reasoning,
                        current_ranked,
                    ) = _recover_and_rerank(
                        intake=read_result.intake,
                        buyer=buyer,
                        current_ranked=current_ranked,
                        attempted_supplier_names=(
                            attempted_supplier_names
                        ),
                        failure_context=failure_context,
                        recovery_events=recovery_events,
                        reasoning_history=reasoning_history,
                        attempt=attempt_number,
                        failed_supplier=supplier.name,
                        stages=stages,
                    )

                except Exception as exc:

                    stages["recovery"] = "failed"

                    recovery_failure_code = _failure_code(
                        stage="RECOVERY",
                        error=exc,
                    )

                    last_failure_code = recovery_failure_code

                    _record_failure(
                        failure_provenance=failure_provenance,
                        stage="RECOVERY",
                        code=recovery_failure_code,
                        message=str(exc),
                        attempt=attempt_number,
                        supplier=supplier.name,
                        recoverable=False,
                    )

                    recovery_events.append(
                        {
                            "attempt": attempt_number,
                            "trigger": "RECOVERY_REASONING_FAILURE",
                            "supplier": supplier.name,
                            "message": str(exc),
                            "failure_code": recovery_failure_code,
                        }
                    )

            continue

        try:

            action = act_on_procurement(
                ActRequest(
                    reasoning=reasoning,
                    buyer=request.buyer,
                    supplier=supplier.policy,
                    buyer_name=request.buyer_name,
                    supplier_name=supplier.name,
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
                    execution_mode=(
                        request.execution_mode
                    ),
                )
            )

            stages["act"] = "complete"

        except Exception as exc:

            failure_context = (
                _build_failure_context(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    stage="ACT",
                    message=str(exc),
                )
            )

            failure_code = _failure_code(
                stage="ACT",
                error=exc,
            )

            last_failure_code = failure_code

            _record_failure(
                failure_provenance=failure_provenance,
                stage="ACT",
                code=failure_code,
                message=str(exc),
                attempt=attempt_number,
                supplier=supplier.name,
                recoverable=(attempt_number < max_attempts),
            )

            attempts.append(
                ProcurementAttempt(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="execution_failed",
                    negotiation_id=None,
                    verified=False,
                    violations=[
                        str(exc)
                    ],
                    recovery_triggered=(
                        attempt_number < max_attempts
                    ),
                    recovery_reason=(
                        "ACT failed; Nexora will "
                        "re-evaluate remaining suppliers."
                        if attempt_number < max_attempts
                        else None
                    ),
                    failure_code=failure_code,
                )
            )

            if attempt_number < max_attempts:

                try:

                    (
                        reasoning,
                        current_ranked,
                    ) = _recover_and_rerank(
                        intake=read_result.intake,
                        buyer=buyer,
                        current_ranked=current_ranked,
                        attempted_supplier_names=(
                            attempted_supplier_names
                        ),
                        failure_context=failure_context,
                        recovery_events=recovery_events,
                        reasoning_history=(
                            reasoning_history
                        ),
                        attempt=attempt_number,
                        failed_supplier=supplier.name,
                        stages=stages,
                    )

                except Exception as recovery_exc:

                    stages["recovery"] = "failed"

                    last_failure_code = _failure_code(
                        stage="RECOVERY",
                        error=recovery_exc,
                    )

                    recovery_failure_code = _failure_code(
                        stage="RECOVERY",
                        error=recovery_exc,
                    )
                    last_failure_code = recovery_failure_code

                    _record_failure(
                        failure_provenance=failure_provenance,
                        stage="RECOVERY",
                        code=recovery_failure_code,
                        message=str(recovery_exc),
                        attempt=attempt_number,
                        supplier=supplier.name,
                        recoverable=False,
                    )

                    recovery_events.append(
                        {
                            "attempt": attempt_number,
                            "trigger": (
                                "RECOVERY_REASONING_FAILURE"
                            ),
                            "supplier": supplier.name,
                            "message": str(
                                recovery_exc
                            ),
                            "failure_code": recovery_failure_code,
                        }
                    )

            continue

        try:

            supplier_policy = (
                PartyPolicy.model_validate(
                    supplier.policy
                )
            )

            verification = (
                verify_autonomous_action(
                    VerifyRequest(
                        action=action,
                        reasoning=reasoning,
                        buyer=buyer,
                        supplier=supplier_policy,
                    )
                )
            )

            stages["verify"] = (
                "complete"
                if verification.verified
                else "failed"
            )

        except Exception as exc:

            stages["verify"] = "failed"

            failure_code = _failure_code(
                stage="VERIFY",
                error=exc,
            )

            last_failure_code = failure_code

            _record_failure(
                failure_provenance=failure_provenance,
                stage="VERIFY",
                code=failure_code,
                message=str(exc),
                attempt=attempt_number,
                supplier=supplier.name,
                recoverable=(attempt_number < max_attempts),
            )

            failure_context = (
                _build_failure_context(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    stage="VERIFY",
                    message=str(exc),
                )
            )

            attempts.append(
                ProcurementAttempt(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="verification_error",
                    negotiation_id=(
                        action.negotiation_id
                    ),
                    verified=False,
                    violations=[
                        str(exc)
                    ],
                    recovery_triggered=(
                        attempt_number < max_attempts
                    ),
                    recovery_reason=(
                        "VERIFY produced an error; "
                        "Nexora will re-evaluate "
                        "remaining suppliers."
                        if attempt_number < max_attempts
                        else None
                    ),
                    failure_code=failure_code,
                )
            )

            if attempt_number < max_attempts:

                try:

                    (
                        reasoning,
                        current_ranked,
                    ) = _recover_and_rerank(
                        intake=read_result.intake,
                        buyer=buyer,
                        current_ranked=current_ranked,
                        attempted_supplier_names=(
                            attempted_supplier_names
                        ),
                        failure_context=failure_context,
                        recovery_events=recovery_events,
                        reasoning_history=(
                            reasoning_history
                        ),
                        attempt=attempt_number,
                        failed_supplier=supplier.name,
                        stages=stages,
                    )

                except Exception as recovery_exc:

                    stages["recovery"] = "failed"

                    recovery_failure_code = _failure_code(
                        stage="RECOVERY",
                        error=recovery_exc,
                    )
                    last_failure_code = recovery_failure_code

                    _record_failure(
                        failure_provenance=failure_provenance,
                        stage="RECOVERY",
                        code=recovery_failure_code,
                        message=str(recovery_exc),
                        attempt=attempt_number,
                        supplier=supplier.name,
                        recoverable=False,
                    )

                    recovery_events.append(
                        {
                            "attempt": attempt_number,
                            "trigger": (
                                "RECOVERY_REASONING_FAILURE"
                            ),
                            "supplier": supplier.name,
                            "message": str(
                                recovery_exc
                            ),
                            "failure_code": recovery_failure_code,
                        }
                    )

            continue

        final_action = (
            action.model_dump()
        )

        final_verification = (
            verification.model_dump()
        )

        if verification.verified:

            attempts.append(
                ProcurementAttempt(
                    attempt=attempt_number,
                    supplier=supplier.name,
                    supplier_score=(
                        supplier_score.compatibility_score
                    ),
                    decision="verified",
                    negotiation_id=(
                        action.negotiation_id
                    ),
                    verified=True,
                    violations=[],
                    recovery_triggered=False,
                    recovery_reason=None,
                )
            )

            return AutonomousProcurementResponse(
                workflow_id=workflow_id,
                anakin={
                    "enabled": os.getenv("ANAKIN_ENABLED", "1").strip() == "1",
                    "sources_read": anakin_sources_read,
                    "authenticated": anakin_authenticated,
                    "direct_http_fallbacks": anakin_fallbacks,
                    "role": "live supplier web evidence ingestion",
                "sources": [
                    {
                        "url": source.url,
                        "provider": source.provider,
                        "status": source.status,
                        "duration_ms": source.duration_ms,
                        "credits_remaining": source.credits_remaining,
                    }
                    for source in read_result.sources
                ],
                },
                status="verified",
                verified=True,
                stages=stages,
                intake=(
                    read_result.intake.model_dump()
                ),
                reasoning=(
                    reasoning.model_dump()
                ),
                reasoning_history=(
                    reasoning_history
                ),
                recovery_events=(
                    recovery_events
                ),
                failure_provenance=(
                    failure_provenance
                ),
                supplier_ranking=[
                    item.model_dump()
                    for item in current_ranked
                ],
                selected_supplier=(
                    selected_supplier
                ),
                attempts=attempts,
                final_action=final_action,
                final_verification=(
                    final_verification
                ),
                failure_code=None,
                demo={
                    "enabled": request.demo_fault != "none",
                    "fault": request.demo_fault,
                    "fault_injected": demo_fault_consumed,
                    "description": (
                        "Controlled recovery demonstration"
                        if request.demo_fault != "none"
                        else "Standard autonomous procurement run"
                    ),
                },
            )

        failure_context = _build_failure_context(
            attempt=attempt_number,
            supplier=supplier.name,
            stage="VERIFY",
            message=(
                "The negotiation completed, "
                "but independent verification rejected "
                "the resulting agreement."
            ),
            violations=verification.violations,
        )

        failure_code = _failure_code(
            stage="VERIFY",
            violations=verification.violations,
        )

        last_failure_code = failure_code

        _record_failure(
            failure_provenance=failure_provenance,
            stage="VERIFY",
            code=failure_code,
            message=(
                "; ".join(verification.violations)
                or "Independent verification rejected the agreement."
            ),
            attempt=attempt_number,
            supplier=supplier.name,
            recoverable=(attempt_number < max_attempts),
        )

        attempts.append(
            ProcurementAttempt(
                attempt=attempt_number,
                supplier=supplier.name,
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
                recovery_triggered=(
                    attempt_number < max_attempts
                ),
                recovery_reason=(
                    "Verification failed; Nexora will "
                    "re-evaluate remaining suppliers."
                    if attempt_number < max_attempts
                    else None
                ),
                failure_code=failure_code,
            )
        )

        if attempt_number < max_attempts:

            try:

                (
                    reasoning,
                    current_ranked,
                ) = _recover_and_rerank(
                    intake=read_result.intake,
                    buyer=buyer,
                    current_ranked=current_ranked,
                    attempted_supplier_names=(
                        attempted_supplier_names
                    ),
                    failure_context=failure_context,
                    recovery_events=recovery_events,
                    reasoning_history=(
                        reasoning_history
                    ),
                    attempt=attempt_number,
                    failed_supplier=supplier.name,
                    stages=stages,
                )

            except Exception as recovery_exc:

                stages["recovery"] = "failed"

                recovery_events.append(
                    {
                        "attempt": attempt_number,
                        "trigger": (
                            "RECOVERY_REASONING_FAILURE"
                        ),
                        "supplier": supplier.name,
                        "message": str(
                            recovery_exc
                        ),
                    }
                )

    stages["act"] = (
        "complete"
        if final_action
        else "failed"
    )

    return AutonomousProcurementResponse(
        workflow_id=workflow_id,
        anakin={
            "enabled": os.getenv("ANAKIN_ENABLED", "1").strip() == "1",
            "sources_read": anakin_sources_read,
            "authenticated": anakin_authenticated,
            "direct_http_fallbacks": anakin_fallbacks,
            "role": "live supplier web evidence ingestion",
            "sources": [
                {
                    "url": source.url,
                    "provider": source.provider,
                    "status": source.status,
                    "duration_ms": source.duration_ms,
                    "credits_remaining": source.credits_remaining,
                }
                for source in read_result.sources
            ],
        },
        status="recovery_exhausted",
        verified=False,
        stages=stages,
        intake=(
            read_result.intake.model_dump()
        ),
        reasoning=(
            reasoning.model_dump()
        ),
        reasoning_history=(
            reasoning_history
        ),
        recovery_events=(
            recovery_events
        ),
        failure_provenance=(
            failure_provenance
        ),
        supplier_ranking=[
            item.model_dump()
            for item in current_ranked
        ],
        selected_supplier=(
            selected_supplier
        ),
        attempts=attempts,
        final_action=final_action,
        final_verification=(
            final_verification
        ),
        failure_reason=(
            "Nexora exhausted its bounded "
            "supplier attempts without producing "
            "a verified agreement."
        ),
        failure_code=last_failure_code or "UNKNOWN_ERROR",
        demo={
            "enabled": request.demo_fault != "none",
            "fault": request.demo_fault,
            "fault_injected": demo_fault_consumed,
            "description": (
                "Controlled recovery demonstration"
                if request.demo_fault != "none"
                else "Standard autonomous procurement run"
            ),
        },
    )


@router.post(
    "/procure",
    response_model=AutonomousProcurementResponse,
)
def autonomous_procurement(
    request: AutonomousProcurementRequest,
) -> AutonomousProcurementResponse:

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
                "Provide at least one supplier."
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
                "minimum_confidence must be "
                "between 0 and 1."
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
                "minimum_supplier_score must "
                "be between 0 and 1."
            ),
        )

    return procure(
        request
    )