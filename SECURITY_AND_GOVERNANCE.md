# Security and Governance — Nexora

Nexora is intentionally designed so that agent autonomy does not mean unrestricted authority.

> **The agent can propose and act within bounds. The application decides what is allowed and verifies what happened.**

## 1. Policy isolation

Buyer and Supplier agents operate from separate policy envelopes.

Private commercial information such as reservation limits and BATNA data must not cross the buyer/supplier boundary.

---

## 2. Deterministic governance

The governance path is:

```text
AI / agent proposal
        ↓
Policy validation
        ↓
Legal validation
        ↓
Agreement validation
        ↓
Governance result
```

A rejected proposal does not become authoritative state.

This is the core safeguard that lets Nexora remain agentic without making an LLM the final business authority.

---

## 3. AI reasoning safety

The Procurement Reasoning Agent is advisory.

Its structured output is treated as reasoning input and merged with the deterministic baseline.

When supported by the runtime configuration, an unavailable reasoning-agent call can fall back to deterministic reasoning instead of stopping the whole workflow.

The AI does not directly write authoritative negotiation state or contracts.

---

## 4. Web evidence safety

Supplier webpages are external input.

Their content is treated as evidence and evaluated against procurement requirements. A webpage can change a candidate's risk or ranking; it cannot directly rewrite internal policy.

This also reduces the impact of prompt-injection-style content embedded in a supplier page.

```text
Supplier page
    ↓
Read as external evidence
    ↓
Compare against requirements
    ↓
Risk / ranking signal

NOT:

Supplier page
    ↓
Rewrite buyer policy
```

---

## 5. Recovery safety

Recovery is bounded by the procurement request's configured attempt limit.

A failed supplier is excluded from the next candidate set, and the failure is passed into the next reasoning step.

The system should not relax hard constraints merely because an earlier candidate failed.

---

## 6. Independent verification

Verification happens after action.

The application therefore distinguishes between:

```text
Agent reports success
        ≠
Application verifies success
```

A proposal or response that does not satisfy the validation criteria is not treated as an accepted result merely because the agent said it succeeded.

---

## 7. Auditability

The audit subsystem records workflow events and supports integrity verification through the existing hash-linked audit mechanism.

This gives the procurement run a traceable decision history rather than only a final conversational answer.

---

## 8. Secrets

Use environment variables or deployment secret stores for:

- Lyzr API keys
- Governance tokens
- LLM credential IDs where applicable
- Deployment credentials
- Other private credentials

Never commit private credentials to source control.

---

## 9. Operational model

The intended runtime model is:

```text
READ external information
        ↓
REASON with AI + deterministic baseline
        ↓
ACT through bounded tools / agents
        ↓
VERIFY independently
        ↓
RECOVER when needed
```

This separation is what makes the system both autonomous and governable.
