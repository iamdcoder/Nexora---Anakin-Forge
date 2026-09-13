from pathlib import Path

from models.contract import B2BContract, SLAContract
from models.proposal import NegotiationProposal, ProposalAction
from contract.generator import create_contract, generate_contract_pdf

def make_proposal():

    return NegotiationProposal(
        round_number=6,
        price=52500,
        delivery_days=32,
        payment_days=45,
        sla_penalty=3,
        sla_uptime=98,
        action=ProposalAction.ACCEPT,
    )

def test_contract_is_created():

    proposal = make_proposal()

    contract = create_contract(
        final_proposal=proposal,
        buyer_name="Buyer Corp",
        supplier_name="Supplier Corp",
        product_name="Industrial Motor",
        quantity=500,
        negotiation_id="NEG-001",
        negotiation_rounds=6,
    )

    assert isinstance(contract, B2BContract)
    assert contract.status == "AGREED"
    assert contract.quantity == 500
    assert contract.unit_price == 52500
    assert contract.delivery_days == 32
    assert contract.payment_days == 45
    assert contract.sla.penalty_percent == 3
    assert contract.sla.minimum_uptime == 98

def test_contract_pdf_is_generated(tmp_path):

    proposal = make_proposal()

    contract = create_contract(
        final_proposal=proposal,
        buyer_name="Buyer Corp",
        supplier_name="Supplier Corp",
        product_name="Industrial Motor",
        quantity=500,
        negotiation_id="NEG-001",
        negotiation_rounds=6,
    )

    pdf_path = tmp_path / "contract.pdf"

    generate_contract_pdf(
        contract,
        str(pdf_path),
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0