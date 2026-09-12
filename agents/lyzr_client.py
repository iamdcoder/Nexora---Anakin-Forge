from __future__ import annotations

import os
from typing import Any

import requests


class LyzrClient:
    """Agent inference adapter: Lyzr ADK first, documented Agent API fallback."""

    def __init__(self):
        self.base_url = os.getenv("LYZR_BASE_URL", "https://agent-prod.studio.lyzr.ai").rstrip("/")
        self.api_key = os.getenv("LYZR_API_KEY", "").strip()
        self.timeout = float(os.getenv("LYZR_CHAT_TIMEOUT", "90"))
        self.use_sdk = os.getenv("LYZR_USE_SDK", "1") == "1"
        self.last_transport = "sdk" if self.use_sdk else "agent_api"
        self._sdk = None
        if self.use_sdk and self.api_key:
            try:
                from agents.lyzr_sdk import LyzrSDKClient
                self._sdk = LyzrSDKClient()
            except Exception:
                self._sdk = None
        if not self.api_key:
            raise ValueError("LYZR_API_KEY is not configured.")

    def chat(self, agent_id: str, user_id: str, session_id: str, message: str) -> Any:
        if not agent_id:
            raise ValueError("Lyzr agent ID is not configured.")

        if self._sdk is not None:
            try:
                self.last_transport = "sdk"
                return self._sdk.chat(agent_id, user_id, session_id, message)
            except Exception:
                if os.getenv("LYZR_SDK_FALLBACK", "1") != "1":
                    raise

        self.last_transport = "agent_api"
        return self._chat_agent_api(agent_id, user_id, session_id, message)

    def _chat_agent_api(self, agent_id: str, user_id: str, session_id: str, message: str) -> Any:
        url = f"{self.base_url}/v3/inference/chat/"
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "message": message,
            "system_prompt_variables": {},
            "filter_variables": {},
            "features": [],
        }
        headers = {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise RuntimeError(f"Lyzr API request failed: {exc}") from exc
        if not response.ok:
            raise RuntimeError(f"Lyzr API error {response.status_code}: {response.text[:500]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError("Lyzr returned a non-JSON response.") from exc
        if not isinstance(data, dict):
            raise ValueError("Unexpected Lyzr response shape.")
        if "response" in data:
            return data["response"]
        if "agent_response" in data:
            return data["agent_response"]
        raise ValueError(f"Unexpected Lyzr response: {data}")
