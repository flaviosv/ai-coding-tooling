# LESSONS — auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation — do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 — When merging two dispatched review agents into one, explicitly update the failure/degraded-handling text (Step 7 or equivalent) to state both tagged dimensions are affected -- not just the success-case Agent Roster/Checklist Matrix entries
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `review-skills` · harmful: 0
- features: review-dispatch-efficiency
- evidence: RD-06, RD-13 (review-skills)
- last seen: 2026-08-08T23:43:41Z

### L-002 — When two planned tasks edit the same shared table or section in one file, plan them as a single task/commit from the start -- non-interactive git cannot cleanly split one coherent table edit into two commits after the fact
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `tlc-spec-driven` · harmful: 0
- features: review-dispatch-efficiency
- evidence: tasks.md T2/T3 SPEC_DEVIATION note, commit 39a47c7 (tlc-spec-driven)
- last seen: 2026-08-08T23:43:42Z

### L-003 — When specifying failure handling for a multi-invocation flow, explicitly define the all-failed branch, not just the partial-failure branch — partial-failure logic alone silently leaves full failure undefined and risks an empty/invalid write.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `ship-spec` · harmful: 0
- features: ship-spec-review-fix-flow
- evidence: spec.md Edge Case / design.md Error Handling Strategy — Step 6 full-failure path (ship-spec)
- last seen: 2026-08-09T01:03:47Z

### L-004 — After changing a subagent's model tier or dispatch mechanism in a Steps section, grep the Guardrails section too — guardrail bullets restate mechanism details and go stale silently when only the Steps are updated.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `ship-spec` · harmful: 0
- features: ship-spec-review-fix-flow
- evidence: skills/ship-spec/SKILL.md:36 — stale Sonnet-subagent Guardrails text vs Haiku drafting mechanism (ship-spec)
- last seen: 2026-08-09T01:03:47Z

### L-005 — When design.md commits to surfacing (not fixing) a pre-existing limitation, verify a task in tasks.md actually implements that reporting — commitments logged in Out-of-Scope or edge-case tables can fall through task decomposition unnoticed.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `ship-spec` · harmful: 0
- features: ship-spec-review-fix-flow
- evidence: spec.md Edge Case (page-cap reporting) — no task in tasks.md ever implemented it (ship-spec)
- last seen: 2026-08-09T01:03:47Z

## Quarantined (failed when applied — ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
