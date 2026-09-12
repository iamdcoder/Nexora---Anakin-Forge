from __future__ import annotations

from dataclasses import dataclass

from models.policy import PartyPolicy
from models.proposal import NegotiationProposal

@dataclass(frozen=True)
class UtilityResult:
    role: str
    total: float
    components: dict[str, float]
    risk_score: float
    rationale: str

def _band_score(value: float, best: float, worst: float, higher_is_better: bool) -> float:
    if higher_is_better:
        if value >= best:
            return 1.0
        if value <= worst:
            return 0.0
        return (value - worst) / (best - worst)
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    return (worst - value) / (worst - best)

def _price_score(price: float, policy: PartyPolicy, role: str) -> float:
    target = policy.price.target
    if role == "buyer":
        worst = policy.price.maximum or target * 1.25
        return _band_score(price, target, worst, higher_is_better=False)
    worst = policy.price.minimum or target * 0.8
    return _band_score(price, target, worst, higher_is_better=True)

def _delivery_score(days: int, policy: PartyPolicy, role: str) -> float:
    target = policy.delivery.target_days
    worst = policy.delivery.maximum_days
    if role == "buyer":
        return _band_score(days, target, worst, higher_is_better=False)
    return _band_score(days, target, worst, higher_is_better=True)

def _payment_score(days: int, policy: PartyPolicy, role: str) -> float:
    preferred = policy.payment.preferred_days
    minimum = policy.payment.minimum_days
    if role == "buyer":
        worst = max(preferred + 1, minimum)
        return _band_score(days, preferred, worst, higher_is_better=True)
    worst = minimum
    return _band_score(days, preferred, worst, higher_is_better=False)

def _sla_uptime_score(uptime: float, policy: PartyPolicy) -> float:
    minimum = policy.sla.minimum_uptime
    return _band_score(uptime, 100.0, minimum, higher_is_better=True)

def _sla_penalty_score(penalty: float, policy: PartyPolicy) -> float:
    maximum = policy.sla.maximum_penalty
    minimum = policy.sla.minimum_penalty
    return _band_score(penalty, minimum, maximum, higher_is_better=False)

def calculate_utility(
    proposal: NegotiationProposal,
    policy: PartyPolicy,
    role: str,
) -> UtilityResult:
    components = {
        "price": round(_price_score(proposal.price, policy, role), 4),
        "delivery": round(_delivery_score(proposal.delivery_days, policy, role), 4),
        "payment": round(_payment_score(proposal.payment_days, policy, role), 4),
        "sla_uptime": round(_sla_uptime_score(proposal.sla_uptime, policy), 4),
        "sla_penalty": round(_sla_penalty_score(proposal.sla_penalty, policy), 4),
    }

    total = (
        components["price"] * 0.45
        + components["delivery"] * 0.20
        + components["payment"] * 0.15
        + components["sla_uptime"] * 0.10
        + components["sla_penalty"] * 0.10
    )

    margins: list[float] = []
    if role == "buyer" and policy.price.maximum is not None:
        margins.append((policy.price.maximum - proposal.price) / policy.price.maximum)
    if role == "supplier" and policy.price.minimum is not None:
        margins.append((proposal.price - policy.price.minimum) / policy.price.minimum)
    margins.append((policy.delivery.maximum_days - proposal.delivery_days) / policy.delivery.maximum_days)
    margins.append((proposal.payment_days - policy.payment.minimum_days) / max(policy.payment.minimum_days, 1))
    margins.append((proposal.sla_uptime - policy.sla.minimum_uptime) / max(100 - policy.sla.minimum_uptime, 1))
    margins.append((policy.sla.maximum_penalty - proposal.sla_penalty) / max(policy.sla.maximum_penalty, 1))

    average_margin = sum(max(0.0, min(1.0, m)) for m in margins) / len(margins)
    risk_score = round(max(0.0, min(100.0, 100.0 * (1.0 - average_margin))), 1)

    if total >= 0.80:
        rationale = "Strong alignment with the party's preferred commercial objectives."
    elif total >= 0.60:
        rationale = "Commercially acceptable with moderate trade-offs."
    elif total >= 0.40:
        rationale = "Marginal package; meaningful trade-offs remain."
    else:
        rationale = "Poor package for this party; close to walk-away territory."

    return UtilityResult(
        role=role,
        total=round(total, 4),
        components=components,
        risk_score=risk_score,
        rationale=rationale,
    )

def explain_tradeoff(
    before: NegotiationProposal,
    after: NegotiationProposal,
    role: str,
    policy: PartyPolicy,
) -> dict:
    before_u = calculate_utility(before, policy, role)
    after_u = calculate_utility(after, policy, role)
    return {
        "utility_before": before_u.total,
        "utility_after": after_u.total,
        "utility_delta": round(after_u.total - before_u.total, 4),
        "risk_before": before_u.risk_score,
        "risk_after": after_u.risk_score,
        "component_deltas": {
            key: round(after_u.components[key] - before_u.components[key], 4)
            for key in before_u.components
        },
    }
