# Nexora + Anakin Integration

Nexora uses **Anakin's live-web URL Scraper API as the READ layer** of autonomous procurement.

## Runtime flow

```text
Supplier URLs
     │
     ▼
 Anakin URL Scraper
     │ clean live page content
     ▼
Nexora evidence normalization
     │
     ▼
Supplier ranking + risk analysis
     │
     ▼
Buyer ↔ Supplier negotiation (Lyzr)
     │
     ▼
Independent verification + recovery
```

Anakin is therefore not a decorative integration. Its output is consumed by the supplier-selection path. Nexora then owns the commercial authority: price ceilings, delivery limits, SLA guardrails, negotiation state, verification, contracts, and bounded recovery.

## Why this matters

A supplier can publish information on its live website that changes the procurement decision. Nexora reads that information before acting. This is the core “READ the web” capability required by Anakin Forge.

## Credentials

`ANAKIN_ENABLED=1` enables Anakin-backed reads.

`ANAKIN_API_KEY` is optional for read-only scraping because Anakin currently supports a zero-touch scrape endpoint. Providing a key upgrades the same endpoint to authenticated usage.

`ANAKIN_FALLBACK_DIRECT=1` keeps the application resilient if the Anakin service is temporarily unavailable. The workflow reports the provider used in its telemetry so a judge can see whether the live run was Anakin-backed.
