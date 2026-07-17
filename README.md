# AI Evaluation & Reliability Platform (`ai-eval`)

A **standalone** quality-control, benchmarking, and regression-testing harness for AI
workflows. It answers — with reproducible, evidence-backed proof — whether a specific
AI workflow configuration produces contract-valid output, extracts the right facts,
detects missing information, avoids unsupported claims, and **did not regress against an
approved baseline**.

> Mental model: a test harness, evidence ledger, benchmark laboratory, scoreboard, and
> release gate for AI systems. It ships with its own reference workloads and runs from a
> clean checkout **without any API credentials**.

## Status

🚧 Under active construction, built in ordered milestones. **Current: Milestone 0 —
specification lock.** See [`docs/implementation-status.md`](docs/implementation-status.md)
for exactly what is implemented versus planned. Nothing below the "Roadmap" line is built
yet, and this README will not claim otherwise.

### First checkpoint (Milestones 0–4) — in progress

The first vertical slice evaluates a platform-owned **Structured Request Triage**
workflow (`reference.request_triage.v1`): messy request text + supporting documents →
strict JSON (summary, tasks, deadline, risk, missing information, attention, evidence
references). It runs entirely offline against deterministic recorded targets, scores
with versioned deterministic scorers, compares against an approved baseline, and enforces
a deterministic regression gate that catches intentionally seeded regressions.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

## Setup

```bash
uv sync            # create venv + install core and dev dependencies
```

## Roadmap (not yet built)

Milestones 5–10 widen the same contracts to multi-provider comparison + CI, persistence /
API / workers, RAG + Qdrant, governed tool-use evaluation, ML baselines + optional
fine-tuning, and a dashboard. Details in [`docs/roadmap/`](docs/roadmap/).

## License

MIT — see [LICENSE](LICENSE).
