# Nexora API Reference

This document highlights the API surface behind the Anakin Forge agent loop. FastAPI's generated OpenAPI schema at runtime remains the authoritative source for exact request and response models.

## Autonomous agent endpoints

| Method | Endpoint | Forge stage | Purpose |
| --- | --- | --- | --- |
| POST | `/api/autonomous/read` | READ | Parse procurement text and source URLs. |
| POST | `/api/autonomous/reason` | REASON | Build structured procurement reasoning. |
| POST | `/api/autonomous/discover` | SELECT | Rank supplier candidates from structured data. |
| POST | `/api/autonomous/discover-web` | READ / SELECT | Read supplier web sources and rank candidates using evidence. |
| POST | `/api/autonomous/act` | ACT | Execute the bounded procurement action / negotiation. |
| POST | `/api/autonomous/verify` | VERIFY | Independently validate an action result. |
| POST | `/api/autonomous/run` | READ → VERIFY | Run the autonomous workflow. |
| POST | `/api/autonomous/run-with-selection` | READ → SELECT → VERIFY | Run the workflow with supplier selection. |
| POST | `/api/autonomous/recover` | RECOVER | Build and execute a bounded recovery path. |
| POST | `/api/autonomous/procure` | End-to-end | Run the bounded autonomous procurement loop. |
| POST | `/api/autonomous/governance-demo` | Governance | Demonstrate AI proposal versus deterministic governance. |

---

## Primary end-to-end endpoint

### `POST /api/autonomous/procure`

This is the main API surface for the full autonomous procurement workflow.

Example request shape:

```json
{
  "text": "We need 1000 industrial servo motors within 30 days. Preferred payment terms are Net 60. Minimum SLA uptime is 98%.",
  "sources": [
    "https://example.com/supplier"
  ],
  "suppliers": [],
  "buyer": {},
  "buyer_name": "Buyer Corp",
  "minimum_confidence": 0.5,
  "minimum_supplier_score": 0.5,
  "max_attempts": 3,
  "execution_mode": "auto"
}
```

The actual policy and supplier structures must match the Pydantic models in the running application.

A successful response can include workflow metadata, reasoning, supplier ranking, attempts, action output, verification output, recovery state, and the selected supplier.

---

## How the endpoint maps to the agent workflow

```text
POST /read
     ↓
POST /reason
     ↓
POST /discover or /discover-web
     ↓
POST /act
     ↓
POST /verify
     ↓
PASS → agreement
FAIL → /recover
```

The `/procure` endpoint packages the bounded autonomous loop into a single workflow call.

---

## Governance demonstration

### `POST /api/autonomous/governance-demo`

This endpoint demonstrates the authority boundary between an AI recommendation and deterministic governance.

The response contains the proposal, governance decision, corrected proposal where applicable, corrected governance decision, and explanation.

The intended demo story is:

```text
AI proposal
   ↓
Policy check
   ↓
BLOCKED
   ↓
Corrected proposal
   ↓
ALLOWED
```

---

## General application endpoints

The platform also exposes conventional negotiation, contract, audit, RFQ, system, and Lyzr status endpoints, including:

```text
GET  /health
GET  /api/architecture
GET  /api/agent/status
GET  /api/lyzr/status
POST /api/lyzr/bootstrap
POST /api/governance/lyzr-custom-guardrail
POST /api/negotiations
GET  /api/negotiations/{negotiation_id}/contract
GET  /api/negotiations/{negotiation_id}/audit
GET  /api/negotiations/{negotiation_id}/audit/verify
GET  /api/negotiations/{negotiation_id}/pdf
GET  /api/negotiations/{negotiation_id}/analytics
POST /api/stress-test
GET  /api/system/governance
POST /api/rfq
```

---

## Runtime API documentation

When the backend is running, FastAPI normally exposes:

```text
/docs
/redoc
/openapi.json
```

Use those routes for the exact deployed schema.
