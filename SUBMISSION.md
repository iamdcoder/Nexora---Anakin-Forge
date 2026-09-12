# Nexora — Anakin Forge Submission Package

## Project Title
Nexora — Autonomous B2B Procurement Agent

## Project Description
Nexora is an autonomous B2B procurement agent that turns a natural-language purchasing request into a bounded end-to-end workflow: READ supplier evidence, REASON about priorities and risks, SELECT a feasible supplier, ACT through Buyer ↔ Supplier Lyzr negotiation agents, VERIFY the real agreement, and RECOVER from failed attempts. Anakin provides the live web-reading layer; Lyzr provides the reasoning/negotiation agents; deterministic policy, legal, agreement, and verification layers remain authoritative.

## Where Anakin Is Used
Anakin is used in the READ stage through its live URL Scraper API. Supplier URLs are fetched through the Anakin client with bounded timeouts/retries and provenance tracking. Returned content is converted into structured procurement evidence covering product, delivery, payment, SLA, warranty, availability, and compliance-related signals. In the evidence-aware web discovery path, that evidence affects supplier ranking but cannot override hard procurement policy. The evidence layer detects contradictory claims within a page, and the tested multi-source reconciliation layer detects disagreements across separate supplier source pages so conflicting information is surfaced rather than silently trusted.

## Autonomous Loop
```text
READ → REASON → SELECT → ACT → VERIFY → RECOVER ↺
```

## Safety / Governance
- AI reasoning is advisory; deterministic policy remains authoritative.
- Buyer and Supplier Lyzr contexts remain separated.
- Hard budget, delivery, payment, and SLA failures produce an ineligible supplier.
- Prompt-injection-like supplier content is quarantined before AI reasoning.
- AI-suggested hard constraints cannot become executable policy.
- Verification is independent of the negotiation agent's claimed result.
- Recovery re-ranks remaining feasible suppliers rather than blindly retrying the same path.

## Validation
The final archive passes the complete automated suite:

**133 tests passed.**

The test suite includes Anakin decision-impact tests, hard-policy firewall tests, prompt-injection tests, AI-output-poisoning tests, recovery-integrity tests, evidence-conflict tests, API tests, deployment tests, negotiation tests, and the cross-source evidence reconciliation test.

## GitHub
https://github.com/Anakin-Inc/anakin

Project repository: **[INSERT YOUR NEXORA GITHUB URL]**

## Deployed Link
**[INSERT YOUR RENDER / DEPLOYMENT URL]**

## Demo Video
**[INSERT YOUR DEMO VIDEO URL]**

## Social Post
Tag **@anakinHQ** and describe the project as an autonomous procurement agent using Anakin for live supplier web reading.

## Recommended Demo
1. Submit a procurement request with explicit delivery, payment, price, and SLA requirements.
2. Show Anakin supplier-source evidence in the READ trace.
3. Show deterministic reasoning plus Lyzr strategy context.
4. Show supplier ranking and policy firewall.
5. Run Buyer ↔ Supplier negotiation.
6. Show independent VERIFY.
7. Trigger the controlled `recovery_once` demo fault and show automatic re-reasoning and supplier failover.
8. Show the final contract and audit trace.

## Final Status
Core engineering, safety hardening, adversarial validation, deployment configuration, and submission documentation are complete. The only submission fields that require external accounts/assets are the actual Nexora GitHub repository URL, deployed URL, demo-video URL, and social-post URL.
