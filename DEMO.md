# Nexora Demo Runbook — Anakin Forge

## Demo goal

Show one thing clearly: Nexora is an agent that can **read information, reason about it, take action, and verify the result**.

The cleanest story is:

```text
READ → REASON → SELECT → ACT → VERIFY
                         ↖ RECOVER ↺
```

Keep the demo focused on the autonomous procurement workflow. Use the governance and recovery demonstrations as proof that the autonomy is bounded and reliable.

---

## 1. Start the application

For a local run:

```bat
setup.bat
run_backend.bat
```

Or use the deployed demo:

<YOUR_RENDER_URL>

Make sure the Lyzr configuration is available before presenting the agent behavior.

---

## 2. Use this request

```text
We need 1000 industrial servo motors.
Delivery must be within 30 days.
Preferred payment terms are Net 60.
Minimum SLA uptime should be 98%.
Please select the strongest supplier and negotiate acceptable commercial terms.
```

This is intentionally simple enough to understand instantly while exercising the full workflow.

---

## 3. Walk the judge through READ

Start autonomous procurement.

Point out that Nexora first turns the natural-language request into structured procurement information and can read supplier web sources when they are provided.

Use this framing:

> The agent is not starting from a fixed answer. It first reads the request and, when available, external supplier evidence.

A useful evidence example is:

```text
Requirement: delivery <= 30 days
Supplier evidence: delivery = 45 days

→ conflict detected
→ risk increases
→ candidate ranking changes
```

---

## 4. Walk through REASON

Show the reasoning output.

Highlight:

- hard constraints
- soft preferences
- risks
- missing information
- strategy
- decision rationale
- confidence

Use this line:

> The Lyzr reasoning agent turns the procurement request into an actionable strategy, but the application still owns the authoritative policy and state.

---

## 5. Walk through SELECT

Show the supplier ranking.

Explain that Nexora combines procurement requirements with supplier evidence and compatibility signals before selecting the next candidate.

The key point is that the agent does not simply choose the first supplier mentioned. It uses the information it has read to make a decision.

---

## 6. Walk through ACT

Show the negotiation stage.

Use this line:

> Now the agent acts. Nexora invokes the Buyer and Supplier Lyzr agents to negotiate commercial terms inside their respective policy boundaries.

The underlying negotiation engine remains deterministic and bounded; Lyzr agents provide the agentic interaction.

---

## 7. Walk through VERIFY

When negotiation completes, pause before calling it a success.

Use this line:

> An agent saying “done” is not enough. Nexora independently verifies the resulting agreement before treating the run as successful.

Visually:

```text
Agent output
    ↓
Verification
    ↓
PASS / FAIL
```

---

## 8. Demonstrate RECOVER

Use a scenario where the first candidate fails verification or execution.

Show:

```text
Attempt 1
   ↓
FAIL
   ↓
Failure becomes new context
   ↓
Failed supplier excluded
   ↓
Remaining suppliers re-ranked
   ↓
Attempt 2
   ↓
VERIFY
   ↓
SUCCESS
```

Say:

> This is recovery, not blind retrying. The failure changes the next decision.

---

## 9. Demonstrate governance

Open the AI-vs-governance demonstration.

Show:

```text
AI proposal      ₹130,000
Buyer maximum    ₹120,000

→ BLOCKED

Corrected proposal ₹120,000

→ ALLOWED
```

Say:

> The agent can propose an action, but it cannot promote its own proposal into authoritative business state. Nexora's deterministic governance decides what is allowed.

---

## 10. Closing statement

> Nexora is an autonomous procurement agent rather than a chatbot. It reads the request and supplier evidence, reasons about the best strategy, takes action through Lyzr negotiation agents, verifies the result independently, and can recover from failure within bounded business rules.

---

## Judge-facing checklist

```text
[ ] Live demo is reachable
[ ] Lyzr API key is configured
[ ] Buyer Agent ID is configured
[ ] Supplier Agent ID is configured
[ ] Reasoning Agent ID is configured
[ ] READ is visible
[ ] Supplier web evidence is visible
[ ] REASONING is visible
[ ] Supplier selection is visible
[ ] ACT / negotiation is visible
[ ] VERIFY is visible
[ ] Recovery scenario is ready
[ ] Governance demo blocks invalid AI output
[ ] Audit verification is available
```
