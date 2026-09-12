from __future__ import annotations

import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests


ANAKIN_BASE_URL = os.getenv("ANAKIN_BASE_URL", "https://api.anakin.io/v1").rstrip("/")
ANAKIN_SCRAPE_PATH = "/url-scraper/scrape"


class AnakinScrapeError(RuntimeError):
    """Raised when the Anakin web-read operation cannot complete."""


def _title_from_markdown(markdown: str) -> str | None:
    for line in markdown.splitlines():
        value = line.strip()
        if not value:
            continue
        value = re.sub(r"^#+\s*", "", value).strip()
        if value:
            return value[:240]
    return None


def scrape_url(
    url: str,
    *,
    use_browser: bool = False,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Read a public webpage through Anakin's hosted URL scraper.

    The no-key endpoint is intentionally supported for the hackathon's
    read-only supplier evidence path. Providing ANAKIN_API_KEY upgrades the
    same call to an authenticated request without changing application code.
    """

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AnakinScrapeError("Only absolute http:// and https:// URLs are allowed.")

    request_timeout = timeout or float(os.getenv("ANAKIN_TIMEOUT", "20"))
    endpoint = f"{ANAKIN_BASE_URL}{ANAKIN_SCRAPE_PATH}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Nexora-Anakin-Forge/1.0",
    }
    api_key = os.getenv("ANAKIN_API_KEY", "").strip()
    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "url": url,
        "useBrowser": bool(use_browser),
    }

    started = time.perf_counter()
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=request_timeout,
        )
    except requests.RequestException as exc:
        raise AnakinScrapeError(f"Anakin request failed: {exc}") from exc

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if not response.ok:
        detail = response.text[:500]
        raise AnakinScrapeError(
            f"Anakin returned HTTP {response.status_code}: {detail}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise AnakinScrapeError("Anakin returned a non-JSON response.") from exc

    if not isinstance(data, dict):
        raise AnakinScrapeError("Anakin returned an unexpected response shape.")

    markdown = (
        data.get("markdown")
        or data.get("content")
        or data.get("text")
        or ""
    )
    if not isinstance(markdown, str):
        markdown = str(markdown)

    trial = data.get("trial")
    remaining = None
    if isinstance(trial, dict):
        remaining = (
            trial.get("remaining_credits")
            or trial.get("credits_remaining")
            or trial.get("remaining")
        )

    return {
        "url": url,
        "status": "read" if markdown.strip() else "empty",
        "title": _title_from_markdown(markdown),
        "text": markdown[:25_000],
        "request_id": data.get("requestId") or data.get("id") or data.get("jobId"),
        "credits_remaining": remaining,
        "duration_ms": data.get("durationMs") or elapsed_ms,
        "authenticated": bool(api_key),
        "raw": data,
    }
