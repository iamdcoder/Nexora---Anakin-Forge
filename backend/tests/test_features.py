from pathlib import Path

from audit.logger import AuditLogger
from audit.models import AuditEventType
from models.policy import PartyPolicy
from models.proposal import NegotiationProposal, ProposalAction
from negotiation.pareto import build_pareto_frontier
from negotiation.risk import calculate_risk
from negotiation.utility import calculate_utility

def policy_buyer():
    return PartyPolicy(
        price={"target": 100, "maximum": 120},
        delivery={"target_days": 30, "maximum_days": 45},
        payment={"preferred_days": 60, "minimum_days": 30},
        sla={"minimum_uptime": 98, "minimum_penalty": 1, "maximum_penalty": 5},
        batna="backup",
        max_rounds=6,
    )

def policy_supplier():
    return PartyPolicy(
        price={"target": 110, "minimum": 95},
        delivery={"target_days": 35, "maximum_days": 50},
        payment={"preferred_days": 30, "minimum_days": 15},
        sla={"minimum_uptime": 97, "minimum_penalty": 1, "maximum_penalty": 5},
        batna="other buyer",
        max_rounds=6,
    )

def proposal(price):
    return NegotiationProposal(
        round_number=1,
        price=price,
        delivery_days=32,
        payment_days=45,
        sla_penalty=2,
        sla_uptime=99,
        action=ProposalAction.COUNTER,
    )

def test_utility_and_risk_are_bounded():
    buyer = policy_buyer()
    supplier = policy_supplier()
    p = proposal(105)
    u = calculate_utility(p, buyer, "buyer")
    assert 0 <= u.total <= 1
    risk = calculate_risk(p, buyer, supplier)
    assert risk["hard_limit_hits"] == 0
    assert risk["label"] in {"LOW", "MEDIUM", "HIGH"}

def test_pareto_marks_nondominated_points():
    points = build_pareto_frontier([proposal(98), proposal(105), proposal(115)], policy_buyer(), policy_supplier())
    assert any(p.pareto_efficient for p in points)
    assert len(points) == 3

def test_audit_hash_chain_verifies(tmp_path: Path):
    logger = AuditLogger(str(tmp_path / "audit.jsonl"))
    logger.log("NEG-1", AuditEventType.NEGOTIATION_STARTED, "engine", "started", {"x": 1})
    logger.log("NEG-1", AuditEventType.POLICY_CHECK, "guardrail", "allowed", {"x": 2})
    verification = logger.verify()
    assert verification["valid"] is True
    assert verification["events"] == 2

def test_risk_distinguishes_policy_compliance_from_commercial_exposure():
    buyer = policy_buyer()
    supplier = policy_supplier()
    p = NegotiationProposal(
        round_number=1,
        price=105,
        delivery_days=32,
        payment_days=45,
        sla_penalty=2,
        sla_uptime=99,
        action=ProposalAction.COUNTER,
    )
    risk = calculate_risk(p, buyer, supplier)
    assert risk["hard_limit_hits"] == 0
    assert risk["policy_compliance"] == 100.0
    assert "Commercial exposure" in risk["interpretation"]
