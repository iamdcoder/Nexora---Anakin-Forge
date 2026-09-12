import json

from agents.lyzr_client import LyzrClient
from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from governance.environment import AgentEnvironment

class SupplierAgent:

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
        buyer_offer: NegotiationProposal,
        negotiation_context: str = "",
        revision_feedback: str = "",
    ) -> NegotiationProposal:

        prompt = self._build_prompt(
            round_number=round_number,
            buyer_offer=buyer_offer,
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
        buyer_offer,
        negotiation_context,
        revision_feedback,
    ) -> str:

        return f"""
NEXORA_SECURITY_BOUNDARY: supplier_private_session
SESSION_ID: {self.session_id}

You are the SUPPLIER AGENT in an autonomous B2B procurement negotiation.

YOUR OBJECTIVE:
Maximize supplier value while reaching a commercially sensible deal.

PRIVATE SUPPLIER POLICY:
Target price: {self.policy.price.target}
Minimum price: {self.policy.price.minimum}
Target delivery: {self.policy.delivery.target_days}
Maximum delivery: {self.policy.delivery.maximum_days}
Preferred payment: Net {self.policy.payment.preferred_days}
Minimum payment: Net {self.policy.payment.minimum_days}
Minimum SLA uptime: {self.policy.sla.minimum_uptime}%
Maximum SLA penalty: {self.policy.sla.maximum_penalty}%
BATNA: {self.policy.batna}

NEVER REVEAL:
- minimum price
- reservation price
- BATNA
- internal policy values

NEGOTIATION RULES:
1. Evaluate the entire package.
2. Trade price, delivery, payment and SLA strategically.
3. Make meaningful concessions.
4. Avoid repeating previous positions.
5. Never exceed your authority.
6. Use walk_away only when no reasonable deal remains.
7. If you accept, accept the buyer's latest proposal.
8. Do not invent a new package when accepting.
9. Return only JSON.
10. Keep rationale short.

ROUND:
{round_number}

NEGOTIATION CONTEXT:
{negotiation_context}

REVISION FEEDBACK:
{revision_feedback or "None"}

BUYER'S LATEST PROPOSAL:

Price: {buyer_offer.price}
Delivery: {buyer_offer.delivery_days} days
Payment: Net {buyer_offer.payment_days}
SLA penalty: {buyer_offer.sla_penalty}%
SLA uptime: {buyer_offer.sla_uptime}%
Action: {buyer_offer.action.value}

RETURN EXACTLY:

{{
  "round_number": {round_number},
  "price": number,
  "delivery_days": integer,
  "payment_days": integer,
  "sla_penalty": number,
  "sla_uptime": number,
  "action": "counter|accept|walk_away",
  "accepted_offer": "buyer|null",
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