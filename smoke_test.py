from __future__ import annotations

import argparse
import sys
from typing import Any

import requests


TIMEOUT_SECONDS = 15


def _get(base_url: str, path: str) -> requests.Response:
    return requests.get(
        f"{base_url.rstrip('/')}{path}",
        timeout=TIMEOUT_SECONDS,
    )


def _print_result(name: str, ok: bool, detail: str = "") -> None:
    marker = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"[{marker}] {name}{suffix}")


def _check_health(base_url: str) -> bool:
    try:
        response = _get(base_url, "/health")
        data = response.json()
    except Exception as exc:
        _print_result("health", False, str(exc))
        return False

    ok = (
        response.status_code == 200
        and data.get("status") == "ok"
        and data.get("service") == "nexora-negotiator"
    )

    _print_result(
        "health",
        ok,
        f"HTTP {response.status_code}",
    )
    return ok


def _check_ready(base_url: str) -> bool:
    try:
        response = _get(base_url, "/ready")
        data = response.json()
    except Exception as exc:
        _print_result("ready", False, str(exc))
        return False

    if response.status_code == 200:
        ok = (
            data.get("status") == "ready"
            and data.get("ready") is True
        )

        _print_result(
            "ready",
            ok,
            "all configured dependencies ready",
        )
        return ok

    if response.status_code == 503:
        detail: dict[str, Any] = data.get("detail", {})
        checks = detail.get("checks", {})
        failed = [
            name
            for name, value in checks.items()
            if not value
        ]
        _print_result(
            "ready",
            False,
            "not ready: " + ", ".join(failed),
        )
        return False

    _print_result(
        "ready",
        False,
        f"unexpected HTTP {response.status_code}",
    )
    return False


def _check_frontend(base_url: str) -> bool:
    try:
        response = _get(base_url, "/")
    except Exception as exc:
        _print_result("frontend", False, str(exc))
        return False

    ok = (
        response.status_code == 200
        and "Nexora" in response.text
    )

    _print_result(
        "frontend",
        ok,
        f"HTTP {response.status_code}",
    )
    return ok


def _check_procurement_route(base_url: str) -> bool:
    try:
        response = requests.options(
            f"{base_url.rstrip('/')}/api/autonomous/procure",
            timeout=TIMEOUT_SECONDS,
        )
    except Exception as exc:
        _print_result(
            "procurement route",
            False,
            str(exc),
        )
        return False

    ok = response.status_code in {
        200,
        204,
        405,
    }

    _print_result(
        "procurement route",
        ok,
        f"HTTP {response.status_code}",
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nexora deployment smoke test"
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default="http://127.0.0.1:8000",
        help="Nexora base URL",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print(f"Nexora smoke test: {base_url}")
    print("-" * 48)

    results = [
        _check_health(base_url),
        _check_ready(base_url),
        _check_frontend(base_url),
        _check_procurement_route(base_url),
    ]

    print("-" * 48)

    if all(results):
        print("SMOKE TEST PASSED")
        return 0

    print("SMOKE TEST FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
