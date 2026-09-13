from __future__ import annotations

from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from negotiation.utility import calculate_utility

def _hard_limit_checks(proposal: NegotiationProposal, buyer: PartyPolicy, supplier: PartyPolicy) -> int:
    checks = [
        buyer.price.maximum is None or proposal.price <= buyer.price.maximum,
        supplier.price.minimum is None or proposal.price >= supplier.price.minimum,
        proposal.delivery_days <= buyer.delivery.maximum_days,
        proposal.delivery_days <= supplier.delivery.maximum_days,
        proposal.payment_days >= buyer.payment.minimum_days,
        proposal.payment_days >= supplier.payment.minimum_days,
        buyer.sla.minimum_penalty <= proposal.sla_penalty <= buyer.sla.maximum_penalty,
        supplier.sla.minimum_penalty <= proposal.sla_penalty <= supplier.sla.maximum_penalty,
        proposal.sla_uptime >= buyer.sla.minimum_uptime,
        proposal.sla_uptime >= supplier.sla.minimum_uptime,
    ]
    return sum(1 for ok in checks if not ok)

def _margin_risk(utility_score: float) -> float:

                                                 
    return round(max(0.0, min(100.0, (1.0 - utility_score) * 100.0)), 1)

def calculate_risk(proposal: NegotiationProposal, buyer_policy: PartyPolicy, supplier_policy: PartyPolicy) -> dict:
    buyer_u = calculate_utility(proposal, buyer_policy, "buyer")
    supplier_u = calculate_utility(proposal, supplier_policy, "supplier")
    hard_limit_hits = _hard_limit_checks(proposal, buyer_policy, supplier_policy)

    buyer_risk = _margin_risk(buyer_u.total)
    supplier_risk = _margin_risk(supplier_u.total)
    commercial_risk = round((buyer_risk + supplier_risk) / 2, 1)

    if hard_limit_hits:
        label = "CRITICAL"
    elif commercial_risk >= 70:
        label = "HIGH"
    elif commercial_risk >= 40:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "label": label,
        "score": commercial_risk,
        "commercial_risk": commercial_risk,
        "policy_compliance": 100.0 if hard_limit_hits == 0 else 0.0,
        "hard_limit_hits": hard_limit_hits,
        "buyer_risk": buyer_risk,
        "supplier_risk": supplier_risk,
        "buyer_utility": buyer_u.total,
        "supplier_utility": supplier_u.total,
        "interpretation": (
            "Hard-policy violation detected; agreement must be blocked."
            if hard_limit_hits else
            "Commercial exposure reflects distance from preferred outcomes; no hard policy violation detected."
        ),
    }
