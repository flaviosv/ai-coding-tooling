# Review Dispatch Efficiency Validation

**Date**: 2026-08-08
**Spec**: `.specs/features/review-dispatch-efficiency/spec.md`
**Diff range**: `cc829ab`, `39a47c7`, `80b44de`
**Verifier**: independent sub-agent (author ≠ verifier)

**Adaptation note**: This feature edits markdown skill-definition files, not application code (per this repo's `CLAUDE.md`: "Do not apply typical software engineering heuristics — including test coverage — to `.md` files", reconfirmed by `tests-code-review-token-efficiency/tasks.md`'s own precedent). The Discrimination Sensor (code-mutation) step is replaced with a **Consistency Sweep** — an independent grep-based search across all 3 changed files for stale agent-name references, wrong agent counts, or any place the new merge mechanism isn't reflected. Interactive UAT is skipped (not applicable to skill prose).

---

## Task Completion

| Task | Status | Notes |
|---|---|---|
| T1 | ✅ Done | Committed as `cc829ab`, as planned |
| T2 | ✅ Done | **SPEC_DEVIATION** (recorded in tasks.md): landed together with T3 in one commit (`39a47c7`) rather than two separate commits. Does not affect requirement coverage — see Requirement Coverage Cross-Check below. |
| T3 | ✅ Done | Same commit as T2 (`39a47c7`) — see SPEC_DEVIATION above |
| T4 | ✅ Done | Committed as `80b44de`, as planned |

---

## Spec-Anchored Acceptance Criteria

### P1: Code-Review Dimension Merge

| # | Criterion (WHEN X THEN Y) | `file:line` evidence | Result |
|---|---|---|---|
| RD-01 | Large/Complex + `general` content → exactly ONE agent (`design-quality-reviewer`) covers both architecture + code-quality, self-loading union of checklists | `skills/code-review/SKILL.md:334` (Merge rule), `:395` (Checklist Matrix row — union set, both dimensions had identical checklists so union == same set) | ✅ PASS |
| RD-02 | Merged agent's findings tagged by original dimension; at-a-glance table keeps two rows | `skills/code-review/SKILL.md:408` ("Findings returned tagged by original dimension — the at-a-glance table and zoned report keep separate Architecture / Code Quality & Docs rows"), at-a-glance table unchanged at `:496-497` | ✅ PASS |
| RD-03 | `regression-reviewer`, `performance-reviewer`, `security-reviewer`, `requirements-tracer` remain independently dispatched | `skills/code-review/SKILL.md:397-400` (Checklist Matrix), `:410-413` (Agent Roster) — all four rows unchanged, still separate | ✅ PASS |
| RD-04 | `docs-only` content (only `code-quality-reviewer` + conditional `requirements-tracer` active) → NO merge, `code-quality-reviewer` dispatches alone | `skills/code-review/SKILL.md:267` (Axis 2 table — no `architecture-reviewer` in `docs-only` row), `:334` ("`architecture-reviewer` never appears in the active set for `docs-only`/`config-infra-only`/`frontend-assets-only`... it dispatches alone exactly as before the merge") | ✅ PASS |
| RD-05 | Review Plan / complexity banner reflect reduced agent count (4, not 5) for `general` content, all dimensions active | `skills/code-review/SKILL.md:302` — Complex-tier example updated `Parallel — 5 agents` → `Parallel — 4 agents`; this is the only banner example matching general-content/all-dimensions-active (Medium example's "5 dimensions" is a dimension count, not an agent count, and is correctly unaffected) | ✅ PASS |
| RD-06 | Merged agent fails/times out → BOTH architecture and code-quality at-a-glance rows show `⚠️ not executed — <reason>` | **No evidence found.** `skills/code-review/SKILL.md:451` (Step 7 outcome table) still reads "Failed or timed out → Mark **dimension** as `⚠️ not executed`" (singular, generic, unchanged by the diff — confirmed no hunk touches Step 7 in `cc829ab`). Nothing in the file explicitly instructs marking BOTH tagged rows when the merged agent fails. | ❌ GAP — see Consistency Sweep finding #1 |

**Subtotal: 5/6 PASS, 1 GAP**

### P1: Tests-Code-Review Dimension Merges

| # | Criterion (WHEN X THEN Y) | `file:line` evidence | Result |
|---|---|---|---|
| RD-07 | Large/Complex → exactly ONE agent (`execution-reviewer`) covers isolation + performance, self-loading `test-review-checklist.md` + stack file + full 7-doc set | `skills/tests-code-review/SKILL.md:313` (Merge rule), `:378` (Agent Roster row) | ✅ PASS |
| RD-08 | Large/Complex → exactly ONE agent (`craft-reviewer`) covers clarity + maintainability, same self-loading mechanism | `skills/tests-code-review/SKILL.md:313`, `:377` (Agent Roster row) | ✅ PASS |
| RD-09 | `TESTING.md` absent → `execution-reviewer` runs degraded (was two individual triggers, now one merged) | `skills/tests-code-review/SKILL.md:131` ("at Large/Complex tier this affects the merged `execution-reviewer` agent as a whole"), `:378` (Degrades-without column: `testing`) | ✅ PASS |
| RD-10 | Merged agents' findings tagged by original dimension; at-a-glance table keeps 4 rows (clarity, coverage, isolation, maintainability) + performance findings | `skills/tests-code-review/SKILL.md:313` ("findings tagged by original dimension"), `:377-378` (Agent Roster rows state tag), at-a-glance table unchanged `:448-453` (6 rows: Clarity, Coverage, Coverage Gaps, Isolation, Maintainability, Performance) | ✅ PASS |
| RD-11 | `coverage-reviewer` / `gap-detector` remain independently dispatched, untouched by either merge | `skills/tests-code-review/SKILL.md:313` ("`coverage-reviewer` and `gap-detector` are untouched by either merge"), Agent Roster rows `:376`, `:379` unchanged | ✅ PASS |
| RD-12 | Review Plan / banner reflect reduced count (3, not 5) plus conditional `gap-detector` | `skills/tests-code-review/SKILL.md:290-291` — `Parallel — 5 agents`→`3 agents` (Large), `6 agents`→`4 agents` (Complex, incl. `gap-detector`); Example 2 banner `:532` also updated to `4 agents` | ✅ PASS |
| RD-13 | Merged agent fails/times out → BOTH of its tagged dimensions' rows show `⚠️ not executed — <reason>` | **No evidence found.** `skills/tests-code-review/SKILL.md:406` (Step 7 outcome table) still reads "Failed or timed out → Mark **dimension** as `⚠️ not executed`" (singular, generic, unchanged by `39a47c7` — no hunk touches Step 7). Same gap pattern as RD-06. | ❌ GAP — see Consistency Sweep finding #1 |

**Subtotal: 6/7 PASS, 1 GAP**

### P2: Ship-Spec Wrapper Merge

| # | Criterion (WHEN X THEN Y) | `file:line` evidence | Result |
|---|---|---|---|
| RD-14 | Step 6 spawns exactly ONE subagent (not two) | `skills/ship-spec/SKILL.md:116` ("Spawn one subagent...") | ✅ PASS |
| RD-15 | Subagent invokes `code-review` first, waits, THEN `tests-code-review` — strictly sequential | `skills/ship-spec/SKILL.md:117-118` (steps a, b: "Wait for `code-review`'s pending review to finish posting, THEN invoke `tests-code-review`... strictly sequential, never parallel") | ✅ PASS |
| RD-16 | Subagent returns ONE compact result — finding counts + severity breakdown for each skill, nothing else | `skills/ship-spec/SKILL.md:119` (step c: "Return **only** one compact result covering both...") | ✅ PASS |
| RD-17 | Either skill's failure → retry-once-then-report rule applies, scoped to the failed skill only; other skill still runs/posts | `skills/ship-spec/SKILL.md:39` (Guardrails: "On a partial failure... retry with a fresh subagent instructed to run ONLY the failed skill"), `:119` (step c: other skill's result "still reported normally") | ✅ PASS |
| RD-18 | Each skill still posts its own SEPARATE pending GitHub review — merge doesn't merge the two reviews | `skills/ship-spec/SKILL.md:123` ("this still produces TWO separate pending reviews, one per skill, exactly as before") | ✅ PASS |

**Subtotal: 5/5 PASS**

---

**Total: 16/18 ACs PASS, 2/18 GAP (RD-06, RD-13)**

---

## Consistency Sweep

(Replaces Discrimination Sensor — not applicable to markdown skill-definition files; see Adaptation note.)

| # | Finding | Files | Severity | Status |
|---|---|---|---|---|
| 1 | **Step 7 failure-handling text was never updated to state dual-row marking for merged agents.** Both T1's and T2/T3's Done-when checklists explicitly claim "Failure-handling text states both tagged dimensions show `⚠️ not executed — <reason>` if the merged agent fails" (tasks.md:73, :107, :137 — all checked `[x]`), but neither diff (`cc829ab`, `39a47c7`) touches Step 7 ("Await + Fallback") in either file. Step 7 still reads the pre-merge generic singular-dimension rule: `Failed or timed out → Mark dimension as ⚠️ not executed — <reason>`. A reader following this text literally has no explicit instruction to propagate a merged agent's failure to both of its tagged rows — it's inferable from the Agent Roster's dimension-tagging description (success case only), not stated for the failure case. | `skills/code-review/SKILL.md:451`; `skills/tests-code-review/SKILL.md:406` | **Medium** — task Done-when overclaims; behavior is inferable but not explicit | ❌ FAIL |
| 2 | **Zoned-format "Zone letter assignment" tables still list pre-merge single-dimension agent names as the dispatching agent**, contradicting the new merge mechanism for the common case (Large/Complex, `general` content). Neither diff touches this table. In `code-review/SKILL.md`, row `Architecture → A → architecture-reviewer` and `Code Quality & Docs → Q → code-quality-reviewer` are only accurate for Performance Audit mode (where the merge explicitly doesn't apply, per `:428`) — in the far more common Large/Complex tier-based dispatch, the actual dispatching agent is `design-quality-reviewer`. In `tests-code-review/SKILL.md`, rows for `clarity-reviewer`, `isolation-reviewer`, `maintainability-reviewer`, `performance-reviewer` are now **entirely obsolete** — none of those agent names ever dispatch standalone anymore (Large/Complex merges them into `execution-reviewer`/`craft-reviewer`; Medium tier folds everything into one undifferentiated all-dimensions agent). This is exactly the "stale reference implying separate dispatch" failure mode the consistency sweep targets. | `skills/code-review/SKILL.md:516-523` (rows 518, 519); `skills/tests-code-review/SKILL.md:464-471` (rows 466, 469, 470, 471) | **Low-Medium** — prose-only, doesn't break the Zone-ID mechanism (Zone is keyed by dimension name, not agent name), but misleads a future reader/maintainer about which agent actually dispatches | ❌ FAIL |
| 3 | Sonar `issues_by_agent` routing key naming (`code_quality_reviewer`) | `skills/code-review/SKILL.md:225-229` | — | ✅ Not stale — accompanying comment (`:226-228`) explicitly documents the key is consumed by whichever agent (`design-quality-reviewer` or standalone) is actually dispatched; intentional, not a leftover |
| 4 | `ship-spec` "in turn" / two-subagent phrasing | `skills/ship-spec/SKILL.md` (full-file grep) | — | ✅ Clean — no remaining "in turn" or two-subagent language found |
| 5 | Remaining literal `architecture-reviewer`/`code-quality-reviewer` / `isolation-reviewer` / etc. mentions elsewhere in the two files | `skills/code-review/SKILL.md:267-269, 396, 409, 428, 633`; `skills/tests-code-review/SKILL.md:313` | — | ✅ All correctly scoped — content-type table (unmerged content types), standalone-dispatch clauses, and the explicit Performance Audit exception, all consistent with the merge rule's stated scope |

**Result**: 3/5 clean, 2/5 stale references found (findings #1 and #2 above) → **Consistency Sweep: FAIL**

---

## Code Quality

| Diff | Scope creep? | Unrelated changes? | Matches file conventions? | Minimal-necessary? |
|---|---|---|---|---|
| `cc829ab` (T1, code-review) | None — only touches version, Sonar comment, banner example, Merge rule paragraph, Checklist Matrix rows, Agent Roster rows, Performance Audit exception | None | Yes — `**Merge rule:**` bold-label style matches existing `**Multi-commit mode:**`/`**Thoroughness directive**` patterns; table formatting preserved | Yes, but incomplete — see Consistency Sweep #1 (Step 7 not updated) and #2 (Zone table not updated) |
| `39a47c7` (T2+T3, tests-code-review) | None — only touches version, degraded-mode note, banner examples, Merge rule paragraph, Agent Roster rows, worked-example agent counts | None | Yes — consistent with code-review's own merge-rule phrasing/pattern (intentional parity) | Yes, but incomplete — same two gaps as above, mirrored in this file |
| `80b44de` (T4, ship-spec) | None — only touches version, Guardrails bullets (updated + 1 new partial-failure bullet), Step 6 rewrite, worked example | None | Yes — bullet-list style, phrasing register matches surrounding Guardrails bullets | Yes — thorough and self-consistent; no residual "in turn"/two-dispatch language anywhere in the file |

**Commit-message accuracy**: All three commit messages accurately describe their diffs; `39a47c7`'s SPEC_DEVIATION note is honest about the T2/T3 merge and doesn't overstate what changed.

---

## Edge Cases

| # | Edge case | Handled? | Evidence |
|---|---|---|---|
| 1 | Large/Complex diff narrows to only ONE of a merge pair's dimensions (e.g. `docs-only`) → NO merge, single dimension dispatches alone | ✅ Yes | `skills/code-review/SKILL.md:267-269` (Axis 2 table never co-activates architecture with code-quality outside `general`), `:334` (Merge rule explicit fallback clause). `tests-code-review` has no content-type axis so this edge case is code-review-only, as spec states — confirmed no content-type axis exists in `skills/tests-code-review/SKILL.md` (no Axis 2 equivalent). |
| 2 | `impl_diff` empty in `tests-code-review`'s Large/Complex tier → `gap-detector` skipped, unaffected by merges | ✅ Yes | `skills/tests-code-review/SKILL.md:315` ("`gap-detector` is dispatched only when `impl_diff` is non-empty; otherwise its at-a-glance row shows `⚠️ skipped`") — this line is untouched by the diff and remains correct; `gap-detector` was never part of either merge pair per `:313` | 
| 3 | `ship-spec`'s `code-review` succeeds but `tests-code-review` fails after retry → report `code-review`'s count normally + `tests-code-review`'s failure reason, don't fail Step 6 wholesale | ✅ Yes | `skills/ship-spec/SKILL.md:119` (step c: "If one skill couldn't complete, return its failure reason in place of its counts — the other skill's result, if it succeeded, is still reported normally"), `:39` (Guardrails scoped-retry bullet) |

**Status**: ✅ All 3 edge cases handled correctly

---

## SPEC_DEVIATION Review (T2/T3 commit-granularity)

tasks.md records that T2 (isolation+performance) and T3 (clarity+maintainability) landed as one commit (`39a47c7`) instead of two, because both edit the same Agent Roster table and Step 6 Merge Rule paragraph and the environment doesn't support `git add -p`.

**Assessment**: This is a commit-granularity deviation only, not a requirement-coverage gap. Confirmed by re-deriving RD-07 through RD-13 directly against the current file content (not against tasks.md's checkbox claims) in the Spec-Anchored Acceptance Criteria section above — all 7 requirements trace to concrete `file:line` evidence in the combined commit's resulting file state. RD-07, RD-08, RD-09, RD-10, RD-11, RD-12 are fully satisfied; RD-13 has a genuine gap (see above), but that gap is identical in nature and cause to RD-06's gap in the separately-committed T1 — i.e., it is not caused by or related to the T2/T3 combination, it's the same category of miss the implementer made independently in both files. **The SPEC_DEVIATION itself is not the source of any requirement gap.**

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
|---|---|---|
| RD-01 | Pending | ✅ Verified |
| RD-02 | Pending | ✅ Verified |
| RD-03 | Pending | ✅ Verified |
| RD-04 | Pending | ✅ Verified |
| RD-05 | Pending | ✅ Verified |
| RD-06 | Pending | ❌ Needs Fix |
| RD-07 | Pending | ✅ Verified |
| RD-08 | Pending | ✅ Verified |
| RD-09 | Pending | ✅ Verified |
| RD-10 | Pending | ✅ Verified |
| RD-11 | Pending | ✅ Verified |
| RD-12 | Pending | ✅ Verified |
| RD-13 | Pending | ❌ Needs Fix |
| RD-14 | Pending | ✅ Verified |
| RD-15 | Pending | ✅ Verified |
| RD-16 | Pending | ✅ Verified |
| RD-17 | Pending | ✅ Verified |
| RD-18 | Pending | ✅ Verified |

---

## Fix Plans

### Fix 1: Explicit dual-row failure handling for merged agents (RD-06, RD-13)

- **Root cause**: T1 and T2/T3's Done-when checklists claimed Step 7 failure-handling text was updated to state both tagged dimensions show `⚠️ not executed` when a merged agent fails, but the actual diffs never touched Step 7 in either file — an oversight in execution vs. the task's own stated done-when criteria.
- **Fix task**: In `skills/code-review/SKILL.md` Step 7 (~line 451) and `skills/tests-code-review/SKILL.md` Step 7 (~line 406), add an explicit rule: when a merged agent (`design-quality-reviewer` / `execution-reviewer` / `craft-reviewer`) fails or times out, mark BOTH of its tagged dimension rows in the at-a-glance table as `⚠️ not executed — <reason>` (one agent's failure means both original dimensions went unreviewed).
- **Priority**: Major — directly contradicts an explicit spec AC (RD-06/RD-13) and a Done-when checkbox marked complete when it wasn't.

### Fix 2: Update Zone letter assignment tables to reflect merged dispatch (Consistency Sweep #2)

- **Root cause**: Neither T1 nor T2/T3 touched the Zoned-format "Zone letter assignment" table, which still lists pre-merge single-dimension agent names as each zone's dispatching agent.
- **Fix task**: In `skills/code-review/SKILL.md` (~line 516-523), update the Architecture/Code Quality & Docs rows to note `design-quality-reviewer` (merged, `general` content) vs. the Performance-Audit-mode exception. In `skills/tests-code-review/SKILL.md` (~line 464-471), update the Clarity/Isolation/Maintainability/Performance rows to reference `craft-reviewer`/`execution-reviewer` (Large/Complex) — these standalone agent names no longer dispatch under any tier.
- **Priority**: Minor — prose-only, doesn't break the Zone-ID mechanism, but misleads future maintainers.

---

## Summary

**Overall**: ⚠️ Issues — 2 concrete, fixable gaps found; core mechanism (dispatch merges, banner/plan updates, ship-spec sequential subagent) is correctly and thoroughly implemented

**Spec-anchored check**: 16/18 ACs matched spec outcome, 2 gaps (RD-06, RD-13)
**Consistency Sweep**: 3/5 clean, 2 stale references found (both pre-existing Zone/failure-handling text never touched by the merge diffs)
**Edge Cases**: 3/3 handled correctly
**Code Quality**: No scope creep, no unrelated changes, all 3 diffs match existing file conventions and are minimal-necessary within what they touched

**What works**: All three dispatch-merge mechanisms (`design-quality-reviewer`, `execution-reviewer`, `craft-reviewer`) are correctly wired into Checklist Matrix / Agent Roster / Merge Rule / banner examples / Review Plan language across both skill files. `ship-spec`'s Step 6 single-subagent sequential rewrite (T4) is exemplary — thorough, no loose ends, correctly updates Guardrails, Step 6, Step 7, and the worked example in lockstep. Content-type gating (RD-04), degraded-mode propagation (RD-09), and the ship-spec partial-failure edge case are all explicitly and correctly documented.

**Issues found**:
1. Step 7 "Await + Fallback" in both `code-review` and `tests-code-review` never got the explicit "both tagged dimensions" failure-handling text the tasks claimed was added (RD-06, RD-13) — Fix 1 above.
2. Zoned-format "Zone letter assignment" tables in both files still name pre-merge standalone agents as each zone's dispatcher, which is now stale/misleading for the common Large/Complex dispatch path — Fix 2 above.

**Next steps**: Apply Fix 1 and Fix 2 (both small, targeted text additions — no new architecture, no re-opened design questions), then re-run this Verifier's Spec-Anchored and Consistency Sweep checks against the fixed files.

---

## Re-verification (iteration 2)

**Date**: 2026-08-08
**Fix commits under test**: `82f91b8` (code-review), `0766349` (tests-code-review)
**Verifier**: independent sub-agent, second pass (author of fix ≠ this verifier)

This pass re-derives RD-06 and RD-13 from scratch against current file content, re-checks the two Zone-letter tables for accuracy against Step 6's actual merge rules, spot-checks 4 previously-PASS ACs for regressions in the touched files, and runs a final consistency grep across all 3 files. The prior evidence for the other 16 ACs (above) still holds — not re-litigated in full.

### RD-06 (code-review) — re-verified

**Criterion**: Merged agent (`design-quality-reviewer`) fails or times out → BOTH the Architecture and Code Quality & Docs at-a-glance rows show `⚠️ not executed — <reason>`.

**Evidence**: `skills/code-review/SKILL.md:455` — new line inserted directly after the Step 7 outcome table (`:448-453`):

> "**Merged agent (`design-quality-reviewer`) failure or timeout:** mark BOTH the Architecture and Code Quality & Docs at-a-glance rows as `⚠️ not executed — <reason>` — one agent's failure means both tagged dimensions went unreviewed. Same rule for degraded: if the merged agent runs degraded, both rows show `⚠️ degraded — <missing item>` (the specific missing item may differ per tag ... note this distinction in the row's summary text when it applies)."

This explicitly names both rows, both failure and degraded cases, and even goes beyond the AC's literal ask by handling the case where the two tags degrade for different reasons. **✅ PASS** — gap closed.

### RD-13 (tests-code-review) — re-verified

**Criterion**: Either merged agent (`execution-reviewer` / `craft-reviewer`) fails or times out → BOTH of its tagged dimensions' rows show `⚠️ not executed — <reason>`.

**Evidence**: `skills/tests-code-review/SKILL.md:410` — new line inserted directly after the Step 7 outcome table (`:403-408`):

> "**Merged agent failure or timeout (Large/Complex tier):** if `execution-reviewer` fails, mark BOTH the Isolation and Performance at-a-glance rows as `⚠️ not executed — <reason>`. If `craft-reviewer` fails, mark BOTH the Clarity and Maintainability rows the same way. One merged agent's failure means both its tagged dimensions went unreviewed. Same rule for degraded mode — both rows show `⚠️ degraded — <missing item>` when the merged agent runs degraded."

Covers both merged agents by name, both failure and degraded cases. **✅ PASS** — gap closed.

### Zone letter tables — re-checked for accuracy against Step 6

**`skills/code-review/SKILL.md:518-525`**:

| Zone | Letter | Dispatched by |
|------|--------|-------|
| Architecture | A | `design-quality-reviewer` (merged with Code Quality when both active — see Step 6 Merge Rule) |
| Code Quality & Docs | Q | `design-quality-reviewer` (merged, general content) or standalone `code-quality-reviewer` (narrowed content types) |

No longer names `architecture-reviewer` as a standalone dispatcher anywhere in this table. Cross-checked against Step 6's Merge Rule (`:334`, Large/Complex-tier, `general` content only) and the content-type table (`:267-269`, narrowed types never co-activate architecture) — the table's claims match. **✅ Accurate.**

**`skills/tests-code-review/SKILL.md:466-473`**:

| Zone | Letter | Dispatched by |
|------|--------|-------|
| Clarity | C | `craft-reviewer` (Large/Complex, merged with Maintainability) or the single Medium-tier agent |
| Isolation | I | `execution-reviewer` (Large/Complex, merged with Performance) or the single Medium-tier agent |
| Maintainability | M | `craft-reviewer` (Large/Complex, merged with Clarity) or the single Medium-tier agent |
| Performance | P | `execution-reviewer` (Large/Complex, merged with Isolation) or the single Medium-tier agent |

None of the four merged-away standalone names (`clarity-reviewer`, `isolation-reviewer`, `maintainability-reviewer`, `performance-reviewer`) remain anywhere in the file outside the Step 6 Merge Rule paragraph itself (confirmed by grep — see Final Consistency Sweep below). Cross-checked against Step 6 (`:313`, merge is Large/Complex-tier only; Medium dispatches one agent covering every dimension, `:309`) — the table's "or the single Medium-tier agent" qualifier is correct and, notably, more precise than the code-review file's equivalent table (see note below). **✅ Accurate.**

**Minor observation (not a gap, not a regression)**: `code-review`'s Zone table rows don't carry an explicit "or the single Medium-tier agent" qualifier the way `tests-code-review`'s rows now do — technically the Medium-tier agent in `code-review` isn't literally named `design-quality-reviewer` either. Confirmed via `git show cc829ab~1` / `39a47c7~1` that **neither file's Zone table ever carried a Medium-tier qualifier**, even before this feature — this is a pre-existing convention (Zone table names the tier-appropriate dispatcher for Large/Complex, the common subagent-review case, and has always glossed over Medium's single-agent mode). Not introduced by `82f91b8`, not a regression, not in scope for RD-06/RD-13 or the original Consistency Sweep finding (which was specifically about merged-away agents being wrongly called standalone dispatchers — that's fixed). Flagging only as a small thoroughness asymmetry between the two sibling fix commits, below the bar for a fix-plan item.

### Spot-check: 4 previously-PASS ACs re-verified against current file content

| AC | Re-check | Result |
|---|---|---|
| RD-01 (merge mechanism) | `skills/code-review/SKILL.md:334` Merge Rule paragraph and `:395` Checklist Matrix row read exactly as before — untouched by `82f91b8` (diff only touched Step 7 and the Zone table, confirmed via `git show 82f91b8`) | ✅ Still PASS, no regression |
| RD-03 (unaffected agents, code-review) | `skills/code-review/SKILL.md:397-400` (Checklist Matrix: `performance-reviewer`, `regression-reviewer`, `security-reviewer`, `requirements-tracer` rows) and `:410-413` (Agent Roster) unchanged | ✅ Still PASS, no regression |
| RD-09 (degraded mode, tests-code-review) | `skills/tests-code-review/SKILL.md:131` — "At Medium tier this affects the single all-dimensions agent's isolation/performance findings; at Large/Complex tier this affects the merged `execution-reviewer` agent as a whole" — untouched by `0766349` (diff only touched Step 7 and the Zone table) | ✅ Still PASS, no regression |
| RD-12 (banner/plan counts, tests-code-review) | `skills/tests-code-review/SKILL.md:290-291` — `Parallel — 3 agents` (Large), `4 agents` (Complex, incl. `gap-detector`) — unchanged | ✅ Still PASS, no regression |

No regressions found in either touched file outside the two intended edit zones (Step 7 addition, Zone table rewrite).

### Final Consistency Sweep (all 3 files)

Grep sweep for stale agent-name/count references across `skills/code-review/SKILL.md`, `skills/tests-code-review/SKILL.md`, `skills/ship-spec/SKILL.md`:

- `architecture-reviewer` / `code-quality-reviewer`: every remaining hit (`code-review/SKILL.md:228, 267-269, 334, 396, 409, 428, 521, 635`) is correctly scoped — content-type table for narrowed types, the Merge Rule's own explanation, the explicit standalone-dispatch clause ("whenever architecture isn't active"), and the explicit Performance Audit mode exception (`:428`, `:635` — merge intentionally doesn't apply there). No stale claim of standalone dispatch in the common tier-based path.
- `clarity-reviewer` / `isolation-reviewer` / `maintainability-reviewer`: zero hits outside `tests-code-review/SKILL.md:313` (the Merge Rule paragraph itself, which correctly describes the pre-merge names being merged). Zone table fully migrated.
- `performance-reviewer` (tests-code-review): only hit is the Merge Rule paragraph (`:313`) — correct, no stale standalone-dispatch claim remains.
- `5 agents` / `6 agents` stale banner counts: zero hits anywhere except inside Merge Rule prose describing the reduction ("reduces ... from 5 agents to 4" / "from 5 dimension agents to 3") — not stale banner examples, both banner examples (`code-review:302`, `tests-code-review:290-291`) already show the reduced counts.
- `ship-spec/SKILL.md`: no "in turn" or two-subagent-dispatch language found; file untouched by either fix commit (confirmed via `git show --stat` on both) and remains internally consistent with RD-14 through RD-18.

**Result**: Clean — no remaining stale references in any of the 3 files.

### Re-verification Summary

| Item | Status |
|---|---|
| RD-06 | ✅ Verified — dual-row failure/degraded handling explicit at `skills/code-review/SKILL.md:455` |
| RD-13 | ✅ Verified — dual-row failure/degraded handling explicit at `skills/tests-code-review/SKILL.md:410` |
| Zone table (code-review) | ✅ Accurate — no merged-away standalone claims, matches Step 6 |
| Zone table (tests-code-review) | ✅ Accurate — no merged-away standalone claims, matches Step 6, more precise than code-review's equivalent (Medium-tier qualifier) |
| Spot-checked ACs (RD-01, RD-03, RD-09, RD-12) | ✅ No regressions |
| Final consistency sweep (3 files) | ✅ Clean |

**Requirement Traceability — final update**:

| Requirement | Status (iteration 1) | Status (iteration 2) |
|---|---|---|
| RD-06 | ❌ Needs Fix | ✅ Verified |
| RD-13 | ❌ Needs Fix | ✅ Verified |
| All other (RD-01–05, 07–12, 14–18) | ✅ Verified | ✅ Verified (unchanged, spot-checked subset re-confirmed) |

**Overall verdict**: ✅ **PASS** — 18/18 ACs verified, Consistency Sweep clean, no regressions found in either fix commit's touched files. Feature RD-EFFICIENCY is ready to ship.
