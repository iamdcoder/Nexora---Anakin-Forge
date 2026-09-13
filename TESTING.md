# Nexora Testing Guide

## Purpose

Testing covers both sides of the system:

1. the deterministic business engine that owns authority, and
2. the autonomous agent workflow that reads, reasons, acts, verifies, and recovers.

## Run the full suite

From the repository root:

```bat
python -m pytest -q
```

Or:

```bat
test.bat
```

---

## Test coverage

### READ

Validates procurement intake parsing and source handling.

### REASON

Validates structured AI-reasoning parsing, confidence handling, fallback behavior, and merging with deterministic reasoning.

### Supplier selection

Validates supplier compatibility, ranking, and policy-aware selection.

### Web evidence

Validates supplier claim extraction and conflict detection against procurement requirements.

### ACT

Validates action creation and invocation of the negotiation path.

### VERIFY

Validates independent agreement and result checks.

### RECOVER

Validates bounded recovery behavior, including failure context, failed-supplier exclusion, and selection of remaining candidates.

### Governance

Validates that out-of-policy proposals are blocked and compliant corrections are accepted.

### Negotiation

Validates convergence, deadlock handling, utilities, risk, and state transitions.

### Contract and audit

Validates contract generation, audit events, and audit integrity behavior.

### Lyzr integration

Validates the integration surfaces and configuration behavior without requiring secrets to be committed to source control.

---

## What the tests are proving

The important end-to-end invariant is:

```text
READ
 ↓
REASON
 ↓
SELECT
 ↓
ACT
 ↓
VERIFY
 ↓
PASS / RECOVER
```

The suite is not only checking isolated functions; it also covers the boundaries between the autonomous layer and the deterministic business engine.

---

## Manual smoke test

After the backend starts:

```text
1. Open the frontend.
2. Run autonomous procurement.
3. Confirm READ completes.
4. Confirm supplier evidence is processed when sources are supplied.
5. Confirm reasoning appears when Lyzr reasoning is enabled.
6. Confirm suppliers are ranked.
7. Confirm ACT invokes the negotiation path.
8. Confirm VERIFY completes independently.
9. Confirm the final result is marked verified.
10. Run the governance demonstration.
11. Run a recovery scenario.
12. Check audit verification.
```

Automated tests can mock external Lyzr or web dependencies. A live deployment should therefore also be smoke-tested with the real Lyzr configuration.
