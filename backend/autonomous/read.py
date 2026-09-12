from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class ReadRequest(BaseModel):
    text: str = Field(
        default="",
        max_length=100_000,
    )

    sources: list[str] = Field(
        default_factory=list,
        max_length=5,
    )


class SourceRead(BaseModel):
    url: str
    status: str
    title: str | None = None
    text: str = ""
    error: str | None = None
    content_hash: str | None = None
    provider: str = "direct_http"
    request_id: str | None = None
    duration_ms: int | None = None
    credits_remaining: int | float | None = None
    authenticated: bool = False


class ProcurementRead(BaseModel):
    intake_id: str

    source_type: str

    product_name: str | None = None

    quantity: int | None = None

    delivery_days: int | None = None

    payment_days: int | None = None

    sla_uptime: float | None = None

    sla_penalty: float | None = None

    currency: str | None = None

    requirements: list[str] = Field(
        default_factory=list
    )

    source_urls: list[str] = Field(
        default_factory=list
    )

    raw_text: str


class ReadResponse(BaseModel):
    intake: ProcurementRead
    sources: list[SourceRead]


class _HTMLTextParser(HTMLParser):

    _IGNORED = {
        "script",
        "style",
        "noscript",
        "svg",
        "head",
    }

    def __init__(self) -> None:

        super().__init__()

        self._ignore_depth = 0

        self.title = ""

        self._in_title = False

        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        tag = tag.lower()

        if tag == "title":

            self._in_title = True

            return

        if tag in self._IGNORED:

            self._ignore_depth += 1

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if tag == "title":

            self._in_title = False

            return

        if (
            tag in self._IGNORED
            and self._ignore_depth
        ):

            self._ignore_depth -= 1

    def handle_data(
        self,
        data: str,
    ) -> None:

        value = " ".join(
            data.split()
        )

        if not value:

            return

        if self._in_title:

            self.title = (
                f"{self.title} {value}"
            ).strip()

            return

        if self._ignore_depth:

            return

        self.parts.append(value)


def _clean_text(
    value: str,
) -> str:

    value = re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()

    return value[:100_000]


def _extract_number(
    patterns: list[str],
    text: str,
    cast: Any = int,
) -> Any:

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

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


def _extract_product(
    text: str,
) -> str | None:

    patterns = [

        r"(?:product|item|material|service)"
        r"\s*(?:name)?\s*[:\-]\s*"
        r"([^\n.;]{2,120})",

        r"(?:we need|looking for|require|"
        r"requirement is)\s+"
        r"([^\n.;]{2,120})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            value = _clean_text(
                match.group(1)
            )

            if value:

                return value

    return None


def _extract_currency(
    text: str,
) -> str | None:

    if (
        "₹" in text
        or re.search(
            r"\bINR\b|\brupees?\b",
            text,
            re.I,
        )
    ):

        return "INR"

    if (
        "$" in text
        or re.search(
            r"\bUSD\b|\bdollars?\b",
            text,
            re.I,
        )
    ):

        return "USD"

    if (
        "€" in text
        or re.search(
            r"\bEUR\b|\beuros?\b",
            text,
            re.I,
        )
    ):

        return "EUR"

    if (
        "£" in text
        or re.search(
            r"\bGBP\b|\bpounds?\b",
            text,
            re.I,
        )
    ):

        return "GBP"

    return None


def _extract_requirements(
    text: str,
) -> list[str]:

    requirements: list[str] = []

    for line in re.split(
        r"[\n•\r]+",
        text,
    ):

        line = _clean_text(
            line
        ).strip("-*")

        lower = line.lower()

        if not line:

            continue

        if any(
            key in lower
            for key in (
                "must",
                "require",
                "specification",
                "spec:",
                "quality",
                "compliance",
            )
        ):

            requirements.append(
                line[:300]
            )

        if len(requirements) >= 20:

            break

    return requirements


def _host_is_blocked(
    host: str,
) -> bool:

    host = (
        host
        or ""
    ).strip().lower().rstrip(".")

    if host in {
        "localhost",
        "localhost.localdomain",
    }:

        return True

    try:

        address = ipaddress.ip_address(
            host
        )

    except ValueError:

        try:

            resolved = socket.gethostbyname(
                host
            )

            address = ipaddress.ip_address(
                resolved
            )

        except OSError:

            return False

    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


def _validate_url(
    url: str,
) -> str:

    parsed = urlparse(url)

    if (
        parsed.scheme not in {
            "http",
            "https",
        }
        or not parsed.netloc
    ):

        raise ValueError(
            "Only absolute http:// and https:// URLs are allowed."
        )

    if _host_is_blocked(
        parsed.hostname or ""
    ):

        raise ValueError(
            "Private or local network URLs are not allowed."
        )

    return url


def _fetch_direct_source(
    safe_url: str,
) -> SourceRead:

    try:

        request = Request(
            safe_url,
            headers={
                "User-Agent":
                    "Nexora-Forge/1.0"
            },
            method="GET",
        )

        with urlopen(
            request,
            timeout=8,
        ) as response:

            raw = response.read(
                200_000
            )

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

        decoded = raw.decode(
            "utf-8",
            errors="ignore",
        )

        if (
            "html"
            in content_type.lower()
            or "<html"
            in decoded[:2000].lower()
        ):

            parser = _HTMLTextParser()
            parser.feed(decoded)
            text = _clean_text(" ".join(parser.parts))
            title = _clean_text(parser.title) or None
        else:
            text = _clean_text(decoded)
            title = None

        digest = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        return SourceRead(
            url=safe_url,
            status="read",
            title=title,
            text=text[:25_000],
            content_hash=digest,
            provider="direct_http",
        )

    except Exception as exc:

        return SourceRead(
            url=safe_url,
            status="error",
            error=str(exc)[:300],
            provider="direct_http",
        )


def _fetch_source(
    url: str,
) -> SourceRead:

    try:
        safe_url = _validate_url(url)
    except ValueError as exc:
        return SourceRead(
            url=url,
            status="rejected",
            error=str(exc),
            provider="validation",
        )

    use_anakin = (
        os.getenv("ANAKIN_ENABLED", "1").strip() == "1"
    )
    if use_anakin:
        try:
            from autonomous.anakin_client import scrape_url

            result = scrape_url(
                safe_url,
                use_browser=(
                    os.getenv("ANAKIN_USE_BROWSER", "0").strip() == "1"
                ),
            )
            text = _clean_text(result.get("text") or "")
            digest = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()
            return SourceRead(
                url=safe_url,
                status="read" if text else "error",
                title=result.get("title"),
                text=text[:25_000],
                error=None if text else "Anakin returned no readable content.",
                content_hash=digest if text else None,
                provider="anakin",
                request_id=result.get("request_id"),
                duration_ms=result.get("duration_ms"),
                credits_remaining=result.get("credits_remaining"),
                authenticated=bool(result.get("authenticated")),
            )
        except Exception as exc:
            if os.getenv("ANAKIN_FALLBACK_DIRECT", "1").strip() == "1":
                fallback = _fetch_direct_source(safe_url)
                if fallback.status == "read":
                    fallback.error = (
                        "Anakin unavailable; direct HTTP fallback used. "
                        + str(exc)[:200]
                    )
                    return fallback
            return SourceRead(
                url=safe_url,
                status="error",
                error=str(exc)[:300],
                provider="anakin",
            )

    return _fetch_direct_source(safe_url)


def _build_intake(
    text: str,
    sources: list[SourceRead],
) -> ProcurementRead:

    source_texts = [
        item.text
        for item in sources
        if item.status == "read"
        and item.text
    ]

    combined = _clean_text(
        "\n".join(
            [
                text,
                *source_texts,
            ]
        )
    )

    source_type = (
        "web"
        if source_texts and not text
        else "mixed"
        if source_texts
        else "manual"
    )

    return ProcurementRead(

        intake_id=(
            f"INT-{uuid4().hex[:10].upper()}"
        ),

        source_type=source_type,

        product_name=_extract_product(
            combined
        ),

        quantity=_extract_number(
            [
                r"(?:quantity|qty|units?)"
                r"\s*[:\-]?\s*"
                r"([0-9][0-9,]*)",

                r"([0-9][0-9,]*)\s+"
                r"(?:units?|pieces?|pcs)",
            ],
            combined,
            lambda value: int(
                value.replace(",", "")
            ),
        ),

        delivery_days=_extract_number(
            [
                r"(?:delivery|lead\s*time|"
                r"ship(?:ping)?\s+time)"
                r"\s*(?:target|within|by|of)?"
                r"\s*[:\-]?\s*"
                r"([0-9]+)"
                r"\s*(?:days?|business\s+days?)",
            ],
            combined,
        ),

        payment_days=_extract_number(
            [
                r"(?:payment|terms?)"
                r"\s*(?:terms)?"
                r"\s*[:\-]?\s*"
                r"(?:net\s*)?([0-9]+)",

                r"net\s*([0-9]+)",
            ],
            combined,
        ),

        sla_uptime=_extract_number(
            [
                r"(?:uptime|availability)"
                r"\s*(?:SLA)?"
                r"\s*[:\-]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*%",
            ],
            combined,
            float,
        ),

        sla_penalty=_extract_number(
            [
                r"(?:SLA\s+)?penalty"
                r"\s*[:\-]?\s*"
                r"([0-9]+(?:\.[0-9]+)?)"
                r"\s*%",
            ],
            combined,
            float,
        ),

        currency=_extract_currency(
            combined
        ),

        requirements=_extract_requirements(
            combined
        ),

        source_urls=[
            item.url
            for item in sources
            if item.status == "read"
        ],

        raw_text=combined[
            :100_000
        ],
    )


@router.post(
    "/read",
    response_model=ReadResponse,
)
def read_procurement_input(
    request: ReadRequest,
) -> ReadResponse:

    if (
        not request.text.strip()
        and not request.sources
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Provide procurement text, "
                "at least one source URL, "
                "or both."
            ),
        )

    unique_sources = list(
        dict.fromkeys(
            url.strip()
            for url in request.sources
            if url.strip()
        )
    )

    sources = [
        _fetch_source(url)
        for url in unique_sources
    ]

    if (
        unique_sources
        and not any(
            source.status == "read"
            for source in sources
        )
        and not request.text.strip()
    ):

        raise HTTPException(
            status_code=422,
            detail=(
                "None of the supplied web "
                "sources could be read."
            ),
        )

    intake = _build_intake(
        request.text,
        sources,
    )

    return ReadResponse(
        intake=intake,
        sources=sources,
    )