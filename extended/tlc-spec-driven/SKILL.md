---
name: tlc-spec-driven-extended
extends: tlc-spec-driven
description: >
  Extension for the tlc-spec-driven skill. MUST be read together with the parent
  tlc-spec-driven SKILL.md. The parent governs spec-driven planning. This extension
  (1) declares how reference-level overlays load, (2) prioritizes planning before
  implementation for non-trivial work, (3) names feature artifacts `<TASK-ID>-<slug>`,
  and (4) augments coding-principles with software-design/observability/stack-style
  references and routes security to the security-best-practices skill and UI work to
  web-design-guidelines.
metadata:
  version: "1.0.0"
  parent_skill: tlc-spec-driven
  source: "ai-coding-tooling (extended/)"
---

# tlc-spec-driven — ai-coding-tooling Extension

Read this file immediately after the parent `SKILL.md`. It **augments** the parent —
it never replaces it. Parent behavior stays in force except where this file overrides
a specific point.

## Planning Is Prioritized

For any **non-trivial** task (3+ steps or an architectural decision), plan before building:
run the parent's Specify → (Design) → (Tasks) flow and confirm the plan before writing code.
Do not jump straight to implementation for non-trivial work. The parent's auto-sizing still
decides depth — small changes stay light, they just don't skip the plan.

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

The overlay's sections add to, or refine, the parent's — apply both together. If a future
overlay is added under `references.extended/`, the same rule applies automatically.

## Technical Design Docs → `technical-design-doc-creator`

**Overrides the parent.** The parent's description routes formal technical design docs to
`create-technical-design-doc` — **that skill does not exist** (no directory, registry entry,
or trigger anywhere). The actual installed skill is **`technical-design-doc-creator`** (Tech
Leads Club). When a task needs a formal Technical Design Document (TDD), invoke
`technical-design-doc-creator`; ignore the parent's stale `create-technical-design-doc`
pointer. The parent's own Design phase still covers lighter spec-style design notes inline —
reach for `technical-design-doc-creator` only when a full standalone TDD is wanted.
