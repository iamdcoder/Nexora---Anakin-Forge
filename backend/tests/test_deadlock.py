from models.policy import (
    PartyPolicy,
    PricePolicy,
    DeliveryPolicy,
    PaymentPolicy,
    SLAPolicy,
)

from models.proposal import (
    NegotiationProposal,
    ProposalAction,
)

from negotiation.engine import NegotiationEngine

class MockBuyerAgent:

    def generate_proposal(
        self,
        round_number,
        supplier_offer,
    ):

        return NegotiationProposal(
            round_number=round_number,
            price=50000,
            delivery_days=30,
            payment_days=45,
            sla_penalty=3,
            sla_uptime=98,
            action=ProposalAction.COUNTER,
        )

class MockSupplierAgent:

    def generate_proposal(
        self,
        round_number,
        buyer_offer,
    ):

        return NegotiationProposal(
            round_number=round_number,
            price=60000,
            delivery_days=30,
            payment_days=45,
            sla_penalty=3,
            sla_uptime=98,
            action=ProposalAction.COUNTER,
        )

def make_buyer_policy():

    return PartyPolicy(
        price=PricePolicy(
            target=48000,
            maximum=50000,
        ),
        delivery=DeliveryPolicy(
            target_days=30,
            maximum_days=45,
        ),
        payment=PaymentPolicy(
            preferred_days=60,
            minimum_days=30,
        ),
        sla=SLAPolicy(
            minimum_uptime=98,
            minimum_penalty=2,
            maximum_penalty=5,
        ),
        batna="Existing supplier",
        max_rounds=10,
    )

def make_supplier_policy():

    return PartyPolicy(
        price=PricePolicy(
            target=62000,
            minimum=60000,
        ),
        delivery=DeliveryPolicy(
            target_days=30,
            maximum_days=45,
        ),
        payment=PaymentPolicy(
            preferred_days=30,
            minimum_days=15,
        ),
        sla=SLAPolicy(
            minimum_uptime=98,
            minimum_penalty=2,
            maximum_penalty=5,
        ),
        batna="Other customer",
        max_rounds=10,
    )

def test_negotiation_deadlock():

    engine = NegotiationEngine(
        buyer_policy=make_buyer_policy(),
        supplier_policy=make_supplier_policy(),
        buyer_agent=MockBuyerAgent(),
        supplier_agent=MockSupplierAgent(),
    )

    result = engine.run()

    assert result.status == "deadlock"