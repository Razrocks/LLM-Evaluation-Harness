# Phase 9 (M9) — ML Baselines & Optional Fine-Tuning

**Status:** ⬜ Planned. Not started. Introduces `reference.risk_classification.v1` — a method
bake-off on frozen splits.

## Goal

Answer the mature question the whole platform is built to ask: **what is the cheapest, safest,
most measurable method that satisfies the requirement?** For risk/attention/escalation
classification, compare four methods on the *same* held-out labels:

1. deterministic rules;
2. **CatBoost** over governed tabular features;
3. a **HuggingFace transformer** text classifier (`distilbert-base-uncased` default);
4. direct **LLM** classification.

## Why this matters

It is entirely possible that a simple deterministic rule or a tiny tabular model beats an LLM on a
narrow decision — cheaper, faster, more stable, more calibratable. The platform is designed to
*measure* that rather than assume the LLM wins.

## Deliverables

- Frozen train/validation/test **split manifests** + leakage checks.
- Deterministic rule baseline.
- **CatBoost**: governed features (deadline distance, missing-info count, risk-keyword count,
  document count, priority, model confidence, source, categorical workflow metadata), training,
  held-out eval, feature importance, **model card**, artifact hash.
- **HuggingFace transformer** classifier via **PyTorch** + **Datasets** + **Evaluate**; pinned
  base model + revision; tokenizer revision; hyperparameters; confusion matrix; calibration.
- Metrics: macro-F1, per-class precision/recall, high-risk recall, calibration, confusion
  matrices, latency, cost — compared against the LLM and deterministic approaches on the same
  cases.
- **Optional** LoRA/PEFT/TRL fine-tuning — only when the fine-tuning gate is satisfied.

## The fine-tuning gate

Fine-tuning may begin **only** when all are true:

1. a reproducible, material base-model failure *cluster* exists;
2. deterministic rules, prompt, schema, and retrieval fixes were tried first;
3. train/val/held-out splits are frozen and leakage-checked;
4. the target metric + minimum improvement are declared **before** training;
5. cost/latency/quality trade-off is measured against the unchanged baseline;
6. the adapter/model, training config, and model card are saved.

Training loss is **not** success. Promotion requires held-out eval improvement without violating
safety, schema, latency, or cost gates.

## Exit criteria

Held-out metrics reproducible; no leakage; artifacts + data revisions hashed; training never
replaces the eval harness; any fine-tuning claim is tied to a measured failure cluster.

## New dependencies / downloads

`ml` group (`catboost`, `transformers`, `torch`, `datasets`, `evaluate`, `peft`, `trl`,
`rapidfuzz`). **HuggingFace downloads:** classifier `distilbert-base-uncased` (~260 MB);
fine-tune base — recommended `Qwen/Qwen2.5-0.5B-Instruct` (permissive, strong for its size),
selected only at gate time. All downloads re-flagged to the owner first.
