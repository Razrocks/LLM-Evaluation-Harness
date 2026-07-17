# Business Ontology

One canonical definition per core noun. Business terms and engineering components are kept
distinct. A term may not silently change meaning between workloads, the API, or the dashboard.

## Principles

1. Every core noun has one canonical definition.
2. Every versioned object has a stable identifier and immutable historical versions.
3. Expected behavior is represented as **atomic assertions**, not a single prose answer.
4. A score is not evidence; it must reference evidence.
5. "Pass" means a declared rule was satisfied — not that output looked good.
6. "Agent" = a system that chooses among typed skills/actions under state and constraints; not
   a label for every LLM call.
7. "Memory" = explicitly stored and governed state, not hidden conversational context.
8. Ambiguity is recorded and adjudicated, not averaged away.

## Canonical entities

| Entity | Meaning |
|---|---|
| Target System | A system/workflow whose behavior is evaluated. Not a model. |
| Workflow | A named, versioned business behavior within a target system. |
| Eval Case | One versioned scenario: input, context, expected values, atomic assertions, provenance, review state. |
| Assertion | One atomic, typed requirement or prohibition. |
| Dataset Release | An immutable, content-addressed list of approved case versions. |
| Execution Configuration | The frozen configuration used to invoke the target. |
| Scoring Plan | Scorer mappings, normalization rules, metric definitions, failure mappings. |
| Eval Plan | Workflow + dataset release + execution config + scoring plan + optional baseline/gate. |
| Eval Run | One attempt to execute one resolved eval plan. |
| Case Execution | One case evaluated in one run. |
| Candidate Output | The raw and parsed output from the target. |
| Trace | Ordered material events from target/harness. |
| Evidence | Source spans, values, trace events, or artifacts supporting a score. |
| Scorer | A versioned evaluator turning expected+observed into an assertion result. |
| Assertion Result | Expected, observed, score, status, evidence, scorer version, failure codes. |
| Metric | A named aggregation with explicit numerator, denominator, scope, missing-data rule. |
| Failure | A concrete deviation, error, or inability to evaluate. |
| Baseline | An explicitly approved comparison reference (not automatically the best run). |
| Regression Gate | Deterministic rules that accept, reject, or invalidate a candidate run. |
| Report | A versioned representation of run results for humans or machines. |

## Banned terms (require a qualifier)

"good output", "smart agent", "accurate", "safe", "uses memory", "RAG works",
"hallucination-free", "production-grade", "human in the loop", "autonomous", "real-time",
"grounded", "high confidence", "the model decided", "the system learned."

## Chosen meanings for ambiguous terms

| Term | Chosen meaning |
|---|---|
| Accuracy | A specifically named metric over a defined assertion set. |
| Hallucination | A material factual claim not supported by available authoritative evidence, or contradicting it. Decomposed into evidence/citation/contradiction/abstention metrics. |
| Ground truth | An approved expected value with provenance; not assumed infallible. |
| Agent | A component that selects among typed skills/actions based on context and state. |
| Safe | Satisfies named policy, permission, approval, and prohibited-action assertions. |
| Pass | Satisfies a declared assertion or gate rule. |
| Confidence | A value whose source and calibration are known; model self-confidence is not auto-trusted. |
| RAG quality | Separate retrieval and grounded-generation metrics, never one blended score. |

## Lifecycle states

- **Eval Case:** `DRAFT → IN_REVIEW → APPROVED → DEPRECATED` (`IN_REVIEW → DRAFT` on changes). An approved version is immutable; corrections create a new `case_version`.
- **Dataset Release:** `DRAFT → VALIDATING → FROZEN → ACTIVE → SUPERSEDED → RETIRED`.
- **Eval Run:** `CREATED → QUEUED → RUNNING → SCORING → COMPLETED`; plus `FAILED`, `CANCELLED`. A completed run is immutable.
- **Case Execution:** `PENDING → INVOKING → RESPONSE_RECEIVED → PARSING → SCORING → PASSED | FAILED_ASSERTIONS`; error terminals `INVOCATION_ERROR`, `PARSE_ERROR`, `SCHEMA_ERROR`, `SCORING_ERROR`, `UNEVALUABLE`.
- **Baseline:** `CANDIDATE → APPROVED → ACTIVE → RETIRED`, or `CANDIDATE → REJECTED`.
