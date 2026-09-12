# Nexora Lyzr Agent Configuration

Nexora uses Lyzr agents at the parts of the workflow where agentic reasoning and negotiation are most useful.

```text
READ
  ↓
REASON → Lyzr Procurement Reasoning Agent
  ↓
SELECT
  ↓
ACT → Lyzr Buyer Agent ↔ Lyzr Supplier Agent
  ↓
VERIFY
```

## Agent roles

### Procurement Reasoning Agent

Environment variable:

```env
LYZR_REASONING_AGENT_ID=<reasoning-agent-id>
```

Responsibilities:

- interpret procurement requirements
- separate hard constraints from soft preferences
- identify risks and missing information
- recommend a negotiation strategy
- explain the decision rationale
- provide a confidence score
- reconsider strategy when recovery context is supplied

It is advisory and must not approve contracts, override deterministic policy, reveal private reservation values, invent supplier facts, or directly mutate authoritative negotiation state.

### Buyer Agent

Environment variable:

```env
BUYER_AGENT_ID=<buyer-agent-id>
```

The Buyer Agent negotiates from the buyer organization's private policy envelope.

### Supplier Agent

Environment variable:

```env
SUPPLIER_AGENT_ID=<supplier-agent-id>
```

The Supplier Agent negotiates from the supplier organization's private policy envelope.

---

## Recommended reasoning-agent behavior

A suitable system instruction is:

```text
You are Nexora's procurement reasoning agent.

Interpret procurement requests and turn them into a structured procurement strategy.

You are advisory. You do not approve contracts, negotiate directly, reveal private reservation information, invent supplier facts, or override deterministic governance.

Identify hard constraints, soft preferences, risks, missing information, supplier evaluation factors, recommended negotiation strategy, confidence, and decision rationale.

When recovery context is supplied, account for the previous failure without relaxing hard constraints merely to obtain a deal.

Return valid JSON only.
```

---

## Environment

```env
LYZR_API_KEY=<private-api-key>
BUYER_AGENT_ID=<buyer-agent-id>
SUPPLIER_AGENT_ID=<supplier-agent-id>
LYZR_REASONING_AGENT_ID=<reasoning-agent-id>
LYZR_USER_ID=nexora-system
LYZR_BASE_URL=https://agent-prod.studio.lyzr.ai
LYZR_AI_REASONING_ENABLED=1
LYZR_USE_SDK=1
LYZR_SDK_FALLBACK=1
LYZR_RESPONSIBLE_AI_ENABLED=1
LYZR_VERIFY_AGENT_FEATURES=1
```

Optional variables can configure external governance, model/provider bootstrap, CORS, and deployment base URLs.

### Environment reference

| Variable | Purpose |
| --- | --- |
| `LYZR_API_KEY` | Private key used to authenticate Lyzr calls. |
| `BUYER_AGENT_ID` | Buyer negotiation agent. |
| `SUPPLIER_AGENT_ID` | Supplier negotiation agent. |
| `LYZR_REASONING_AGENT_ID` | Procurement reasoning agent. |
| `LYZR_USER_ID` | User identifier sent to Lyzr. |
| `LYZR_BASE_URL` | Lyzr API base URL. |
| `LYZR_USE_SDK` | Prefer the Lyzr SDK client when enabled. |
| `LYZR_SDK_FALLBACK` | Fall back to the HTTP client when needed. |
| `LYZR_AI_REASONING_ENABLED` | Enables the dedicated reasoning-agent call. |
| `LYZR_RESPONSIBLE_AI_ENABLED` | Enables Responsible AI status reporting used by the platform. |
| `LYZR_VERIFY_AGENT_FEATURES` | Verifies configured Buyer/Supplier agent capabilities before use. |
| `LYZR_GUARDRAIL_URL` | Optional external governance / guardrail URL. |
| `LYZR_GUARDRAIL_TOKEN` | Token for the external governance service. |
| `LYZR_GOVERNANCE_TIMEOUT` | Timeout for external governance calls. |
| `LYZR_RAI_POLICY_ID` | Optional Responsible AI policy identifier. |
| `LYZR_PROVIDER_ID` | Optional provider identifier for bootstrap flows. |
| `LYZR_MODEL` | Optional model name for bootstrap flows. |
| `LYZR_LLM_CREDENTIAL_ID` | Optional LLM credential identifier. |
| `CORS_ORIGINS` | Allowed CORS origins. |
| `PUBLIC_BASE_URL` | Optional public deployment URL. |

---

## Policy isolation

Buyer and Supplier policies must remain separate.

The Buyer Agent should not receive the Supplier Agent's private minimums, BATNA, or reservation information.

The Supplier Agent should not receive the Buyer's private maximums, BATNA, or reservation information.

The Procurement Reasoning Agent should receive only the policy information necessary for procurement reasoning.

This separation lets Nexora use multiple agents without collapsing their incentives and private information into one context.

---

## Deployment guidance

Store secrets in deployment secret stores or environment variables.

Agent IDs are configuration values, while API keys and governance tokens are secrets.

Do not commit private credentials to the repository.
