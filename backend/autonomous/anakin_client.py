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


def _retryable_status(status_code: int) -> bool:
    return status_code in {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }


def _retry_delay(
    attempt: int,
    base_delay: float,
) -> float:
    return min(
        2.0,
        max(
            0.0,
            base_delay
            * (2 ** attempt),
        ),
    )


def scrape_url(
    url: str,
    *,
    use_browser: bool = False,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Read a public webpage through Anakin's hosted URL scraper.

    The request is bounded, validates its URL before network access, and
    retries only transient transport/server failures. Authentication is
    optional and does not change the application contract.
    """

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AnakinScrapeError(
            "Only absolute http:// and https:// URLs are allowed."
        )

    request_timeout = timeout or float(
        os.getenv("ANAKIN_TIMEOUT", "20")
    )

    max_retries = int(
        os.getenv("ANAKIN_MAX_RETRIES", "2")
    )

    max_retries = max(
        0,
        min(
            max_retries,
            4,
        ),
    )

    retry_base_delay = float(
        os.getenv("ANAKIN_RETRY_BASE_DELAY", "0.25")
    )

    endpoint = (
        f"{ANAKIN_BASE_URL}{ANAKIN_SCRAPE_PATH}"
    )

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Nexora-Anakin-Forge/1.0",
    }

    api_key = os.getenv(
        "ANAKIN_API_KEY",
        "",
    ).strip()

    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "url": url,
        "useBrowser": bool(use_browser),
    }

    started = time.perf_counter()
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=request_timeout,
            )

        except requests.Timeout as exc:
            last_error = (
                f"Anakin request timed out: {exc}"
            )

            if attempt >= max_retries:
                raise AnakinScrapeError(
                    last_error
                ) from exc

            time.sleep(
                _retry_delay(
                    attempt,
                    retry_base_delay,
                )
            )
            continue

        except requests.RequestException as exc:
            last_error = (
                f"Anakin request failed: {exc}"
            )

            if attempt >= max_retries:
                raise AnakinScrapeError(
                    last_error
                ) from exc

            time.sleep(
                _retry_delay(
                    attempt,
                    retry_base_delay,
                )
            )
            continue

        if response.ok:
            break

        detail = response.text[:500]
        last_error = (
            f"Anakin returned HTTP "
            f"{response.status_code}: {detail}"
        )

        if (
            not _retryable_status(
                response.status_code
            )
            or attempt >= max_retries
        ):
            raise AnakinScrapeError(
                last_error
            )

        time.sleep(
            _retry_delay(
                attempt,
                retry_base_delay,
            )
        )

    else:
        raise AnakinScrapeError(
            last_error
            or "Anakin request failed after bounded retries."
        )

    elapsed_ms = int(
        (time.perf_counter() - started) * 1000
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise AnakinScrapeError(
            "Anakin returned a non-JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise AnakinScrapeError(
            "Anakin returned an unexpected response shape."
        )

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
        "status": (
            "read"
            if markdown.strip()
            else "empty"
        ),
        "title": _title_from_markdown(
            markdown
        ),
        "text": markdown[:25_000],
        "request_id": (
            data.get("requestId")
            or data.get("id")
            or data.get("jobId")
        ),
        "credits_remaining": remaining,
        "duration_ms": (
            data.get("durationMs")
            or elapsed_ms
        ),
        "authenticated": bool(api_key),
        "attempts": attempt + 1,
        "raw": data,
    }
