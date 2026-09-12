from __future__ import annotations

import re
from typing import Any

from autonomous.reason import ProcurementReasoning
from autonomous.read import SourceRead
from models.policy import PartyPolicy
from pydantic import BaseModel, Field


class EvidenceFinding(BaseModel):
    field: str
    observed_value: str
    required_value: str
    status: str
    severity: str
    source_url: str | None = None
    explanation: str


class SupplierEvidenceAssessment(BaseModel):
    source_status: str
    source_url: str | None = None
    claims: list[EvidenceFinding] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    evidence_score: float = 0.5
    summary: str = ""


def _first_number(
    patterns: list[str],
    text: str,
    cast: Any = float,
) -> Any:

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        try:
            return cast(
                match.group(1)
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return None


def extract_supplier_claims(
    source: SourceRead,
) -> dict[str, Any]:

    text = " ".join(
        part
        for part in [
            source.title or "",
            source.text or "",
        ]
        if part
    )

    delivery_days = _first_number(
        [
            (
                r"(?:delivery|lead\s*time|ships?|"
                r"dispatch(?:es)?)\D{0,30}"
                r"(\d+)\s*(?:business\s*)?days?"
            ),
            (
                r"(?:within|under|in)\s+"
                r"(\d+)\s*days?\s+"
                r"(?:delivery|shipping|dispatch)"
            ),
        ],
        text,
        int,
    )

    payment_days = _first_number(
        [
            (
                r"(?:net|payment\s*terms?|credit)"
                r"\D{0,20}(\d+)\s*days?"
            ),
            (
                r"(\d+)\s*day(?:s)?\s+"
                r"(?:credit|payment)\s*terms?"
            ),
        ],
        text,
        int,
    )

    sla_uptime = _first_number(
        [
            (
                r"(?:uptime|availability|"
                r"service\s*level)\D{0,30}"
                r"(\d+(?:\.\d+)?)\s*%"
            ),
            (
                r"(\d+(?:\.\d+)?)\s*%\s+"
                r"(?:uptime|availability)"
            ),
        ],
        text,
        float,
    )

    return {
        "delivery_days": delivery_days,
        "payment_days": payment_days,
        "sla_uptime": sla_uptime,
    }


def _finding(
    *,
    field: str,
    observed: Any,
    required: Any,
    status: str,
    severity: str,
    source_url: str | None,
    explanation: str,
) -> EvidenceFinding:

    return EvidenceFinding(
        field=field,
        observed_value=str(observed),
        required_value=str(required),
        status=status,
        severity=severity,
        source_url=source_url,
        explanation=explanation,
    )


def assess_supplier_evidence(
    source: SourceRead,
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> SupplierEvidenceAssessment:

    if source.status != "read":

        return SupplierEvidenceAssessment(
            source_status=source.status,
            source_url=source.url,
            claims=[],
            risk_flags=[
                (
                    "Supplier website could not be "
                    "verified from the supplied source."
                )
            ],
            evidence_score=0.25,
            summary=(
                "No readable supplier evidence was "
                "available; the supplier should be "
                "treated with lower evidence confidence."
            ),
        )

    claims_data = extract_supplier_claims(
        source
    )

    claims: list[EvidenceFinding] = []

    risk_flags: list[str] = []

    observed_delivery = claims_data[
        "delivery_days"
    ]

    required_delivery = (
        reasoning.target_delivery_days
    )

    if (
        observed_delivery is not None
        and required_delivery is not None
    ):

        if observed_delivery > required_delivery:

            claims.append(
                _finding(
                    field="delivery_days",
                    observed=observed_delivery,
                    required=required_delivery,
                    status="conflict",
                    severity="high",
                    source_url=source.url,
                    explanation=(
                        "The supplier website states "
                        "a delivery time slower than "
                        "the procurement requirement."
                    ),
                )
            )

            risk_flags.append(
                (
                    "Website delivery claim conflicts "
                    "with the required delivery timeline."
                )
            )

        else:

            claims.append(
                _finding(
                    field="delivery_days",
                    observed=observed_delivery,
                    required=required_delivery,
                    status="compatible",
                    severity="low",
                    source_url=source.url,
                    explanation=(
                        "The website delivery claim "
                        "is within the requested timeline."
                    ),
                )
            )

    observed_payment = claims_data[
        "payment_days"
    ]

    required_payment = (
        reasoning.target_payment_days
    )

    if (
        observed_payment is not None
        and required_payment is not None
    ):

        if observed_payment < required_payment:

            claims.append(
                _finding(
                    field="payment_days",
                    observed=observed_payment,
                    required=required_payment,
                    status="conflict",
                    severity="medium",
                    source_url=source.url,
                    explanation=(
                        "The supplier website offers "
                        "shorter payment terms than the "
                        "requested preference."
                    ),
                )
            )

            risk_flags.append(
                (
                    "Website payment terms are less "
                    "favorable than the requested terms."
                )
            )

        else:

            claims.append(
                _finding(
                    field="payment_days",
                    observed=observed_payment,
                    required=required_payment,
                    status="compatible",
                    severity="low",
                    source_url=source.url,
                    explanation=(
                        "The website payment claim is "
                        "compatible with or better than "
                        "the requested terms."
                    ),
                )
            )

    observed_sla = claims_data[
        "sla_uptime"
    ]

    required_sla = (
        reasoning.target_sla_uptime
    )

    if (
        observed_sla is not None
        and required_sla is not None
    ):

        if observed_sla < required_sla:

            claims.append(
                _finding(
                    field="sla_uptime",
                    observed=observed_sla,
                    required=required_sla,
                    status="conflict",
                    severity="high",
                    source_url=source.url,
                    explanation=(
                        "The supplier website states "
                        "an SLA uptime below the required minimum."
                    ),
                )
            )

            risk_flags.append(
                "Website SLA claim is below the required uptime."
            )

        else:

            claims.append(
                _finding(
                    field="sla_uptime",
                    observed=observed_sla,
                    required=required_sla,
                    status="compatible",
                    severity="low",
                    source_url=source.url,
                    explanation=(
                        "The website SLA claim meets the requested uptime."
                    ),
                )
            )

    detected_values = sum(
        value is not None
        for value in (
            observed_delivery,
            observed_payment,
            observed_sla,
        )
    )

    conflicts = sum(
        claim.status == "conflict"
        for claim in claims
    )

    evidence_score = min(
        1.0,
        0.50
        + (
            0.15
            * detected_values
        )
        - (
            0.20
            * conflicts
        ),
    )

    if (
        conflicts == 0
        and detected_values > 0
    ):

        summary = (
            "Supplier web evidence contains claims "
            "compatible with the current procurement requirements."
        )

    elif conflicts > 0:

        summary = (
            f"Supplier web evidence contains "
            f"{conflicts} claim conflict(s) that should "
            "affect supplier ranking."
        )

    else:

        summary = (
            "The supplier page was readable, but no structured "
            "delivery, payment, or SLA claims could be extracted."
        )

    return SupplierEvidenceAssessment(
        source_status=source.status,
        source_url=source.url,
        claims=claims,
        risk_flags=risk_flags,
        evidence_score=round(
            evidence_score,
            4,
        ),
        summary=summary,
    )