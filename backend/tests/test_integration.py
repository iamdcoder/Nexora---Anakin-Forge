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
from audit.logger import AuditLogger

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

def test_complete_negotiation_with_audit(tmp_path):

    audit_path = tmp_path / "audit.jsonl"

    audit_logger = AuditLogger(
        path=str(audit_path)
    )

    engine = NegotiationEngine(
        buyer_policy=make_buyer_policy(),
        supplier_policy=make_supplier_policy(),
        buyer_agent=MockBuyerAgent(),
        supplier_agent=MockSupplierAgent(),
        audit_logger=audit_logger,
        negotiation_id="NEG-INTEGRATION",
        buyer_name="Buyer Corp",
        supplier_name="Supplier Corp",
    )

    result = engine.run()

    assert result.status == "agreed"
    assert result.final_proposal is not None

    assert len(result.rounds) == 1

    assert audit_path.exists()

    audit_text = audit_path.read_text(
        encoding="utf-8"
    )

    assert "negotiation_started" in audit_text
    assert "proposal_generated" in audit_text
    assert "agreement_reached" in audit_text