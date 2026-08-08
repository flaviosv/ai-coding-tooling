# Review Dispatch Efficiency — Tasks

## Execution Protocol (MANDATORY — do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Spec:** [spec.md](spec.md) — Feature ID: RD-EFFICIENCY
**Design:** skipped (both changes reuse already-proven mechanisms — the Medium-tier single-agent pattern for the merges, standard sequential subagent dispatch for ship-spec — no new architecture)
**Status:** Done — Verifier PASS after 1 fix round (2 iterations). Commits: `cc829ab` (T1), `39a47c7` (T2+T3, combined per SPEC_DEVIATION), `80b44de` (T4), `82f91b8`+`0766349` (Verifier gap fixes: RD-06/RD-13). See `validation.md` for the full report and `~/.claude/skills/tlc-spec-driven/scripts/lessons.py` entries L-001/L-002 for distilled lessons.

---

## Test Coverage Matrix

> Generated from codebase and project guidelines — confirm before Execute. Guidelines found: `CLAUDE.md` ("Do not apply typical software engineering heuristics — including test coverage — to `.md` files; clarity and correctness of content is what matters"), reconfirmed by CR-TOKEN/TCR-TOKEN's own precedent (`.specs/features/tests-code-review-token-efficiency/tasks.md`: "All tasks edit a markdown skill file... verification is grep/structural inspection").

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
|---|---|---|---|---|
| Skill definition (`.md`) | none | Structural/grep inspection only — no automated test suite applies to skill prose | `skills/*/SKILL.md` | `grep -n <pattern> <file>` (per-task, see Done-when) |

## Gate Check Commands

| Gate Level | When to Use | Command |
|---|---|---|
| Inspection | After every task (all tasks are markdown-only) | grep/structural verification per the task's Done-when criteria, plus a full-file consistency grep for stale references to the pre-merge dimension names/counts |

---

## Tools (all tasks)

`Edit`, `Read`, `Bash`/`Grep` (grep verification). No MCPs. No skills. Same convention as CR-TOKEN/TCR-TOKEN's own tasks (`.specs/features/tests-code-review-token-efficiency/tasks.md`) — not re-asked per task since there's no meaningful alternative for markdown-only edits.

---

## Execution Plan

Single phase — 4 tasks, well under the ~8-task single-batch threshold, executed inline with no sub-agent delegation.

### Phase 1: Dispatch Merges + Ship-Spec Fix

```
T1
T2 → T3
T4
```

T1 and T4 have no dependencies (different files, independent of everything else). T2 → T3 is a real dependency: both edit `skills/tests-code-review/SKILL.md`'s same tables (Agent Roster, Step 6 dispatch, banner examples), so T3 lands second to keep each commit's diff clean and avoid overlapping edits landing out of order. All four execute in listed order (T1, T2, T3, T4) regardless of the independent ones' lack of a drawn arrow — execution is strictly sequential per the skill's own rules.

---

## Task Breakdown

### T1: code-review — merge architecture-reviewer + code-quality-reviewer

**What**: Merge `architecture-reviewer` and `code-quality-reviewer` into one delegated agent (`design-quality-reviewer`) throughout `skills/code-review/SKILL.md` — Checklist Matrix, Agent Roster, Step 6 execution-mode description, Review Plan agent-count language, complexity-banner examples, and workflow examples. Findings still tag by original dimension (`architecture` / `code-quality`) so the at-a-glance table keeps two rows.
**Where**: `skills/code-review/SKILL.md`
**Depends on**: None
**Reuses**: The Medium-tier single-agent mechanism already in the file (union-of-checklists `## Before You Begin` block, findings tagged by dimension) — same pattern, applied to a merged pair instead of all dimensions.
**Requirement**: RD-01, RD-02, RD-03, RD-04, RD-05, RD-06

**Tools**: Edit, Read, Bash/Grep. No MCPs. No skills.

**Done when**:
- [x] Checklist Matrix and Agent Roster show one `design-quality-reviewer` row (union checklist set) instead of separate `architecture-reviewer`/`code-quality-reviewer` rows
- [x] Step 6 Large/Complex execution-mode text describes `design-quality-reviewer` dispatching once and returning findings tagged by both original dimensions
- [x] `regression-reviewer`, `performance-reviewer`, `security-reviewer`, `requirements-tracer` sections are unchanged (still independently dispatched)
- [x] Content-type table (Axis 2) still lists `code-quality-reviewer` alone for `docs-only`/`frontend-assets-only` types where `architecture-reviewer` isn't active — no merge applies when only one of the pair is active
- [x] Review Plan template and every complexity-banner example with `general` content + all dimensions active shows the reduced agent count (4, not 5)
- [x] Failure-handling text states both tagged dimensions show `⚠️ not executed — <reason>` if the merged agent fails
- [x] Workflow examples (Step 5/6 narrative) reflect the new agent count
- [x] `metadata.version` bumped (2.6.1 → 2.7.0 — new capability, not a patch-level fix)

**Verify**:
```bash
grep -n "design-quality-reviewer" skills/code-review/SKILL.md | wc -l    # present in Checklist Matrix, Agent Roster, Step 6, examples
grep -n "architecture-reviewer\|code-quality-reviewer" skills/code-review/SKILL.md   # only appear as finding-tag labels / dimension names, not as separate dispatched-agent rows
grep -n "Parallel — 5 agents" skills/code-review/SKILL.md    # → 0 for general-content, all-dimensions-active examples (now 4)
grep -n "version:" skills/code-review/SKILL.md   # → 2.7.0
```

**Tests**: none **Gate**: inspection
**Commit**: `feat(code-review): merge architecture + code-quality dimensions into one agent`

---

### T2: tests-code-review — merge isolation-reviewer + performance-reviewer

**SPEC_DEVIATION**: Landed together with T3 in one commit (`39a47c7`) — both merges edit the same Agent Roster table and Step 6 Merge Rule paragraph, and this environment doesn't support interactive git (`git add -p`) to split one coherent table edit into two commits after the fact. See T3 for the combined commit's full message.

**What**: Merge `isolation-reviewer` and `performance-reviewer` into one delegated agent (`execution-reviewer`) throughout `skills/tests-code-review/SKILL.md` — Agent Roster, Step 6 execution-mode description, degraded-mode handling (both were the only two dimensions degrading without `TESTING.md` — now the merged agent degrades as a whole), Review Plan agent-count language, banner examples.
**Where**: `skills/tests-code-review/SKILL.md`
**Depends on**: None
**Reuses**: Same Medium-tier single-agent union-checklist mechanism as T1.
**Requirement**: RD-07, RD-09, RD-10 (isolation/performance portion), RD-11, RD-12, RD-13 (isolation/performance portion)

**Tools**: Edit, Read, Bash/Grep. No MCPs. No skills.

**Done when**:
- [x] Agent Roster shows one `execution-reviewer` row (self-loads `test-review-checklist.md` + `<stack>-*-tests-code-review.md` + full 7-doc set) instead of separate `isolation-reviewer`/`performance-reviewer` rows
- [x] `TESTING.md`-absent degraded-mode note now refers to `execution-reviewer` running degraded (single trigger, was two)
- [x] `coverage-reviewer`, `clarity-reviewer`(→`craft-reviewer`), `maintainability-reviewer`(→`craft-reviewer`), `gap-detector` sections landed together in the same commit (see SPEC_DEVIATION above) rather than staying unchanged at this point
- [x] Step 6 execution-mode table/text describes `execution-reviewer` dispatching once, findings tagged by both original dimensions
- [x] Failure-handling text states both tagged dimensions show `⚠️ not executed — <reason>` if the merged agent fails

**Verify**:
```bash
grep -n "execution-reviewer" skills/tests-code-review/SKILL.md | wc -l
grep -n "isolation-reviewer\|performance-reviewer" skills/tests-code-review/SKILL.md   # only as finding-tag labels, not separate dispatched-agent rows
grep -n "TESTING.md.*degraded\|degraded.*TESTING" skills/tests-code-review/SKILL.md    # refers to execution-reviewer, singular
```

**Tests**: none **Gate**: inspection
**Commit**: `feat(tests-code-review): merge isolation + performance dimensions into one agent`

---

### T3: tests-code-review — merge clarity-reviewer + maintainability-reviewer, finalize consistency

**SPEC_DEVIATION**: Landed together with T2 in one commit — `39a47c7 feat(tests-code-review): merge isolation+performance and clarity+maintainability into two agents`. Reason: see T2's note above. Both tasks' Done-when criteria verified together before the single commit (see Verify commands under each task — all ran clean against the combined edit).

**What**: Merge `clarity-reviewer` and `maintainability-reviewer` into one delegated agent (`craft-reviewer`), same mechanism as T2. Then do a whole-file consistency pass: Review Plan agent-count language, every complexity-banner example, workflow examples, and the version bump — covering BOTH T2's and this task's merges together, since both must be reflected consistently in the same shared sections (banner examples, agent-count language) that T2 intentionally left untouched.
**Where**: `skills/tests-code-review/SKILL.md`
**Depends on**: T2
**Reuses**: Same mechanism as T1/T2.
**Requirement**: RD-08, RD-10 (clarity/maintainability portion + final consistency), RD-11 (final), RD-12 (final), RD-13 (clarity/maintainability portion)

**Tools**: Edit, Read, Bash/Grep. No MCPs. No skills.

**Done when**:
- [x] Agent Roster shows one `craft-reviewer` row (same self-loading set as any reviewing agent) instead of separate `clarity-reviewer`/`maintainability-reviewer` rows
- [x] `coverage-reviewer` and `gap-detector` sections remain untouched (both merges done, neither touches these)
- [x] Step 6 execution-mode table/text describes both `execution-reviewer` and `craft-reviewer` dispatching once each, alongside standalone `coverage-reviewer` and conditional `gap-detector`
- [x] Failure-handling text covers `craft-reviewer` the same way T2 covered `execution-reviewer`
- [x] Every Large/Complex-tier complexity-banner example shows the reduced agent count (3 dimension agents + conditional `gap-detector`, not 5/6)
- [x] Review Plan template and workflow examples reflect the new agent count
- [x] `metadata.version` bumped (2.4.1 → 2.5.0 — new capability, not a patch-level fix)

**Verify**:
```bash
grep -n "craft-reviewer" skills/tests-code-review/SKILL.md | wc -l
grep -n "clarity-reviewer\|maintainability-reviewer" skills/tests-code-review/SKILL.md   # only as finding-tag labels
grep -n "Parallel — 5 agents\|Parallel — 6 agents" skills/tests-code-review/SKILL.md     # only remaining hits should be Complex-tier's gap-detector-inclusive count if unaffected by this merge; verify each hit manually
grep -n "version:" skills/tests-code-review/SKILL.md   # → 2.5.0
```

**Tests**: none **Gate**: inspection
**Commit**: `feat(tests-code-review): merge clarity + maintainability dimensions into one agent`

---

### T4: ship-spec — merge Step 6 into one sequential subagent

**What**: Rewrite `ship-spec`'s Step 6 to spawn ONE subagent that invokes `code-review` then `tests-code-review` sequentially (strictly in that order, within the same subagent conversation) instead of two separate subagent dispatches. The subagent returns one compact result covering both skills' finding counts. Each skill still posts its own separate pending GitHub review — only the subagent PROCESS merges, not the two reviews.
**Where**: `skills/ship-spec/SKILL.md`
**Depends on**: None
**Reuses**: N/A — this is `ship-spec`'s only per-skill dispatch section.
**Requirement**: RD-14, RD-15, RD-16, RD-17, RD-18

**Tools**: Edit, Read, Bash/Grep. No MCPs. No skills.

**Done when**:
- [x] Step 6 describes spawning exactly one subagent (not "run `code-review`'s subagent to completion before starting `tests-code-review`'s" as two separate dispatches)
- [x] The subagent's prompt instructs it to invoke `code-review` in GitHub PR mode, wait for its pending review to post, THEN invoke `tests-code-review` the same way — sequential within its own conversation
- [x] The subagent's return contract stays "compact result only" — now covering both skills' finding counts/severity breakdowns in one return, not two
- [x] Guardrail bullet updated to reflect the new single-subagent structure (sequential-by-construction) without weakening the underlying constraint (still never posts two pending reviews concurrently); also added a new bullet for scoped partial-failure retry
- [x] Retry-on-failure rule is scoped per-skill within the single subagent (a `code-review` failure doesn't block `tests-code-review` from still running)
- [x] Step 7 (Report) and the worked example updated to reflect one subagent dispatch instead of two, same total finding-count reporting as before
- [x] `metadata.version` bumped (1.2.1 → 1.3.0 — dispatch-mechanism change)

**Verify**:
```bash
grep -n "Spawn a subagent" skills/ship-spec/SKILL.md | wc -l   # → 1 (was implicitly 2 via "for each of code-review and tests-code-review, in turn")
grep -n "never in parallel\|in turn" skills/ship-spec/SKILL.md
grep -n "version:" skills/ship-spec/SKILL.md   # → 1.3.0
```

**Tests**: none **Gate**: inspection
**Commit**: `refactor(ship-spec): merge review-and-publish step into one sequential subagent`

---

## Requirement Coverage

| Requirement | Task |
|---|---|
| RD-01 | T1 |
| RD-02 | T1 |
| RD-03 | T1 |
| RD-04 | T1 |
| RD-05 | T1 |
| RD-06 | T1 |
| RD-07 | T2 |
| RD-08 | T3 |
| RD-09 | T2 |
| RD-10 | T2, T3 |
| RD-11 | T2, T3 |
| RD-12 | T2, T3 |
| RD-13 | T2, T3 |
| RD-14 | T4 |
| RD-15 | T4 |
| RD-16 | T4 |
| RD-17 | T4 |
| RD-18 | T4 |

All 18 requirements covered.

---

## Task Granularity Check

| Task | Scope | Status |
|---|---|---|
| T1: Merge architecture + code-quality | 1 file, 1 cohesive merge (checklist/roster/dispatch/examples/version, all describing the same single change) | ✅ Granular |
| T2: Merge isolation + performance | 1 file, 1 cohesive merge | ✅ Granular |
| T3: Merge clarity + maintainability + finalize consistency | 1 file, 1 cohesive merge + the shared cross-merge consistency pass that only makes sense once both merges exist | ✅ Granular (consistency pass is inseparable from T3 — banner/agent-count text can't be finalized after only one of two merges lands) |
| T4: Ship-spec Step 6 merge | 1 file, 1 cohesive dispatch-mechanism change | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
|---|---|---|---|
| T1 | None | (standalone, no arrow) | ✅ Match |
| T2 | None | (standalone, no arrow) | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | (standalone, no arrow) | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
|---|---|---|---|---|
| T1 | Skill definition (`.md`) | none | none | ✅ OK |
| T2 | Skill definition (`.md`) | none | none | ✅ OK |
| T3 | Skill definition (`.md`) | none | none | ✅ OK |
| T4 | Skill definition (`.md`) | none | none | ✅ OK |

All four tasks match the Test Coverage Matrix's "none" requirement for skill-definition files — no violations.
