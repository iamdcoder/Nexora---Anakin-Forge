from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from autonomous.evidence import EvidenceFinding, SupplierEvidenceAssessment
from autonomous.reason import ProcurementReasoning
from autonomous.read import SourceRead
from models.policy import PartyPolicy


_NUMERIC_FIELDS = {
    "delivery_days",
    "payment_days",
    "sla_uptime",
}


def reconcile_supplier_sources(
    sources: Iterable[SourceRead],
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> SupplierEvidenceAssessment:
    """Combine supplier evidence across URLs and flag cross-source conflicts."""

    from autonomous.evidence import assess_supplier_evidence

    source_list = list(sources)
    assessments = [
        assess_supplier_evidence(
            source=source,
            reasoning=reasoning,
            buyer=buyer,
        )
        for source in source_list
    ]

    if not assessments:
        return SupplierEvidenceAssessment(
            source_status="unavailable",
            source_provider="unknown",
            source_mode="UNKNOWN",
            evidence_score=0.0,
            risk_flags=["No supplier sources were available for reconciliation."],
            summary="No supplier evidence was available.",
        )

    claims = [claim for assessment in assessments for claim in assessment.claims]
    risk_flags: list[str] = []
    snippets: list[str] = []
    warnings: list[str] = []

    for assessment in assessments:
        risk_flags.extend(assessment.risk_flags)
        snippets.extend(assessment.evidence_snippets)
        warnings.extend(assessment.source_warnings)

    numeric_values: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for assessment in assessments:
        for claim in assessment.claims:
            if claim.field not in _NUMERIC_FIELDS:
                continue
            try:
                raw_values = [float(part.strip()) for part in claim.observed_value.split(",")]
            except ValueError:
                continue
            for value in raw_values:
                if value not in [existing[0] for existing in numeric_values[claim.field]]:
                    numeric_values[claim.field].append((value, claim.source_url or "unknown source"))

    required_map = {
        "delivery_days": reasoning.target_delivery_days,
        "payment_days": reasoning.target_payment_days,
        "sla_uptime": reasoning.target_sla_uptime,
    }

    conflict_count = 0
    for field, values in numeric_values.items():
        if len(values) < 2:
            continue

        just_values = sorted({value for value, _ in values})
        if len(just_values) <= 1:
            continue

        conflict_count += 1
        source_summary = "; ".join(
            f"{value:g} ({url})" for value, url in values
        )
        claims.append(
            EvidenceFinding(
                field=field,
                observed_value=", ".join(f"{value:g}" for value in just_values),
                required_value=str(required_map.get(field, "not specified")),
                status="conflict",
                severity="high" if field != "payment_days" else "medium",
                source_url=None,
                explanation=(
                    "The supplier's separate source pages disagree on this procurement term: "
                    + source_summary
                ),
            )
        )
        label = field.replace("_", " ")
        risk_flags.append(
            f"Supplier sources contain conflicting {label} claims."
        )

    base_score = sum(a.evidence_score for a in assessments) / len(assessments)
    score = max(0.0, min(1.0, base_score - (0.15 * conflict_count)))

    status = "read" if any(a.source_status == "read" for a in assessments) else "unavailable"
    provider = ",".join(sorted({a.source_provider for a in assessments}))
    mode = ",".join(sorted({a.source_mode for a in assessments}))

    return SupplierEvidenceAssessment(
        source_status=status,
        source_url=source_list[0].url if len(source_list) == 1 else None,
        source_provider=provider or "unknown",
        source_mode=mode or "UNKNOWN",
        content_hash=None,
        request_id=None,
        source_duration_ms=sum(
            a.source_duration_ms or 0 for a in assessments
        ) or None,
        source_authenticated=all(
            a.source_authenticated for a in assessments
        ),
        extracted_attributes={
            "source_count": len(source_list),
            "source_urls": [source.url for source in source_list],
        },
        evidence_snippets=list(dict.fromkeys(snippets)),
        source_warnings=list(dict.fromkeys(warnings)),
        claims=claims,
        risk_flags=list(dict.fromkeys(risk_flags)),
        evidence_score=round(score, 4),
        summary=(
            f"Reconciled {len(source_list)} supplier source(s); "
            f"detected {conflict_count} cross-source conflict(s)."
        ),
    )
