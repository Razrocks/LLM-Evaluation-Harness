# Deterministic vs Agentic Boundary

## Rule

Use probabilistic models **only** for work whose value comes from contextual interpretation,
synthesis, ranking, drafting, or semantic comparison. Keep authority, policy, state
transitions, permissions, audit, validation, evidence integrity, and execution gating
**deterministic**.

## Deterministic responsibilities

IDs and version resolution; content hashes; dataset membership; schema validation; reference
integrity; case/release/run state transitions; manifest resolution; request construction;
timeout/retry classification; raw evidence capture; date normalization under declared rules;
exact and normalized comparisons; set metrics; numeric tolerance; policy lookup/oracle where
codified; permission and approval checks; tool allowlists and argument validation; score
aggregation; baseline compatibility; gate evaluation; audit events; Qdrant corpus/index version
mapping; report serialization.

## Agentic / model-assisted responsibilities

Target-system reasoning and generation; summarization; extracting semantically expressed tasks;
drafting synthetic eval cases; proposing assertion candidates; semantic equivalence scoring
where deterministic methods are inadequate; failure-cluster suggestions; report-narrative
drafting; retrieval reranking when explicitly evaluated; policy *explanation* (never policy
authority).

## Human-only / human-approved

Approving expected outcomes; resolving ambiguous labels; approving dataset releases;
calibrating semantic judges; approving baselines; overriding gates; changing high-stakes policy
snapshots; authorizing production execution.

## No-fake-agent rule

Do **not** create separate "agents" for loading data, validating JSON, computing metrics,
writing files, or checking thresholds. Those are deterministic components or skills. An agent
boundary is justified **only** when a component must choose among multiple valid skills/actions
using incomplete context **and its choice is itself evaluated**.

## First slice (M0–M4)

Everything in the first slice is deterministic. The only probabilistic element is the *target
under test*, and the harness never modifies the target response before evidence capture. No LLM
judge is used — see [adr/0003-no-llm-judge-in-first-slice.md](adr/0003-no-llm-judge-in-first-slice.md).
