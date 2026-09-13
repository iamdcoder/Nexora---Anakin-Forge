# Backend Architecture

The backend implements the Anakin Forge agent loop as explicit orchestration stages.

```text
API
 ↓
READ
 ↓
REASON
 ↓
DISCOVER / SELECT
 ↓
ACT
 ↓
VERIFY
 ↓
RECOVER (when needed)
 ↓
Contract + Audit
```

## Autonomous orchestration

`backend/autonomous/` coordinates:

```text
READ
REASON
DISCOVER / SELECT
ACT
VERIFY
RECOVER
```

The purpose of this package is orchestration. It does not replace the core negotiation mechanics.

## READ

`read.py` handles procurement intake and source reading.

`web_discover.py` supports supplier web-source discovery / reading where configured.

## REASON

`reason.py` builds the deterministic procurement reasoning baseline.

`ai_reasoner.py` integrates the dedicated Lyzr Procurement Reasoning Agent when enabled.

The AI reasoning result is advisory and does not replace application-owned policy.

## SELECT

`discover.py` ranks supplier candidates, while evidence-related modules provide external supplier signals that can affect ranking.

## ACT

`act.py` invokes the action / negotiation path.

The autonomous layer calls the existing `backend/negotiation` engine instead of implementing a second negotiation algorithm.

## VERIFY

`verify.py` independently checks the resulting agreement or action output.

The verification stage is intentionally separated from the agent response so that “agent said success” does not equal “business state is accepted.”

## RECOVER

`recover.py` handles bounded failure recovery.

A failed supplier becomes failure context, is excluded from the next candidate set, and remaining candidates can be re-ranked for another attempt.

## Negotiation engine

`backend/negotiation/engine.py` and supporting modules manage proposal exchange, convergence, deadlock, utility, risk, and negotiation state.

## Guardrails and governance

`backend/guardrails/` contains deterministic policy, legal, and agreement validation.

`backend/governance/` manages governance configuration and optional external governance behavior.

## Audit and contracts

`backend/audit/` stores audit events and supports integrity verification.

`backend/contract/` generates contract representations and PDF output where supported.

## Application entrypoint

`backend/main.py` creates the FastAPI application, registers autonomous and conventional negotiation routes, configures CORS, and serves the frontend.
