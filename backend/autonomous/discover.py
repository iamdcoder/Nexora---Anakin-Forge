from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.reason import ProcurementReasoning
from models.policy import PartyPolicy
from autonomous.evidence import SupplierEvidenceAssessment


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class SupplierCandidate(BaseModel):

    name: str

    policy: dict[str, Any]

    evidence: list[str] = Field(
        default_factory=list
    )

    source_url: str | None = None

    description: str = ""

    evidence_assessment: (
        SupplierEvidenceAssessment | None
    ) = None


class SupplierScore(BaseModel):

    supplier: SupplierCandidate

    compatibility_score: float

    price_score: float

    delivery_score: float

    payment_score: float

    sla_score: float

    evidence_score: float

    risk_flags: list[str] = Field(
        default_factory=list
    )

    recommendation: str


class SupplierDiscoveryRequest(BaseModel):

    reasoning: ProcurementReasoning

    suppliers: list[SupplierCandidate]

    buyer: dict[str, Any]


class SupplierDiscoveryResponse(BaseModel):

    discovery_id: str

    selected_supplier: SupplierScore | None

    ranked_suppliers: list[SupplierScore]

    decision: str


def _score_range(
    value: float,
    minimum: float | None,
    maximum: float | None,
) -> float:

    if (
        minimum is not None
        and value < minimum
    ):
        return 0.0

    if (
        maximum is not None
        and value > maximum
    ):
        return 0.0

    if (
        minimum is None
        or maximum is None
        or maximum <= minimum
    ):
        return 1.0

    midpoint = (
        minimum + maximum
    ) / 2

    distance = abs(
        value - midpoint
    )

    half_range = (
        maximum - minimum
    ) / 2

    score = 1.0 - (
        distance / half_range
    )

    return round(
        max(
            0.0,
            min(
                1.0,
                score,
            ),
        ),
        4,
    )


def _score_supplier(
    candidate: SupplierCandidate,
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> SupplierScore:

    supplier_policy = (
        PartyPolicy.model_validate(
            candidate.policy
        )
    )

    price_score = _score_price(
        supplier_policy,
        buyer,
    )

    delivery_score = _score_delivery(
        supplier_policy,
        reasoning,
        buyer,
    )

    payment_score = _score_payment(
        supplier_policy,
        reasoning,
        buyer,
    )

    sla_score = _score_sla(
        supplier_policy,
        reasoning,
        buyer,
    )

    evidence_assessment = (
        candidate.evidence_assessment
    )

    if evidence_assessment is not None:

        evidence_score = (
            evidence_assessment.evidence_score
        )

    else:

        evidence_score = min(
            1.0,
            0.5
            + (
                0.1
                * len(
                    candidate.evidence
                )
            ),
        )

    risk_flags: list[str] = []

    if evidence_assessment is not None:

        risk_flags.extend(
            evidence_assessment.risk_flags
        )

    if price_score == 0:

        risk_flags.append(
            "Supplier price envelope is incompatible with buyer budget."
        )

    if delivery_score == 0:

        risk_flags.append(
            "Supplier delivery envelope cannot satisfy the procurement requirement."
        )

    if payment_score == 0:

        risk_flags.append(
            "Supplier payment requirements may conflict with buyer preferences."
        )

    if sla_score == 0:

        risk_flags.append(
            "Supplier SLA envelope may not satisfy the procurement requirement."
        )

    if not candidate.evidence:

        risk_flags.append(
            "No supplier evidence was supplied."
        )

    compatibility_score = round(
        (
            price_score * 0.30
            + delivery_score * 0.25
            + payment_score * 0.15
            + sla_score * 0.20
            + evidence_score * 0.10
        ),
        4,
    )

    
    
    if evidence_assessment is not None:

        conflicts = sum(
            claim.status == "conflict"
            for claim
            in evidence_assessment.claims
        )

        compatibility_score = round(
            max(
                0.0,
                compatibility_score
                - (
                    0.10
                    * conflicts
                ),
            ),
            4,
        )

    risk_flags = list(
        dict.fromkeys(
            risk_flags
        )
    )

    if compatibility_score >= 0.80:

        recommendation = (
            "strong_candidate"
        )

    elif compatibility_score >= 0.60:

        recommendation = "candidate"

    else:

        recommendation = (
            "weak_candidate"
        )

    return SupplierScore(
        supplier=candidate,
        compatibility_score=compatibility_score,
        price_score=price_score,
        delivery_score=delivery_score,
        payment_score=payment_score,
        sla_score=sla_score,
        evidence_score=round(
            evidence_score,
            4,
        ),
        risk_flags=risk_flags,
        recommendation=recommendation,
    )


def _score_price(
    supplier: PartyPolicy,
    buyer: PartyPolicy,
) -> float:

    supplier_min = (
        supplier.price.minimum
        if supplier.price.minimum is not None
        else supplier.price.target
    )

    supplier_max = (
        supplier.price.maximum
        if supplier.price.maximum is not None
        else supplier.price.target
    )

    buyer_min = (
        buyer.price.minimum
        if buyer.price.minimum is not None
        else buyer.price.target
    )

    buyer_max = (
        buyer.price.maximum
        if buyer.price.maximum is not None
        else buyer.price.target
    )

    overlap_min = max(
        supplier_min,
        buyer_min,
    )

    overlap_max = min(
        supplier_max,
        buyer_max,
    )

    if overlap_min > overlap_max:

        return 0.0

    return _score_range(
        buyer.price.target,
        overlap_min,
        overlap_max,
    )


def _score_delivery(
    supplier: PartyPolicy,
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> float:

    required_days = (
        reasoning.target_delivery_days
    )

    if required_days is None:

        return 1.0

    supplier_max = (
        supplier.delivery.maximum_days
    )

    buyer_max = (
        buyer.delivery.maximum_days
    )

    if (
        required_days > supplier_max
        or required_days > buyer_max
    ):

        return 0.0

    difference = abs(
        supplier.delivery.target_days
        - required_days
    )

    return round(
        max(
            0.0,
            1.0
            - (
                difference
                / max(
                    1,
                    required_days,
                )
            ),
        ),
        4,
    )


def _score_payment(
    supplier: PartyPolicy,
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> float:

    target_days = (
        reasoning.target_payment_days
    )

    if target_days is None:

        target_days = (
            buyer.payment.preferred_days
        )

    if (
        target_days
        < supplier.payment.minimum_days
    ):

        return 0.0

    if (
        target_days
        < buyer.payment.minimum_days
    ):

        return 0.0

    difference = abs(
        supplier.payment.preferred_days
        - target_days
    )

    return round(
        max(
            0.0,
            1.0
            - (
                difference
                / max(
                    1,
                    target_days,
                )
            ),
        ),
        4,
    )


def _score_sla(
    supplier: PartyPolicy,
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> float:

    target_uptime = (
        reasoning.target_sla_uptime
    )

    if target_uptime is None:

        target_uptime = (
            buyer.sla.minimum_uptime
        )

    if (
        target_uptime
        < supplier.sla.minimum_uptime
    ):

        return 0.0

    if (
        target_uptime
        < buyer.sla.minimum_uptime
    ):

        return 0.0

    return 1.0


def rank_suppliers(
    reasoning: ProcurementReasoning,
    suppliers: list[SupplierCandidate],
    buyer: PartyPolicy,
) -> list[SupplierScore]:

    ranked = [
        _score_supplier(
            candidate,
            reasoning,
            buyer,
        )
        for candidate in suppliers
    ]

    ranked.sort(
        key=lambda item: (
            item.compatibility_score,
            item.evidence_score,
        ),
        reverse=True,
    )

    return ranked


@router.post(
    "/discover",
    response_model=SupplierDiscoveryResponse,
)
def discover_supplier(
    request: SupplierDiscoveryRequest,
) -> SupplierDiscoveryResponse:

    if not request.suppliers:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one supplier candidate is required."
            ),
        )

    try:

        buyer = PartyPolicy.model_validate(
            request.buyer
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid buyer policy.",
                "error": str(exc),
            },
        ) from exc

    try:

        ranked = rank_suppliers(
            request.reasoning,
            request.suppliers,
            buyer,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Supplier evaluation failed.",
                "error": str(exc),
            },
        ) from exc

    selected = (
        ranked[0]
        if ranked
        else None
    )

    return SupplierDiscoveryResponse(
        discovery_id=(
            f"DSC-{uuid4().hex[:10].upper()}"
        ),
        selected_supplier=selected,
        ranked_suppliers=ranked,
        decision=(
            "selected"
            if selected
            else "no_candidate"
        ),
    )