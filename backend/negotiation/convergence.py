from models.proposal import NegotiationProposal

def calculate_gap(
    buyer: NegotiationProposal,
    supplier: NegotiationProposal,
) -> float:
    price_scale = max(
        abs(buyer.price),
        abs(supplier.price),
        1.0,
    )

    price_gap = (
        abs(buyer.price - supplier.price)
        / price_scale
    )

    delivery_gap = (
        abs(
            buyer.delivery_days
            - supplier.delivery_days
        )
        / 60.0
    )

    payment_gap = (
        abs(
            buyer.payment_days
            - supplier.payment_days
        )
        / 60.0
    )

    sla_gap = (
        abs(
            buyer.sla_penalty
            - supplier.sla_penalty
        )
        / 10.0
    )

    return (
        price_gap * 0.55
        + delivery_gap * 0.20
        + payment_gap * 0.15
        + sla_gap * 0.10
    )

def is_converging(
    previous_gap: float,
    current_gap: float,
) -> bool:
    return current_gap < previous_gap

def calculate_concession(
    previous: NegotiationProposal,
    current: NegotiationProposal,
    role: str,
) -> dict:
    """
    Calculate how much an agent moved from its previous proposal.

    The values are normalized so they can be displayed in the UI
    and compared across different negotiation issues.
    """

    price_delta = current.price - previous.price

    delivery_delta = (
        current.delivery_days
        - previous.delivery_days
    )

    payment_delta = (
        current.payment_days
        - previous.payment_days
    )

    sla_delta = (
        current.sla_penalty
        - previous.sla_penalty
    )

     

                                            

                                 
                                           
    if role == "buyer":
        price_concession = max(
            previous.price - current.price,
            0,
        )
        delivery_concession = max(
            current.delivery_days
            - previous.delivery_days,
            0,
        )
        payment_concession = max(
            current.payment_days
            - previous.payment_days,
            0,
        )
        sla_concession = max(
            previous.sla_penalty
            - current.sla_penalty,
            0,
        )

    else:
        price_concession = max(
            current.price - previous.price,
            0,
        )
        delivery_concession = max(
            previous.delivery_days
            - current.delivery_days,
            0,
        )
        payment_concession = max(
            previous.payment_days
            - current.payment_days,
            0,
        )
        sla_concession = max(
            current.sla_penalty
            - previous.sla_penalty,
            0,
        )

    return {
        "price_delta": price_delta,
        "delivery_delta": delivery_delta,
        "payment_delta": payment_delta,
        "sla_delta": sla_delta,
        "price_concession": price_concession,
        "delivery_concession": delivery_concession,
        "payment_concession": payment_concession,
        "sla_concession": sla_concession,
    }