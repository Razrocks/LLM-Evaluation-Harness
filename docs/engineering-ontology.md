# Engineering Ontology

## Principles

1. Domain contracts are independent from provider SDKs.
2. Target invocation is separate from scoring.
3. Parsing failure is separate from assertion failure.
4. Retrieval evaluation is separate from generation evaluation.
5. Raw evidence is retained before transformation.
6. Every derived result records its producer and version.
7. Integration adapters do not own domain policy.
8. Run orchestration does not interpret business correctness directly; scorers do.
9. UI and API layers consume stable application contracts.
10. Async infrastructure is added only when synchronous execution is an actual constraint.

## Components and boundaries

| Component | Responsibility | Must NOT own |
|---|---|---|
| Case Repository | Load/persist case versions and dataset releases. | Target execution or scoring. |
| Dataset Validator | Validate schemas, references, hashes, review state, release invariants. | Label creation. |
| Eval Plan Resolver | Resolve all references into an immutable run manifest. | Provider calls. |
| Run Orchestrator | Coordinate execution, parsing, scoring, aggregation, reporting. | Workflow-specific score semantics. |
| Target Adapter | Invoke one target workflow under a typed contract. | Aggregation or gate decisions. |
| Provider Adapter | Translate provider-neutral invocation to a provider API. | Business workflow semantics. |
| Prompt Renderer | Render a versioned prompt spec from case inputs. | Transport or scoring. |
| Output Parser | Convert raw output into a candidate structured value. | Silent correctness repair. |
| Schema Validator | Validate candidate data against a versioned schema. | Semantic scoring. |
| Scorer | Evaluate one assertion type into evidence-backed results. | Orchestration. |
| Judge Adapter | Invoke a configured semantic judge and validate its output. | High-stakes gate authority. |
| Evidence Resolver | Resolve source spans, chunks, trace references. | Changing canonical source content. |
| Metric Aggregator | Compute named aggregates from assertion/operational observations. | Case-label mutation. |
| Failure Classifier | Map explicit conditions to controlled taxonomy labels. | Hiding unknown failures in generic buckets. |
| Baseline Service | Manage candidate/approved/active baselines. | Editing completed runs. |
| Gate Evaluator | Execute deterministic threshold and critical-case rules. | Creating metrics ad hoc. |
| Report Generator | Render run data into machine and human reports. | Becoming the system of record. |
| Result Store | Persist immutable run evidence and derived results. | Provider credentials or policy. |

Deterministic components are never renamed "agents."

## Distinct error classes (must survive into reports)

dataset validation error · plan resolution error · target invocation error · timeout ·
rate-limit · raw-response error · parse error · schema error · assertion failure · scoring
error · judge error · retrieval error · evidence-resolution error · report error · persistence
error · gate failure · user cancellation.

A target invocation error is **not** a low-quality answer. A schema error is **not** a semantic
failure. See [failure-taxonomy.md](failure-taxonomy.md).

## Package layout (`src/ai_eval/`)

Introduced per milestone; only directories actually used are created.

```
domain/       # Pydantic models, enums, state machines, hashing (M1)
datasets/     # case loader, dataset validator, release freezer (M1)
execution/    # eval-plan resolver, run orchestrator (M2)
targets/      # TargetAdapter base + recorded fixtures (M2); providers/ (M5)
artifacts/    # per-run artifact writer, raw-before-parse capture (M2)
parsing/      # strict parser + schema validator (M3)
scoring/      # versioned scorers + registry + deadline normalizer (M3)
evidence/     # evidence resolver (M3)
metrics/      # metric aggregator (M3)
failures/     # failure classifier (M3)
reporting/    # JSONL/JSON/CSV/Markdown generators (M3)
baselines/    # baseline manifest + comparison (M4)
gates/        # deterministic gate evaluator (M4)
cli/          # Typer app (M4)
# later: retrieval/ (M7), agent_evaluation/ (M8), ml/ (M9), api/+workers/ (M6)
```
