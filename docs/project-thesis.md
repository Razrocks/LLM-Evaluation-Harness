# Project Thesis

## Thesis

AI workflow reliability is a **versioned, evidence-backed software quality problem**, not a
prompt-tuning problem.

The platform converts an AI workflow from:

> "It usually gives a good answer."

into:

> "This exact workflow configuration ran against this exact immutable dataset release, under
> these exact schemas, prompts/configs, scorers, and thresholds; every result retained raw
> evidence; the candidate met or failed declared quality, safety, latency, and cost rules;
> and the comparison is reproducible."

## One-sentence definition

A standalone evaluation platform that ships with reference workloads, executes AI systems
against versioned cases, scores outputs and traces using deterministic and controlled
semantic methods, preserves evidence, compares configurations, and enforces regression gates.

## Why it exists

It prevents: ontology drift; undefined success criteria; vague prompts standing in for
contracts; fake multi-agent architecture; untraceable model behavior; accidental scope
expansion; "AI wrapper" thinking; mutable or unverifiable ground truth; dashboards whose
metrics cannot be explained; and rebuilding evaluation logic for every workflow.

## Core design principle

The platform does **not** own production business execution. It owns **evaluation definition,
reference workloads, sandbox execution, execution evidence, scoring, comparison, and gating.**
External applications are optional targets, never prerequisites.

## Reference workloads (all run without an external app)

| Workload | Purpose | Milestone |
|---|---|---|
| `reference.request_triage.v1` | Structured extraction: summary, tasks, deadline, risk, missing info, attention, evidence. | **M0–M4 (first slice)** |
| `reference.grounded_qa.v1` | Chunking, embeddings, Qdrant retrieval, grounded answer + retrieval/generation attribution. | M7 |
| `reference.governed_tool_use.v1` | Skill selection, policy outcome, approval, tool proposals, sandbox execution gates, trace. | M8 |
| `reference.risk_classification.v1` | Deterministic rules vs CatBoost vs HuggingFace transformer vs LLM on frozen splits. | M9 |

## The proof

The first proof is **not** that the platform can call many models. It is that the platform
**catches one meaningful structured-output regression, preserves the evidence, explains the
failure, and blocks promotion under a deterministic contract.** The complete proof is that the
same standalone contracts also evaluate retrieval, grounded generation, governed tool use,
classifiers, cost, latency, and regressions — without requiring another product.

## Model coverage (targets under test)

The same provider-neutral target-adapter contract evaluates **Claude (Anthropic), ChatGPT
(OpenAI), Gemini (Google), and local HuggingFace models** identically (M5), plus **CatBoost**
and a **HuggingFace transformer classifier** as ML baselines compared against LLMs on the same
held-out labels (M9). See [technology-map.md](technology-map.md).
