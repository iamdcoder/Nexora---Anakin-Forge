from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from autonomous.discover import (
    SupplierCandidate,
    SupplierScore,
    rank_suppliers,
)

from autonomous.read import _fetch_source

from autonomous.reason import (
    ProcurementReasoning,
)

from autonomous.evidence import (
    assess_supplier_evidence,
)

from models.policy import PartyPolicy


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class WebSupplierCandidate(BaseModel):

    name: str

    source_url: str

    policy: dict[str, Any]

    description: str = ""


class WebSupplierDiscoveryRequest(BaseModel):

    reasoning: ProcurementReasoning

    suppliers: list[WebSupplierCandidate]

    buyer: dict[str, Any]


class WebSupplierDiscoveryResponse(BaseModel):

    discovery_id: str

    selected_supplier: SupplierScore | None

    ranked_suppliers: list[SupplierScore]

    sources_read: list[dict[str, Any]]

    decision: str


def _build_candidate(
    supplier: WebSupplierCandidate,
    reasoning: ProcurementReasoning | None = None,
    buyer: PartyPolicy | None = None,
) -> SupplierCandidate:

    source = _fetch_source(
        supplier.source_url
    )

    evidence: list[str] = []

    if source.status == "read":

        if source.title:

            evidence.append(
                f"Website title: {source.title}"
            )

        if source.text:

            preview = (
                source.text
                .replace(
                    "\n",
                    " ",
                )
                .strip()
            )

            evidence.append(
                "Website content: "
                + preview[:800]
            )

    else:

        evidence.append(
            "Website could not be read: "
            + (
                source.error
                or source.status
            )
        )

    evidence_assessment = None

    if (
        reasoning is not None
        and buyer is not None
    ):

        evidence_assessment = (
            assess_supplier_evidence(
                source=source,
                reasoning=reasoning,
                buyer=buyer,
            )
        )

    return SupplierCandidate(
        name=supplier.name,
        policy=supplier.policy,
        evidence=evidence,
        source_url=supplier.source_url,
        description=supplier.description,
        evidence_assessment=evidence_assessment,
    )


def _read_supplier_sources(
    suppliers: list[WebSupplierCandidate],
    reasoning: ProcurementReasoning,
    buyer: PartyPolicy,
) -> tuple[
    list[SupplierCandidate],
    list[dict[str, Any]],
]:

    candidates: list[SupplierCandidate] = []

    sources: list[dict[str, Any]] = []

    for supplier in suppliers:

        source = _fetch_source(
            supplier.source_url
        )

        source_data = {
            "url": supplier.source_url,
            "status": source.status,
            "title": source.title,
            "content_hash": source.content_hash,
            "error": source.error,
        }

        sources.append(
            source_data
        )

        evidence: list[str] = []

        if source.status == "read":

            if source.title:

                evidence.append(
                    f"Website title: {source.title}"
                )

            if source.text:

                preview = (
                    source.text
                    .replace(
                        "\n",
                        " ",
                    )
                    .strip()
                )

                evidence.append(
                    "Website content: "
                    + preview[:800]
                )

        else:

            evidence.append(
                "Website could not be read: "
                + (
                    source.error
                    or source.status
                )
            )

        assessment = (
            assess_supplier_evidence(
                source=source,
                reasoning=reasoning,
                buyer=buyer,
            )
        )

        candidates.append(
            SupplierCandidate(
                name=supplier.name,
                policy=supplier.policy,
                evidence=evidence,
                source_url=supplier.source_url,
                description=supplier.description,
                evidence_assessment=assessment,
            )
        )

    return candidates, sources


@router.post(
    "/discover-web",
    response_model=WebSupplierDiscoveryResponse,
)
def discover_suppliers_from_web(
    request: WebSupplierDiscoveryRequest,
) -> WebSupplierDiscoveryResponse:

    if not request.suppliers:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one supplier URL is required."
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

        candidates, sources = (
            _read_supplier_sources(
                request.suppliers,
                request.reasoning,
                buyer,
            )
        )

        ranked = rank_suppliers(
            reasoning=request.reasoning,
            suppliers=candidates,
            buyer=buyer,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Web supplier discovery failed."
                ),
                "error": str(exc),
            },
        ) from exc

    selected = (
        ranked[0]
        if ranked
        else None
    )

    return WebSupplierDiscoveryResponse(
        discovery_id=(
            f"WEB-{uuid4().hex[:10].upper()}"
        ),
        selected_supplier=selected,
        ranked_suppliers=ranked,
        sources_read=sources,
        decision=(
            "selected"
            if selected
            else "no_candidate"
        ),
    )