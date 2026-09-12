from models.proposal import NegotiationProposal

def calculate_concession(
    previous: NegotiationProposal,
    current: NegotiationProposal,
) -> dict:

    return {
        "price": (
            current.price
            - previous.price
        ),

        "delivery_days": (
            current.delivery_days
            - previous.delivery_days
        ),

        "payment_days": (
            current.payment_days
            - previous.payment_days
        ),

        "sla_penalty": (
            current.sla_penalty
            - previous.sla_penalty
        ),

        "sla_uptime": (
            current.sla_uptime
            - previous.sla_uptime
        ),
    }

def has_meaningful_concession(
    previous: NegotiationProposal,
    current: NegotiationProposal,
) -> bool:

    changes = calculate_concession(
        previous,
        current,
    )

    return any(
        abs(value) > 0.01
        for value in changes.values()
    )

def negotiation_pressure(
    current_round: int,
    max_rounds: int,
) -> float:

    if max_rounds <= 0:
        return 1.0

    return min(
        current_round / max_rounds,
        1.0,
    )