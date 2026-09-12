from __future__ import annotations

from typing import Any, Literal

FailureCode = Literal[
    "ANAKIN_ERROR",
    "LYZR_ERROR",
    "POLICY_BLOCK",
    "VERIFY_FAIL",
    "TIMEOUT",
    "ACT_ERROR",
    "DEMO_FAULT",
    "READ_ERROR",
    "REASON_ERROR",
    "SELECTION_ERROR",
    "RECOVERY_ERROR",
    "UNKNOWN_ERROR",
]


def _flatten_error(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(
            _flatten_error(item)
            for item in value.values()
        )

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            _flatten_error(item)
            for item in value
        )

    return str(value or "")


def classify_failure(
    *,
    stage: str,
    error: Any = None,
    violations: list[str] | None = None,
) -> FailureCode:
    text = (
        _flatten_error(error)
        + " "
        + _flatten_error(violations or [])
    ).casefold()

    if (
        "timeout" in text
        or "timed out" in text
        or "readtimeout" in text
        or "time out" in text
    ):
        return "TIMEOUT"

    if "anakin" in text:
        return "ANAKIN_ERROR"

    if "lyzr" in text:
        return "LYZR_ERROR"

    if any(
        marker in text
        for marker in (
            "policy violation",
            "policy block",
            "policy blocked",
            "guardrail",
            "outside buyer policy",
            "outside supplier policy",
            "hard constraint",
            "policy constraint",
            "policy constraints",
        )
    ):
        return "POLICY_BLOCK"

    normalized_stage = stage.upper()

    if normalized_stage == "VERIFY":
        return "VERIFY_FAIL"

    if normalized_stage == "READ":
        return "READ_ERROR"

    if normalized_stage == "REASON":
        return "REASON_ERROR"

    if normalized_stage == "ACT":
        return "ACT_ERROR"

    if normalized_stage in {
        "SUPPLIER_SELECTION",
        "SELECTION",
    }:
        return "SELECTION_ERROR"

    if normalized_stage == "RECOVERY":
        return "RECOVERY_ERROR"

    return "UNKNOWN_ERROR"
