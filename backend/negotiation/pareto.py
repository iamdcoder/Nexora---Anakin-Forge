from __future__ import annotations

from dataclasses import dataclass

from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from negotiation.utility import calculate_utility

@dataclass(frozen=True)
class ParetoPoint:
    index: int
    buyer_utility: float
    supplier_utility: float
    joint_utility: float
    proposal: NegotiationProposal
    pareto_efficient: bool

def build_pareto_frontier(
    proposals: list[NegotiationProposal],
    buyer_policy: PartyPolicy,
    supplier_policy: PartyPolicy,
) -> list[ParetoPoint]:
    points: list[ParetoPoint] = []
    for index, proposal in enumerate(proposals):
        buyer = calculate_utility(proposal, buyer_policy, "buyer").total
        supplier = calculate_utility(proposal, supplier_policy, "supplier").total
        points.append(
            ParetoPoint(
                index=index,
                buyer_utility=buyer,
                supplier_utility=supplier,
                joint_utility=round((buyer + supplier) / 2, 4),
                proposal=proposal,
                pareto_efficient=True,
            )
        )

    efficient: list[ParetoPoint] = []
    for point in points:
        dominated = False
        for other in points:
            if other is point:
                continue
            no_worse = (
                other.buyer_utility >= point.buyer_utility
                and other.supplier_utility >= point.supplier_utility
            )
            strictly_better = (
                other.buyer_utility > point.buyer_utility
                or other.supplier_utility > point.supplier_utility
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            efficient.append(point)

    efficient_keys = {p.index for p in efficient}
    return [
        ParetoPoint(
            index=p.index,
            buyer_utility=p.buyer_utility,
            supplier_utility=p.supplier_utility,
            joint_utility=p.joint_utility,
            proposal=p.proposal,
            pareto_efficient=p.index in efficient_keys,
        )
        for p in points
    ]
