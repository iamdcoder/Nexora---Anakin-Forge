"""
Lyzr bootstrap helpers for Nexora.

This module never stores an API key in source code. It reads LYZR_API_KEY from
the environment, discovers existing agents, and writes only non-secret agent IDs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("LYZR_BASE_URL", "https://agent-prod.studio.lyzr.ai").rstrip("/")

BUYER_PROMPT = """You are the Nexora BUYER AGENT in a bounded B2B procurement negotiation.

You represent the buyer only. Never reveal or infer private supplier reservation
prices, BATNA values, or internal supplier policy.

Your job is to negotiate price, delivery, payment terms, SLA uptime and SLA
penalties while staying strictly inside the buyer policy provided in each request.

Return ONLY the required JSON proposal. Never include hidden policy values in
your rationale."""
SUPPLIER_PROMPT = """You are the Nexora SUPPLIER AGENT in a bounded B2B procurement negotiation.

You represent the supplier only. Never reveal or infer private buyer reservation
prices, BATNA values, or internal buyer policy.

Your job is to negotiate price, delivery, payment terms, SLA uptime and SLA
penalties while staying strictly inside the supplier policy provided in each request.

Return ONLY the required JSON proposal. Never include hidden policy values in
your rationale."""

def _headers(api_key: str) -> dict[str, str]:
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key,
    }

def require_key() -> str:
    key = os.getenv("LYZR_API_KEY", "").strip()
    if not key:
        raise RuntimeError("LYZR_API_KEY is not configured.")
    return key

def list_agents() -> list[dict[str, Any]]:
    key = require_key()
    response = requests.get(
        f"{BASE_URL}/v3/agents/",
        headers=_headers(key),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("agents", data if isinstance(data, list) else [])

def get_agent(agent_id: str) -> dict[str, Any]:
    key = require_key()
    response = requests.get(
        f"{BASE_URL}/v3/agents/{agent_id}",
        headers=_headers(key),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("agent", data) if isinstance(data, dict) else {}

def summarize_features(agent: dict[str, Any]) -> dict[str, Any]:
    features = agent.get("features", []) if isinstance(agent, dict) else []
    names: list[str] = []
    raw = json.dumps(features, sort_keys=True, default=str).lower()
    if isinstance(features, list):
        for item in features:
            if isinstance(item, dict):
                value = item.get("type") or item.get("name") or item.get("feature")
                if value:
                    names.append(str(value))
            elif isinstance(item, str):
                names.append(item)
    rai_terms = ("rai", "responsible", "guardrail", "safe ai")
    rai_detected = any(term in raw for term in rai_terms)
    return {"feature_names": names, "rai_feature_detected": rai_detected}

def find_named_agents(
    agents: list[dict[str, Any]],
    buyer_name: str = "Nexora Buyer Agent",
    supplier_name: str = "Nexora Supplier Agent",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    buyer = next((a for a in agents if str(a.get("name", "")).strip() == buyer_name), None)
    supplier = next((a for a in agents if str(a.get("name", "")).strip() == supplier_name), None)
    return buyer, supplier

def create_agent(
    *,
    name: str,
    description: str,
    system_prompt: str,
    model: str | None = None,
    provider_id: str | None = None,
    llm_credential_id: str | None = None,
) -> dict[str, Any]:
    key = require_key()
    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "response_format": {
            "type": "json_object",
        },
        "temperature": 0.2,
        "top_p": 0.9,
        "store_messages": True,
    }
    if model:
        payload["model"] = model
    if provider_id:
        payload["provider_id"] = provider_id
    if llm_credential_id:
        payload["llm_credential_id"] = llm_credential_id

    response = requests.post(
        f"{BASE_URL}/v3/agents/",
        headers=_headers(key),
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("agent", data)

def write_env_ids(
    buyer_id: str | None,
    supplier_id: str | None,
    env_path: str = ".env",
) -> None:
    path = Path(env_path)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    updates = {
        "BUYER_AGENT_ID": buyer_id or "",
        "SUPPLIER_AGENT_ID": supplier_id or "",
    }
    lines = existing.splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")

def bootstrap_agents(
    *,
    env_path: str = ".env",
    auto_create: bool = False,
) -> dict[str, Any]:
    agents = list_agents()
    buyer, supplier = find_named_agents(agents)

    if auto_create and buyer is None:
        buyer = create_agent(
            name="Nexora Buyer Agent",
            description="Bounded buyer agent for autonomous B2B procurement negotiation.",
            system_prompt=BUYER_PROMPT,
            model=os.getenv("LYZR_MODEL") or None,
            provider_id=os.getenv("LYZR_PROVIDER_ID") or None,
            llm_credential_id=os.getenv("LYZR_LLM_CREDENTIAL_ID") or None,
        )
    if auto_create and supplier is None:
        supplier = create_agent(
            name="Nexora Supplier Agent",
            description="Bounded supplier agent for autonomous B2B procurement negotiation.",
            system_prompt=SUPPLIER_PROMPT,
            model=os.getenv("LYZR_MODEL") or None,
            provider_id=os.getenv("LYZR_PROVIDER_ID") or None,
            llm_credential_id=os.getenv("LYZR_LLM_CREDENTIAL_ID") or None,
        )

    buyer_id = (buyer or {}).get("id") or (buyer or {}).get("agent_id")
    supplier_id = (supplier or {}).get("id") or (supplier or {}).get("agent_id")
    write_env_ids(buyer_id, supplier_id, env_path=env_path)

    return {
        "buyer": buyer,
        "supplier": supplier,
        "total_agents": len(agents),
        "created": {
            "buyer": auto_create and buyer is not None,
            "supplier": auto_create and supplier is not None,
        },
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure Nexora Lyzr agents.")
    parser.add_argument("--create", action="store_true", help="Create missing Nexora agents.")
    parser.add_argument("--env", default=".env", help="Path to the local environment file.")
    args = parser.parse_args()

    result = bootstrap_agents(env_path=args.env, auto_create=args.create)
    print(json.dumps(result, indent=2, default=str))
