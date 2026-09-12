from dataclasses import dataclass, field

from models.proposal import NegotiationProposal

@dataclass
class NegotiationState:
    current_round: int = 0

    buyer_proposals: list[NegotiationProposal] = field(
        default_factory=list
    )

    supplier_proposals: list[NegotiationProposal] = field(
        default_factory=list
    )

    gaps: list[float] = field(
        default_factory=list
    )

    round_metrics: list[dict] = field(
        default_factory=list
    )

    consecutive_non_concessions: int = 0

    consecutive_repeated_proposals: int = 0

    agreement_reached: bool = False

    deadlock: bool = False

    def record_round(
        self,
        buyer_proposal: NegotiationProposal,
        supplier_proposal: NegotiationProposal,
        gap: float,
        metrics: dict | None = None,
    ) -> None:

        self.current_round = buyer_proposal.round_number

        self.buyer_proposals.append(
            buyer_proposal
        )

        self.supplier_proposals.append(
            supplier_proposal
        )

        self.gaps.append(gap)

        if metrics is not None:
            self.round_metrics.append(metrics)

    @property
    def initial_gap(self) -> float | None:
        if not self.gaps:
            return None

        return self.gaps[0]

    @property
    def latest_gap(self) -> float | None:
        if not self.gaps:
            return None

        return self.gaps[-1]

    @property
    def gap_reduction(self) -> float | None:
        if not self.gaps:
            return None

        return self.initial_gap - self.latest_gap

    @property
    def convergence_ratio(self) -> float:
        if not self.gaps:
            return 0.0

        if self.initial_gap == 0:
            return 1.0

        reduction = self.initial_gap - self.latest_gap

        return max(
            0.0,
            min(
                1.0,
                reduction / self.initial_gap,
            ),
        )