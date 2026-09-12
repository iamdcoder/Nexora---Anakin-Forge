# Deployment Checklist

## Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the repository and use `render.yaml`.
3. Set `LYZR_API_KEY` to your existing Lyzr key.
4. Set `LYZR_REASONING_AGENT_ID` if the separate reasoning agent is configured; otherwise deterministic reasoning remains the safe fallback.
5. Leave `ANAKIN_API_KEY` empty for the zero-touch read-only Anakin path, or provide your Anakin key to use authenticated mode.
6. After the `/health` check is green, open the root URL.
7. Use that URL in the submission form as the Deployed Link.

## Submission smoke test

Run the main button once and confirm the decision trace shows:

`ANAKIN LIVE WEB` → `READ` → `REASON` → `SELECT` → `ACT` → `VERIFY`

The decision trace also reports the number of Anakin-backed sources read.
