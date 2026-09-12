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
            price=105,
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
            price=105,
            delivery_days=30,
            payment_days=45,
            sla_penalty=3,
            sla_uptime=98,
            action=ProposalAction.COUNTER,
        )

def make_buyer_policy():

    return PartyPolicy(
        price=PricePolicy(
            target=100,
            maximum=110,
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
            target=115,
            minimum=100,
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

def test_negotiation_reaches_agreement():

    engine = NegotiationEngine(
        buyer_policy=make_buyer_policy(),
        supplier_policy=make_supplier_policy(),
        buyer_agent=MockBuyerAgent(),
        supplier_agent=MockSupplierAgent(),
    )

    result = engine.run()

    assert result.status == "agreed"
    assert result.final_proposal is not None
    assert len(result.rounds) == 1

def test_llm_offer_is_projected_into_joint_feasible_zone():
    from negotiation.engine import NegotiationEngine
    from models.policy import PartyPolicy, PricePolicy, DeliveryPolicy, PaymentPolicy, SLAPolicy
    from models.proposal import NegotiationProposal, ProposalAction

    buyer = PartyPolicy(
        price=PricePolicy(target=105000, minimum=95000, maximum=115000),
        delivery=DeliveryPolicy(target_days=30, maximum_days=35),
        payment=PaymentPolicy(preferred_days=60, minimum_days=45),
        sla=SLAPolicy(minimum_uptime=98, minimum_penalty=2, maximum_penalty=5),
        batna='alt', max_rounds=10,
    )
    supplier = PartyPolicy(
        price=PricePolicy(target=120000, minimum=100000, maximum=130000),
        delivery=DeliveryPolicy(target_days=28, maximum_days=35),
        payment=PaymentPolicy(preferred_days=45, minimum_days=30),
        sla=SLAPolicy(minimum_uptime=97, minimum_penalty=0, maximum_penalty=3),
        batna='alt', max_rounds=10,
    )
    proposal = NegotiationProposal(
        round_number=3,
        price=118000,
        delivery_days=30,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.COUNTER,
    )
    engine = NegotiationEngine(buyer, supplier, None, None)
    projected = engine._project_to_joint_feasible_zone(proposal, 'supplier')
    assert projected.price == 115000
    assert projected.delivery_days == 30
    assert projected.payment_days == 45
    assert projected.sla_penalty == 3
    assert projected.sla_uptime == 98

def test_joint_feasible_supplier_offer_closes_after_negotiation_round():
    from negotiation.engine import NegotiationEngine
    from models.policy import PartyPolicy, PricePolicy, DeliveryPolicy, PaymentPolicy, SLAPolicy
    from models.proposal import NegotiationProposal, ProposalAction

    buyer = PartyPolicy(
        price=PricePolicy(target=105000, minimum=95000, maximum=115000),
        delivery=DeliveryPolicy(target_days=30, maximum_days=35),
        payment=PaymentPolicy(preferred_days=60, minimum_days=45),
        sla=SLAPolicy(minimum_uptime=98, minimum_penalty=2, maximum_penalty=5),
        batna='alt', max_rounds=10,
    )
    supplier = PartyPolicy(
        price=PricePolicy(target=120000, minimum=100000, maximum=130000),
        delivery=DeliveryPolicy(target_days=28, maximum_days=35),
        payment=PaymentPolicy(preferred_days=45, minimum_days=30),
        sla=SLAPolicy(minimum_uptime=97, minimum_penalty=0, maximum_penalty=3),
        batna='alt', max_rounds=10,
    )

    class Buyer:
        def generate_proposal(self, round_number, supplier_offer=None, negotiation_context='', revision_feedback=''):
            price = 105000 if round_number == 1 else 110000
            penalty = 5
            return NegotiationProposal(round_number=round_number, price=price, delivery_days=30, payment_days=60, sla_penalty=penalty, sla_uptime=98, action=ProposalAction.OFFER if round_number == 1 else ProposalAction.COUNTER)

    class Supplier:
        def generate_proposal(self, round_number, buyer_offer=None, negotiation_context='', revision_feedback=''):
            return NegotiationProposal(round_number=round_number, price=118000, delivery_days=30, payment_days=45, sla_penalty=3, sla_uptime=98, action=ProposalAction.COUNTER)

    result = NegotiationEngine(buyer, supplier, Buyer(), Supplier()).run()
    assert result.status == 'agreed'
    assert result.final_proposal is not None
    assert result.final_proposal.price == 115000
    assert result.final_proposal.payment_days == 45
    assert result.final_proposal.sla_penalty == 3
