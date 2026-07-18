# Architecture

This document is the visual backbone of the platform. It shows how the pieces fit together,
how a single evaluation flows from a case to a gate decision, how the domain entities relate,
and how each object moves through its lifecycle. Every other doc links back here.

> If you read only one diagram, read [The evaluation pipeline](#2-the-evaluation-pipeline). It
> is the spine of the whole system: a case goes in, evidence and a gate decision come out, and
> nothing in between is allowed to hide a failure.

---

## 1. System context — what sits inside the boundary

The platform is a **self-contained evaluation harness**. It ships with its own datasets,
targets, scorers, and reports, and runs end-to-end from a clean checkout with no external
service. Optional integrations (model providers, a database, a vector store, a dashboard) attach
at the edges in later milestones but are never prerequisites.

```mermaid
flowchart TB
    subgraph OUT["Optional / later milestones (never required to run)"]
        direction LR
        PROV["Model providers<br/>Claude · ChatGPT · Gemini · HF<br/>(M5)"]
        DB[("PostgreSQL<br/>(M6)")]
        QD[("Qdrant<br/>(M7)")]
        DASH["Dashboard<br/>Next.js (M10)"]
        CI["GitHub Actions<br/>(M5, owner-operated)"]
    end

    subgraph CORE["ai-eval platform (standalone, offline-capable)"]
        direction TB
        DEF["Definition memory<br/>cases · releases · schemas · scorers · gates"]
        ORCH["Run orchestrator"]
        TGT["Target adapters<br/>(recorded fixtures by default)"]
        SCOR["Scoring + metrics + evidence"]
        REP["Reports + baselines + gate"]
        DEF --> ORCH --> TGT --> SCOR --> REP
    end

    USER["Engineer / reviewer / CI principal"] --> CORE
    TGT -. "opt-in (M5)" .-> PROV
    REP -. "opt-in (M6)" .-> DB
    SCOR -. "opt-in (M7)" .-> QD
    REP -. "opt-in (M10)" .-> DASH
    CI -. "runs" .-> CORE
```

**Reading it:** the solid path (top box) is everything the first checkpoint needs. The dashed
edges are opt-in and additive — remove them all and the platform still validates datasets, runs
evaluations, scores, reports, compares, and gates.

---

## 2. The evaluation pipeline

One case, from definition to gate decision. This is the control flow the run orchestrator
drives. The single most important rule is visible here: **raw output is captured before any
parsing**, so an invalid response can never be silently repaired into a passing score.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as CLI / caller
    participant RES as Plan Resolver
    participant ORCH as Orchestrator
    participant TGT as Target Adapter
    participant ART as Artifact Store
    participant PAR as Parser + Schema Validator
    participant SC as Scorer Registry
    participant AGG as Metric Aggregator
    participant CMP as Baseline Comparator
    participant GATE as Gate Evaluator

    CLI->>RES: eval plan (workflow, dataset release, target, scoring plan, gate)
    RES->>RES: resolve every ref to an immutable version + hash
    RES-->>ORCH: run manifest (no floating references)
    loop each case in the frozen release
        ORCH->>TGT: invoke(case_input, context)
        TGT-->>ORCH: raw output + trace + usage + latency + errors
        ORCH->>ART: persist RAW (before parsing)
        ORCH->>PAR: parse + validate against output schema
        PAR-->>ORCH: parsed value OR explicit parse/schema failure
        ORCH->>SC: score each atomic assertion
        SC-->>ORCH: assertion results (+ evidence, + failure codes)
    end
    ORCH->>AGG: aggregate metrics (with denominators)
    AGG-->>ORCH: metric summary
    ORCH->>CMP: compare to approved baseline (optional)
    ORCH->>GATE: evaluate deterministic gate
    GATE-->>CLI: PASS / FAIL / INVALID (+ per-rule evidence, + exit code)
```

**Reading it:** steps 5–6 (raw capture) always precede step 7 (parsing). Every assertion
produces a result (step 9) — none are silently dropped. The gate (step 14) is deterministic and
returns per-rule evidence, not just a verdict.

---

## 3. Component architecture

The engineering components and the one-directional dependency flow between them. Each component
has a single responsibility and an explicit "must not own" boundary (see
[engineering-ontology.md](engineering-ontology.md)). Deterministic components are never renamed
"agents."

```mermaid
flowchart LR
    subgraph DEFN["Definition & data"]
        CR["Case Repository"]
        DV["Dataset Validator"]
        HASH["Hashing / canonical serialization"]
    end
    subgraph EXEC["Execution"]
        EPR["Eval Plan Resolver"]
        RO["Run Orchestrator"]
        TA["Target Adapter"]
        AW["Artifact Writer"]
    end
    subgraph SCORE["Scoring & evidence"]
        OP["Output Parser"]
        SV["Schema Validator"]
        SR["Scorer Registry"]
        ER["Evidence Resolver"]
        FC["Failure Classifier"]
    end
    subgraph ANALYZE["Analysis & decision"]
        MA["Metric Aggregator"]
        RG["Report Generator"]
        BS["Baseline Service"]
        GE["Gate Evaluator"]
    end

    CR --> DV --> EPR
    HASH --> DV
    EPR --> RO --> TA --> AW
    RO --> OP --> SV --> SR --> ER
    SR --> FC
    SR --> MA --> RG
    MA --> BS --> GE
    GE --> RG
```

**Directory mapping:** `datasets/` (CR, DV) · `domain/` (HASH, models) · `execution/` (EPR, RO)
· `targets/` (TA) · `artifacts/` (AW) · `parsing/` (OP, SV) · `scoring/` (SR) · `evidence/`
(ER) · `failures/` (FC) · `metrics/` (MA) · `reporting/` (RG) · `baselines/` (BS) · `gates/`
(GE) · `cli/` (entrypoints).

---

## 4. Entity-relationship map

How the canonical business entities connect. A **Target System** exposes **Workflows**; a
**Workflow** owns **Eval Cases**; approved cases are frozen into a **Dataset Release**; a
release plus an execution configuration and scoring plan form an **Eval Plan**; running a plan
produces an **Eval Run** of many **Case Executions**, each yielding **Assertion Results** backed
by **Evidence**. See [business-ontology.md](business-ontology.md) for the full narrative.

```mermaid
erDiagram
    TARGET_SYSTEM ||--o{ WORKFLOW : exposes
    WORKFLOW ||--o{ EVAL_CASE : "defines cases for"
    EVAL_CASE ||--|{ ASSERTION : "declares"
    EVAL_CASE ||--o{ EVIDENCE_UNIT : "provides source context"
    DATASET ||--o{ DATASET_RELEASE : "has versions"
    DATASET_RELEASE }o--|{ EVAL_CASE : "freezes exact versions of"
    EVAL_PLAN }o--|| WORKFLOW : "targets"
    EVAL_PLAN }o--|| DATASET_RELEASE : "runs against"
    EVAL_PLAN }o--|| EXECUTION_CONFIG : "invokes with"
    EVAL_PLAN }o--|| SCORING_PLAN : "scored by"
    EVAL_PLAN }o--o| GATE_POLICY : "gated by"
    EVAL_RUN }o--|| EVAL_PLAN : "instantiates"
    EVAL_RUN ||--o{ CASE_EXECUTION : "contains"
    CASE_EXECUTION ||--|| CANDIDATE_OUTPUT : "produces"
    CASE_EXECUTION ||--o{ TRACE_EVENT : "emits"
    CASE_EXECUTION ||--|{ ASSERTION_RESULT : "produces"
    ASSERTION_RESULT }o--|| SCORER : "produced by"
    ASSERTION_RESULT ||--o{ EVIDENCE_UNIT : "references"
    ASSERTION_RESULT ||--o{ FAILURE : "may raise"
    BASELINE }o--|| EVAL_RUN : "approves"
    GATE_RESULT }o--|| EVAL_RUN : "judges"
    GATE_RESULT }o--o| BASELINE : "compares against"
```

---

## 5. Lifecycle state machines

Every versioned object has an explicit lifecycle. Immutability points are where a version can no
longer change — corrections create a **new** version instead of mutating the old one.

**Eval Case** — an approved version is immutable; a correction is a new `case_version`.

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> IN_REVIEW : submit
    IN_REVIEW --> DRAFT : changes requested
    IN_REVIEW --> APPROVED : reviewer approves
    APPROVED --> DEPRECATED : replaced / invalidated
    DEPRECATED --> [*]
    note right of APPROVED : immutable
```

**Dataset Release** — only FROZEN/ACTIVE releases can back a publishable run.

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> VALIDATING : assemble
    VALIDATING --> DRAFT : validation failure
    VALIDATING --> FROZEN : all invariants pass
    FROZEN --> ACTIVE : promote
    ACTIVE --> SUPERSEDED : newer release
    SUPERSEDED --> RETIRED
    RETIRED --> [*]
    note right of FROZEN : content-addressed,<br/>membership immutable
```

**Eval Run** — a completed run is immutable and fully reproducible from its manifest.

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> QUEUED
    QUEUED --> RUNNING
    RUNNING --> SCORING
    SCORING --> COMPLETED
    QUEUED --> CANCELLED
    RUNNING --> CANCELLED
    QUEUED --> FAILED
    RUNNING --> FAILED
    SCORING --> FAILED
    COMPLETED --> [*]
    note right of COMPLETED : immutable
```

**Case Execution** — the fine-grained path; note the distinct error terminals.

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> INVOKING
    INVOKING --> RESPONSE_RECEIVED
    INVOKING --> INVOCATION_ERROR
    RESPONSE_RECEIVED --> PARSING
    PARSING --> PARSE_ERROR
    PARSING --> SCHEMA_ERROR
    PARSING --> SCORING
    SCORING --> SCORING_ERROR
    SCORING --> UNEVALUABLE
    SCORING --> PASSED
    SCORING --> FAILED_ASSERTIONS
    PASSED --> [*]
    FAILED_ASSERTIONS --> [*]
```

**Baseline** — approval is explicit; the highest score does not auto-promote.

```mermaid
stateDiagram-v2
    [*] --> CANDIDATE
    CANDIDATE --> APPROVED : baseline approver
    CANDIDATE --> REJECTED
    APPROVED --> ACTIVE : set for scope
    ACTIVE --> RETIRED : replaced
    REJECTED --> [*]
    RETIRED --> [*]
```

---

## 6. Deterministic vs agentic zones

The platform keeps authority deterministic and confines probabilistic behavior to the *target
under test* and a few explicitly justified evaluator steps (added later). See
[deterministic-agentic-boundary.md](deterministic-agentic-boundary.md).

```mermaid
flowchart TB
    subgraph DET["Deterministic (authoritative)"]
        d1["version resolution + hashing"]
        d2["schema validation"]
        d3["date normalization (versioned rules)"]
        d4["exact / categorical / set scoring"]
        d5["metric aggregation"]
        d6["gate evaluation + audit"]
    end
    subgraph AG["Probabilistic (evaluated, never authoritative)"]
        a1["target reasoning / generation"]
        a2["semantic judge (M3+/M7, opt-in)"]
        a3["retrieval reranking (M7)"]
    end
    AG -- "output captured as evidence" --> DET
    DET -- "never delegated to a model" --> DET
```

---

## 7. Storage & memory layout (first checkpoint)

All local files — no database in M0–M4. Each memory class (see
[memory-model.md](memory-model.md)) maps to a concrete location.

```mermaid
flowchart LR
    subgraph A["A. Immutable definition"]
        s1["schemas/*.json"]
        s2["datasets/reference/.../cases.jsonl + manifest.json"]
        s3["configs/gates/*.json"]
    end
    subgraph C["C. Evidence (append-only)"]
        r1["runs/&lt;run_id&gt;/raw/*"]
        r2["runs/&lt;run_id&gt;/traces.jsonl"]
        r3["runs/&lt;run_id&gt;/assertion_results.jsonl"]
    end
    subgraph D["D. Analytical (regenerable)"]
        m1["runs/&lt;run_id&gt;/metric_summary.json/.csv"]
        m2["runs/&lt;run_id&gt;/failure_report.md"]
        m3["runs/&lt;run_id&gt;/comparison_report.md"]
        m4["runs/&lt;run_id&gt;/gate_result.json"]
    end
    A --> C --> D
```

---

## 8. Where to go next

- **The domain in depth:** [business-ontology.md](business-ontology.md)
- **The engineering components:** [engineering-ontology.md](engineering-ontology.md)
- **The first workflow's contract + worked example:** [workflow-contracts/reference-request-triage-v1.md](workflow-contracts/reference-request-triage-v1.md)
- **What is and isn't in scope:** [system-boundary.md](system-boundary.md)
- **Technology and why each dependency exists:** [technology-map.md](technology-map.md)
