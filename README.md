# Nexora — Autonomous B2B Procurement Agent

**Anakin Forge submission: Build AI Agents That Read, Reason, and Act**

**Deployment:** Render-ready; set the `LYZR_API_KEY` and publish the service to obtain the submission URL.

Nexora is an autonomous B2B procurement agent that turns a natural-language purchasing request into a bounded end-to-end workflow.

It is built around the Anakin Forge loop:

```text
READ → REASON → ACT → VERIFY
              ↖ RECOVER ↺
```

The agent can read procurement requirements and supplier web evidence, reason about the best procurement strategy, select and negotiate with suppliers through Lyzr agents, verify the resulting agreement, and recover from a failed attempt by reconsidering the remaining candidates.

> **AI provides adaptability. Deterministic software provides authority.**

---

## Why Nexora fits Anakin Forge

The goal of Nexora is not to build another chatbot that explains what a procurement team should do. The goal is to let an agent actually carry the workflow forward.

| Forge capability | Nexora implementation |
| --- | --- |
| **READ** | Reads the procurement request and supplier webpages through Anakin's live-web scraping API. |
| **REASON** | Uses a dedicated Lyzr reasoning agent plus deterministic reasoning to turn the request into constraints, risks, priorities, and strategy. |
| **ACT** | Selects a supplier and invokes bounded Buyer/Supplier Lyzr negotiation agents to perform the commercial negotiation. |
| **VERIFY** | Independently validates the negotiated result against policy, legal, agreement, and audit conditions. |
| **RECOVER** | On a failed attempt, uses the failure as new context, excludes the failed supplier, re-ranks remaining suppliers, and tries again within a configured limit. |

This gives Nexora a useful action-oriented loop instead of a single AI response.

---

## The problem

B2B procurement is usually fragmented across requirements, supplier websites, spreadsheets, emails, negotiation, approvals, and contract checks.

A conventional chatbot can summarize those steps, but it still leaves a human to execute them.

Nexora turns the process into one bounded agentic workflow:

```text
Natural-language request
        ↓
Read requirements + supplier evidence
        ↓
Reason about priorities, risks, and strategy
        ↓
Select the strongest candidate
        ↓
Negotiate through Buyer ↔ Supplier agents
        ↓
Verify the actual agreement
        ↓
Recover and try another supplier when needed
```

---

## What Nexora actually does

A request can include a product or service, quantity, delivery target, price expectations, payment terms, SLA requirements, compliance requirements, and supplier URLs.

Nexora then:

1. Structures the request into procurement facts and constraints.
2. Reads supplier web sources when supplied.
3. Identifies evidence conflicts and supplier risks.
4. Produces a procurement strategy with priorities and confidence.
5. Ranks supplier candidates.
6. Starts a bounded negotiation using isolated Buyer and Supplier agents.
7. Verifies the resulting agreement independently.
8. Generates a recovery path when an attempt fails.
9. Preserves the workflow and audit trail so the decision path can be inspected.

The result is a procurement action, not just a recommendation.

---

## The agent architecture

Nexora uses three Lyzr roles with different responsibilities.

### 1. Procurement Reasoning Agent

The reasoning agent interprets the procurement request before execution and during recovery.

It produces structured guidance such as:

- Hard constraints
- Soft preferences
- Risk signals
- Missing information
- Supplier evaluation factors
- Negotiation strategy
- Decision rationale
- Confidence

The reasoning agent is advisory. It does not own authoritative business state.

### 2. Buyer Agent

The Buyer Agent negotiates from the buyer organization's private policy envelope.

### 3. Supplier Agent

The Supplier Agent negotiates from the supplier organization's private policy envelope.

Buyer and Supplier contexts remain separated so that one party's private reservation information is not simply handed to the other party.

---

## End-to-end autonomous flow

```text
                         USER REQUEST
                              │
                              ▼
                            READ
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
        Procurement facts            Supplier web evidence
                 │                         │
                 └────────────┬────────────┘
                              ▼
                           REASON
                              │
                    Lyzr strategy proposal
                              │
                              ▼
                           SELECT
                              │
                    Supplier ranking / risk
                              │
                              ▼
                            ACT
                              │
                  Buyer Agent ↔ Supplier Agent
                              │
                              ▼
                           VERIFY
                         ┌────┴────┐
                         │         │
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

### READ

Nexora reads the natural-language procurement request and uses **Anakin's live URL Scraper API** for supplier webpages. Anakin returns clean page content that becomes evidence for supplier ranking and risk assessment. The procurement engine remains the authority over what is accepted.

The web evidence layer is useful because supplier claims can affect the decision. For example:

```text
Requirement: delivery <= 30 days
Supplier page: delivery = 45 days

→ Evidence conflict
→ Higher risk
→ Lower supplier ranking
```

### REASON

Nexora creates a deterministic baseline and can enrich it with the dedicated Lyzr Procurement Reasoning Agent.

The AI output is merged into the authoritative reasoning object rather than becoming the source of truth.

### ACT

Nexora selects a supplier and invokes the existing Buyer and Supplier Lyzr negotiation path. The negotiation engine remains bounded by application policy and guardrails.

### VERIFY

Nexora does not accept an agent's statement of success as proof. The application independently checks the resulting agreement.

```text
Agent says: SUCCESS
Application verifies: SUCCESS / FAIL
```

### RECOVER

A failed action does not trigger an unlimited retry loop.

```text
Attempt 1
   ↓
VERIFY → FAIL
   ↓
Record failure context
   ↓
Exclude failed supplier
   ↓
Re-rank remaining candidates
   ↓
Attempt 2
   ↓
VERIFY → PASS
```

The failure becomes new reasoning context. That is the key difference between recovery and blind retrying.

---

## Governance: agents can act, but they cannot bypass policy

Nexora deliberately separates AI recommendation from business authority.

```text
AI proposal
    ↓
Deterministic governance
    ↓
Allowed? ── No ──→ BLOCK
    │
   Yes
    ↓
Continue
```

A built-in governance demonstration makes this boundary visible:

```text
AI proposal      ₹130,000
Buyer maximum    ₹120,000

→ BLOCKED

Corrected proposal ₹120,000

→ ALLOWED
```

This means the Lyzr agent can reason and propose actions without becoming the sole authority over commercial state.

---

## Example procurement request

```text
We need 1000 industrial servo motors.
Delivery must be within 30 days.
Preferred payment terms are Net 60.
Minimum SLA uptime should be 98%.
Please select the strongest supplier and negotiate acceptable commercial terms.
```

A successful run can visibly show:

```text
READ
↓
AI REASONING
↓
SUPPLIER EVIDENCE
↓
SELECT
↓
NEGOTIATE
↓
VERIFY
```

And the recovery path can show:

```text
FAILED ATTEMPT
↓
REASON AGAIN
↓
NEW SUPPLIER
↓
VERIFY
↓
SUCCESS
```

---

## Why this is more than a chatbot

Nexora has an explicit action loop and application-owned state:

```text
Read information
      ↓
Reason across multiple signals
      ↓
Choose what to do
      ↓
Perform the action
      ↓
Check whether it actually worked
      ↓
Adapt when it did not
```

The AI is used where adaptation is valuable. Deterministic code owns the parts that must remain predictable: policies, guardrails, verification, attempt limits, and authoritative state.

---

## Tech stack

- **Anakin URL Scraper API** — live supplier-web evidence ingestion
- **Lyzr Agent API / Lyzr Studio** — Buyer, Supplier, and procurement reasoning agents
- **FastAPI / Python** — orchestration and API layer
- **Deterministic negotiation engine** — bounded commercial negotiation
- **Guardrails + governance** — policy, legal, and agreement validation
- **Audit + contract generation** — traceability and final agreement output
- **Frontend UI** — autonomous trace, reasoning, evidence, negotiation, verification, recovery, and governance views
- **Docker + Render** — deployment

---

## Repository structure

```text
.
├── agents/
│   ├── buyer_agent.py
│   ├── supplier_agent.py
│   ├── lyzr_bootstrap.py
│   ├── lyzr_client.py
│   ├── lyzr_sdk.py
│   └── lyzr/
│
├── backend/
│   ├── autonomous/
│   │   ├── read.py
│   │   ├── reason.py
│   │   ├── ai_reasoner.py
│   │   ├── evidence.py
│   │   ├── discover.py
│   │   ├── web_discover.py
│   │   ├── act.py
│   │   ├── verify.py
│   │   ├── recover.py
│   │   ├── run.py
│   │   └── procure.py
│   ├── negotiation/
│   ├── guardrails/
│   ├── governance/
│   ├── contract/
│   ├── audit/
│   ├── models/
│   └── main.py
│
├── frontend/
├── Dockerfile
├── render.yaml
├── setup.bat
├── run_backend.bat
├── test.bat
└── .env.example
```

---

## Run locally

### Windows

```bat
setup.bat
run_backend.bat
```

Or start FastAPI manually from the backend environment:

```bat
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

FastAPI's runtime documentation is available at `/docs`.

---

## Anakin configuration

The READ stage is Anakin-backed by default:

```env
ANAKIN_ENABLED=1
ANAKIN_API_KEY=
ANAKIN_BASE_URL=https://api.anakin.io/v1
ANAKIN_USE_BROWSER=0
ANAKIN_FALLBACK_DIRECT=1
```

`ANAKIN_API_KEY` is optional for read-only scraping. Nexora supports Anakin's zero-touch read path and can therefore run the hackathon demo without a paid plan. If a key is provided, the same endpoint is authenticated.

See [`ANAKIN_INTEGRATION.md`](ANAKIN_INTEGRATION.md) for the authority boundary and runtime behavior.

## Lyzr configuration

Create the required deployment environment variables from `.env.example`:

```env
LYZR_API_KEY=
BUYER_AGENT_ID=
SUPPLIER_AGENT_ID=
LYZR_REASONING_AGENT_ID=
LYZR_USER_ID=nexora-system
LYZR_BASE_URL=https://agent-prod.studio.lyzr.ai
```

Optional settings control SDK usage, AI reasoning, Responsible AI status reporting, agent feature verification, and external governance integration.

Never commit private API keys or deployment credentials.

---

## Testing

Run:

```bat
python -m pytest -q
```

or:

```bat
test.bat
```

The suite covers the autonomous workflow, negotiation engine, web evidence, governance, verification, recovery, contracts, audit behavior, and Lyzr integration surfaces.

---

## Documentation

- [`DEMO.md`](DEMO.md) — judge-facing demo runbook
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design and authority boundaries
- [`API_REFERENCE.md`](API_REFERENCE.md) — autonomous and platform API surface
- [`AGENT_CONFIGURATION.md`](AGENT_CONFIGURATION.md) — Lyzr agent roles and environment
- [`SECURITY_AND_GOVERNANCE.md`](SECURITY_AND_GOVERNANCE.md) — safety and governance model
- [`TESTING.md`](TESTING.md) — test and smoke-test guidance
- [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) — repository map

---

## The core idea

```text
AI proposes what should happen.

Nexora decides what is allowed.

Nexora acts.

Nexora verifies whether it worked.

Nexora recovers when it did not.
```

That is Nexora's implementation of **Read → Reason → Act** for a real business workflow.
