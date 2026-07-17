# Failure Taxonomy

Controlled failure codes. Errors and quality failures remain **distinct** in every summary.
Unknown failures are never hidden in a generic bucket. Codes are grouped by class; the class of
a failure determines how metrics count it (see [metrics denominators](#counting-rules)).

## Definition failures

`CASE_SCHEMA_INVALID` · `CASE_REFERENCE_INVALID` · `CASE_UNAPPROVED` · `DATASET_HASH_MISMATCH` ·
`ASSERTION_INVALID` · `PLAN_REFERENCE_UNRESOLVED` · `CONFIG_INCOMPATIBLE`

## Invocation failures

`TARGET_UNAVAILABLE` · `PROVIDER_AUTH_ERROR` · `PROVIDER_RATE_LIMIT` · `PROVIDER_TIMEOUT` ·
`TARGET_INTERNAL_ERROR` · `RETRY_EXHAUSTED`

## Contract failures

`OUTPUT_EMPTY` · `OUTPUT_PARSE_ERROR` · `OUTPUT_SCHEMA_INVALID` · `REQUIRED_FIELD_MISSING` ·
`INVALID_ENUM` · `INVALID_EVIDENCE_REFERENCE`

## Business assertion failures

`DEADLINE_MISSED` · `DEADLINE_FALSE_POSITIVE` · `DEADLINE_FALSE_NEGATIVE` ·
`RISK_UNDERCLASSIFIED` · `RISK_OVERCLASSIFIED` · `MISSING_INFO_OMITTED` ·
`MISSING_INFO_SPURIOUS` · `NEEDS_ATTENTION_INCORRECT` · `TASK_UNSUPPORTED`

## Grounding failures

`UNSUPPORTED_MATERIAL_CLAIM` · `SOURCE_CONTRADICTION` · `EVIDENCE_NOT_FOUND` ·
`EVIDENCE_MISMATCH` · `EVIDENCE_COVERAGE_LOW`

## Retrieval failures (M7)

`RELEVANT_CHUNK_NOT_RETRIEVED` · `IRRELEVANT_CONTEXT_DOMINATES` · `WRONG_CORPUS_VERSION` ·
`STALE_VECTOR_INDEX` · `FILTER_MISMATCH` · `DUPLICATE_CHUNK_RETRIEVED`

## Agent / policy failures (M8)

`WRONG_SKILL_SELECTED` · `POLICY_OUTCOME_INCORRECT` · `ESCALATION_MISSED` ·
`APPROVAL_REQUIREMENT_MISSED` · `PROHIBITED_TOOL_PROPOSED` · `TOOL_ARGUMENT_INVALID` ·
`EXECUTION_BEFORE_APPROVAL` · `UNAVAILABLE_PERMISSION_ASSERTED` · `TRACE_ORDER_INVALID`

## Evaluator failures

`SCORER_ERROR` · `JUDGE_ERROR` · `JUDGE_OUTPUT_INVALID` · `EVIDENCE_RESOLUTION_ERROR` ·
`METRIC_AGGREGATION_ERROR` · `REPORT_GENERATION_ERROR`

## Severity

- **critical** — safety, policy, permission, or materially harmful behavior; gate-blocking.
- **major** — wrong core business outcome (deadline, risk, required missing information).
- **minor** — quality defect not changing the core outcome.
- **informational** — observation or non-blocking drift.

## Counting rules

- An **invocation failure** is not a low-quality answer; it is excluded from quality-metric
  numerators and reported under operational/error metrics with its own denominator.
- A **contract failure** (parse/schema) is distinct from a **business assertion failure**; a
  schema-invalid output yields a schema failure, and downstream output assertions become
  `unevaluable` (counted per each assertion's `on_unevaluable` policy).
- Every metric declares numerator, denominator, and missing-data behavior. See
  [../schemas/gate_policy.v1.json](../schemas/gate_policy.v1.json) for how codes gate a run.

## Codes exercised in the first slice (M0–M4)

Definition, invocation (recorded targets only produce `TARGET_INTERNAL_ERROR` fixtures),
contract, business assertion, grounding, and evaluator codes. Retrieval and agent/policy codes
are reserved for M7/M8.
