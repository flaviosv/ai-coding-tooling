---
name: subagent-models
description: Shared model-pinning matrix for every `Agent`-tool dispatch across build-feature and the skills it orchestrates — which model each dispatch site runs on, plus the alias and effort rules that govern how a model is set at all.
type: template
---

## Why this exists

Model choice used to live as prose inside each skill, restated at every dispatch site — roughly fifteen places across six files, plus a diagram that restated them again. Retuning the pipeline meant hunting all of them, and any one missed left a step silently running on the wrong tier. This table is the single authority: a skill names its dispatch site here and links to this file rather than hardcoding a model in prose.

A skill that dispatches an `Agent` **must** set `model` explicitly. Never omit it to let a subagent inherit the calling session's model — a dispatch site's tier is a property of the work, not of whoever happened to invoke it.

## Two hard facts about the `Agent` tool

**1. `model` takes one of four short aliases, verbatim: `sonnet`, `opus`, `haiku`, `fable`.** Never resolve an alias into a versioned model ID (`claude-haiku-4-5-…`, `claude-sonnet-5`, …) on the way to the call, however confidently the environment advertises one. The param accepts only the four aliases, so a versioned ID fails input validation and the subagent never starts. A launch rejected that way did nothing at all — no worktree, no checkout, no commit — so correct the param and relaunch; it doesn't consume any retry the dispatching skill allows.

**2. There is no reasoning-effort parameter.** Effort cannot be set on a dispatch. Where a step wants high effort, the only mechanism is an explicit instruction in the subagent's own prompt (e.g. *"work at high effort: be thorough, verify every finding against the actual diff before including it"*). Treat that as steering, not as a knob — two dispatch sites on the same model differ only by what their prompts say, never by cost or capability. When a step genuinely needs a different tier, change the **model**, not the prose.

## The matrix

| Skill | Dispatch site | Model |
|-------|---------------|-------|
| `architecture-evaluate` | its own run, all three modes (self-pinned — see the skill's Model guardrail) | `sonnet` |
| `build-feature` | orchestrator — the invoking conversation, not a dispatch | `sonnet` (recommended) |
| `build-feature` | Step 3 — architecture-evaluate gate (decision only) | `haiku` |
| `build-feature` | Step 6a — Specify | `sonnet` |
| `build-feature` | Step 6b — Design | `sonnet` |
| `build-feature` | Step 7 — Tasks | `haiku` |
| `build-feature` | Step 9 — Execute | `sonnet` |
| `build-feature` | Step 11 — complete-review wrapper | `sonnet` |
| `build-feature` | Step 12 — fix-review wrapper | `haiku` |
| `build-feature` | Step 13 — architecture-evaluate (Incremental) | `sonnet` |
| `build-feature` | Step 15 — merge-conflict resolution | `sonnet` |
| `code-review` | Step 6 dimension subagents, every mode and tier | `sonnet` |
| `complete-review` | Batch Mode per-PR subagents | `sonnet` |
| `complete-review` | Single PR Mode review subagent | `sonnet` |
| `fix-review` | Batch Mode per-PR subagents | `haiku` |
| `fix-review` | GitHub/Session-Only Mode per-cluster fix subagents | `haiku` |
| `tests-code-review` | Step 6 dimension subagents, every mode and tier | `sonnet` |

`build-feature`'s orchestrator row is the one entry nothing can enforce — it's whatever model the user's own session runs on. It is listed because two things inherit it: `grilling` (Step 4) and `design-sync` (Step 14) both run live in that conversation rather than in a dispatch. Grilling's notes seed `spec.md`, which every later step elaborates, so the orchestrator's tier is a real quality input, not just bookkeeping.

## Invariants

- **Model never varies with `human_review`.** A step runs on the same model whether or not a human is gating it. `human_review` decides where a run *pauses*, never how capable the thing doing the work is — a pipeline that quietly gets weaker when nobody is watching is the opposite of what that parameter is for.
- **Merge-conflict resolution stays on `sonnet`.** It reasons about two divergent implementations of the same behavior and is explicitly required to detect ambiguity and stop rather than pick a side — the exact failure a weaker model commits silently. It also runs only when a PR actually conflicts, so pinning it up costs almost nothing.
- **A tier change here is a pipeline change.** `complete-review` delegates the real work to `code-review`/`tests-code-review`; retiering one without the others leaves the stack inconsistent. Change the rows together.
