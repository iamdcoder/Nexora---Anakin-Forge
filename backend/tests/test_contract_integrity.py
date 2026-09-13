from contract.generator import contract_payload_hash, create_contract
from models.proposal import NegotiationProposal, ProposalAction

def test_contract_has_stable_hash():
    proposal = NegotiationProposal(
        round_number=1, price=110000, delivery_days=31, payment_days=60,
        sla_penalty=2, sla_uptime=98, action=ProposalAction.COUNTER,
    )
    contract = create_contract(proposal, "Buyer", "Supplier", "Motors", 10, "NEG-1", 3)
    first = contract_payload_hash(contract)
    contract.contract_hash = first
    second = contract_payload_hash(contract)
    assert first == second
    assert len(first) == 64
