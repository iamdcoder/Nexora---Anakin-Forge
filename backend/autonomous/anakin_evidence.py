from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class AnakinEvidence(BaseModel):
    """
    Normalized evidence produced from an Anakin web read.

    This object deliberately keeps provenance separate from
    interpreted procurement claims.
    """

    source_mode: str = "LIVE"

    source_url: str

    title: str | None = None

    content_hash: str | None = None

    request_id: str | None = None

    duration_ms: int | None = None

    authenticated: bool = False

    credits_remaining: int | float | None = None

    text: str = ""

    claims: dict[str, Any] = Field(
        default_factory=dict
    )

    evidence_snippets: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )


def _first_match(
    patterns: list[str],
    text: str,
    cast: type | None = None,
):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        value = match.group(1).strip()

        if cast is None:
            return value

        try:
            return cast(value)
        except (
            TypeError,
            ValueError,
        ):
            continue

    return None


def _extract_warranty_months(
    text: str,
) -> int | None:
    months = _first_match(
        [
            r"(?:warranty|guarantee)"
            r"\D{0,30}"
            r"(\d+)\s*months?",
            r"(\d+)\s*months?"
            r"\s*(?:warranty|guarantee)",
        ],
        text,
        int,
    )

    if months is not None:
        return months

    years = _first_match(
        [
            r"(?:warranty|guarantee)"
            r"\D{0,30}"
            r"(\d+)\s*years?",
            r"(\d+)\s*years?"
            r"\s*(?:warranty|guarantee)",
        ],
        text,
        int,
    )

    if years is not None:
        return years * 12

    return None


def _collect_snippets(
    text: str,
    keywords: tuple[str, ...],
    limit: int = 8,
) -> list[str]:
    snippets: list[str] = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()

        if not line:
            continue

        lower = line.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):
            snippets.append(line[:500])

        if len(snippets) >= limit:
            break

    return snippets


def extract_claims(
    text: str,
) -> dict[str, Any]:
    normalized = " ".join(
        text.split()
    )

    claims = {
        "delivery_days": _first_match(
            [
                r"(?:delivery|lead\s*time)"
                r"\D{0,30}"
                r"(\d+)"
                r"\s*(?:business\s*)?days?",
                r"(?:within|under|in)"
                r"\s+(\d+)"
                r"\s*days?"
                r"\s+(?:delivery|shipping)",
            ],
            normalized,
            int,
        ),
        "payment_days": _first_match(
            [
                r"(?:net|payment\s*terms?|credit)"
                r"\D{0,20}"
                r"(\d+)\s*(?:business\s*)?days?",
                r"(?:net|payment\s*terms?)"
                r"\s*(\d+)\b",
                r"(\d+)"
                r"\s*day(?:s)?"
                r"\s+(?:credit|payment)"
                r"\s*terms?",
            ],
            normalized,
            int,
        ),
        "sla_uptime": _first_match(
            [
                r"(?:uptime|availability|service\s*level)"
                r"\D{0,30}"
                r"(\d+(?:\.\d+)?)"
                r"\s*%",
                r"(\d+(?:\.\d+)?)"
                r"\s*%"
                r"\s+(?:uptime|availability)",
            ],
            normalized,
            float,
        ),
        "warranty_months": _extract_warranty_months(
            normalized
        ),
        "availability": _first_match(
            [
                r"((?:currently\s+)?in\s+stock)",
                r"((?:currently\s+)?out\s+of\s+stock)",
                r"(back[- ]?ordered)",
                r"((?:currently\s+)?unavailable)",
                r"((?:currently\s+)?available(?:\s+for\s+(?:purchase|procurement|shipment))?)",
                r"(ready\s+to\s+ship)",
            ],
            normalized,
        ),
        "certification": _first_match(
            [
                r"\b(ISO\s*\d{4,5}(?:\s*[-/]?\s*\d{4})?)\b",
                r"\b(BIS(?:\s+certified)?)\b",
                r"\b(CE(?:\s+certified)?)\b",
                r"\b(RoHS(?:\s+compliant)?)\b",
                r"\b(IEC\s*\d{3,5}(?:[-/]\d+)?)\b",
                r"\b(SOC\s*[12])\b",
                r"\b([A-Z]{2,8}\s+certified)\b",
            ],
            normalized,
        ),
        "product": _first_match(
            [
                r"(?:product|item|model|part(?:\s*number)?)"
                r"\s*(?:name|number)?\s*[:\-]\s*"
                r"([^.;\n]{2,120})",
                r"(?:we\s+(?:supply|offer)|product\s+is)\s+"
                r"([^.;\n]{2,120})",
            ],
            normalized,
        ),
    }

    return claims


def normalize_anakin_result(
    result: dict[str, Any],
) -> AnakinEvidence:
    text = str(
        result.get("text")
        or ""
    ).strip()

    claims = extract_claims(text)

    snippets = _collect_snippets(
        text,
        (
            "delivery",
            "lead time",
            "payment",
            "warranty",
            "uptime",
            "availability",
            "stock",
            "sla",
            "certification",
            "certified",
            "compliance",
            "product",
            "model",
        ),
    )

    warnings: list[str] = []

    if not text:
        warnings.append(
            "Anakin returned no readable text."
        )

    detected = sum(
        value is not None
        for value in claims.values()
    )

    if detected == 0:
        warnings.append(
            "No structured procurement claims "
            "could be extracted from the page."
        )

    return AnakinEvidence(
        source_mode="LIVE",
        source_url=str(
            result.get("url")
            or ""
        ),
        title=result.get("title"),
        content_hash=result.get(
            "content_hash"
        ),
        request_id=result.get(
            "request_id"
        ),
        duration_ms=result.get(
            "duration_ms"
        ),
        authenticated=bool(
            result.get("authenticated")
        ),
        credits_remaining=result.get(
            "credits_remaining"
        ),
        text=text[:25_000],
        claims=claims,
        evidence_snippets=snippets,
        warnings=warnings,
    )