# Source Specification

This directory holds the **original, verbatim** project-definition documents that this repository
implements. They are the historical source of truth for intent; the maintained, implementation-
facing documentation lives one level up in [`docs/`](../) and is what gets updated as behavior
changes.

## The three source documents

| File | What it is |
|---|---|
| `01_standalone_ai_evaluation_platform.md` | **Platform vision** — the reference benchmark families, what the project teaches, the phased build path, repository shape, and MVP acceptance criteria. |
| `02_standalone_ai_evaluation_system_blueprint.md` | **System Definition Blueprint** — implementation-grade ontology, primitives, abstractions, roles, workflow contracts, deterministic/agentic boundary, memory model, integration boundaries, data contracts, invariants, and the test/demo plan. |
| `03_master_build_prompt.md` | **Master Build Prompt** — the executable directive: anti-drift rules, ordered milestones (M0–M10), the pinned technology/dependency contract, error model, run-artifact layout, gate defaults, and the mandated final-response format. |

## Source-of-truth order

When these documents and the working code disagree, resolve in this order (from
`03_master_build_prompt.md` §2):

1. Existing repository behavior and tests (when not in conflict with the build prompt).
2. `02_…blueprint.md`.
3. `01_…platform.md`.
4. `03_master_build_prompt.md`.
5. Explicit, documented assumptions (recorded in [`../adr/`](../adr/) and
   [`../implementation-status.md`](../implementation-status.md)).

## How to populate this directory

These three files are provided by the repository owner (they exist as local files). Drop them in
here with the filenames above. The derived docs in [`docs/`](../) already distill their content —
this directory preserves the originals for provenance and audit.

> The derived documentation is authoritative for *current behavior*; these source docs are
> authoritative for *original intent*. Neither is marketing — both describe the system precisely.
