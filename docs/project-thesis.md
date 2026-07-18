# Project Thesis

## The problem

AI workflows ship on vibes. A prompt is tuned until a handful of hand-tried examples look good,
the demo works, and the thing goes to production. Then a "small" prompt change, a model version
bump, or a new document format quietly degrades one behavior in ten — and nobody notices until a
deadline is missed, a high-risk item is waved through, or an invented number reaches a customer.

The root cause is that probabilistic systems are treated as if they were deterministic: tested
once, trusted forever. But the same input can produce different output, "good" is undefined, and
there is no frozen population of reviewed cases to measure against. Traditional software has unit
tests, regression suites, and release gates. Most AI workflows have none of the equivalents.

## The thesis

> **AI workflow reliability is a versioned, evidence-backed software quality problem — not a
> prompt-tuning problem.**

The behavior of an AI workflow becomes governable the moment it can be *specified, measured,
reproduced, reviewed, compared, and gated.* That requires six things working together, and the
platform provides all six:

1. **Approved datasets** — frozen, reviewed cases with atomic expected claims.
2. **Explicit contracts** — versioned input/output schemas the output must satisfy.
3. **Deterministic scoring** — rules, not opinions, wherever correctness is a rule.
4. **Trace-based evidence** — every score resolves to the source span or event that justifies it.
5. **Configuration comparison** — full resolved manifests, so comparisons are fair and repeatable.
6. **Regression thresholds** — a deterministic gate that blocks promotion on a real regression.

## The shift it forces

The platform converts a claim from the left column into a claim from the right column:

| Vibes | Evidence |
|---|---|
| "It usually gives a good answer." | "This configuration passed 30/30 approved cases." |
| "The new prompt seems fine." | "Missing-information recall fell 0.92→0.71 on 8 named cases." |
| "This model is better." | "Same release, same scorers: +3% schema, −7% high-risk recall, −40% latency." |
| "It doesn't hallucinate." | "Unsupported-material-claim rate 0.00 over 30 cases; 2 invalid evidence refs." |
| "Ship it." | "Gate PASS: all critical rules met, no regression vs approved baseline v1." |

## One-sentence definition

A standalone evaluation platform that ships with reference workloads, executes AI systems
against versioned cases, scores outputs and traces using deterministic and controlled semantic
methods, preserves evidence, compares configurations, and enforces regression gates.

## Why it must start narrow

A generic "evaluate any AI" platform, built first, reliably produces heavy configuration, weak
semantics, and a dashboard reporting numbers nobody validated. So the thesis is proven on **one
concrete workload** — Structured Request Triage — end to end, before anything widens. The
discipline is captured in [adr/0001](adr/0001-domain-specific-first-slice.md): do not widen until
the first slice is green.

## What the platform owns — and does not

**Owns:** evaluation definition, reference workloads, sandbox execution, execution evidence,
scoring, comparison, and gating.
**Does not own:** production business execution, identity, authorization, live pricing, or any
real side effect. External applications are *optional targets*, never prerequisites. See
[system-boundary.md](system-boundary.md).

## Reference workloads

All four run without an external application. Each exercises a different evaluation class using
the *same* contracts.

| Workload | Evaluation class it proves | Milestone |
|---|---|---|
| `reference.request_triage.v1` | Structured extraction: dates, risk, missing info, tasks, evidence. | **M0–M4 (first slice)** |
| `reference.grounded_qa.v1` | Retrieval + grounded generation, separately attributed. | M7 |
| `reference.governed_tool_use.v1` | Agentic skill/tool selection, policy, approval, escalation. | M8 |
| `reference.risk_classification.v1` | Method bake-off: rules vs CatBoost vs HuggingFace transformer vs LLM. | M9 |

The same provider-neutral target contract evaluates **Claude, ChatGPT, Gemini, and local
HuggingFace models** identically (M5); **CatBoost** and a **HuggingFace transformer classifier**
join as ML baselines compared against LLMs on the same held-out labels (M9). See
[technology-map.md](technology-map.md).

## The proof

The first proof is deliberately humble and deliberately hard to fake:

> The platform catches **one** meaningful structured-output regression, preserves the evidence,
> explains exactly why it failed, and blocks promotion under a deterministic contract.

The complete proof is that the *same standalone contracts* also evaluate retrieval, grounded
generation, governed tool use, classifiers, cost, latency, and regressions — without ever
requiring another product. Not "we can call many models," but "we can prove, case by case,
whether a configuration got better or worse."
