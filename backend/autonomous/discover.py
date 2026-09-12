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

    scoring_weights: dict[str, float] = Field(
        default_factory=dict
    )

    selection_rationale: str = ""

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


def _priority_position(
    priorities: list[str],
    aliases: tuple[str, ...],
) -> int | None:

    for index, priority in enumerate(priorities):

        text = priority.casefold()

        if any(
            alias in text
            for alias in aliases
        ):
            return index

    return None


def _build_scoring_weights(
    reasoning: ProcurementReasoning,
) -> dict[str, float]:
    """Translate reasoning priorities into bounded scoring weights.

    The reasoning agent can influence trade-off emphasis, but it cannot
    introduce arbitrary scoring dimensions or bypass deterministic policy
    checks. Only known procurement dimensions are recognized here.
    """

    base_weights = {
        "price": 0.30,
        "delivery": 0.25,
        "payment": 0.15,
        "sla": 0.20,
        "evidence": 0.10,
    }

    aliases = {
        "price": (
            "price",
            "cost",
            "budget",
            "commercial",
        ),
        "delivery": (
            "delivery",
            "timeline",
            "lead time",
            "urgency",
        ),
        "payment": (
            "payment",
            "terms",
            "credit",
        ),
        "sla": (
            "sla",
            "uptime",
            "availability",
            "service level",
        ),
        "evidence": (
            "evidence",
            "quality",
            "compliance",
            "certification",
            "documentation",
            "provenance",
            "risk",
        ),
    }

    multipliers = (
        1.60,
        1.10,
        0.95,
        0.85,
    )

    adjusted: dict[str, float] = {}

    for dimension, base in base_weights.items():

        position = _priority_position(
            reasoning.priorities,
            aliases[dimension],
        )

        if position is None:

            multiplier = 0.80

        elif position < len(multipliers):

            multiplier = multipliers[
                position
            ]

        else:

            multiplier = 0.80

        adjusted[dimension] = (
            base * multiplier
        )

    total = sum(
        adjusted.values()
    )

    if total <= 0:

        return base_weights

    return {
        key: round(
            value / total,
            4,
        )
        for key, value in adjusted.items()
    }


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

    scoring_weights = _build_scoring_weights(
        reasoning
    )

    # ------------------------------------------------------------
    # HARD POLICY FIREWALL
    # ------------------------------------------------------------
    #
    # Evidence and reasoning priorities are allowed to influence
    # trade-offs only after deterministic policy feasibility has
    # been established.
    #
    # A supplier failing ANY hard procurement dimension is
    # immediately considered ineligible.
    #
    # This prevents a supplier with perfect Anakin evidence or a
    # highly favorable AI-generated ranking from reaching ACT while
    # violating budget, delivery, payment, or SLA requirements.
    # ------------------------------------------------------------

    hard_policy_failures: list[str] = []

    if price_score <= 0:

        hard_policy_failures.append(
            "price"
        )

    if delivery_score <= 0:

        hard_policy_failures.append(
            "delivery"
        )

    if payment_score <= 0:

        hard_policy_failures.append(
            "payment"
        )

    if sla_score <= 0:

        hard_policy_failures.append(
            "sla"
        )

    if hard_policy_failures:

        compatibility_score = 0.0

        for dimension in hard_policy_failures:

            flag = (
                f"Hard procurement constraint failed: "
                f"{dimension}."
            )

            if flag not in risk_flags:

                risk_flags.append(
                    flag
                )

    else:

        compatibility_score = round(
            (
                price_score
                * scoring_weights["price"]
                + delivery_score
                * scoring_weights["delivery"]
                + payment_score
                * scoring_weights["payment"]
                + sla_score
                * scoring_weights["sla"]
                + evidence_score
                * scoring_weights["evidence"]
            ),
            4,
        )

    # Evidence conflicts reduce an otherwise feasible supplier,
    # but evidence can never restore eligibility after a hard
    # policy failure.
    if (
        evidence_assessment is not None
        and not hard_policy_failures
    ):

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

    if hard_policy_failures:

        recommendation = (
            "ineligible"
        )

    elif compatibility_score >= 0.80:

        recommendation = (
            "strong_candidate"
        )

    elif compatibility_score >= 0.60:

        recommendation = "candidate"

    else:

        recommendation = (
            "weak_candidate"
        )

    priority_summary = (
        ", ".join(
            reasoning.priorities[:3]
        )
        if reasoning.priorities
        else "default procurement priorities"
    )

    if hard_policy_failures:

        selection_rationale = (
            "Supplier rejected by deterministic hard-policy validation. "
            "Failed dimensions: "
            + ", ".join(
                hard_policy_failures
            )
            + ". "
            "Anakin evidence and AI reasoning cannot override hard procurement constraints."
        )

    else:

        selection_rationale = (
            f"Ranked using deterministic supplier compatibility with emphasis on: "
            f"{priority_summary}. "
            f"The resulting score is {compatibility_score:.4f}; "
            f"model recommendations cannot override policy validation."
        )

    return SupplierScore(
        supplier=candidate,
        compatibility_score=(
            compatibility_score
        ),
        price_score=price_score,
        delivery_score=delivery_score,
        payment_score=payment_score,
        sla_score=sla_score,
        evidence_score=round(
            evidence_score,
            4,
        ),
        scoring_weights=scoring_weights,
        selection_rationale=(
            selection_rationale
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

    # A feasible price overlap exists. Price is not a "closer to the
    # midpoint is best" dimension like delivery/payment/SLA — for the
    # buyer, cheaper is always strictly better, never "too cheap" in
    # the way a delivery date can be "too soon" relative to a target.
    # Re-using `_score_range`'s centrality formula here (as the
    # original implementation did) silently zeroes out the score
    # whenever the buyer's target sits outside the overlap window —
    # which is the *expected*, common case, since a buyer's target is
    # an aspirational anchor and is supposed to sit below what any
    # supplier's floor can actually offer. That's what the negotiation
    # stage exists to close. A hard zero there wrongly treats a
    # negotiable gap as a disqualifying incompatibility.
    #
    # Instead, score monotonically: lower achievable prices are always
    # better, never penalized. Blend two monotonic signals:
    #   - floor_component: how favorable the cheapest price actually
    #     achievable in the overlap (`overlap_min`) is, relative to the
    #     buyer's own full acceptable band.
    #   - asking_component: how favorable the supplier's own price
    #     target is within the overlap, so two suppliers with the same
    #     floor but a cheaper asking price/ceiling still differentiate.
    # Both are 1.0 for the cheapest possible outcome and taper toward
    # 0.0 for the most expensive outcome still inside the overlap —
    # never dropping below 0.0 or hitting an artificial hard zero.

    buyer_band = max(
        1,
        buyer_max - buyer_min,
    )

    floor_component = max(
        0.0,
        min(
            1.0,
            1.0
            - (
                (overlap_min - buyer_min)
                / buyer_band
            ),
        ),
    )

    overlap_width = max(
        1,
        overlap_max - overlap_min,
    )

    clamped_supplier_target = min(
        max(
            supplier.price.target,
            overlap_min,
        ),
        overlap_max,
    )

    asking_component = max(
        0.0,
        min(
            1.0,
            1.0
            - (
                (clamped_supplier_target - overlap_min)
                / overlap_width
            ),
        ),
    )

    return round(
        (
            floor_component
            + asking_component
        )
        / 2,
        4,
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