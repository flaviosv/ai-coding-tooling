# Feature Spec — Review Dispatch Efficiency

**Feature ID:** RD-EFFICIENCY
**Status:** Implemented — Verifier PASS (2026-08-08, 2 iterations; see `validation.md`)
**Skill targets:** `skills/code-review/SKILL.md`, `skills/tests-code-review/SKILL.md`, `skills/ship-spec/SKILL.md`
**Parent pattern:** CR-TOKEN / TCR-TOKEN (both `Implemented`) — extends their agent-count-reduction principle from the Medium tier (already single-agent, restored 2026-08-08) to the Large/Complex tiers, plus a small companion fix in `ship-spec`.

---

## Problem Statement

Real usage data (6 sampled sessions, `~/.claude/tools/review-token-usage.py`, 150.9M tokens combined) confirms dimension-agent cost is dominated by `cache_read_input_tokens` — each dispatched agent independently re-primes the same diff, checklists, and codebase docs from a cold context. Checklist-overlap analysis found genuine merge candidates in both skills' Large/Complex-tier dispatch (one agent per dimension) that would cut agent count without diluting review focus, extending the exact mechanism the Medium tier already uses (one delegated agent covering multiple dimensions). Separately, `ship-spec`'s PR-review step pays a small, avoidable double context-priming cost by spawning two separate fresh subagents (one per skill) instead of one.

Two other candidates surfaced during investigation and were rejected — recorded here to prevent re-litigating them:
- Having `ship-spec` invoke the skills directly instead of via a subagent: doesn't reduce total tokens (the orchestration cost just relocates into `ship-spec`'s own persistent context) and violates its explicit context-isolation guardrail.
- Porting `code-review`'s content-type detection axis to `tests-code-review`: no real foundation — `tests-code-review`'s diff is already pre-filtered to test files only, which doesn't have the same content-type variance a whole-repo diff has. See Out of Scope.

---

## Goals

- [x] Reduce `code-review`'s Large/Complex-tier dimension-agent count from 5 to 4 by merging `architecture-reviewer` + `code-quality-reviewer`.
- [x] Reduce `tests-code-review`'s Large/Complex-tier dimension-agent count from 5 to 3 by merging `isolation-reviewer` + `performance-reviewer`, and `clarity-reviewer` + `maintainability-reviewer`.
- [x] Reduce `ship-spec`'s Step 6 double cold-start cost by running both skill invocations sequentially inside one subagent instead of two.
- [x] Preserve full review quality — no regression in findings coverage, at-a-glance table structure (each original dimension keeps its own row), or degraded-mode handling.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Further merging beyond the settled pairs (e.g. folding in `regression-reviewer`, `coverage-reviewer`, or `security-reviewer`) | Checklist- and/or focus-disjoint from every merge candidate — explicitly rejected during the checklist-overlap analysis (grilling session, 2026-08-08) |
| Model-tier changes (cheaper model for some dimensions) | Explicitly rejected — agent-count reduction is the correct lever, not model downgrade; user vetoed this directly |
| Relocating `ship-spec`'s review step into its own main context | Investigated and rejected — doesn't reduce total tokens, relocates them into a persistent context, and violates `ship-spec`'s explicit isolation guardrail |
| Content-type detection axis for `tests-code-review` | **Parked as a research spike, not a requirement.** No real foundation found: the diff is already pre-filtered to test files only (no formally-defined glob pattern exists for "test file" in the skill today), which doesn't have the whole-repo content-type variance `code-review`'s axis relies on. A genuine alternative (test-logic vs. test-support/fixture-only files) was considered and rejected — even a pure test-helper refactor still meaningfully engages most dimensions. Revisit only if someone finds real evidence of exploitable variance; do not invent an unproven classification to fill this gap. |
| Orchestrator-inlines-shared-docs-once prototype | Parked from the grilling session — revisit only if post-fix measurement (via `~/.claude/tools/review-token-usage.py`) still shows meaningful redundant-Read cost after this spec lands |
| `.specs/features/{code-review,tests-code-review}-subagent-orchestration` | Already marked `Abandoned — superseded` (task A, 2026-08-08) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|---|---|---|---|
| A merged agent's `## Before You Begin` block lists the UNION of both original dimensions' checklists (deduplicated) | Reuse the existing Medium-tier single-agent mechanism verbatim | Already proven, already implemented — Medium tier does exactly this for ALL dimensions today | y |
| A merged agent tags its returned findings by their ORIGINAL dimension name, not a new combined name | Preserve existing at-a-glance table structure (one row per original dimension) | Minimal-impact — the report's shape shouldn't change just because two agents became one | y |
| `ship-spec`'s merged Step 6 subagent still posts TWO separate pending GitHub reviews (one per skill), not a combined one | Only the SUBAGENT PROCESS merges; each skill's own Step 9 GitHub-posting mechanics (separate pending review, `event` omitted) stay untouched | Matches the "never in parallel" guardrail's actual intent (avoid two concurrent pending-review operations colliding on the same PR) without changing GitHub-facing behavior at all | y |
| Merged-agent naming: `architecture-reviewer`+`code-quality-reviewer` → internal label `design-quality-reviewer`; `isolation-reviewer`+`performance-reviewer` → `execution-reviewer`; `clarity-reviewer`+`maintainability-reviewer` → `craft-reviewer` (dispatch/prompt labels only — findings still tag by original dimension per the row above) | Short, descriptive internal names for the Agent Roster / Checklist Matrix tables | Needed somewhere to refer to "the agent that does both X and Y" without repeating both names everywhere | y |

**Open questions:** none — all resolved during the grilling session and this session's investigation (ship-spec wrapper, content-type parity).

---

## User Stories

### P1: Code-Review Dimension Merge ⭐ MVP

**User Story**: As an engineer running `code-review` on a Large/Complex-tier PR, I want `architecture-reviewer` and `code-quality-reviewer` merged into one delegated agent, so that reviews cost 4 agents instead of 5 without losing either dimension's findings.

**Why P1**: Proven merge candidate — identical checklist set (`review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md`) and adjacent focus (both are static "how well is this code built" lenses). Directly reduces the dominant cost driver (redundant per-agent context re-priming) confirmed by real usage data.

**Acceptance Criteria**:

1. WHEN the size tier is Large or Complex AND content type is `general` (both dimensions active) THEN exactly ONE delegated agent (`design-quality-reviewer`) SHALL cover both the architecture and code-quality dimensions in a single pass, self-loading the union of their checklists (deduplicated).
2. WHEN the merged agent returns its findings THEN each finding SHALL be tagged with its original dimension (`architecture` or `code-quality`) so the at-a-glance table keeps two separate rows, exactly as before the merge.
3. WHEN `regression-reviewer`, `performance-reviewer`, `security-reviewer`, or `requirements-tracer` are active THEN they SHALL remain independently dispatched agents — the merge applies ONLY to architecture+code-quality.
4. WHEN content type is `docs-only` (only `code-quality-reviewer` + conditional `requirements-tracer` are active per the existing content-type table) THEN NO merge applies — `code-quality-reviewer` dispatches alone as it does today (merging requires BOTH original dimensions to be active).
5. WHEN the Review Plan and complexity banner are emitted THEN the stated agent count SHALL reflect the reduction (e.g. `Parallel — 4 agents` instead of `5 agents`, for `general` content with all dimensions active).
6. WHEN the merged agent fails or times out THEN BOTH the architecture and code-quality at-a-glance rows SHALL show `⚠️ not executed — <reason>` (the existing per-agent failure handling applied to both tagged dimensions, since one agent's failure means both dimensions went unreviewed).

**Independent Test**: Run `code-review` against a Large-tier `general`-content diff. Confirm exactly 4 agents dispatched (not 5), and the at-a-glance table still shows separate Architecture and Code Quality rows with findings correctly attributed.

---

### P1: Tests-Code-Review Dimension Merges ⭐ MVP

**User Story**: As an engineer running `tests-code-review` on a Large/Complex-tier PR, I want `isolation-reviewer`+`performance-reviewer` merged into one agent (`execution-reviewer`), and `clarity-reviewer`+`maintainability-reviewer` merged into another (`craft-reviewer`), so that reviews cost 3 specialized agents (plus `coverage-reviewer` and conditional `gap-detector`) instead of 5.

**Why P1**: Same rationale as the code-review merge, mirroring TCR-TOKEN's sibling relationship to CR-TOKEN. Grounded in checklist/focus analysis: `isolation`+`performance` share the only `TESTING.md`-degradation dependency in the skill and both concern test *execution mechanics*; `clarity`+`maintainability` both concern test-*authoring craftsmanship*. `coverage-reviewer` and `gap-detector` stay separate — the skill already draws an explicit boundary between them (different diff input; `gap-detector` uses no checklist and "does NOT judge quality of existing tests").

**Acceptance Criteria**:

1. WHEN size tier is Large or Complex THEN exactly ONE delegated agent (`execution-reviewer`) SHALL cover both isolation and performance dimensions, self-loading `test-review-checklist.md` + `<stack>-*-tests-code-review.md` (if present) + the full 7-doc codebase set — the same self-loading mechanism any reviewing agent uses today.
2. WHEN size tier is Large or Complex THEN exactly ONE delegated agent (`craft-reviewer`) SHALL cover both clarity and maintainability dimensions, using the same self-loading mechanism.
3. WHEN `TESTING.md` is absent from the availability map THEN the `execution-reviewer` (isolation+performance) SHALL run degraded — the same degraded-mode trigger that applied to `isolation-reviewer` and `performance-reviewer` individually before the merge, now applying to the merged agent as a whole.
4. WHEN either merged agent returns findings THEN each finding SHALL be tagged by its original dimension so the at-a-glance table keeps 4 separate quality-dimension rows (clarity, coverage, isolation, maintainability) plus performance findings, exactly as before the merge.
5. WHEN `coverage-reviewer` or `gap-detector` are active THEN they SHALL remain independently dispatched — the merges do not touch either.
6. WHEN the Review Plan/banner are emitted THEN the stated agent count SHALL reflect the reduction (e.g. `Parallel — 3 agents` instead of `5`, plus `gap-detector` when `impl_diff` is non-empty).
7. WHEN either merged agent fails or times out THEN BOTH of its tagged dimensions' at-a-glance rows SHALL show `⚠️ not executed — <reason>`.

**Independent Test**: Run `tests-code-review` against a Large-tier diff with `TESTING.md` present. Confirm 3 dimension agents dispatched (not 5) plus `gap-detector` if `impl_diff` is non-empty. At-a-glance table shows 4 separate rows (clarity, coverage, isolation, maintainability) with performance findings correctly attributed to the `execution-reviewer`'s output.

---

### P2: Ship-Spec Wrapper Merge

**User Story**: As an engineer running `/ship-spec`, I want its Step 6 review step to spawn ONE subagent that invokes both `code-review` and `tests-code-review` sequentially, instead of two separate subagents, so that the second skill's shared context (system prompt, `CLAUDE.md`, tool definitions) is read from cache instead of re-primed from cold.

**Why P2**: Real but modest saving — measured `cache_creation_input_tokens` across the two current wrapper agents totaled ~1M tokens out of 19.3M wrapper cost in the one sampled session (~5%). Included because the user wants it bundled with this spec despite the modest size, and it carries no meaningful risk or design cost.

**Acceptance Criteria**:

1. WHEN `ship-spec` Step 6 runs THEN it SHALL spawn exactly ONE subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: false`) instead of two.
2. WHEN that subagent runs THEN it SHALL invoke `code-review` in GitHub PR mode against the PR number, wait for it to complete and post its pending review, THEN invoke `tests-code-review` the same way — strictly sequential within the same subagent conversation, preserving the existing "never in parallel" guardrail (both skills still post to the same PR; a single subagent naturally serializes them).
3. WHEN the subagent completes THEN it SHALL return ONE compact result covering both skills — total finding count and per-severity breakdown for each of `code-review` and `tests-code-review` separately — nothing else, matching the existing "compact result only" contract.
4. WHEN either skill invocation inside the subagent fails to complete THEN the existing retry-once-then-report-failure rule SHALL apply, scoped to the failed skill only (a `code-review` failure does not prevent `tests-code-review` from still running and posting its own review).
5. WHEN each skill posts to GitHub THEN it SHALL continue posting its own SEPARATE pending review (unchanged `event`-omitted, per-skill Step 9 mechanics) — merging the subagent process does NOT merge the two GitHub reviews into one.

**Independent Test**: Run `/ship-spec` end-to-end on a feature with an open draft PR. Confirm exactly one `Agent` tool dispatch occurs for Step 6 (not two), both skills' findings get posted as two separate pending reviews on the PR, and the reported summary shows both skills' finding counts.

---

## Edge Cases

- WHEN a Large/Complex-tier diff's content type narrows to only ONE of a merge pair's dimensions (e.g. `docs-only` activates `code-quality-reviewer` but not `architecture-reviewer`) THEN NO merge applies — the single active dimension dispatches alone, unchanged from today's behavior (code-review only; `tests-code-review` has no content-type axis, so both merge pairs are always fully active together when their tier is Large/Complex).
- WHEN `impl_diff` is empty in `tests-code-review`'s Large/Complex tier THEN `gap-detector` is skipped as today — unaffected by the merges (it was never part of either merged pair).
- WHEN `ship-spec`'s merged subagent's `code-review` call succeeds but `tests-code-review` fails after retry THEN the subagent SHALL report `code-review`'s finding count normally and `tests-code-review`'s failure reason — `ship-spec` does not fail Step 6 wholesale for one skill's failure.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| RD-01 | P1: Code-Review Dimension Merge | Verified | ✅ Verified |
| RD-02 | P1: Code-Review Dimension Merge (finding tagging) | Verified | ✅ Verified |
| RD-03 | P1: Code-Review Dimension Merge (unaffected agents) | Verified | ✅ Verified |
| RD-04 | P1: Code-Review Dimension Merge (content-type gating) | Verified | ✅ Verified |
| RD-05 | P1: Code-Review Dimension Merge (banner/plan) | Verified | ✅ Verified |
| RD-06 | P1: Code-Review Dimension Merge (failure handling) | Verified | ✅ Verified (fix round: `82f91b8`) |
| RD-07 | P1: Tests-Code-Review Dimension Merges (execution-reviewer) | Verified | ✅ Verified |
| RD-08 | P1: Tests-Code-Review Dimension Merges (craft-reviewer) | Verified | ✅ Verified |
| RD-09 | P1: Tests-Code-Review Dimension Merges (degraded mode) | Verified | ✅ Verified |
| RD-10 | P1: Tests-Code-Review Dimension Merges (finding tagging) | Verified | ✅ Verified |
| RD-11 | P1: Tests-Code-Review Dimension Merges (unaffected agents) | Verified | ✅ Verified |
| RD-12 | P1: Tests-Code-Review Dimension Merges (banner/plan) | Verified | ✅ Verified |
| RD-13 | P1: Tests-Code-Review Dimension Merges (failure handling) | Verified | ✅ Verified (fix round: `0766349`) |
| RD-14 | P2: Ship-Spec Wrapper Merge (single subagent) | Verified | ✅ Verified |
| RD-15 | P2: Ship-Spec Wrapper Merge (sequential invocation) | Verified | ✅ Verified |
| RD-16 | P2: Ship-Spec Wrapper Merge (compact result) | Verified | ✅ Verified |
| RD-17 | P2: Ship-Spec Wrapper Merge (partial failure) | Verified | ✅ Verified |
| RD-18 | P2: Ship-Spec Wrapper Merge (separate GitHub reviews) | Verified | ✅ Verified |

**Coverage:** 18 total, 18 mapped to tasks, 0 unmapped — all verified by independent Verifier (2 iterations, see `validation.md`)

---

## Success Criteria

- [x] `code-review` dispatches 4 agents (not 5) for a Large/Complex-tier `general`-content diff with all dimensions active.
- [x] `tests-code-review` dispatches 3 agents (not 5) for a Large/Complex-tier diff, plus `gap-detector` when applicable.
- [x] Both skills' at-a-glance tables retain one row per ORIGINAL dimension — no visible report-shape change from the merge.
- [x] Degraded-mode and failure-handling behavior correctly attributes to both dimensions when a merged agent is affected.
- [x] `ship-spec` Step 6 spawns one subagent instead of two, and still posts two separate pending GitHub reviews.
- [ ] `~/.claude/tools/review-token-usage.py`, re-run against fresh post-fix sessions, shows a measurable reduction in dimension-agent-bucket tokens for Large/Complex-tier reviews. **(pending — requires real post-fix usage data; not verifiable at implementation time)**

---

## Pending Validation (deferred — run in a future session once fresh usage data exists)

This is the one Success Criterion still unchecked. Everything needed to run it:

**Script** (durable, cross-session, not in scratchpad): `~/.claude/tools/review-token-usage.py`
**Baseline** (durable copy, captured before ANY of this session's fixes landed): `.specs/features/review-dispatch-efficiency/baseline-before-fix.jsonl` — 6 sessions, 150.9M tokens combined, real recargapay usage from 2026-08-07/08.

**How to run it:**
```bash
python3 ~/.claude/tools/review-token-usage.py --json .specs/features/review-dispatch-efficiency/after-fix.jsonl
```
Defaults to scanning the same 3 recargapay project dirs (main + 2 worktrees) the baseline came from. Requires fresh `code-review`/`tests-code-review` sessions to exist there, run AFTER commits `cc829ab`, `39a47c7`, `80b44de`, `82f91b8`, `0766349` (all on `main` as of this session) — i.e. real work done in a later session, not something runnable right now.

**What to check in the output:**
1. `dimension_agents` count for a Large/Complex-tier, `general`-content `code-review` run: expect **4** (was 5 pre-fix).
2. `dimension_agents` count for a Large/Complex-tier `tests-code-review` run: expect **3** (+`gap-detector` if `impl_diff` non-empty; was 5 pre-fix).
3. Per-session `bucket_totals.dimension` should be meaningfully lower than a size-matched session in the baseline file — exact-size matches won't exist, so compare proportionally (tokens roughly scale with file/line count × agent count; fewer agents at the same diff size should show a roughly proportional drop).
4. If a `ship-spec`-pattern session exists post-fix, confirm exactly 1 `dispatcher_agents` entry (not 2) per delivery run.

**Once confirmed:** check the last Success Criteria box above, and update `spec.md`'s Status line to note the measurement is closed out (with the actual before/after numbers).
