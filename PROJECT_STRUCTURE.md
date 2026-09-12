# Nexora Project Structure

The repository is organized around the autonomous agent loop rather than around a chatbot UI.

```text
Nexora-Autonomous-B2B-Negotiation/
├── agents/
├── backend/
├── frontend/
├── data/
├── .dockerignore
├── .env.example
├── Dockerfile
├── render.yaml
├── setup.bat
├── run_backend.bat
├── test.bat
├── README.md
├── ARCHITECTURE.md
├── AGENT_CONFIGURATION.md
├── API_REFERENCE.md
├── SECURITY_AND_GOVERNANCE.md
├── DEMO.md
├── TESTING.md
└── PROJECT_STRUCTURE.md
```

## `agents/`

Lyzr integration surface.

```text
agents/
├── buyer_agent.py
├── supplier_agent.py
├── lyzr_bootstrap.py
├── lyzr_client.py
├── lyzr_sdk.py
└── lyzr/
```

The three agent roles are:

```text
Procurement Reasoning Agent
Buyer Agent
Supplier Agent
```

## `backend/autonomous/`

The core Anakin Forge workflow:

```text
READ
REASON
DISCOVER / SELECT
ACT
VERIFY
RECOVER
```

Key modules:

```text
read.py
reason.py
ai_reasoner.py
evidence.py
discover.py
web_discover.py
act.py
verify.py
recover.py
run.py
run_selection.py
procure.py
governance_demo.py
```

## `backend/negotiation/`

The underlying commercial negotiation engine and calculations:

```text
convergence.py
deadlock.py
engine.py
pareto.py
risk.py
state.py
strategy.py
utility.py
```

The autonomous layer orchestrates this engine rather than duplicating it.

## `backend/guardrails/`

Deterministic validation for:

- policy constraints
- legal constraints
- agreement consistency
- combined guardrail decisions

## `backend/governance/`

Governance configuration and optional external governance integration.

## `backend/contract/`

Contract generation and PDF support.

## `backend/audit/`

Audit models, event logging, and integrity verification.

## `backend/models/`

Shared typed models for policies, proposals, contracts, and validation.

## `backend/tests/`

Unit and integration coverage for the autonomous workflow, negotiation, governance, audit, contract generation, Lyzr integration, web evidence, and deployment behavior.

## `frontend/`

The primary deployed interface is `index.html`. It presents:

- autonomous workflow state
- AI reasoning
- supplier evidence
- supplier ranking
- negotiation progress
- verification
- recovery history
- governance demonstration
- audit results

The standalone `.jsx` files in this directory are reference components and are not imported by `index.html`.
