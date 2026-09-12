from __future__ import annotations

import os
from typing import Any


class LyzrSDKClient:
    """Thin adapter around the Lyzr ADK Studio/Agent interface."""

    def __init__(self):
        try:
            from lyzr import Studio
        except ImportError as exc:
            raise RuntimeError("lyzr-adk is not installed") from exc

        api_key = os.getenv("LYZR_API_KEY", "").strip()
        if not api_key:
            raise ValueError("LYZR_API_KEY is not configured.")
        self.studio = Studio(api_key=api_key, log="error")

    def get_agent(self, agent_id: str) -> Any:
        return self.studio.get_agent(agent_id)

    def chat(self, agent_id: str, user_id: str, session_id: str, message: str) -> Any:
        agent = self.get_agent(agent_id)
        result = agent.run(message, session_id=session_id, user_id=user_id)
        if hasattr(result, "response"):
            return result.response
        return result

    def list_agents(self) -> list[Any]:
        return list(self.studio.list_agents())
