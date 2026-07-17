# Workflow Contract — `reference.request_triage.v1`

The first vertical slice. Converts a messy business request plus optional supporting documents
into a strict structured work item, then evaluates it with deterministic evidence-backed
scorers.

## Purpose

Given an unstructured request and supporting text, the target returns structured JSON containing
a summary, tasks, deadline, risk, missing information, attention status, and evidence references.
The platform proves — case by case — whether that output is contract-valid, correct, and
evidence-backed, and whether a configuration change caused a regression.

## Input contract — `request_triage.input.v1`

Schema: [`../../schemas/reference/request_triage_input.v1.json`](../../schemas/reference/request_triage_input.v1.json)

Required: `request_id`, `message`, `received_at` (ISO-8601 **with offset**),
`reference_timezone` (IANA), `documents[]` (`document_id`, `document_version`, `text`,
`content_hash`). Optional: `metadata` (`source`, `priority_hint`, `category_hint`).

A relative deadline cannot be interpreted without `received_at` + `reference_timezone`; both are
mandatory (invariant #4).

## Output contract — `request_triage.output.v1`

Schema: [`../../schemas/reference/request_triage_output.v1.json`](../../schemas/reference/request_triage_output.v1.json)

Required: `summary`, `tasks[]`, `deadline{date,kind,evidence_refs}`, `risk_level`,
`risk_reasons[]`, `missing_information[]` (controlled `key`), `needs_attention`,
`material_claims[]`. Model self-confidence is **not** part of the trusted contract.

`deadline.kind ∈ {explicit_absolute, explicit_relative, inferred, none, ambiguous}`.
`risk_level ∈ {low, medium, high}`.

## Core evaluation questions

- Is the JSON valid and schema-conformant?
- Is the deadline `kind` and normalized `date` correct?
- Is the risk label correct? (high-risk underclassification is critical/major by case criticality)
- Were required missing-information items found (recall)? Any spurious ones (precision)?
- Is `needs_attention` consistent with the approved label?
- Do evidence references exist and support the claims?
- Were prohibited/unsupported facts (e.g. invented amounts) introduced?

## Assertion types used

`schema_valid`, `normalized_date_equal`, `deadline_kind_equal`, `categorical_equal`,
`boolean_equal`, `set_precision_recall_f1`, `required_task_coverage`, `evidence_reference_valid`,
`evidence_span_support`, `unsupported_material_claim_absent`, `prohibited_value_absent`.
(`semantic_equivalence_judge` is defined but **not used** in the first slice.)

## Deadline normalization (versioned)

Uses the case's `received_at` + `reference_timezone`. Preserves the distinction between
explicit / inferred / absent deadlines; parses named weekdays deterministically; tests
week/month/year boundaries; never infers a date from urgency language alone; ambiguous dates take
an explicit ambiguity/unevaluable path. **No wall-clock time is used in tests.**

## Missing-information vocabulary (controlled keys)

`request_identifier`, `requester_identity`, `desired_outcome`, `responsible_owner`,
`approval_status`, `target_resource`, `source_document`, `governing_terms`,
`amount_or_scope_breakdown`, `deadline_basis`, `previous_correspondence`,
`risk_acceptance_owner`. A versioned alias map normalizes reviewed synonyms to these keys; fuzzy
matching is conservative, versioned, and visible in evidence — never silently turning a
different item into a match.

## Metrics produced

Contract: invocation success rate, parse success rate, schema pass rate. Business: deadline
accuracy, deadline-kind accuracy, risk accuracy + macro-F1, high-risk recall,
missing-information precision/recall/F1, needs-attention accuracy, evidence-reference validity,
evidence coverage, unsupported-material-claim count/rate. Operational: latency, attempts,
usage, cost (when a price table is present), error counts by class.

## Built-in target configurations (recorded, no credentials)

`recorded_pass.v1` · `recorded_missing_information_regression.v1` ·
`recorded_deadline_regression.v1` · `recorded_evidence_regression.v1` ·
`recorded_schema_failure.v1` · optional `provider_structured_output.v1` (M5).

## Postconditions

Every case produces raw output (captured before parsing), a parsed value or explicit
parse/schema failure, one result per assertion, aggregated metrics with denominators, and a
gate decision when a gate policy is supplied.
