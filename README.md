# AI Evaluation & Reliability Platform (`ai-eval`)

A standalone quality-control, benchmarking, and regression-testing harness for AI workflows. It
measures whether a given workflow configuration produces contract-valid output, extracts the
correct facts, detects missing information, avoids unsupported claims, and regresses against an
approved baseline. Results are reproducible and every score resolves to source evidence.

The repository ships with its own reference workload, dataset, targets, scorers, and gate, and
runs from a clean checkout with no API credentials.

## Quickstart

```bash
uv sync
uv run ai-eval demo
```

`ai-eval demo` executes five steps offline and exits non-zero if any gate outcome differs from
the expected result:

```
1. Validate the frozen dataset release        -> 12 approved cases valid
2. Run the approved BASELINE configuration    -> GATE: PASS
3. Approve that run as the baseline           -> explicit human decision
4. Run a DEGRADED candidate                   -> GATE: FAIL
       schema_pass_rate           = 1.0   <- STILL VALID JSON
       missing_information_recall = 0.0   <- REGRESSED
       [FAIL] no_critical_case_failures: critical-case failures=5 > 0
       [FAIL] missing_information_recall_floor: 0.0 < 0.85
       [FAIL] missing_information_recall_no_regression: delta=-1.0000 < -0.03

       One failing case, with evidence:
         case      : request_triage_001
         assertion : missing_information (scorer set_precision_recall_f1.v1)
         expected  : ['amount_or_scope_breakdown']
         observed  : []
         codes     : ['MISSING_INFO_OMITTED']
5. Run the CORRECTED configuration            -> GATE: PASS
```

The degraded configuration returns schema-valid JSON, so a parse check accepts it. The gate
rejects it because `missing_information_recall` falls to 0.0, and reports the failing cases,
assertions, failure codes, and source evidence. Exit code is 1. No model is called and the run
is deterministic.

## Status

**Milestones 0–4 complete. Milestone 5 (provider adapters + CI) is code-complete, with no live
model call or CI run executed yet.** 168 tests pass; `ruff` and `mypy --strict` are clean.

[`docs/implementation-status.md`](docs/implementation-status.md) is the authoritative record of
what is implemented, what is partially implemented, and what has not been started. Read it before
relying on any capability listed below.

The first vertical slice evaluates a platform-owned **Structured Request Triage** workflow
(`reference.request_triage.v1`): messy request text + supporting documents → strict JSON
(summary, tasks, deadline, risk, missing information, attention, evidence references).

## What's implemented

| Capability | Where |
|---|---|
| Versioned eval cases, dataset release + content hashing | `datasets/`, `src/ai_eval/datasets/` |
| Provider-neutral target adapter + 5 recorded fixtures | `src/ai_eval/targets/` |
| Immutable run manifest, raw capture **before** parsing | `src/ai_eval/execution/`, `artifacts/` |
| Strict parser (empty / malformed / schema-invalid kept distinct) | `src/ai_eval/parsing/` |
| 11 deterministic scorers + versioned deadline normalizer | `src/ai_eval/scoring/` |
| Evidence resolution + grounding checks | `src/ai_eval/evidence/` |
| Metrics with explicit denominators (scikit-learn for macro-F1) | `src/ai_eval/metrics/` |
| Failure taxonomy + inventory | `src/ai_eval/failures/` |
| JSONL / JSON / CSV / Markdown reports (reproducible) | `src/ai_eval/reporting/` |
| Baseline approval + candidate comparison | `src/ai_eval/baselines/` |
| Deterministic gate: PASS / FAIL / INVALID + exit codes | `src/ai_eval/gates/` |
| CLI + offline regression demo | `src/ai_eval/cli/`, `src/ai_eval/demo.py` |
| Versioned, content-addressed prompt registry | `prompts/`, `src/ai_eval/prompts/` |
| Provider adapters — Claude, ChatGPT, Gemini, local HuggingFace *(contract-tested against a fake client; no live API call executed)* | `src/ai_eval/targets/providers/` |
| Versioned price tables; cost reported only when computable | `src/ai_eval/pricing/` |
| Repeated-trial variance (library-only, not on the CLI) | `src/ai_eval/trials.py` |
| CI workflows *(committed; not yet run)* | `.github/workflows/` |

## Commands

```bash
uv run ai-eval dataset validate --dataset datasets/reference/request_triage/v1
uv run ai-eval run   --plan configs/plans/reference_request_triage_baseline.json \
                     --gate configs/gates/reference_request_triage_v1.json
uv run ai-eval compare --candidate runs/<run_id> --baseline <baseline.json>
uv run ai-eval gate  --run runs/<run_id> --policy configs/gates/reference_request_triage_v1.json
uv run ai-eval demo
```

**Exit codes** (relied on by CI): `0` PASS · `1` FAIL · `2` INVALID. `INVALID` means the run
could not be judged (a required metric was absent or a supplied baseline was incompatible) — it
is never treated as a pass.

## Run artifacts

```
runs/<run_id>/
  run_manifest.json        # every reference resolved to an immutable version + hash
  raw/<case>.json          # raw target output, captured BEFORE parsing
  traces.jsonl             # ordered execution events
  case_executions.jsonl    # per-case state, latency, usage
  parsed_outputs.jsonl     assertion_results.jsonl     failures.jsonl
  metric_summary.json      metric_summary.csv          failure_report.md
  comparison_report.md     gate_result.json            # when a baseline / gate is supplied
```

## Requirements

Python 3.12+ and [uv](https://docs.astral.sh/uv/). Nothing else — no database, no vector store,
no API keys.

## Verify

```bash
uv run pytest -q        # 168 passed
uv run ruff check .
uv run mypy src
```

## Documentation

Start with [`docs/architecture.md`](docs/architecture.md) (diagrams: system context, evaluation
pipeline, entity map, state machines), then
[`docs/business-ontology.md`](docs/business-ontology.md) for the domain and use cases. The
first workload's contract is in
[`docs/workflow-contracts/reference-request-triage-v1.md`](docs/workflow-contracts/reference-request-triage-v1.md).

## License

MIT — see [LICENSE](LICENSE).
