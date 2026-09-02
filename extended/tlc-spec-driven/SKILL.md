---
name: tlc-spec-driven-extended
extends: tlc-spec-driven
description: >
  Extension for the tlc-spec-driven skill. MUST be read together with the parent
  tlc-spec-driven SKILL.md. The parent governs spec-driven planning. This extension
  (1) declares how reference-level overlays load, (2) prioritizes planning before
  implementation for non-trivial work, (3) names feature artifacts `<TASK-ID>-<slug>`,
  (4) augments coding-principles with software-design/observability/stack-style
  references and routes security to the security-best-practices skill, and (5)
  requires a persisted per-feature commit log
  (`commits.md`) of every atomic commit hash traceable to that feature, and (6) records the
  model tier each phase is expected to run on.
metadata:
  version: "1.1.1"
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
| `references/implement.md` | `references.extended/implement.md` |
| `references/specify.md` | `references.extended/specify.md` |
| `references/design.md` | `references.extended/design.md` |

The overlay's sections add to, or refine, the parent's — apply both together. If a future
overlay is added under `references.extended/`, the same rule applies automatically.

## Phase Artifact Numbering

Number artifacts in each phase so they can be referenced precisely in conversation and across documents:

| Phase | Artifact | Prefix | Example |
|-------|----------|--------|---------|
| Specify | User stories | `US-` | `US-1`, `US-2` |
| Design | Design components / decisions (one shared sequence) | `DC-` | `DC-1`, `DC-2` |
| Tasks | Atomic tasks | `T` | `T1`, `T2` |

Apply numbering sequentially within each feature. Use the prefix+number when discussing, reviewing, or cross-linking artifacts (e.g. "T2 implements US-1"). Numbering is always applied in the Specify phase; apply it in Design and Tasks phases when those phases are not skipped.

The parent's `tasks.md` template already numbers tasks natively as `T1`, `T2` throughout its
dependency graphs and diagrams — that satisfies this rule as-is, no overlay needed. The parent's
`specify.md` and `design.md` templates have no ID slot for stories/components/decisions, so
`references.extended/specify.md` and `references.extended/design.md` (loaded per the Reference
Extension Convention above) patch those templates with the `US-`/`DC-` id.

## Commit Log: `commits.md`

Every feature that produces at least one atomic commit maintains
`.specs/features/[feature]/commits.md` — a sequential list of that feature's commit hashes,
created on the first commit (never earlier) and appended to immediately after each subsequent
commit lands. Only commits traceable to this feature's tasks or fix tasks qualify — commits made
outside the feature's context are never added. Full mechanics (what qualifies, format, Verifier
cross-check): `references.extended/implement.md`, loaded per the Reference Extension Convention
above.

## Phase Models

Each phase has a model tier it is expected to run on, recorded in [Subagent Models](../../templates/subagent-models.md):

| Phase | Model |
|-------|-------|
| Design | `sonnet` |
| Execute | `sonnet` |
| Specify | `sonnet` |
| Tasks | `haiku` |

Tasks sits a tier below the rest deliberately: by the time it runs, Specify and Design have already made every judgment call, and Tasks is a mechanical decomposition of an existing design into atomic units — the one phase where a cheaper model changes throughput without changing what gets decided.

**This skill never dispatches itself into a subagent to honor that.** All four phases are interactive by nature — Specify asks clarifying questions, Design surfaces trade-offs, Execute reports progress — and a dispatched `Agent` cannot pause for a reply. So the tiers are enforced by whoever *calls* the phase:

- **Called by an orchestrator** (`build-feature`'s Steps 6a/6b/7/9 are the reference implementation) → the orchestrator dispatches each phase as its own subagent with the model pinned per the table. That is where the table binds.
- **Invoked directly by the user** → the phase runs in that conversation, on whatever model the session is using. Nothing here overrides the user's session model or asks them to switch; note the intended tier if it's obviously mismatched and let them decide.

The model never varies with whether a human is reviewing the phase's output. Approval gates decide where a run pauses, not how capable the work is.

## Technical Design Docs → `technical-design-doc-creator`

**Overrides the parent.** The parent's description routes formal technical design docs to
`create-technical-design-doc` — **that skill does not exist** (no directory, registry entry,
or trigger anywhere). The actual installed skill is **`technical-design-doc-creator`** (Tech
Leads Club). When a task needs a formal Technical Design Document (TDD), invoke
`technical-design-doc-creator`; ignore the parent's stale `create-technical-design-doc`
pointer. The parent's own Design phase still covers lighter spec-style design notes inline —
reach for `technical-design-doc-creator` only when a full standalone TDD is wanted.
