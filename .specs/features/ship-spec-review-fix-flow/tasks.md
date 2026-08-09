# Ship-Spec Review & Fix-Triage Redesign Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/ship-spec-review-fix-flow/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from project guidelines — confirm before Execute. Guidelines found: `CLAUDE.md` (project root) — "Project Nature" section: this repo is markdown-skill-driven; typical software-engineering test-coverage heuristics do not apply to `.md` files (skill definitions, templates) — clarity/correctness of content is what matters. Precedent: the prior `review-dispatch-efficiency` feature in this same repo applied the same matrix shape.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Skill definition (`SKILL.md`) | none | Content correctness verified by inspection — structural read-through + `grep` for exact changed strings/sections, cross-checked against spec ACs | `skills/*/SKILL.md` | manual inspection |
| Shared template | none | Same as above | `templates/*.md` | manual inspection |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Inspection | After every task (all tasks are markdown edits) | Read the diff; confirm the new/changed text matches the design and doesn't contradict adjacent unedited sections (Guardrails, Examples, other Steps) |

---

## Execution Plan

Phases are ordered and run sequentially — each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Return-Only Publish Mechanism (Foundation)

```
T1 → T2
```

### Phase 2: Step 6 Rewrite

```
T3
```

### Phase 3: Comment-Triage Rewrite

```
T4 → T5 → T6
```

### Phase 4: Consistency & Documentation

```
T7 → T8
```

8 tasks total — fits a single batch (≤ ~8), no sub-agent offer needed; executes inline.

---

## Task Breakdown

### T1: Add the Return-Only Variant to the shared GitHub PR Mode template

**What**: Add a new subsection under Step B (e.g. "B2'. Return-Only Variant") that assembles the same `comments` array as B2 (`path`/`line`/`body`, exact-line anchoring) but returns it instead of issuing the `gh api ... POST`. Existing B1–B3 text is untouched — this is additive only.
**Where**: `templates/github-pr-review-mode.md`
**Depends on**: None
**Reuses**: B2's existing payload-assembly logic and exact-line-anchoring rule
**Requirement**: SSF-01, SSF-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] New subsection exists under Step B, clearly named as a variant (not replacing B1–B3)
- [ ] Assembled `comments` array shape matches B2's exactly (`path`, `line`, `body`)
- [ ] Explicitly states no `gh api POST` is issued in this variant — the array is returned to the caller instead
- [ ] B1, B2, B3 text is unchanged (diff shows only an addition)

**Tests**: none
**Gate**: inspection
**Commit**: `feat(templates): add return-only variant to GitHub PR review mode`

---

### T2: Wire the Return-Only Variant into `code-review` and `tests-code-review` Step 9

**What**: In each skill's Step 9, add a one-line conditional: when invoked by `ship-spec`'s merged-post flow, use the Return-Only Variant (T1) instead of B2's posting path. Existing direct/local-mode invocation (interactive B1 selection, B2 posting) is unchanged.
**Where**: `skills/code-review/SKILL.md` (Step 9), `skills/tests-code-review/SKILL.md` (Step 9)
**Depends on**: T1
**Reuses**: T1's Return-Only Variant
**Requirement**: SSF-01, SSF-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `code-review/SKILL.md` Step 9 references the Return-Only Variant conditionally
- [ ] `tests-code-review/SKILL.md` Step 9 references it identically
- [ ] Neither skill's existing direct-invocation posting path (B1–B3) changed
- [ ] Both skills' `metadata.version` bumped (patch — behavior addition, backward compatible)

**Tests**: none
**Gate**: inspection
**Commit**: `feat(review-skills): wire return-only GitHub PR mode variant into Step 9`

---

### T3: Rewrite `ship-spec` Step 6 — one subagent, concurrent internal dispatch, merge, single post

**What**: Keep today's single-subagent dispatch shape (one isolated Sonnet subagent, `run_in_background: false`) but change what happens inside it: instead of invoking `code-review` then waiting, then invoking `tests-code-review` sequentially, the subagent issues **two concurrent tool calls in the same turn** — both skills' Return-Only Variant — each returning a `comments` array + counts (or a failure reason). Still inside that same subagent: merge both arrays, issue exactly one `POST .../reviews` call, and return only a compact summary (counts, PR confirmation) to `ship-spec`'s own conversation. Update the Guardrails bullets that describe the old mechanism (L29–30 delegation wording — the subagent still runs both skills, just concurrently now; L38 "never in parallel" — replace with the real constraint: GitHub's one-pending-review-per-PR limit, respected by merging into a single POST rather than by serializing dispatch; L39 partial-failure retry rule — adapt to "retry only the failed invocation inside the subagent, then merge/post with whatever succeeded"). SPEC_DEVIATION: `design.md`/`spec.md` originally specified two top-level subagents dispatched by `ship-spec` directly; refined during Execute to one subagent with internal concurrency once it became clear the two-subagent design would leak full findings text into `ship-spec`'s persistent context (violating the existing context-isolation guarantee) — strictly better on cost (one cold start, not two), parallelism (unchanged), and context cleanliness. `spec.md`/`design.md` already updated to match.
**Where**: `skills/ship-spec/SKILL.md` (Guardrails section + Step 6)
**Depends on**: T2
**Reuses**: T1/T2's Return-Only Variant; existing `gh api ... reviews POST` mechanics from `github-pr-review-mode.md` B2
**Requirement**: SSF-01, SSF-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Step 6 dispatches both analysis subagents concurrently (not sequential awaits), each using the Return-Only Variant
- [ ] Step 6 merges both results and issues exactly one `POST .../reviews` call
- [ ] Partial-failure case (one subagent fails) posts a single review with only the succeeded skill's findings, and retries only the failed skill once per the existing retry-rule guardrail
- [ ] Full-failure case (both fail) stops before any `POST`, reports both failures
- [ ] Guardrails L29–30 (delegation wording), L38 ("never in parallel"), L39 (partial-failure retry) updated to match the new mechanism — no stale text claiming two separate pending reviews
- [ ] Step 7 (report + stop) unchanged

**Tests**: none
**Gate**: inspection
**Commit**: `feat(ship-spec): concurrent analysis with single merged pending review`

---

### T4: Rewrite Comment-Triage Mode classification — uniform comment-presence rule

**What**: Replace step 2's origin-based classification (tests-code-review always-fix / code-review conditional) with the uniform rule: no comment → auto-fix; question → answer-only, leave open; suggestion that validates → apply-as-directed; suggestion that doesn't validate → pushback, leave open; standalone comment → same apply-or-pushback treatment. Applies identically regardless of which skill produced the finding.
**Where**: `skills/ship-spec/SKILL.md` (Comment-Triage Mode step 2)
**Depends on**: T3
**Reuses**: Existing GraphQL `reviewThreads` fetch and its `isResolved`/`PENDING` filters (step 1, unchanged)
**Requirement**: SSF-03, SSF-04, SSF-05, SSF-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Step 2's five classification bullets rewritten to the comment-presence rule, with no reference to finding origin as a classification input
- [ ] Each of the four outcomes (auto-fix / answer-only / apply-as-directed / pushback) explicitly stated
- [ ] Step 1 (fetch) unchanged

**Tests**: none
**Gate**: inspection
**Commit**: `feat(ship-spec): uniform comment-presence classification for comment-triage`

---

### T5: Add plan-file generation and re-fetch staleness check

**What**: Insert a new step between classification and execution: write the classified, grouped plan to `.specs/features/<feature>/fix-code-review.md` (flat list, `## Parallel` / `## Sequential` headers per `design.md`'s Data Models section) — reversing the current "no batch plan step" rule (deliberate). Immediately after writing the plan (no approval gate), perform one additional GraphQL fetch of the same query, diff against the plan, and silently drop any item no longer present/changed/resolved.
**Where**: `skills/ship-spec/SKILL.md` (Comment-Triage Mode, new step inserted between what are today's steps 2 and 3)
**Depends on**: T4
**Reuses**: Existing GraphQL `reviewThreads` query (same shape, called twice per run)
**Requirement**: SSF-07, SSF-08, SSF-09, SSF-10

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Plan-file step writes `.specs/features/<feature>/fix-code-review.md`, grouped by same-file/thread dependency (Sequential) vs. everything else (Parallel), before any fix execution
- [ ] Zero-threads case still writes the file noting zero items, then stops
- [ ] No approval gate between plan-write and execution — explicitly stated
- [ ] Re-fetch + diff step runs immediately after plan-write, drops stale items silently, no per-item GitHub reads
- [ ] "No batch plan step" language from the current step 3 removed/reversed

**Tests**: none
**Gate**: inspection
**Commit**: `feat(ship-spec): write fix plan before comment-triage execution`

---

### T6: Rewrite fix execution — split-phase concurrency + Haiku model tiering

**What**: Replace the current one-at-a-time fix dispatch with: parallel-bucket items drafted concurrently (capped at 4 concurrent subagents, `model: claude-haiku-4-5-20251001`, no git writes — investigation/fix-drafting only, returning a proposed change or a blocker reason); commits applied one at a time on the shared checkout (never two concurrent); sequential-bucket items drafted and committed one at a time, honoring order. Each committed fix runs only its own directly relevant test(s) — not a full gate/verify cycle. Classification and reply composition stay on the orchestrator's default model (never Haiku).
**Where**: `skills/ship-spec/SKILL.md` (Comment-Triage Mode steps 3–4, rewritten)
**Depends on**: T5
**Reuses**: Existing atomic-commit / Conventional-Commits convention (from tlc-spec-driven, referenced by the current step 4)
**Requirement**: SSF-11, SSF-12, SSF-13, SSF-14, SSF-15, SSF-16

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Parallel-bucket drafting explicitly capped at 4 concurrent subagents, `model: claude-haiku-4-5-20251001`, explicitly no git writes during drafting
- [ ] Batches of >4 items process in successive groups of ≤4 concurrent drafts
- [ ] Commit application step explicitly serialized ("one at a time... never two commits attempted concurrently")
- [ ] Sequential-bucket items explicitly drafted+committed one at a time, in required order, no concurrent drafting
- [ ] A drafted change that no longer matches current file state at commit time is marked blocked, not force-applied
- [ ] Each commit's test scope explicitly limited to that item's own relevant test(s) — no full gate/verify cycle language remains
- [ ] Classification/reply steps explicitly state they stay on the default model, never Haiku

**Tests**: none
**Gate**: inspection
**Commit**: `feat(ship-spec): split-phase concurrent fix execution with Haiku drafting`

---

### T7: Update Guardrails for worktree/retry consistency and reply/resolve behavior

**What**: Update the Guardrails bullet on worktree isolation (currently written for sequential dispatch) to explicitly cover the new concurrent-drafting shape (still no worktree — drafting has no git writes to isolate; only the serialized commit step touches the checkout). Update Comment-Triage step 5 (reply/resolve) to match T4's new classification: silent resolve (no reply) for auto-fix/apply-as-directed, reply-and-leave-open for pushback/answer-only — replacing the old origin-based reply wording.
**Where**: `skills/ship-spec/SKILL.md` (Guardrails section, Comment-Triage Mode step 5)
**Depends on**: T6
**Reuses**: Existing `resolveReviewThread` / reply mutation mechanics (`references/github-delivery.md`, unchanged)
**Requirement**: SSF-04, SSF-05, SSF-06, SSF-13

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Worktree-isolation guardrail explicitly addresses why split-phase drafting (T6) doesn't need it
- [ ] Step 5 reply/resolve wording matches T4's four classification outcomes exactly (no stale origin-based language remains anywhere in the file)
- [ ] Guardrail on unsubmitted-review fix-trigger message (SSF-04's PENDING-review guard) present and explicit

**Tests**: none
**Gate**: inspection
**Commit**: `fix(ship-spec): align guardrails and reply behavior with new classification`

---

### T8: Update Examples and bump version

**What**: Rewrite Example 1 (delivery run) to show the merged single-post outcome instead of two separate reviews. Rewrite Example 2 (comment-triage round) to show the new classification labels, the plan-file step, and concurrent+serialized fix execution. Bump `ship-spec/SKILL.md`'s `metadata.version` (minor — new capability/behavior change per project semver convention) and refresh the frontmatter `description` if it still describes the old two-review mechanism.
**Where**: `skills/ship-spec/SKILL.md` (Examples section, frontmatter)
**Depends on**: T7
**Reuses**: N/A — documentation-only task
**Requirement**: N/A (documentation completeness for SSF-01 through SSF-16)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Example 1 shows one merged pending review with a combined finding count, not "9 findings... then 3 findings" as two separate events
- [ ] Example 2 shows: fetch → classify (new labels) → plan file written → re-fetch/diff → concurrent draft (capped 4, Haiku) → serialized commits → reply/resolve per classification → push
- [ ] `metadata.version` bumped and frontmatter `description` matches actual behavior
- [ ] Full read-through of the file finds no remaining reference to the old two-separate-reviews or origin-based-classification mechanisms anywhere (Guardrails, Steps, Examples)

**Tests**: none
**Gate**: inspection
**Commit**: `docs(ship-spec): update examples and version for review-fix-flow redesign`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ──→ T2
Phase 2:  T3
Phase 3:  T4 ──→ T5 ──→ T6
Phase 4:  T7 ──→ T8
```

Execution is strictly sequential — 8 tasks total, single batch, no sub-agent dispatch needed (fits inline, per the ≤ ~8 task rule).

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Return-only variant | 1 template, 1 new subsection | ✅ Granular |
| T2: Wire variant into both review skills | 2 files, identical 1-line pattern each | ✅ Granular (cohesive — same mechanical change) |
| T3: Step 6 rewrite | 1 file, 1 cohesive step + its guardrails | ✅ Granular |
| T4: Classification rewrite | 1 file, 1 step | ✅ Granular |
| T5: Plan-file + re-fetch | 1 file, 1 new step | ✅ Granular |
| T6: Split-phase execution + tiering | 1 file, 1 cohesive step pair | ✅ Granular |
| T7: Guardrails/reply consistency | 1 file, 2 related sections | ✅ Granular (cohesive — same consistency pass) |
| T8: Examples + version | 1 file, documentation only | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | No arrow in | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | Phase 1 → Phase 2 (T2 → T3) | ✅ Match |
| T4 | T3 | Phase 2 → Phase 3 (T3 → T4) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | Phase 3 → Phase 4 (T6 → T7) | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Shared template (`.md`) | none | none | ✅ OK |
| T2 | Skill definition (`.md`) x2 | none | none | ✅ OK |
| T3 | Skill definition (`.md`) | none | none | ✅ OK |
| T4 | Skill definition (`.md`) | none | none | ✅ OK |
| T5 | Skill definition (`.md`) | none | none | ✅ OK |
| T6 | Skill definition (`.md`) | none | none | ✅ OK |
| T7 | Skill definition (`.md`) | none | none | ✅ OK |
| T8 | Skill definition (`.md`) | none | none | ✅ OK |

All tasks touch only `.md` skill/template files — matrix requires `none` for this layer across the board (per project convention), so `Tests: none` is valid everywhere, not a deferral.
