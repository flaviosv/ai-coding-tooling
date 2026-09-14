---
name: tlc-spec-driven-extended
extends: tlc-spec-driven
description: >
  Extension for the tlc-spec-driven skill. MUST be read together with the parent
  tlc-spec-driven SKILL.md. The parent governs spec-driven planning. This extension
  (1) declares how reference-level overlays load, (2) names feature artifacts `<TASK-ID>-<slug>`,
  (3) numbers phase artifacts (`US-N`, `DC-N`, `T`), and (4) augments coding-principles with
  software-design/observability/stack-style references, and passes them
  to batch workers.
metadata:
  version: "1.2.1"
  parent_skill: tlc-spec-driven
  source: "ai-coding-tooling (extended/)"
---

# tlc-spec-driven — ai-coding-tooling Extension

Parent behavior stays in force except where this file overrides a specific point.

## Artifact Naming: `<TASK-ID>-<slug>`

Name every feature directory `<TASK-ID>-<slug>` — a task identifier plus a short
kebab-case description — instead of the parent's bare feature name:

- Feature → `.specs/features/<TASK-ID>-<slug>/` (e.g. `.specs/features/PROJ-42-user-auth/`)

Ask for the TASK-ID when you don't have one. If the project has no task tracker at all, fall
back to the parent's native naming (`<slug>` for features).

## Reference Extension Convention

This project ships reference-level overlays alongside the parent skill. **Whenever you
load a parent reference file `references/<X>.md`, immediately check for and load
`references.extended/<X>.md` from the skill root, reading it right after the parent
reference as an augmentation (never a replacement).**

Currently provided:

| Parent reference | Loads-after overlay |
|------------------|---------------------|
| `references/coding-principles.md` | `references.extended/coding-principles.md` |
| `references/design.md` | `references.extended/design.md` |
| `references/specify.md` | `references.extended/specify.md` |

The overlay's sections add to, or refine, the parent's — apply both together. If a future
overlay is added under `references.extended/`, the same rule applies automatically.

## Batch Worker Payload

When this skill dispatches a batch worker, its payload includes
`references.extended/coding-principles.md` and every `references.extended/coding-guidelines/`
file that file loads for the task, alongside the parent's `references/coding-principles.md`.

## Phase Artifact Numbering

Number artifacts in each phase so they can be referenced precisely in conversation and across documents:

| Phase | Artifact | Prefix | Example |
|-------|----------|--------|---------|
| Specify | User stories | `US-` | `US-1`, `US-2` |
| Design | Design components / decisions (one shared sequence) | `DC-` | `DC-1`, `DC-2` |
| Tasks | Atomic tasks | `T` | `T1`, `T2` |

Apply numbering sequentially within each feature. Use the prefix+number when discussing, reviewing, or cross-linking artifacts (e.g. "T2 implements US-1"). Numbering is always applied in the Specify phase; apply it in Design and Tasks phases when those phases are not skipped.
