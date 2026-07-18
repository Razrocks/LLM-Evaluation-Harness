# Phase 10 (M10) — Dashboard & Operational Hardening

**Status:** ⬜ Planned. Not started. Begins only when report + API contracts are stable.

## Goal

Give the platform a read/review surface — run history, comparisons, failure drill-down, RAG and
agent outcomes, cost/latency, regression history — **without** letting the browser become
authoritative for anything.

## The one hard rule

> The dashboard **never computes canonical metrics and never enforces gates.** It displays
> server-produced results and supports review actions with explicit authority and audit records.

Every number on screen traces back to a metric the harness computed and stored; every chart is a
view of `metric_summary.json`, not a re-derivation.

## Deliverables

- **Next.js** + **React** + **TypeScript**; **shadcn/ui** primitives; **TanStack Table** for
  large result/failure tables; **Recharts** for metric/latency/cost/regression charts; **Sentry**
  for frontend errors.
- Typed API clients matching the canonical API schemas (generated or checked against them).
- Pages: Eval Runs · Model/Configuration Comparison · Failed Cases (with raw evidence) · RAG
  Metrics · Agent/Tool-Use Outcomes · Classifier Results · Cost & Latency · Regression History ·
  Dataset/Corpus Versions · Baselines & Gates.
- Server-side authorization, pagination, redaction, observability; **Docker Compose** for the full
  local stack; realistic seeded demo data.

## Exit criteria

Dashboard reads canonical API contracts; the browser computes no canonical metric; role
permissions + audit semantics are enforced server-side; every aggregate links to underlying
evidence; all major features remain usable without an external target application.

## New dependencies

Node/Next.js frontend stack (separate `web/` app); Sentry. No change to the Python domain
contracts.
