import json
import os
import uuid
from pathlib import Path
import sys
from typing import Literal
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from agents.buyer_agent import BuyerAgent
from agents.supplier_agent import SupplierAgent
from governance.environment import AgentEnvironment
from agents.lyzr_bootstrap import list_agents as lyzr_list_agents, bootstrap_agents
from governance.lyzr_governance import LyzrGovernance

from audit.logger import AuditLogger
from audit.models import AuditEventType

from guardrails.guardrail_engine import GuardrailEngine

from contract.generator import (
    create_contract,
    contract_to_json,
    generate_contract_pdf,
    contract_payload_hash,
)

from models.policy import PartyPolicy
from models.proposal import (
    NegotiationProposal,
    ProposalAction,
)

from negotiation.engine import NegotiationEngine
from negotiation.utility import calculate_utility, explain_tradeoff
from negotiation.pareto import build_pareto_frontier
from negotiation.risk import calculate_risk
from autonomous.read import router as autonomous_read_router
from autonomous.reason import router as autonomous_reason_router
from autonomous.act import router as autonomous_act_router
from autonomous.verify import router as autonomous_verify_router
from autonomous.web_discover import (
    router as autonomous_web_discover_router
)
from autonomous.discover import (
    router as autonomous_discover_router
)
from autonomous.run import (
    router as autonomous_run_router
)
from autonomous.run_selection import (
    router as autonomous_selection_router
)
from autonomous.recover import (
    router as autonomous_recovery_router
)
from autonomous.procure import (
    router as autonomous_procure_router
)
from autonomous.governance_demo import (
    router as autonomous_governance_demo_router
)
app = FastAPI(
    title="Autonomous B2B Negotiator",
    version="3.2.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = PROJECT_ROOT / "frontend" / "index.html"

_cors_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(autonomous_read_router)
app.include_router(autonomous_reason_router)
app.include_router(autonomous_act_router)
app.include_router(autonomous_verify_router)
app.include_router(autonomous_run_router)
app.include_router(autonomous_discover_router)
app.include_router(autonomous_selection_router)
app.include_router(
    autonomous_web_discover_router
)
app.include_router(
    autonomous_recovery_router
)
app.include_router(
    autonomous_procure_router
)
app.include_router(
    autonomous_governance_demo_router
)
_store: dict[str, dict] = {}

class NegotiationRequest(BaseModel):
    buyer: PartyPolicy
    supplier: PartyPolicy

    buyer_name: str = "Buyer Corp"
    supplier_name: str = "Supplier Corp"

    product_name: str = (
        "Industrial Components"
    )

    quantity: int = 1000

    execution_mode: Literal[
        "auto",
        "simulation",
        "lyzr",
    ] = "auto"

class RFQRequest(BaseModel):
    buyer: PartyPolicy
    buyer_name: str = "Buyer Corp"
    product_name: str = "Industrial Components"
    quantity: int = 1000
    suppliers: list[dict]

                                                              

class SimulationBuyerAgent:

    def __init__(
        self,
        policy: PartyPolicy,
    ):
        self.policy = policy

    def generate_proposal(
        self,
        round_number: int,
        supplier_offer: NegotiationProposal | None,
        negotiation_context: str = "",
        revision_feedback: str = "",
    ) -> NegotiationProposal:

        target = self.policy.price.target

        maximum = (
            self.policy.price.maximum
            or target
        )

        if supplier_offer is None:

            price = target

        else:

            price = min(
                maximum,
                max(
                    target,
                    supplier_offer.price
                    - (
                        maximum - target
                    ) * 0.25,
                ),
            )

        return NegotiationProposal(
            round_number=round_number,

            price=round(
                price,
                2,
            ),

            delivery_days=min(
                self.policy.delivery.maximum_days,
                (
                    self.policy.delivery.target_days
                    + min(
                        round_number - 1,
                        4,
                    )
                ),
            ),

            payment_days=(
                self.policy.payment.preferred_days
            ),

            sla_penalty=(
                self.policy.sla.minimum_penalty
            ),

            sla_uptime=(
                self.policy.sla.minimum_uptime
            ),

            action=ProposalAction.COUNTER,

            rationale=(
                "Simulation buyer proposal."
            ),
        )

class SimulationSupplierAgent:

    def __init__(
        self,
        policy: PartyPolicy,
    ):
        self.policy = policy

    def generate_proposal(
        self,
        round_number: int,
        buyer_offer: NegotiationProposal,
        negotiation_context: str = "",
        revision_feedback: str = "",
    ) -> NegotiationProposal:

        minimum = (
            self.policy.price.minimum
            or self.policy.price.target
        )

        target = self.policy.price.target

                                
        if (
            buyer_offer.price >= minimum
            and
            buyer_offer.delivery_days
            <= self.policy.delivery.maximum_days
            and
            buyer_offer.payment_days
            >= self.policy.payment.minimum_days
            and
            buyer_offer.sla_penalty
            <= self.policy.sla.maximum_penalty
            and
            buyer_offer.sla_uptime
            >= self.policy.sla.minimum_uptime
        ):

            return NegotiationProposal(
                round_number=round_number,

                price=buyer_offer.price,

                delivery_days=(
                    buyer_offer.delivery_days
                ),

                payment_days=(
                    buyer_offer.payment_days
                ),

                sla_penalty=(
                    buyer_offer.sla_penalty
                ),

                sla_uptime=(
                    buyer_offer.sla_uptime
                ),

                action=ProposalAction.ACCEPT,

                accepted_offer="buyer",

                rationale=(
                    "Buyer package satisfies "
                    "supplier constraints."
                ),
            )

                                              
        pressure = min(
            round_number / 10,
            1.0,
        )

        price = max(
            minimum,
            target
            - (
                target - minimum
            ) * pressure,
        )

        return NegotiationProposal(
            round_number=round_number,

            price=round(
                price,
                2,
            ),

            delivery_days=min(
                buyer_offer.delivery_days,
                self.policy.delivery.maximum_days,
            ),

            payment_days=max(
                self.policy.payment.minimum_days,
                min(
                    buyer_offer.payment_days,
                    self.policy.payment.preferred_days,
                ),
            ),

            sla_penalty=min(
                buyer_offer.sla_penalty,
                self.policy.sla.maximum_penalty,
            ),

            sla_uptime=max(
                buyer_offer.sla_uptime,
                self.policy.sla.minimum_uptime,
            ),

            action=ProposalAction.COUNTER,

            rationale=(
                "Simulation supplier "
                "counter-offer."
            ),
        )

                                                              

def _round_analytics(result_rounds, buyer_policy, supplier_policy):
    analytics = []
    previous_buyer = None
    previous_supplier = None

    for item in result_rounds:
        buyer = item["buyer"]
        supplier = item["supplier"]
        if isinstance(buyer, dict):
            buyer = _proposal_from_payload(buyer)
        if isinstance(supplier, dict):
            supplier = _proposal_from_payload(supplier)
        buyer_u = calculate_utility(buyer, buyer_policy, "buyer")
        supplier_u = calculate_utility(supplier, supplier_policy, "supplier")
        tradeoff = None
        if previous_buyer is not None:
            tradeoff = {
                "buyer": explain_tradeoff(previous_buyer, buyer, "buyer", buyer_policy),
                "supplier": explain_tradeoff(previous_supplier, supplier, "supplier", supplier_policy),
            }
        risk = calculate_risk(supplier, buyer_policy, supplier_policy)
        analytics.append({
            "round": item["round"],
            "buyer_utility": buyer_u.total,
            "supplier_utility": supplier_u.total,
            "joint_utility": round((buyer_u.total + supplier_u.total) / 2, 4),
            "buyer_components": buyer_u.components,
            "supplier_components": supplier_u.components,
            "buyer_risk": buyer_u.risk_score,
            "supplier_risk": supplier_u.risk_score,
            "risk": risk,
            "tradeoff": tradeoff,
        })
        previous_buyer = buyer
        previous_supplier = supplier

    return analytics

def _proposal_from_payload(payload: dict) -> NegotiationProposal:
    return NegotiationProposal.model_validate({
        "round_number": int(payload.get("round_number", 1)),
        "price": float(payload["price"]),
        "delivery_days": int(payload["delivery_days"]),
        "payment_days": int(payload["payment_days"]),
        "sla_penalty": float(payload["sla_penalty"]),
        "sla_uptime": float(payload["sla_uptime"]),
        "action": payload.get("action", "counter"),
        "accepted_offer": payload.get("accepted_offer"),
        "rationale": payload.get("rationale"),
    })

                                                              


@app.get("/api/architecture")
def architecture_status():
    buyer_id = os.getenv("BUYER_AGENT_ID", "").strip()
    supplier_id = os.getenv("SUPPLIER_AGENT_ID", "").strip()
    return {
        "layers": [
            {"name": "Environment", "status": "active", "detail": "Private buyer/supplier session boundaries and redacted shared context"},
            {"name": "Agent", "status": "configured" if buyer_id and supplier_id else "missing", "detail": "Two independent Lyzr Studio agents"},
            {"name": "Inference", "status": "configured" if os.getenv("LYZR_API_KEY") else "missing", "detail": "Lyzr ADK agent.run with documented Agent API fallback"},
            {"name": "Governance", "status": "active", "detail": "Lyzr RAI when configured plus deterministic policy/legal firewall"},
            {"name": "Contract", "status": "active", "detail": "Agreement firewall is the only contract authority"},
            {"name": "Audit", "status": "active", "detail": "Hash-linked local audit record"},
        ],
        "separation_ok": bool(buyer_id and supplier_id),
        "sdk_preferred": os.getenv("LYZR_USE_SDK", "1") == "1",
        "agent_ids": {"buyer": buyer_id, "supplier": supplier_id},
    }

@app.get("/api/agent/status")
def agent_status():
    buyer_id = os.getenv("BUYER_AGENT_ID", "").strip()
    supplier_id = os.getenv("SUPPLIER_AGENT_ID", "").strip()
    key_ready = bool(os.getenv("LYZR_API_KEY", "").strip())
    sdk_installed = False
    sdk_error = None
    if key_ready:
        try:
            import lyzr  
            sdk_installed = True
        except Exception as exc:
            sdk_error = str(exc)
    return {
        "api": {"configured": key_ready, "base_url": os.getenv("LYZR_BASE_URL", "https://agent-prod.studio.lyzr.ai")},
        "sdk": {"installed": sdk_installed, "preferred": os.getenv("LYZR_USE_SDK", "1") == "1", "fallback_enabled": os.getenv("LYZR_SDK_FALLBACK", "1") == "1", "error": sdk_error},
        "agents": {"buyer_id": buyer_id, "supplier_id": supplier_id, "both_configured": bool(buyer_id and supplier_id)},
        "security": {"api_key_exposed": False, "private_reservation_values_exposed": False},
    }

@app.get("/api/lyzr/status")
def lyzr_status():
    """Report live Lyzr configuration without exposing the API key."""
    configured = bool(os.getenv("LYZR_API_KEY"))
    buyer_id = os.getenv("BUYER_AGENT_ID", "").strip()
    supplier_id = os.getenv("SUPPLIER_AGENT_ID", "").strip()
    result = {
        "api_key_configured": configured,
        "buyer_agent_configured": bool(buyer_id),
        "supplier_agent_configured": bool(supplier_id),
        "live_mode_ready": configured and bool(buyer_id) and bool(supplier_id),
        "responsible_ai": {
            "custom_guardrail_endpoint": "/api/governance/lyzr-custom-guardrail",
            "policy_id_configured": bool(os.getenv("LYZR_RAI_POLICY_ID")),
            "studio_assignment_claim": bool(os.getenv("LYZR_RESPONSIBLE_AI_ENABLED")),
            "agent_feature_check_enabled": os.getenv("LYZR_VERIFY_AGENT_FEATURES", "1") == "1",
        },
    }
    if configured:
        try:
            agents = lyzr_list_agents()
            result["agent_count"] = len(agents)
            result["agents"] = [
                {
                    "id": a.get("id") or a.get("agent_id"),
                    "name": a.get("name"),
                }
                for a in agents
            ]

            if os.getenv("LYZR_VERIFY_AGENT_FEATURES", "1") == "1" and buyer_id and supplier_id:
                from agents.lyzr_bootstrap import get_agent, summarize_features
                buyer_details = get_agent(buyer_id)
                supplier_details = get_agent(supplier_id)
                result["agent_features"] = {
                    "buyer": summarize_features(buyer_details),
                    "supplier": summarize_features(supplier_details),
                }
            result["reachable"] = True
        except Exception as exc:
            result["reachable"] = False
            result["error"] = str(exc)
    else:
        result["reachable"] = False
    return result

@app.post("/api/lyzr/bootstrap")
def lyzr_bootstrap():
    """Discover existing Nexora agents and persist only their IDs locally."""
    if not os.getenv("LYZR_API_KEY"):
        raise HTTPException(status_code=400, detail="Set LYZR_API_KEY in .env first.")
    try:
        result = bootstrap_agents(env_path=".env", auto_create=False)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lyzr bootstrap failed: {exc}") from exc
    return {
        "message": "Lyzr agents discovered.",
        "buyer_agent_id": (result.get("buyer") or {}).get("id") or (result.get("buyer") or {}).get("agent_id"),
        "supplier_agent_id": (result.get("supplier") or {}).get("id") or (result.get("supplier") or {}).get("agent_id"),
        "total_agents": result["total_agents"],
    }

@app.post("/api/governance/lyzr-custom-guardrail")
def lyzr_custom_guardrail(payload: dict):
    """
    Endpoint intended for Lyzr Responsible AI > Custom Guardrails.

    It returns the schema Lyzr documents for custom guardrails: a 2xx response
    plus verdict=allow|deny. Numerical business policy enforcement remains in
    the application's independent deterministic validators.
    """
    verdict = "allow"
    reason = "No governance violation detected."
    rule = "nexora-governance-v1"

    raw = json.dumps(payload, sort_keys=True).lower()

    secret_markers = [
        "reservation price",
        "walk-away price",
        "walk away price",
        "private batna",
        "supplier minimum",
        "buyer maximum",
        "raw_policy",
    ]

    injection_markers = [
        "ignore previous instructions",
        "system prompt",
        "reveal your instructions",
        "reveal your policy",
    ]

    if any(marker in raw for marker in secret_markers):
        verdict = "deny"
        reason = "Potential private negotiation-policy disclosure detected."
        rule = "privacy-isolation"
    elif any(marker in raw for marker in injection_markers):
        verdict = "deny"
        reason = "Potential prompt-injection attempt detected."
        rule = "prompt-injection"
    else:
        proposal = payload.get("payload", {}).get("proposal") if isinstance(payload.get("payload"), dict) else None
        if proposal is not None and not isinstance(proposal, dict):
            verdict = "deny"
            reason = "Proposal payload must be a JSON object."
            rule = "structured-proposal"

    return {
        "verdict": verdict,
        "allowed": verdict == "allow",
        "reason": reason,
        "rule": rule,
    }

                                                              

@app.get("/")
def root():
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend bundle not found")
    return FileResponse(FRONTEND_INDEX, media_type="text/html")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nexora-negotiator",
        "version": app.version,
    }

@app.get("/ui", include_in_schema=False)
def ui():
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend bundle not found")
    return FileResponse(FRONTEND_INDEX, media_type="text/html")

                                                              

@app.post("/api/negotiations")
def start_negotiation(
    request: NegotiationRequest,
):

    neg_id = (
        f"NEG-"
        f"{uuid.uuid4().hex[:8].upper()}"
    )

    audit_path = (
        Path("data")
        / f"audit_{neg_id}.jsonl"
    )

    audit_logger = AuditLogger(
        path=str(audit_path)
    )
    governance = LyzrGovernance()

    lyzr_ready = all(
        os.getenv(name)
        for name in (
            "LYZR_API_KEY",
            "BUYER_AGENT_ID",
            "SUPPLIER_AGENT_ID",
        )
    )

                    

    if request.execution_mode == "lyzr":

        if not lyzr_ready:

            raise HTTPException(
                status_code=503,
                detail=(
                    "Lyzr execution was requested, "
                    "but LYZR_API_KEY, BUYER_AGENT_ID, "
                    "or SUPPLIER_AGENT_ID is missing."
                ),
            )

        buyer_environment = AgentEnvironment(
            actor="buyer",
            private_policy=request.buyer,
            session_id=f"{neg_id}-buyer",
            shared_context={
                "negotiation_id": neg_id
            },
        )

        supplier_environment = AgentEnvironment(
            actor="supplier",
            private_policy=request.supplier,
            session_id=f"{neg_id}-supplier",
            shared_context={
                "negotiation_id": neg_id
            },
        )

        buyer_agent = BuyerAgent(
            policy=request.buyer,
            agent_id=os.environ[
                "BUYER_AGENT_ID"
            ],
            user_id=os.getenv(
                "LYZR_USER_ID",
                "buyer-system",
            ),
            session_id=(
                f"{neg_id}-buyer"
            ),
            environment=buyer_environment,
        )

        supplier_agent = SupplierAgent(
            policy=request.supplier,
            agent_id=os.environ[
                "SUPPLIER_AGENT_ID"
            ],
            user_id=os.getenv(
                "LYZR_USER_ID",
                "supplier-system",
            ),
            session_id=(
                f"{neg_id}-supplier"
            ),
            environment=supplier_environment,
        )

        mode = "lyzr"

    elif request.execution_mode == "simulation":

        buyer_agent = (
            SimulationBuyerAgent(
                request.buyer
            )
        )

        supplier_agent = (
            SimulationSupplierAgent(
                request.supplier
            )
        )

        mode = "simulation"

    else:

        if lyzr_ready:

            buyer_environment = AgentEnvironment(
                actor="buyer",
                private_policy=request.buyer,
                session_id=f"{neg_id}-buyer",
                shared_context={
                    "negotiation_id": neg_id
                },
            )

            supplier_environment = AgentEnvironment(
                actor="supplier",
                private_policy=request.supplier,
                session_id=f"{neg_id}-supplier",
                shared_context={
                    "negotiation_id": neg_id
                },
            )

            buyer_agent = BuyerAgent(
                policy=request.buyer,
                agent_id=os.environ[
                    "BUYER_AGENT_ID"
                ],
                user_id=os.getenv(
                    "LYZR_USER_ID",
                    "buyer-system",
                ),
                session_id=(
                    f"{neg_id}-buyer"
                ),
                environment=buyer_environment,
            )

            supplier_agent = SupplierAgent(
                policy=request.supplier,
                agent_id=os.environ[
                    "SUPPLIER_AGENT_ID"
                ],
                user_id=os.getenv(
                    "LYZR_USER_ID",
                    "supplier-system",
                ),
                session_id=(
                    f"{neg_id}-supplier"
                ),
                environment=supplier_environment,
            )

            mode = "lyzr"

        else:

            buyer_agent = (
                SimulationBuyerAgent(
                    request.buyer
                )
            )

            supplier_agent = (
                SimulationSupplierAgent(
                    request.supplier
                )
            )

            mode = "simulation"

    engine = NegotiationEngine(
        buyer_policy=request.buyer,
        supplier_policy=request.supplier,

        buyer_agent=buyer_agent,
        supplier_agent=supplier_agent,

        audit_logger=audit_logger,

        negotiation_id=neg_id,

        buyer_name=request.buyer_name,
        supplier_name=request.supplier_name,
        governance=governance,
    )

                

    try:

        result = engine.run()

    except Exception as exc:

        audit_logger.log(
            negotiation_id=neg_id,

            event_type=(
                AuditEventType.DEADLOCK
            ),

            actor="api",

            status="error",

            details={
                "error": str(exc),
                "error_type": (
                    type(exc).__name__
                ),
                "mode": mode,
            },
        )

        raise HTTPException(
            status_code=(
                502
                if mode == "lyzr"
                else 500
            ),

            detail={
                "message": (
                    "Negotiation execution failed."
                ),
                "error": str(exc),
                "mode": mode,
            },
        ) from exc

              

    contract_data = None
    pdf_path = None

    if (
        result.status == "agreed"
        and result.final_proposal
    ):

        contract = create_contract(
            final_proposal=(
                result.final_proposal
            ),

            buyer_name=(
                request.buyer_name
            ),

            supplier_name=(
                request.supplier_name
            ),

            product_name=(
                request.product_name
            ),

            quantity=request.quantity,

            negotiation_id=neg_id,

            negotiation_rounds=(
                len(result.rounds)
            ),
        )

        contract.contract_hash = contract_payload_hash(contract)
        contract_data = json.loads(
            contract_to_json(contract)
        )

        pdf_file = (
            Path("data")
            / f"contract_{neg_id}.pdf"
        )

        try:

            generate_contract_pdf(
                contract,
                str(pdf_file),
            )

            pdf_path = str(
                pdf_file
            )

        except Exception as exc:

            audit_logger.log(
                negotiation_id=neg_id,
                event_type=(
                    AuditEventType
                    .CONTRACT_GENERATED
                ),
                actor="contract_generator",
                status="error",
                details={
                    "error": str(exc)
                },
            )

        if pdf_path:

            audit_logger.log(
                negotiation_id=neg_id,

                event_type=(
                    AuditEventType
                    .CONTRACT_GENERATED
                ),

                actor="contract_generator",

                status="success",

                details={
                    "contract_id": (
                        contract.contract_id
                    ),

                    "pdf_path": pdf_path,
                },
            )

                  

    _store[neg_id] = {
        "contract": contract_data,
        "audit_path": str(audit_path),
        "pdf_path": pdf_path,
    }

                   

    rounds_out = []

    for item in result.rounds:

        buyer_p = item["buyer"]
        supplier_p = item["supplier"]

        round_output = {
            "round": item["round"],

            "buyer": (
                buyer_p.model_dump()
            ),

            "supplier": (
                supplier_p.model_dump()
            ),

            "gap": item["gap"],
        }

        if "metrics" in item:
            round_output["metrics"] = (
                item["metrics"]
            )

        rounds_out.append(
            round_output
        )

    convergence = {
        "initial_gap": engine.state.initial_gap,
        "latest_gap": engine.state.latest_gap,
        "gap_reduction": engine.state.gap_reduction,
        "convergence_ratio": engine.state.convergence_ratio,
    }

    analytics = _round_analytics(
        rounds_out, request.buyer, request.supplier
    )
    if neg_id in _store:
        _store[neg_id]["analytics"] = {
            "rounds": analytics,
            "convergence": convergence,
        }

    final_risk = (
        calculate_risk(
            result.final_proposal,
            request.buyer,
            request.supplier,
        )
        if result.final_proposal
        else {"label": "UNKNOWN", "score": 100, "hard_limit_hits": 0}
    )

    pareto_candidates = []
    if result.final_proposal:
        candidates = [
            item["buyer"] if item["buyer"].action.value != "accept" else item["supplier"]
            for item in result.rounds
        ]
        pareto_candidates = [
            {
                "index": p.index,
                "buyer_utility": p.buyer_utility,
                "supplier_utility": p.supplier_utility,
                "joint_utility": p.joint_utility,
                "pareto_efficient": p.pareto_efficient,
                "proposal": p.proposal.model_dump(),
            }
            for p in build_pareto_frontier(
                candidates, request.buyer, request.supplier
            )
        ]

    return {
        "negotiation_id": neg_id,

        "status": result.status,

        "reason": result.reason,

        "final_proposal": (
            result.final_proposal.model_dump()
            if result.final_proposal
            else None
        ),

        "contract": contract_data,

        "rounds": rounds_out,

        "convergence": convergence,
        "analytics": analytics,
        "final_risk": final_risk,
        "pareto": pareto_candidates,
        "policy_integrity": {
            "buyer_private": True,
            "supplier_private": True,
            "cross_party_reservation_exposure": False,
        },
        "audit_integrity": AuditLogger(path=str(audit_path)).verify(),

        "mode": mode,
        "governance": {
            "mode": governance.mode,
            "external_responsible_ai_configured": bool(governance.guardrail_url),
            "local_audit_fallback": True,
            "lyzr_sdk_preferred": os.getenv("LYZR_USE_SDK", "1") == "1",
            "lyzr_agent_api_fallback": True,
            "environment_separation": True,
        },
    }

                                                              

@app.get(
    "/api/negotiations/{negotiation_id}/contract"
)
def get_contract(
    negotiation_id: str,
):

    entry = _store.get(
        negotiation_id
    )

    if not entry:

        raise HTTPException(
            status_code=404,
            detail="Negotiation not found",
        )

    if not entry["contract"]:

        raise HTTPException(
            status_code=404,
            detail=(
                "No contract — negotiation "
                "did not reach agreement"
            ),
        )

    return entry["contract"]

                                                              

@app.get(
    "/api/negotiations/{negotiation_id}/audit"
)
def get_audit(
    negotiation_id: str,
):

    entry = _store.get(
        negotiation_id
    )

    if not entry:

        raise HTTPException(
            status_code=404,
            detail="Negotiation not found",
        )

    audit_file = Path(
        entry["audit_path"]
    )

    if not audit_file.exists():

        return {
            "negotiation_id": (
                negotiation_id
            ),
            "events": [],
        }

    events = []

    for line in audit_file.read_text(
        encoding="utf-8"
    ).splitlines():

        if line.strip():

            events.append(
                json.loads(line)
            )

    return {
        "negotiation_id": (
            negotiation_id
        ),
        "events": events,
    }

                 

@app.get("/api/negotiations/{negotiation_id}/audit/verify")
def verify_audit(negotiation_id: str):
    entry = _store.get(negotiation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    logger = AuditLogger(path=entry["audit_path"])
    result = logger.verify()
    return {"negotiation_id": negotiation_id, **result}

@app.get("/api/negotiations/{negotiation_id}/pdf")
def get_contract_pdf(negotiation_id: str):
    from fastapi.responses import FileResponse
    entry = _store.get(negotiation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    pdf_path = entry.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail="Contract PDF not available")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{negotiation_id}-contract.pdf")

@app.get("/api/negotiations/{negotiation_id}/analytics")
def get_analytics(negotiation_id: str):
    entry = _store.get(negotiation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return entry.get("analytics", {})

@app.post("/api/stress-test")
def stress_test(request: NegotiationRequest):
    samples = [
        {"name": "buyer_over_budget", "price": (request.buyer.price.maximum or request.buyer.price.target) * 1.25},
        {"name": "supplier_below_floor", "price": (request.supplier.price.minimum or request.supplier.price.target) * 0.75},
        {"name": "delivery_violation", "delivery_days": request.buyer.delivery.maximum_days + 10},
        {"name": "payment_violation", "payment_days": max(1, request.buyer.payment.minimum_days - 1)},
        {"name": "sla_penalty_violation", "sla_penalty": request.buyer.sla.maximum_penalty + 3},
        {"name": "uptime_violation", "sla_uptime": max(0, request.buyer.sla.minimum_uptime - 5)},
    ]
    baseline = {
        "round_number": 1,
        "price": request.buyer.price.target,
        "delivery_days": request.buyer.delivery.target_days,
        "payment_days": request.buyer.payment.preferred_days,
        "sla_penalty": request.buyer.sla.minimum_penalty,
        "sla_uptime": request.buyer.sla.minimum_uptime,
        "action": "counter",
    }
    results = []
    for sample in samples:
        payload = {**baseline, **sample}
        proposal = _proposal_from_payload(payload)
        validations = {
            "buyer": GuardrailEngine.validate(proposal, request.buyer, "buyer").model_dump(mode="json"),
            "supplier": GuardrailEngine.validate(proposal, request.supplier, "supplier").model_dump(mode="json"),
        }
        blocked = any(v["status"] == "blocked" for v in validations.values())
        results.append({"name": sample["name"], "blocked": blocked, "validations": validations})
    blocked_count = sum(1 for r in results if r["blocked"])
    return {
        "total": len(results),
        "blocked": blocked_count,
        "pass_rate": round(blocked_count / len(results), 3) if results else 1.0,
        "results": results,
    }

@app.get("/api/system/governance")
def governance_status():
    governance = LyzrGovernance()
    outbox = governance.outbox_status()
    return {
        "mode": governance.mode,
        "responsible_ai_configured": bool(governance.guardrail_url),
        "local_fallback": {
            "enabled": True,
            "checks": [
                "private-policy leakage",
                "prompt injection",
                "proposal schema",
                "numeric sanity",
            ],
            "failure_mode": "fail_closed",
        },
        "policy_authority": "deterministic_local_validator",
        "external_gate_failure_mode": "fail_closed" if governance.guardrail_url else "not_configured",
    }

@app.post("/api/rfq")
def run_rfq(request: RFQRequest):
    """Run a lightweight buyer-vs-many-suppliers RFQ in simulation mode."""
    if not request.suppliers:
        raise HTTPException(status_code=400, detail="At least one supplier is required")
    results = []
    for index, raw_supplier in enumerate(request.suppliers, start=1):
        supplier_policy = PartyPolicy.model_validate(raw_supplier["policy"])
        buyer_agent = SimulationBuyerAgent(request.buyer)
        supplier_agent = SimulationSupplierAgent(supplier_policy)
        neg_id = f"RFQ-{uuid.uuid4().hex[:8].upper()}"
        logger = AuditLogger(path=str(Path("data") / f"audit_{neg_id}.jsonl"))
        engine = NegotiationEngine(
            buyer_policy=request.buyer,
            supplier_policy=supplier_policy,
            buyer_agent=buyer_agent,
            supplier_agent=supplier_agent,
            audit_logger=logger,
            negotiation_id=neg_id,
            buyer_name=request.buyer_name,
            supplier_name=raw_supplier.get("name", f"Supplier {index}"),
        )
        result = engine.run()
        final = result.final_proposal
        score = None
        if final:
            bu = calculate_utility(final, request.buyer, "buyer").total
            su = calculate_utility(final, supplier_policy, "supplier").total
            score = {"buyer_utility": bu, "supplier_utility": su, "joint_utility": round((bu+su)/2, 4)}
        results.append({
            "supplier": raw_supplier.get("name", f"Supplier {index}"),
            "status": result.status,
            "reason": result.reason,
            "rounds": len(result.rounds),
            "final_proposal": final.model_dump() if final else None,
            "score": score,
        })
    ranked = sorted(results, key=lambda x: (x["score"] or {"joint_utility": 0})["joint_utility"], reverse=True)
    return {"buyer": request.buyer_name, "results": ranked, "winner": ranked[0] if ranked else None}
