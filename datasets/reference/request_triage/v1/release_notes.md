# Release notes — `reference.request_triage.dataset.v1`

- **Workflow:** `reference.request_triage.v1`
- **State:** frozen (content-addressed; see `manifest.json` for the release hash and per-case hashes)
- **Distribution:** synthetic, public-safe
- **Cases:** 12 seed cases (all `review.status = approved`)

## Purpose

The first-checkpoint dataset for the Structured Request Triage workflow. Small enough to review
by hand, broad enough to exercise every deterministic scorer the first slice ships: schema
validity, deadline normalization (absolute / relative / none / ambiguous), risk classification,
missing-information set scoring, attention, and grounding (unsupported-claim absence).

## Authoring model

Cases are authored as reviewable per-file JSON under `cases/` (clean diffs, one case per file).
`manifest.json` and `cases.jsonl` are **generated** by
`scripts/build_request_triage_release.py`, which validates (approval required), computes each
case's content hash, and freezes the release. Do not edit the generated files by hand — edit a
case file and re-freeze; the release hash will change, which is the point.

## Case inventory

| Case | Scenario | Deadline kind | Risk | Criticality |
|---|---|---|---|---|
| 001 | Invoice exceeds quote, "by Friday" | explicit_relative | high | critical |
| 002 | Venue booking, absolute ISO date | explicit_absolute | medium | normal |
| 003 | Handbook request, "no rush" | none | low | normal |
| 004 | "early next week" | ambiguous | low | normal |
| 005 | Duplicate charge, no account id | explicit_relative | medium | normal |
| 006 | References an unattached SOW | none | medium | normal |
| 007 | "URGENT!!!" guest wifi password | none | low | normal |
| 008 | Casual request for prod DB write access | none | high | critical |
| 009 | Three dates, one real deadline | explicit_absolute | medium | normal |
| 010 | Prompt injection inside a document | none | high | critical |
| 011 | Reset admin password and email it | none | high | critical |
| 012 | Contract USD vs invoice CAD conflict | explicit_relative | high | critical |

## Distributions

- **Risk:** high 5 · medium 4 · low 3
- **Criticality:** critical 5 · normal 7
- **Deadline kinds:** explicit_relative 4 · none 5 · explicit_absolute 2 · ambiguous 1
- **Adversarial / decoupling:** urgent-not-risky (007), risky-not-urgent (008), prompt-injection
  (010), unsupported-action (011), document conflicts (001, 012).

## Coverage intent

Tone is deliberately decoupled from risk (007 loud+low, 008 calm+high). Ambiguity is recorded,
not guessed (004). Grounding is tested by prohibiting invented amounts/terms (001, 006, 012) and
by treating source text as untrusted (010). Missing information uses the controlled canonical key
vocabulary throughout.

## Limitations

- Synthetic scenarios authored for evaluation, not sampled from production traffic.
- English-only; a single reference timezone family (America/Toronto).
- 12 seed cases; expansion toward 30–50 is planned in a later pass.
