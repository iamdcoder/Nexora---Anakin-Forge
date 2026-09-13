import json

from agents.lyzr_client import LyzrClient
from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from governance.environment import AgentEnvironment

class BuyerAgent:

    def __init__(
        self,
        policy: PartyPolicy,
        agent_id: str,
        user_id: str,
        session_id: str,
        environment: AgentEnvironment | None = None,
    ):

        self.policy = policy
        self.agent_id = agent_id
        self.user_id = user_id
        self.session_id = session_id
        self.environment = environment or AgentEnvironment(
            actor="buyer" if "buyer_agent.py" in __file__ else "supplier",
            private_policy=policy,
            session_id=session_id,
        )

        self.client = LyzrClient()

    def generate_proposal(
        self,
        round_number: int,
        supplier_offer: NegotiationProposal | None,
        negotiation_context: str = "",
        revision_feedback: str = "",
    ) -> NegotiationProposal:

        prompt = self._build_prompt(
            round_number=round_number,
            supplier_offer=supplier_offer,
            negotiation_context=negotiation_context,
            revision_feedback=revision_feedback,
        )

        response = self.client.chat(
            agent_id=self.agent_id,
            user_id=self.user_id,
            session_id=self.session_id,
            message=prompt,
        )

        return self._parse_response(response)

    def _build_prompt(
        self,
        round_number,
        supplier_offer,
        negotiation_context,
        revision_feedback,
    ) -> str:

        if supplier_offer is None:

            supplier_text = (
                "No supplier proposal exists yet. "
                "Make the opening offer."
            )

        else:

            supplier_text = f"""
SUPPLIER'S LATEST PROPOSAL

Price: {supplier_offer.price}
Delivery: {supplier_offer.delivery_days} days
Payment: Net {supplier_offer.payment_days}
SLA penalty: {supplier_offer.sla_penalty}%
SLA uptime: {supplier_offer.sla_uptime}%
Action: {supplier_offer.action.value}
"""

        autonomous_reasoning_context = self.environment.shared_context.get(
            "autonomous_reasoning_context",
            "",
        )

        return f"""
NEXORA_SECURITY_BOUNDARY: buyer_private_session
SESSION_ID: {self.session_id}

You are the BUYER AGENT in an autonomous B2B procurement negotiation.

YOUR OBJECTIVE:
Secure the best feasible commercial package.

PRIVATE BUYER POLICY:
Target price: {self.policy.price.target}
Maximum price: {self.policy.price.maximum}
Target delivery: {self.policy.delivery.target_days}
Maximum delivery: {self.policy.delivery.maximum_days}
Preferred payment: Net {self.policy.payment.preferred_days}
Minimum payment: Net {self.policy.payment.minimum_days}
Minimum SLA uptime: {self.policy.sla.minimum_uptime}%
Maximum SLA penalty: {self.policy.sla.maximum_penalty}%
BATNA: {self.policy.batna}

NEVER REVEAL:
- maximum price
- reservation price
- BATNA
- internal policy values

NEGOTIATION RULES:
1. Optimize the complete package.
2. Negotiate price, delivery, payment and SLA together.
3. Prefer useful trade-offs over random concessions.
4. Do not repeat the same proposal.
5. Never exceed your authority.
6. Use walk_away only when no reasonable deal remains.
7. If you accept, you are accepting the supplier's latest proposal.
8. When accepting, do not invent different terms.
9. Return only JSON.
10. Keep rationale short.

ROUND:
{round_number}

NEGOTIATION CONTEXT:
{negotiation_context}

AUTONOMOUS PROCUREMENT REASONING:
{autonomous_reasoning_context or "No additional procurement strategy was supplied."}

Use this reasoning as strategic guidance only. Your private policy and the
negotiation guardrails remain authoritative. Do not reveal private policy values.

REVISION FEEDBACK:
{revision_feedback or "None"}

{supplier_text}

RETURN EXACTLY:

{{
  "round_number": {round_number},
  "price": number,
  "delivery_days": integer,
  "payment_days": integer,
  "sla_penalty": number,
  "sla_uptime": number,
  "action": "offer|counter|accept|walk_away",
  "accepted_offer": "supplier|null",
  "rationale": "brief reason"
}}
"""

    @staticmethod
    def _parse_response(
        response,
    ) -> NegotiationProposal:

        if isinstance(response, dict):
            data = response

        else:

            text = response.strip()

            if text.startswith("```json"):
                text = text[7:]

                if text.endswith("```"):
                    text = text[:-3]

            elif text.startswith("```"):
                text = text[3:]

                if text.endswith("```"):
                    text = text[:-3]

            data = json.loads(
                text.strip()
            )

        return NegotiationProposal.model_validate(
            data
        )