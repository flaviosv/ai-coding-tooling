Model tier for each named `Agent`-dispatch site in this project. Load this file from [../SKILL.md](../SKILL.md) once the dispatch site is identified as one of the skills listed below — the two hard facts and the four-field contract there apply regardless of which row is used.

| Skill | Dispatch site | Model |
|-------|---------------|-------|
| `architecture-evaluate` | its own run, all three modes (self-pinned — see the skill's Model guardrail) | `sonnet` |
| `build-feature` | orchestrator — the invoking conversation, not a dispatch | `sonnet` (recommended) |
| `build-feature` | Step 3 — architecture-evaluate gate (decision only) | `haiku` |
| `build-feature` | Step 6a — Specify | `sonnet` |
| `build-feature` | Step 6b — Design | `sonnet` |
| `build-feature` | Step 7 — Tasks | `haiku` |
| `build-feature` | Step 9 — Execute | `sonnet` |
| `build-feature` | Step 12 — architecture-evaluate (Incremental) | `sonnet` |
| `build-feature` | Step 14 — merge-conflict resolution | `sonnet` |
| `code-review` | Batch Mode fix and review workers, per PR | `sonnet` |
| `code-review` | Stage 1 review worker | `sonnet` |
| `code-review` | Stage 3 fix worker | `sonnet` |
| `code-review` | Step 6 dimension subagents, every entry, scope, and tier | `sonnet` |
| `session-evaluate` | Step 6 covering agent or per-dimension agents, every tier | `opus` |

`build-feature`'s orchestrator row is the one entry nothing can enforce — it's whatever model the user's own session runs on. It's listed because `grilling` (Step 4) and `code-review` (Step 11, whose own workers carry the heavy work) run live in that conversation rather than in a dispatch; the orchestrator's tier is a real quality input, not just bookkeeping.

## Invariants

- **Model never varies with `human_review`.** A step runs on the same model whether or not a human is gating it — `human_review` decides where a run *pauses*, never how capable the thing doing the work is.
- **Merge-conflict resolution stays on `sonnet`.** It reasons about two divergent implementations of the same behavior and must detect ambiguity and stop rather than pick a side — the exact failure a weaker model commits silently. It also runs only when a PR actually conflicts, so pinning it up costs almost nothing.
- **`session-evaluate` sits outside `build-feature`'s pipeline** but is pinned to `opus` in its own right — classification work (matching a digest signal to a catalog class, judging Structural vs Incidental, attributing a fix target) is reasoning-dense enough to warrant it.
- **A tier change here is a pipeline change.** `code-review`'s review worker delegates to its dimension subagents and its fix worker acts on their findings, and `build-feature`'s Step 11 runs all of it; retiering one row without the others leaves the stack inconsistent. Change the rows together.
