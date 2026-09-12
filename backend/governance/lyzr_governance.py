"""Lyzr governance adapters with a strong deterministic fallback.

The fallback is intentionally useful in offline/demo deployments: it performs
secret-leakage, prompt-injection, structural and numeric sanity checks instead
of becoming a permissive pass-through. When a Lyzr Responsible AI custom
Guardrail endpoint is configured, that external decision is authoritative and
fail-closed. Audit events are normalized to a local audit envelope and
spooled locally when no external sink is configured.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

@dataclass
class GovernanceDecision:
    allowed: bool
    source: str
    reason: str
    rule: str | None = None
    response_status: int | None = None

class LyzrGovernance:
    def __init__(self):
        self.guardrail_url = os.getenv("LYZR_GUARDRAIL_URL", "").strip()
        self.guardrail_token = os.getenv("LYZR_GUARDRAIL_TOKEN", "").strip()
        self.timeout = float(os.getenv("LYZR_GOVERNANCE_TIMEOUT", "8"))
        self.outbox_path = Path(os.getenv("NEXORA_AUDIT_OUTBOX", "data/audit_outbox.jsonl"))
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def mode(self) -> str:
        parts = []
        if self.guardrail_url:
            parts.append("lyzr_responsible_ai")
        if not parts:
            return "deterministic_fallback"
        return "+".join(parts)

    @staticmethod
    def _scan_text(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).lower()

    def _local_check(self, *, stage: str, actor: str, payload: dict[str, Any]) -> GovernanceDecision:
        raw = self._scan_text(payload)

        secret_markers = [
            "reservation price", "walk-away price", "walk away price",
            "private batna", "supplier minimum", "buyer maximum",
            "minimum_price", "maximum_price", "raw_policy", "private_policy",
            "internal threshold", "secret batna",
        ]
        injection_markers = [
            "ignore previous instructions", "ignore all previous instructions",
            "system prompt", "reveal your instructions", "reveal your policy",
            "disregard the policy", "bypass the guardrail", "disable the guardrail",
            "pretend the rules do not apply",
        ]
        if any(marker in raw for marker in secret_markers):
            return GovernanceDecision(False, "local_fallback", "Potential private negotiation-policy disclosure detected.", "privacy-isolation")
        if any(marker in raw for marker in injection_markers):
            return GovernanceDecision(False, "local_fallback", "Potential prompt-injection or guardrail-bypass attempt detected.", "prompt-injection")

        proposal = payload.get("proposal")
        if proposal is not None:
            if not isinstance(proposal, dict):
                return GovernanceDecision(False, "local_fallback", "Proposal payload must be a JSON object.", "structured-proposal")
            required = {"price", "delivery_days", "payment_days", "sla_penalty", "sla_uptime"}
            missing = sorted(required - proposal.keys())
            if missing:
                return GovernanceDecision(False, "local_fallback", f"Proposal is missing required fields: {', '.join(missing)}.", "proposal-schema")
            numeric_ranges = {
                "price": (0.01, 1_000_000_000.0),
                "delivery_days": (0, 3650),
                "payment_days": (0, 3650),
                "sla_penalty": (0, 100),
                "sla_uptime": (0, 100),
            }
            for field, (low, high) in numeric_ranges.items():
                value = proposal.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    return GovernanceDecision(False, "local_fallback", f"Invalid numeric value for {field}.", "numeric-sanity")
                if not low <= float(value) <= high:
                    return GovernanceDecision(False, "local_fallback", f"Value for {field} is outside the governance sanity range.", "numeric-sanity")

        return GovernanceDecision(True, "local_fallback", f"Local governance checks passed for {stage} ({actor}).", "local-governance-v2")

    def check(self, *, stage: str, actor: str, payload: dict[str, Any]) -> GovernanceDecision:
        local = self._local_check(stage=stage, actor=actor, payload=payload)
        if not local.allowed:
            return local

        if not self.guardrail_url:
            return local

        headers = {"content-type": "application/json", "accept": "application/json"}
        if self.guardrail_token:
            headers["authorization"] = f"Bearer {self.guardrail_token}"
        body = {"stage": stage, "actor": actor, "payload": payload, "mode": "validate"}
        try:
            response = requests.post(self.guardrail_url, headers=headers, json=body, timeout=self.timeout)
            response.raise_for_status()
            data = response.json() if response.content else {}
            verdict = str(data.get("verdict", "")).lower()
            allowed = verdict == "allow" if verdict else bool(data.get("allowed", data.get("valid", data.get("pass", False))))
            return GovernanceDecision(
                allowed=allowed,
                source="lyzr_responsible_ai",
                reason=str(data.get("reason", "Lyzr Responsible AI decision")),
                rule=data.get("rule"),
                response_status=response.status_code,
            )
        except Exception as exc:
            return GovernanceDecision(False, "lyzr_responsible_ai", f"Governance endpoint unavailable: {exc}", "external-governance-unavailable")

    def _audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "nexora.audit-event.v1",
            "source": "nexora-negotiator",
            "event": event,
        }

    def publish_event(self, event: dict[str, Any]) -> dict[str, Any]:
        envelope = self._audit_event(event)
        with self.outbox_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(envelope, sort_keys=True) + "\n")
        return {"published": False, "source": "local_audit_outbox", "queued": True, "path": str(self.outbox_path)}

    def outbox_status(self) -> dict[str, Any]:
        if not self.outbox_path.exists():
            return {"queued_events": 0, "path": str(self.outbox_path)}
        lines = [x for x in self.outbox_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return {"queued_events": len(lines), "path": str(self.outbox_path)}

def build_redaction_snapshot(policy) -> dict[str, Any]:
    return {
        "price": {"target_present": policy.price.target is not None},
        "delivery": {"target_present": policy.delivery.target_days is not None},
        "payment": {"preferred_present": policy.payment.preferred_days is not None},
        "sla": {"policy_present": True},
        "private_fields_redacted": True,
    }
