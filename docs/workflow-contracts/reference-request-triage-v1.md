# Workflow Contract — `reference.request_triage.v1`

The first vertical slice, and the workload every other doc uses as its example. It converts a
messy business request plus optional supporting documents into a strict structured work item,
then evaluates that item with deterministic, evidence-backed scorers. This document is the
precise contract: inputs, outputs, the questions we ask of every case, and how each is scored.

## Purpose

Given an unstructured request and supporting text, the target returns structured JSON containing a
summary, tasks, deadline, risk, missing information, attention status, and evidence references.
The platform proves — case by case — whether that output is contract-valid, correct, and
evidence-backed, and whether a configuration change caused a regression.

## Why this workload was chosen first

It is narrow enough to finish without hiding behind infrastructure, yet it exercises **every**
core contract of the platform at once:

- structured generation and strict schema validation;
- explicit **and** relative date reasoning (with timezone);
- classification (risk, attention) with a controlled label set;
- set-based reasoning (missing-information precision/recall/F1);
- conflicting evidence across documents;
- grounding — did the output invent facts, or cite real ones?

If the platform can measure all of that on one workload with reproducible evidence, the same
contracts extend to RAG, governed tool use, and classification later.

## The evaluation flow for one case

```mermaid
sequenceDiagram
    autonumber
    participant ORCH as Orchestrator
    participant TGT as Triage Target
    participant ART as runs/&lt;id&gt;/raw
    participant PAR as Parser + request_triage.output.v1
    participant SC as Scorers
    ORCH->>TGT: request_triage.input.v1 (message, received_at, tz, documents)
    TGT-->>ORCH: raw JSON candidate
    ORCH->>ART: persist raw BEFORE parsing
    ORCH->>PAR: parse + schema-validate
    alt malformed or schema-invalid
        PAR-->>ORCH: contract failure → output assertions UNEVALUABLE
    else valid
        PAR-->>ORCH: parsed work item
        ORCH->>SC: schema / deadline / deadline_kind / risk / missing_info / evidence / no-invented-amount
        SC-->>ORCH: one assertion result each (+ evidence + failure codes)
    end
```

## Input contract — `request_triage.input.v1`

Schema: [`../../schemas/reference/request_triage_input.v1.json`](../../schemas/reference/request_triage_input.v1.json)

| Field | Required | Notes |
|---|---|---|
| `request_id` | ✅ | stable identifier |
| `message` | ✅ | the raw request text |
| `received_at` | ✅ | ISO-8601 **with offset**, e.g. `2026-07-13T10:00:00-04:00` |
| `reference_timezone` | ✅ | IANA name, e.g. `America/Toronto` |
| `documents[]` | ✅ | each with `document_id`, `document_version`, `text`, `content_hash` |
| `metadata` | optional | `source`, `priority_hint`, `category_hint` |

A relative deadline ("by Friday") cannot be interpreted without `received_at` +
`reference_timezone`; both are mandatory. This is system invariant #4.

## Output contract — `request_triage.output.v1`

Schema: [`../../schemas/reference/request_triage_output.v1.json`](../../schemas/reference/request_triage_output.v1.json)

Required fields: `summary`, `tasks[]`, `deadline{date,kind,evidence_refs}`, `risk_level`,
`risk_reasons[]`, `missing_information[]` (controlled `key`), `needs_attention`,
`material_claims[]`.

- `deadline.kind ∈ {explicit_absolute, explicit_relative, inferred, none, ambiguous}`
- `risk_level ∈ {low, medium, high}`
- Model self-confidence is **not** part of the trusted contract. It may be recorded as a separate
  observation only if calibration is explicitly evaluated.

## Core evaluation questions

Every case answers these, each as one or more atomic assertions:

1. Is the JSON valid and schema-conformant?
2. Is the deadline `kind` correct, and the normalized `date` correct?
3. Is the risk label correct? (high-risk **underclassification** is critical/major by criticality)
4. Were the required missing-information items found (recall)? Any spurious ones (precision)?
5. Is `needs_attention` consistent with the approved label?
6. Do the evidence references exist and actually support the claims?
7. Were prohibited/unsupported facts (e.g. an invented monetary amount) introduced?

## Assertion types used

`schema_valid`, `normalized_date_equal`, `deadline_kind_equal`, `categorical_equal`,
`boolean_equal`, `set_precision_recall_f1`, `required_task_coverage`, `evidence_reference_valid`,
`evidence_span_support`, `unsupported_material_claim_absent`, `prohibited_value_absent`.
(`semantic_equivalence_judge` is defined in the contract but **not used** in the first slice — see
[../adr/0003-no-llm-judge-in-first-slice.md](../adr/0003-no-llm-judge-in-first-slice.md).)

## Worked example

The canonical invoice/Friday case — a vendor emails on Monday July 13 that an invoice exceeds the
quote and asks for a reply "by Friday," with conflicting amounts in two attached documents — is
is traced through the pipeline (input → assertions → scoring → gate) in
[../business-ontology.md §4](../business-ontology.md#4-worked-example--one-case-through-the-whole-pipeline).

## Deadline normalization (versioned)

Uses the case's `received_at` + `reference_timezone`. It preserves the distinction between
explicit / inferred / absent deadlines; parses named weekdays deterministically; is tested across
week/month/year boundaries; **never** infers a date from urgency language alone; and routes
ambiguous dates to an explicit ambiguity/unevaluable path. **No wall-clock time is used in
tests** — every date is computed relative to the case's own `received_at`.

## Missing-information vocabulary (controlled keys)

Scoring uses stable keys, not free-text sentences:

`request_identifier`, `requester_identity`, `desired_outcome`, `responsible_owner`,
`approval_status`, `target_resource`, `source_document`, `governing_terms`,
`amount_or_scope_breakdown`, `deadline_basis`, `previous_correspondence`,
`risk_acceptance_owner`.

A versioned alias map normalizes reviewed synonyms to these keys (e.g. "line-item detail" →
`amount_or_scope_breakdown`). Fuzzy matching, if used, is conservative, versioned, and visible in
the evidence — it never silently turns a genuinely different item into a match.

## Metrics produced

- **Contract:** invocation success rate, parse success rate, schema pass rate.
- **Business:** deadline accuracy, deadline-kind accuracy, risk accuracy + macro-F1, high-risk
  recall, missing-information precision/recall/F1, needs-attention accuracy.
- **Grounding:** evidence-reference validity, evidence coverage, unsupported-material-claim
  count/rate.
- **Operational:** latency, attempts, usage, and cost (only when a price table is present),
  error counts by class.

## Built-in target configurations (recorded, no credentials)

| Config | Behavior | Proves |
|---|---|---|
| `recorded_pass.v1` | correct outputs | baseline PASS |
| `recorded_missing_information_regression.v1` | valid JSON, drops required items | recall regression caught |
| `recorded_deadline_regression.v1` | shifts/drops deadlines | date regression caught |
| `recorded_evidence_regression.v1` | cites invalid evidence | grounding regression caught |
| `recorded_schema_failure.v1` | malformed / schema-invalid JSON | contract failure caught |
| `provider_structured_output.v1` (M5) | live model behind the same schema | provider parity |

The first five require no credentials, which is what makes the demo and CI deterministic.

## Postconditions

Every case produces: raw output captured before parsing; a parsed value or an explicit
parse/schema failure; exactly one result per assertion; aggregated metrics with denominators; and
a gate decision when a gate policy is supplied. Nothing is silently omitted or repaired.
