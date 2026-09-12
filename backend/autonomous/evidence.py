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
    source_provider: str = "unknown"
    source_mode: str = "UNKNOWN"
    content_hash: str | None = None
    request_id: str | None = None
    source_duration_ms: int | None = None
    source_authenticated: bool = False
    extracted_attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_snippets: list[str] = Field(default_factory=list)
    source_warnings: list[str] = Field(default_factory=list)
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


def _first_match(
    patterns: list[str],
    text: str,
) -> str | None:
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            value = match.group(1).strip()

            if value:
                return value

    return None


def _product_matches(
    observed: str,
    required: str,
) -> bool:
    observed_tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            observed.lower(),
        )
        if len(token) >= 3
    }

    required_tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            required.lower(),
        )
        if len(token) >= 3
    }

    if not observed_tokens or not required_tokens:
        return True

    overlap = observed_tokens & required_tokens

    return (
        len(overlap) / len(required_tokens)
    ) >= 0.50


def _availability_status(
    value: str,
) -> tuple[str, str, str]:
    normalized = value.casefold()

    negative_markers = (
        "out of stock",
        "unavailable",
        "backordered",
        "back-ordered",
        "not available",
        "currently unavailable",
    )

    positive_markers = (
        "in stock",
        "available",
        "ready to ship",
        "ready for shipment",
    )

    if any(
        marker in normalized
        for marker in negative_markers
    ):
        return (
            "conflict",
            "high",
            "The supplier source indicates that the item is not immediately available.",
        )

    if any(
        marker in normalized
        for marker in positive_markers
    ):
        return (
            "compatible",
            "low",
            "The supplier source indicates that the item is available for procurement.",
        )

    return (
        "observed",
        "low",
        "The supplier source mentions availability but does not clearly establish immediate stock status.",
    )


def _all_numbers(
    patterns: list[str],
    text: str,
    cast: Any = float,
) -> list[Any]:
    values: list[Any] = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            try:
                values.append(
                    cast(
                        match.group(1)
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

    return list(
        dict.fromkeys(
            values
        )
    )


def extract_supplier_claims(
    source: SourceRead,
) -> dict[str, Any]:
    normalized_claims = dict(
        source.claims or {}
    )

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
                r"\D{0,20}"
                r"(\d+)\s*(?:business\s*)?days?"
            ),
            (
                r"(\d+)\s*day(?:s)?\s+"
                r"(?:credit|payment)\s*terms?"
            ),
            (
                r"(?:net|payment\s*terms?)"
                r"\s*(\d+)"
                r"\b"
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

    warranty_months = normalized_claims.get(
        "warranty_months"
    )

    if warranty_months is None:
        warranty_months = _first_number(
            [
                (
                    r"(?:warranty|guarantee)"
                    r"\D{0,30}"
                    r"(\d+)\s*months?"
                ),
                (
                    r"(\d+)\s*months?"
                    r"\s*(?:warranty|guarantee)"
                ),
                (
                    r"(?:warranty|guarantee)"
                    r"\D{0,30}"
                    r"(\d+)\s*years?"
                ),
                (
                    r"(\d+)\s*years?"
                    r"\s*(?:warranty|guarantee)"
                ),
            ],
            text,
            int,
        )

        years_match = re.search(
            r"(?:warranty|guarantee)\D{0,30}(\d+)\s*years?"
            r"|"
            r"(\d+)\s*years?\s*(?:warranty|guarantee)",
            text,
            flags=re.IGNORECASE,
        )

        if (
            warranty_months is not None
            and years_match
        ):
            warranty_months *= 12

    availability = normalized_claims.get(
        "availability"
    )

    if availability is None:
        availability = _first_match(
            [
                r"((?:currently\s+)?in\s+stock)",
                r"((?:currently\s+)?out\s+of\s+stock)",
                r"(back[- ]?ordered)",
                r"((?:currently\s+)?unavailable)",
                (
                    r"((?:currently\s+)?available"
                    r"(?:\s+for\s+"
                    r"(?:purchase|procurement|shipment))?)"
                ),
                r"(ready\s+to\s+ship)",
            ],
            text,
        )

    certification = normalized_claims.get(
        "certification"
    )

    if certification is None:
        certification = _first_match(
            [
                r"\b(ISO\s*\d{4,5}(?:\s*[-/]?\s*\d{4})?)\b",
                r"\b(BIS(?:\s+certified)?)\b",
                r"\b(CE(?:\s+certified)?)\b",
                r"\b(RoHS(?:\s+compliant)?)\b",
                r"\b(IEC\s*\d{3,5}(?:[-/]\d+)?)\b",
                r"\b(SOC\s*[12])\b",
                r"\b([A-Z]{2,8}\s+certified)\b",
            ],
            text,
        )

    product = normalized_claims.get(
        "product"
    )

    if product is None:
        product = _first_match(
            [
                (
                    r"(?:product|item|model|"
                    r"part(?:\s*number)?)"
                    r"\s*(?:name|number)?\s*[:\-]\s*"
                    r"([^.;\n]{2,120})"
                ),
                (
                    r"(?:we\s+(?:supply|offer)|"
                    r"product\s+is)\s+"
                    r"([^.;\n]{2,120})"
                ),
            ],
            text,
        )

    delivery_values = _all_numbers(
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

    payment_values = _all_numbers(
        [
            (
                r"(?:net|payment\s*terms?|credit)"
                r"\D{0,20}"
                r"(\d+)\s*(?:business\s*)?days?"
            ),
            (
                r"(\d+)\s*day(?:s)?\s+"
                r"(?:credit|payment)\s*terms?"
            ),
            (
                r"(?:net|payment\s*terms?)"
                r"\s*(\d+)\b"
            ),
        ],
        text,
        int,
    )

    sla_values = _all_numbers(
        [
            (
                r"(?:uptime|availability|service\s*level)"
                r"\D{0,30}"
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

    extracted = {
        "delivery_values": delivery_values,
        "payment_values": payment_values,
        "sla_values": sla_values,
        "delivery_conflict": (
            len(delivery_values) > 1
        ),
        "payment_conflict": (
            len(payment_values) > 1
        ),
        "sla_conflict": (
            len(sla_values) > 1
        ),
        "delivery_days": (
            normalized_claims.get(
                "delivery_days"
            )
            if normalized_claims.get(
                "delivery_days"
            ) is not None
            else delivery_days
        ),
        "payment_days": (
            normalized_claims.get(
                "payment_days"
            )
            if normalized_claims.get(
                "payment_days"
            ) is not None
            else payment_days
        ),
        "sla_uptime": (
            normalized_claims.get(
                "sla_uptime"
            )
            if normalized_claims.get(
                "sla_uptime"
            ) is not None
            else sla_uptime
        ),
        "warranty_months": warranty_months,
        "availability": availability,
        "certification": certification,
        "product": product,
    }

    for key, value in normalized_claims.items():
        extracted.setdefault(
            key,
            value,
        )

    return extracted


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
            source_provider=source.provider,
            source_mode=source.source_mode,
            content_hash=source.content_hash,
            request_id=source.request_id,
            source_duration_ms=source.duration_ms,
            source_authenticated=source.authenticated,
            extracted_attributes=dict(
                source.claims or {}
            ),
            evidence_snippets=list(
                source.evidence_snippets
            ),
            source_warnings=list(
                source.warnings
            ),
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

    if claims_data.get(
        "delivery_conflict"
    ):
        values = claims_data.get(
            "delivery_values",
            [],
        )

        claims.append(
            _finding(
                field="delivery_days",
                observed=", ".join(
                    map(
                        str,
                        values,
                    )
                ),
                required=(
                    reasoning.target_delivery_days
                ),
                status="conflict",
                severity="high",
                source_url=source.url,
                explanation=(
                    "The supplier source contains multiple "
                    "conflicting delivery claims and cannot "
                    "be treated as internally consistent."
                ),
            )
        )

        risk_flags.append(
            "Supplier source contains conflicting delivery claims."
        )

    if claims_data.get(
        "payment_conflict"
    ):
        values = claims_data.get(
            "payment_values",
            [],
        )

        claims.append(
            _finding(
                field="payment_days",
                observed=", ".join(
                    map(
                        str,
                        values,
                    )
                ),
                required=(
                    reasoning.target_payment_days
                ),
                status="conflict",
                severity="medium",
                source_url=source.url,
                explanation=(
                    "The supplier source contains multiple "
                    "conflicting payment-term claims."
                ),
            )
        )

        risk_flags.append(
            "Supplier source contains conflicting payment claims."
        )

    if claims_data.get(
        "sla_conflict"
    ):
        values = claims_data.get(
            "sla_values",
            [],
        )

        claims.append(
            _finding(
                field="sla_uptime",
                observed=", ".join(
                    map(
                        str,
                        values,
                    )
                ),
                required=(
                    reasoning.target_sla_uptime
                ),
                status="conflict",
                severity="high",
                source_url=source.url,
                explanation=(
                    "The supplier source contains multiple "
                    "conflicting SLA/uptime claims."
                ),
            )
        )

        risk_flags.append(
            "Supplier source contains conflicting SLA claims."
        )

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

    observed_product = claims_data[
        "product"
    ]

    required_product = (
        reasoning.product_name
    )

    if observed_product:

        if (
            required_product
            and not _product_matches(
                observed_product,
                required_product,
            )
        ):

            claims.append(
                _finding(
                    field="product",
                    observed=observed_product,
                    required=required_product,
                    status="conflict",
                    severity="high",
                    source_url=source.url,
                    explanation=(
                        "The supplier source appears to describe "
                        "a different product or model from the "
                        "procurement request."
                    ),
                )
            )

            risk_flags.append(
                "Supplier product evidence does not clearly match the requested product."
            )

        else:

            claims.append(
                _finding(
                    field="product",
                    observed=observed_product,
                    required=(
                        required_product
                        or "requested product"
                    ),
                    status="compatible",
                    severity="low",
                    source_url=source.url,
                    explanation=(
                        "The supplier source contains product "
                        "information consistent with the procurement request."
                    ),
                )
            )

    observed_warranty = claims_data[
        "warranty_months"
    ]

    if observed_warranty is not None:

        claims.append(
            _finding(
                field="warranty_months",
                observed=observed_warranty,
                required="not specified",
                status="observed",
                severity="low",
                source_url=source.url,
                explanation=(
                    "The supplier source reports a warranty "
                    "duration that can be carried into procurement review."
                ),
            )
        )

    observed_availability = claims_data[
        "availability"
    ]

    if observed_availability:

        (
            availability_status,
            availability_severity,
            availability_explanation,
        ) = _availability_status(
            observed_availability
        )

        claims.append(
            _finding(
                field="availability",
                observed=observed_availability,
                required="available for procurement",
                status=availability_status,
                severity=availability_severity,
                source_url=source.url,
                explanation=availability_explanation,
            )
        )

        if (
            availability_status
            == "conflict"
        ):
            risk_flags.append(
                "Supplier availability evidence indicates stock or fulfillment risk."
            )

    observed_certification = claims_data[
        "certification"
    ]

    if observed_certification:

        claims.append(
            _finding(
                field="certification",
                observed=observed_certification,
                required="not specified",
                status="observed",
                severity="low",
                source_url=source.url,
                explanation=(
                    "The supplier source reports a certification or "
                    "compliance attribute that can be used during procurement review."
                ),
            )
        )

    detected_values = sum(
        value is not None
        for value in (
            observed_delivery,
            observed_payment,
            observed_sla,
            observed_product,
            observed_warranty,
            observed_availability,
            observed_certification,
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
            * min(
                detected_values,
                3,
            )
        )
        + (
            0.05
            * max(
                0,
                min(
                    detected_values - 3,
                    4,
                ),
            )
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
            "Supplier web evidence contains structured procurement "
            "attributes compatible with the current requirements."
        )

    elif conflicts > 0:

        summary = (
            f"Supplier web evidence contains {conflicts} claim conflict(s) "
            "that should affect supplier ranking."
        )

    else:

        summary = (
            "The supplier page was readable, but no structured procurement "
            "claims could be extracted."
        )

    return SupplierEvidenceAssessment(
        source_status=source.status,
        source_url=source.url,
        source_provider=source.provider,
        source_mode=source.source_mode,
        content_hash=source.content_hash,
        request_id=source.request_id,
        source_duration_ms=source.duration_ms,
        source_authenticated=source.authenticated,
        extracted_attributes=claims_data,
        evidence_snippets=list(
            source.evidence_snippets
        ),
        source_warnings=list(
            source.warnings
        ),
        claims=claims,
        risk_flags=list(
            dict.fromkeys(
                risk_flags
            )
        ),
        evidence_score=round(
            evidence_score,
            4,
        ),
        summary=summary,
    )