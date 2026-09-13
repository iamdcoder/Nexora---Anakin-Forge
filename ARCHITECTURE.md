# Nexora Architecture — Read, Reason, Act, Verify

## Design objective

Nexora is designed as an autonomous agent workflow for B2B procurement.

The architectural goal is to give AI enough responsibility to interpret information and drive a useful workflow, while keeping business authority in deterministic application components.

```text
READ → REASON → SELECT → ACT → VERIFY
                         ↖ RECOVER ↺
```

This separation is central to the system: Lyzr agents can propose and negotiate, while application-owned policy, guardrails, verification, and state determine what is actually accepted.

---

## System topology

```text
                              USER / RFQ
                                  │
                                  ▼
                                READ
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
              Procurement facts          Supplier web evidence
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                               REASON
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
              Deterministic baseline      Lyzr Reasoning Agent
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                               SELECT
                                  │
                         Supplier ranking
                                  │
                                  ▼
                                 ACT
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
               Buyer Agent               Supplier Agent
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                         Negotiation Engine
                                  │
                                  ▼
                               VERIFY
                             ┌────┴────┐
                             ▼         ▼
                           PASS      FAIL
                             │         │
                             ▼         ▼
                         AGREEMENT   RECOVER
                                         │
                                         ▼
                                    REASON AGAIN
                                         │
                                         └──────↺
```

---

## Layer responsibilities

### 1. Lyzr agent layer

`agents/` provides the Lyzr integration surface and Buyer/Supplier agent wrappers.

The application keeps agent roles distinct and sends role-specific context rather than collapsing the whole workflow into one shared model conversation.

### 2. Autonomous layer

`backend/autonomous/` implements the agentic workflow:

```text
READ
REASON
DISCOVER / SELECT
ACT
VERIFY
RECOVER
```

The autonomous layer is the workflow orchestrator. It does not replace the underlying negotiation implementation.

### 3. Negotiation layer

`backend/negotiation/` owns proposal exchange, convergence, deadlock, utility, risk, and negotiation state.

The autonomous layer calls this existing engine as its action mechanism.

### 4. Guardrail layer

`backend/guardrails/` contains deterministic checks for policy, legal, and agreement conditions.

These checks are authoritative over the AI output.

### 5. Governance layer

`backend/governance/` manages governance configuration and optional external governance integration.

### 6. Contract and audit layers

`backend/contract/` generates agreement representations and PDF output where supported.

`backend/audit/` records workflow events and supports integrity verification.

---

## The authority boundary

The most important design decision is that the Lyzr agent is not the source of truth.

```text
Lyzr reasoning / proposal
          ↓
Deterministic validation
          ↓
     ┌────┴────┐
     │         │
   BLOCK      ALLOW
     │         │
     ▼         ▼
    STOP     ACT
               ↓
            VERIFY
```

This allows agentic behavior without turning a language-model response into an unconditional business decision.

---

## Web reading and evidence

The READ stage can work with supplier source URLs.

The supplier page is treated as **external evidence**, not as trusted instructions. Evidence is extracted and compared with procurement requirements.

For example:

```text
Buyer requirement: delivery <= 30 days
Supplier claim:    delivery = 45 days

Result:
- evidence conflict
- elevated risk
- weaker candidate ranking
```

This is important for an agentic system because external content can be both useful information and untrusted input.

---

## Recovery architecture

Recovery is explicitly bounded.

```text
Action / verification failure
            ↓
      Record failure
            ↓
     Add failure context
            ↓
 Exclude failed supplier
            ↓
 Re-rank remaining candidates
            ↓
      Next bounded attempt
```

The attempt limit comes from the procurement request. Recovery therefore adapts the workflow without creating an uncontrolled retry loop.

---

## Failure handling

The architecture uses graceful fallback for non-authoritative AI components where supported.

For example, the reasoning stage can use a deterministic baseline when the dedicated Lyzr reasoning call is unavailable.

By contrast, governance and verification are not replaced by an optimistic AI response. Their role is to remain authoritative over acceptance of the outcome.

---

## Data flow

```text
Request
  ↓
READ result
  ↓
Reasoning object
  ↓
Supplier ranking
  ↓
Action / negotiation
  ↓
Verification result
  ↓
Agreement OR recovery
```

Intermediate results and recovery history are retained so the frontend can present the decision path.

---

## Security boundaries

Buyer and Supplier policies remain isolated.

The Buyer Agent should not receive supplier private reservation values, and the Supplier Agent should not receive buyer private reservation values.

Supplier webpages are treated as untrusted external content and cannot directly rewrite internal policy.

Credentials are supplied through environment variables rather than source code.

---

## Frontend boundary

`frontend/index.html` is the primary deployed interface and presents the autonomous trace, reasoning, supplier evidence, selection, negotiation, verification, recovery, governance, and audit state.

The other JSX files are standalone reference components and are not imported by `index.html`.

The frontend presents decisions and evidence. The backend remains responsible for authoritative state and validation.
