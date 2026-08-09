# Ship-Spec Review & Fix-Triage Redesign Validation

**Date**: 2026-08-08
**Spec**: `.specs/features/ship-spec-review-fix-flow/spec.md`
**Diff range**: `f64ac71..HEAD` (`d13c237`, `6246299`, `3ed9b71`, `446d5e2`, `a188b72`, `19e25f8`, `83b3628`, `4ee3d9c`)
**Verifier**: independent sub-agent (author ≠ verifier)

**Adaptation note**: This feature edits markdown skill-definition/template files only, per this repo's `CLAUDE.md` ("Project Nature": typical software-engineering test-coverage heuristics don't apply to `.md` files) and `tasks.md`'s Test Coverage Matrix (`Tests: none`, `Gate: inspection` for all 8 tasks). Gate-command execution and mutation-tooling sensors are **N/A** for this feature type — no gate command exists to run, no test counts to delta. In place of the code-mutation Discrimination Sensor, this report runs a **Consistency Sweep**: an independent search for stale leftover text from the old mechanism and internal contradictions between Guardrails and the Steps they describe (per the orchestrator's explicit adaptation instructions). Interactive UAT is skipped (not applicable to skill prose).

**AC-to-requirement-ID mapping note**: `spec.md`'s Requirement Traceability table allocates fewer SSF IDs (18) than there are individual `WHEN/THEN` AC bullets across the 5 stories (24 bullets total — e.g. Story 1 has 5 AC bullets but only 2 IDs, SSF-01/02). `spec.md` does not state a sub-mapping. This report groups the AC bullets under their story's allocated IDs in bullet order (documented per-row below) — a reasonable-but-inferred grouping, not an implementation defect; flagged here for transparency rather than silently picked.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 | ✅ Done | `d13c237` — pure addition (+6/-0) to `templates/github-pr-review-mode.md`, all 4 Done-when criteria met. **Note**: tasks.md's own Done-when checkboxes (L80–83) were never ticked despite the work being complete — bookkeeping gap only, content verified independently. |
| T2 | ✅ Done | `6246299` — 1-line conditional added to both skills' Step 9, versions bumped 2.7.0→2.7.1 / 2.5.0→2.5.1 (patch). **Note**: Done-when checkboxes (L104–107) also unticked — same bookkeeping gap. |
| T3 | ⚠️ Partial | `3ed9b71` — concurrent dispatch, merge, and single-POST mechanism (SSF-01/02) are correctly implemented and match its own Done-when L128–130. **L131's explicit Done-when criterion — "Full-failure case (both fail) stops before any `POST`, reports both failures" — is genuinely unmet**: no text in Step 6 or Guardrails states this; see Spec-Anchored ACs and Consistency Sweep below. This checkbox is (correctly) still unchecked in tasks.md — the tooling didn't overclaim here, but the gap was never closed either. |
| T4 | ✅ Done | `446d5e2` — uniform comment-presence classification, all 4 outcomes stated, Step 1 untouched. **Note**: Done-when checkboxes (L154–156) unticked — same bookkeeping gap. |
| T5 | ✅ Done | `a188b72` — plan-file generation + re-fetch/staleness check, all 5 Done-when criteria (L181–185, checked) verified against current file content. |
| T6 | ✅ Done | `a188b72` (combined w/ T5 per documented SPEC_DEVIATION) — split-phase concurrency + Haiku tiering, all 7 Done-when criteria (L206–212, checked) verified. |
| T7 | ✅ Done | `19e25f8` — worktree guardrail update + new step 0 pending-review guard (scope expansion, documented). Both Done-when criteria (L233–235, checked) verified. |
| T8 | ✅ Done | `83b3628` — Examples rewritten, version bumped 1.3.0→1.4.0 (minor). All 4 Done-when criteria (L256–259, checked) verified. |

**SPEC_DEVIATION reviews**: T3's two-subagent→one-subagent-with-internal-concurrency refinement is well-justified (avoids leaking full findings text into `ship-spec`'s persistent context) and `spec.md`/`design.md` were updated in the same commit, confirmed via `git show 3ed9b71`. T5+T6+T7's-reply-wording consolidation is justified (shared numbered-step sequence, avoids a self-contradictory intermediate commit) and is the same pattern used by the prior `review-dispatch-efficiency` feature. Neither deviation caused a requirement-coverage gap by itself — the T3 gap found below (full-failure handling) is an omission independent of the one-subagent refinement, not caused by it.

---

## Spec-Anchored Acceptance Criteria

### P1: Concurrent analysis, single merged pending review (SSF-01, SSF-02)

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + evidence | Result |
| --- | --- | --- | --- |
| AC1 (SSF-01): Step 6 dispatches ONE subagent; its own turn issues two concurrent tool calls (not sequential awaits); neither invocation posts to GitHub | One subagent, two concurrent Return-Only Variant calls, zero GitHub writes during analysis | `skills/ship-spec/SKILL.md:116-117` — "Spawn one subagent... Issue two concurrent tool calls in the same turn (not sequential awaits)... Neither invocation touches GitHub" | ✅ PASS |
| AC2 (SSF-02): once both return, merge into one `comments` array, issue exactly one `POST .../reviews` call, entirely inside the subagent | Exactly one POST per run, merged payload | `skills/ship-spec/SKILL.md:118` — "merge both `comments` arrays into one... and issue **exactly one** `gh api ... POST` call... this POST must never fire more than once per run" | ✅ PASS |
| AC3 (SSF-02): subagent returns only a compact summary, never full findings text/comments array | Compact summary only (counts, PR confirmation) | `skills/ship-spec/SKILL.md:119` — "Return **only** one compact result covering both: each skill's total finding count and a per-severity breakdown"; reinforced at `:123` ("Only the one compact summary returns... not the underlying diffs, findings text, or comments arrays") | ✅ PASS |
| AC4 (SSF-02): one invocation fails → post a review with only the succeeded skill's findings, report which failed and why, never a second separate POST | Partial-failure: single POST with succeeded skill's findings only | `skills/ship-spec/SKILL.md:39` (Guardrails: "retry ONLY the failed invocation once... Issue the single merged POST only after both invocations have resolved") + `:118` ("or use just the succeeded one's, on an unrecovered partial failure") + `:119` (failure reason returned in place of counts) | ✅ PASS |
| AC5 (SSF-02): after the compact summary, `ship-spec` proceeds to Step 7 and stops | Unchanged behavior | `skills/ship-spec/SKILL.md:125-127` (Step 7, unmodified: "Report the PR URL... Stop. Wait for the user.") | ✅ PASS |
| **Not covered by AC1-5 but required by the story's own Edge Cases / T3's own Done-when (L131)**: both invocations fail | Stop **before** any POST; report both failures; never proceed as if a review was posted | **No evidence found.** Step 6's only failure-path text (`:118`, `:39`) describes *partial* failure ("use just the succeeded one's"); nothing states what happens when there is no succeeded result to use — a literal reading would still execute "issue exactly one POST call" with an empty/absent `comments` array rather than skip the POST and report. Guardrails `:41` covers a subagent that "could not complete" (crashed/errored), not the case where the subagent completes normally but both internal invocations failed. | ❌ GAP |

**Subtotal: 5/6 covered, 1 confirmed GAP** (full-failure case — see Consistency Sweep #1 and Fix Plan below)

### P1: Comment-presence-driven fix classification (SSF-03, SSF-04, SSF-05, SSF-06)

| Criterion | Spec-defined outcome | `file:line` + evidence | Result |
| --- | --- | --- | --- |
| AC1 (SSF-03): no comment → auto-fix, same rule regardless of origin skill | auto-fix, uniform | `skills/ship-spec/SKILL.md:135-136` — "applied identically regardless of which skill produced the underlying finding... **auto-fix** — no user comment... Fix it directly, no exceptions" | ✅ PASS |
| AC2 (SSF-04): question → answer-only, reply, don't fix unless answer implies change | answer-only, leave open | `skills/ship-spec/SKILL.md:137` — "**answer-only** — the comment is phrased as, or amounts to, a question. Reply with the answer; don't fix unless the answer implies a change. Leave the thread unresolved" | ✅ PASS |
| AC3 (SSF-05): sound suggestion → apply-as-directed | apply-as-directed | `skills/ship-spec/SKILL.md:138` — "**apply-as-directed** — the comment suggests an approach and it validates... Fix it as directed" | ✅ PASS |
| AC4 (SSF-06): unsound suggestion → pushback, not applied uncritically | pushback, leave open | `skills/ship-spec/SKILL.md:139` — "**pushback** — the comment suggests an approach that doesn't validate... Don't comply blindly: reply rejecting it with your reasoning... Leave the thread unresolved" | ✅ PASS |
| AC5 (SSF-06): standalone comment, no anchored finding → same apply-or-pushback treatment | Same as AC3/AC4 | `skills/ship-spec/SKILL.md:140` — "**standalone comment, not anchored to a code-review/tests-code-review finding** — same apply-as-directed-or-pushback treatment" | ✅ PASS |

**Subtotal: 5/5 PASS**

### P1: Lightweight plan generation with immediate execution (SSF-07, SSF-08, SSF-09, SSF-10)

| Criterion | Spec-defined outcome | `file:line` + evidence | Result |
| --- | --- | --- | --- |
| AC1 (SSF-07): fix trigger invoked while review still PENDING → report, don't fetch/classify/fix | Explicit stop message, no side effects | `skills/ship-spec/SKILL.md:133` — Comment-Triage step 0: "if the PR's Step-6-created review is still `PENDING`... stop and tell the user... Do not fetch, classify, or execute anything" (this was T7's scope-expansion fix — previously step 1 only silently filtered) | ✅ PASS |
| AC2 (SSF-08): review submitted → fetch once, classify, write `fix-code-review.md` grouped Parallel/Sequential, before execution | Written plan file, correct grouping, before any fix runs | `skills/ship-spec/SKILL.md:141` — "Write the classified plan to `.specs/features/<feature>/fix-code-review.md` before any execution — a flat list grouped into `## Parallel`... and `## Sequential`..." | ✅ PASS |
| AC3 (SSF-09): plan written → no pause for approval, execution proceeds same invocation | No gate | `skills/ship-spec/SKILL.md:142` — "Immediately after writing the plan — **no approval gate**; invoking this mode with 'fix the findings' is itself the user's go-ahead" | ✅ PASS |
| AC4 (SSF-10): execution about to begin → one more GraphQL fetch, diff against plan, silently drop stale/resolved/changed items, no further per-item reads | One re-fetch, silent drop, no per-item GitHub reads | `skills/ship-spec/SKILL.md:142` — "perform one more GraphQL fetch of the same `reviewThreads` query, diff it against the plan just written, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch. No further per-item GitHub reads follow this" | ✅ PASS |
| AC5 (SSF-08): zero unresolved threads → still write `fix-code-review.md` noting zero items, stop, no fix agents dispatched | Zero-items file written, hard stop | `skills/ship-spec/SKILL.md:141` — "If zero threads were found, still write the file noting zero items, then stop — do not proceed to step 4" | ✅ PASS |

**Subtotal: 5/5 PASS**

### P1: Safe concurrent fix execution (SSF-11–SSF-16)

| Criterion | Spec-defined outcome | `file:line` + evidence | Result |
| --- | --- | --- | --- |
| AC1 (SSF-11): parallel bucket → up to 4 concurrent drafting subagents, investigation/drafting only, no file edits/git ops, return proposed change | Capped-4 concurrent draft, no git writes | `skills/ship-spec/SKILL.md:143` — "draft fixes concurrently, capped at 4 subagents at a time... each drafting subagent performs only the investigation/fix-drafting for its one item (no file edits, no git operations) and returns its proposed change" | ✅ PASS |
| AC2 (SSF-12): draft ready → apply + commit serially, never two commits concurrently | Serialized commit | `skills/ship-spec/SKILL.md:143` — "apply and commit it via a subagent call too... **one item at a time — never two commits concurrently** on the shared checkout" | ✅ PASS |
| AC3 (SSF-13): >4 parallel items → batches of ≤4 concurrent drafts, commits still fully serialized | Batched drafting, serial commits | `skills/ship-spec/SKILL.md:143` — "Batches of more than 4 `## Parallel` items process in successive groups of up to 4 concurrent drafts" | ✅ PASS |
| AC4 (SSF-13): sequential bucket → draft+commit one at a time, honoring order, no concurrent drafting | Ordered, non-concurrent | `skills/ship-spec/SKILL.md:143` — "`## Sequential`-bucket items are drafted one at a time, in order, using the same subagent shape — no concurrency for this bucket" | ✅ PASS |
| AC5 (SSF-14): commit → run only that item's own relevant test(s), not full suite/gate cycle | Narrow test scope | `skills/ship-spec/SKILL.md:143` — "running only that item's own directly relevant test(s), not a full gate/verify cycle" | ✅ PASS |
| AC6 (SSF-15): drafting subagent blocked → record as item outcome, don't fail silently or halt other items | Recorded outcome, others proceed | `skills/ship-spec/SKILL.md:143` (blocker reason returned) + Guardrails `:41` (retry-once-then-report rule) + `:146` (step 8 report: "items blocked after a failed retry (with the reason)") | ✅ PASS |
| AC7 (SSF-16): commits applied → reply/resolve per classification (silent resolve for auto-fix/apply-as-directed, reply+leave-open for pushback/question), no `isolation: worktree` on these subagents | Classification-driven reply/resolve, no worktree | `skills/ship-spec/SKILL.md:144` (step 6: silent resolve for auto-fix/apply-as-directed, reply+resolve for pushback, reply+leave-open for answer-only) + Guardrails `:40` ("Do NOT set `isolation: worktree` on the Step 6 or Comment-Triage subagents... This holds for the concurrent fix-drafting subagents too") | ✅ PASS |

**Subtotal: 7/7 PASS**

### P2: Model tiering for fix drafting (SSF-17, SSF-18)

| Criterion | Spec-defined outcome | `file:line` + evidence | Result |
| --- | --- | --- | --- |
| AC1 (SSF-17): drafting subagent dispatched → use Haiku | `model: claude-haiku-4-5-20251001` | `skills/ship-spec/SKILL.md:143` — "(`Agent` tool, `agentType: general-purpose`, `model: claude-haiku-4-5-20251001`, `run_in_background: false`)" | ✅ PASS |
| AC2 (SSF-18): classification/reply composition → default model, never Haiku | Default model only | `skills/ship-spec/SKILL.md:143` — "compose the reply directly in this conversation, on the default model (never Haiku)"; Example 2 (`:171`) reinforces: "their replies are composed directly, on the default model" | ✅ PASS |

**Subtotal: 2/2 PASS. Contradicted elsewhere — see Consistency Sweep #2** (a stale Guardrails bullet, `:36`, still claims the whole fix step runs on "an isolated Sonnet subagent," which is inaccurate for the drafting half since T6; the correct, current instruction — Haiku for drafting — lives at `:143` and is what actually governs behavior, so SSF-17/18 pass on the operative text, but the contradiction itself is a real defect, reported separately below rather than silently ignored).

---

**Overall Spec-Anchored total: 23/24 AC bullets covered with exact-outcome evidence, 1 confirmed GAP** (Step 6 full-failure handling). All 18 allocated SSF IDs have at least one PASS-covered AC bullet; SSF-02's coverage includes one gap adjacent to its allocated ACs (documented above, not silently dropped).

---

## Consistency Sweep

(Replaces the code-mutation Discrimination Sensor — not applicable to markdown skill-definition files; this feature has no test suite to mutate against. Per the orchestrator's adaptation instructions: hunt for stale leftover text from the old mechanism, internal contradictions between Guardrails and Steps, and plausible-careless-reading risks.)

| # | Finding | File:line | Severity | Status |
| --- | --- | --- | --- | --- |
| 1 | **Step 6 has no explicit "both invocations fail" handling.** `skills/ship-spec/SKILL.md:118` ("merge both `comments` arrays into one (or use just the succeeded one's, on an unrecovered partial failure) and issue exactly one POST call") only names the full-success and partial-failure paths. Guardrails `:39` and `:41` mirror this — `:39` is scoped to "partial failure," `:41` is scoped to a subagent that "could not complete" (crashed), not one that completed but both internal invocations failed. A plausible careless reading of `:118` is to still execute "issue exactly one POST" with an empty `comments` array when both fail, directly contradicting `spec.md`'s Edge Case ("SHALL NOT proceed as if a review was successfully posted") and `design.md`'s Error Handling Strategy row ("Stop before any POST; report both failures"). **Confirmed independently by tasks.md itself**: T3's own Done-when line 131 — "Full-failure case (both fail) stops before any `POST`, reports both failures" — is still unchecked (`- [ ]`), and this report's own text search confirms the criterion is genuinely unmet, not just unticked. | `skills/ship-spec/SKILL.md:39, 41, 118` | **Major** — a real, plausible failure mode (both `code-review` and `tests-code-review` erroring, e.g. on an auth/rate-limit blip) has no defined behavior and risks either an errored `gh api` call with an empty payload or a silently-"successful" empty pending review | ❌ Confirmed gap |
| 2 | **Guardrails `:36` is stale relative to T6's Haiku split-phase rewrite.** "Do NOT implement a comment-triage fix directly in this conversation — delegate the read/edit/test/commit work to an isolated Sonnet subagent per Comment-Triage Mode's fix step" still names "Sonnet" for the whole fix step, but Comment-Triage Mode step 5 (`:143`, and SSF-17) explicitly dispatches drafting subagents on **Haiku**, not Sonnet — this line was never touched across T4–T8 (confirmed via `git log -p f64ac71..HEAD -- skills/ship-spec/SKILL.md \| grep "Sonnet subagent"`, which shows this exact line unchanged since before the feature). T8's own "grep sweep" claim (Done-when L259) was scoped to "old two-separate-reviews, sequential-only, or origin-based-classification" phrasing specifically — this is a different, real staleness category (wrong model name) that sweep didn't check for. | `skills/ship-spec/SKILL.md:36` (contradicts `:143`) | **Medium** — doesn't change actual runtime behavior (the operative Step 5 text at `:143` correctly says Haiku, so an implementer following the Steps gets it right), but a reader who trusts the Guardrails bullet in isolation would believe the wrong model, and it fails the "no stale references anywhere in Guardrails" bar T7/T8 implicitly claimed to have met | ❌ Confirmed contradiction |
| 3 | Old sequential/origin-based/two-review language sweep | `skills/ship-spec/SKILL.md` (full-file grep for "never in parallel", "strictly sequential", "two separate pending", "classify by finding origin", "always-fix") | — | ✅ Clean — zero hits; confirmed removed (present in the pre-feature version at `/tmp/old-ship-spec.md:38,118,121,134`, absent in current file) |
| 4 | Step-number cross-references within Comment-Triage Mode (0→1→2→3→4→5→6→7→8) | `skills/ship-spec/SKILL.md:133-146` | — | ✅ Clean — "step 4" (`:143`) correctly refers to the re-fetch step, "step 2" (`:144`) correctly refers to classification; no stale numbering found after the T5/T6/T7 renumbering |
| 5 | Model references (`sonnet` for Step 6 outer subagent, `claude-haiku-4-5-20251001` for drafting only, "default model" for classification/reply) | `skills/ship-spec/SKILL.md:116, 143, 159, 171` | — | ✅ Clean on the operative Step text (see #2 above for the one Guardrails-level exception) |
| 6 | `fix-code-review.md` plan-entry format (`design.md`'s Data Models section) vs. what Comment-Triage step 3 actually instructs | `skills/ship-spec/SKILL.md:141` vs `design.md:138-146` | — | ✅ Consistent — both specify `## Parallel`/`## Sequential` headers, per-entry thread ID + classification + `path:line` + one-line direction; SKILL.md additionally clarifies answer-only/pushback entries are audit-trail-only (a strict superset of, not a contradiction of, the design doc) |
| 7 | `templates/github-pr-review-mode.md` B1–B3 unchanged by the new B2' variant | `templates/github-pr-review-mode.md:20-34, 42-49` vs. `d13c237` diff | — | ✅ Clean — diff was pure addition (+6/-0), confirmed via `git show d13c237` |

**Result**: 5/7 clean, 2/7 confirmed defects (findings #1 and #2) → **Consistency Sweep: FAIL**

---

## Code Quality

| Principle | Status | Notes |
| --- | --- | --- |
| Minimum code | ✅ | Each commit's diff is proportional to its task (T1: +6/-0; T2: +4/-4 across 2 files; no oversized rewrites for the scope claimed) |
| Surgical changes | ✅ | T1/T2 are pure additions/1-line insertions; T3/T4/T5+T6/T7/T8 each touch only `skills/ship-spec/SKILL.md` (+ `.specs/` planning docs, expected) — no unrelated files touched in any commit |
| No scope creep | ⚠️ | T7 and T8 each note a documented, justified scope expansion (T7: added missing step-0 pending-review guard for SSF-07 AC1; T8: fixed an apply+commit delegation-wording ambiguity) — both are explicitly logged in tasks.md, not silent, and both close real gaps rather than adding unrequested features. Acceptable per project convention (documented deviations), not a defect. |
| Matches existing patterns | ✅ | New Guardrails/Step bullets match the file's existing bullet-list register and cross-reference style (e.g. "(see Guardrails)"); `B2'` naming in the template matches the existing `B1`/`B2`/`B3` convention |
| Spec-anchored outcome check (asserted values match spec) | ⚠️ | 23/24 AC bullets match exactly; 1 gap (Step 6 full-failure handling) — see above |
| Every changed section maps to a spec requirement — no unclaimed additions | ✅ | All Guardrails/Step edits trace to specific SSF IDs or documented SPEC_DEVIATION/scope-expansion notes; nothing added beyond what tasks.md scoped |
| Documented project guidelines followed | ✅ | `CLAUDE.md`'s "Skill Modification Rules" (only modify `local`-source skills) — all 4 touched files (`skills/ship-spec/`, `skills/code-review/`, `skills/tests-code-review/`, `templates/`) are project-local, not vendor-sourced; `docs/CLI.md`/`fsvskills` conventions not implicated (no `config/skills.json` changes needed for content-only edits) |
| Would a senior engineer approve? | ⚠️ | The core concurrent-dispatch/merge/classify/plan/split-phase-execution mechanism is well-designed and thoroughly cross-referenced. A senior reviewer would very likely flag the full-failure gap (a real, plausible production scenario with undefined behavior) and the stale Sonnet/Haiku Guardrails contradiction before approving — both are small, targeted fixes, not architectural problems |

---

## Edge Cases

From `spec.md`'s Edge Cases section:

- [ ] **>100 unresolved threads (GraphQL page-size cap) → process first page only, explicitly note in report that additional threads may exist.** ❌ **NOT handled.** `design.md`'s Out of Scope table explicitly states the cap itself is unchanged but "now explicitly surfaced in reporting (Edge Cases) rather than silently truncated" — i.e., the *reporting* half is in this feature's scope. Grepped `skills/ship-spec/SKILL.md` for "100", "page", "truncat" — zero hits in Comment-Triage Mode; step 8's report (`:146`) lists "threads processed, commits pushed, items blocked, items dropped by staleness check" but never a possible-truncation note. No task's Done-when (T1–T8) targeted this explicitly either — it fell through task decomposition.
- [x] **GitHub API call fails (posting) → report, don't swallow/retry indefinitely.** ✅ Handled for the Step 6 POST path (Guardrails `:39, 41`) and for subagent-level failures generally (`:41`). Fetch-specific failure handling (GraphQL read failures at Comment-Triage steps 1/4, which run in the orchestrator's own turn, not a subagent) has no explicit text — but this gap pre-dates the feature (confirmed absent in `/tmp/old-ship-spec.md` too) and was not part of any task's stated scope; noting as a pre-existing, out-of-diff condition rather than a regression.
- [ ] **Both Step 6 invocations fail → report both, don't proceed as if posted.** ❌ **NOT handled** — see Consistency Sweep #1 above (same gap, cross-referenced here since `spec.md` lists it independently under both the Story-1 narrative and Edge Cases).
- [x] **Fix trigger invoked a second time after a prior run resolved most threads → sees only remaining unresolved threads, fresh plan.** ✅ Handled — this falls out of the unchanged `isResolved: true` filter at Comment-Triage step 1 (`:134`), confirmed unchanged from the pre-feature version, and the plan file is explicitly "overwritten fresh each triage run" per `design.md`'s Data Models section (matches `:141`'s per-run write, no accumulation language).

**Status**: 2/4 handled, 2/4 confirmed gaps (both independently corroborated: the page-cap reporting gap by an absent Done-when item across all 8 tasks, and the full-failure gap by T3's own unticked Done-when checkbox)

---

## Gate Check

N/A for this feature. No test runner or build gate exists for `.md`-only changes — `tasks.md`'s Gate Check Commands table specifies `Gate Level: Inspection` for every task ("Read the diff; confirm the new/changed text matches the design and doesn't contradict adjacent unedited sections"), which is what this report performed throughout the Task Completion, Spec-Anchored, and Consistency Sweep sections above. No test-count delta applies (0 tests before, 0 tests after, by design).

---

## Fix Plans

### Fix 1: Explicit "both Step 6 invocations fail" handling (Story 1's implicit AC + spec.md Edge Case + T3's own unmet Done-when L131)

- **Root cause**: T3's Step 6 rewrite (`3ed9b71`) covered the full-success and partial-failure paths explicitly but never added text for the case where both `code-review` and `tests-code-review` invocations fail — an omission from the task's own stated Done-when criteria, not caught before commit.
- **Fix task**: In `skills/ship-spec/SKILL.md` Step 6 (near `:118`) and/or Guardrails (near `:39`), add an explicit rule: if both invocations have exhausted their scoped retry and both failed, do **not** issue any `POST .../reviews` call; return a compact result reporting both failure reasons; `ship-spec`'s own Step 7 should then report the failure to the user rather than claiming findings were published.
- **Priority**: Major — a real, reachable failure mode with currently undefined/risky behavior (empty-payload POST or silently-successful-looking failure).

### Fix 2: Reconcile Guardrails `:36` with the Haiku split-phase mechanism (Consistency Sweep #2)

- **Root cause**: T6 (`a188b72`) rewrote Comment-Triage Mode's execution mechanism to split drafting (Haiku) from commit-application, but never revisited the older, more general Guardrails bullet at `:36` that still describes the whole fix step as one "isolated Sonnet subagent."
- **Fix task**: Update `skills/ship-spec/SKILL.md:36` to reflect the current two-phase reality — e.g. "delegate fix-drafting to a Haiku subagent (capped at 4 concurrent) and commit-application to its own subagent call, per Comment-Triage Mode's fix step; keep only classification and reply/reject reasoning here."
- **Priority**: Medium — no runtime behavior is currently wrong (the operative Step 5 text governs), but the contradiction misleads anyone reading Guardrails in isolation and violates the "no stale text anywhere" bar the feature otherwise achieved.

### Fix 3: Add the >100-thread page-cap reporting note (spec.md Edge Case, no task ever scoped it)

- **Root cause**: `design.md`'s Out of Scope table explicitly commits to surfacing (not fixing) the pre-existing GraphQL 100-thread cap in reporting, but no task in `tasks.md` (T1–T8) carried a Done-when item for it — it fell through task decomposition between Design and Tasks.
- **Fix task**: In `skills/ship-spec/SKILL.md`, Comment-Triage Mode step 1 (fetch) or step 8 (report, `:146`), add: if the fetched thread count equals the page-size cap (100), note in the final report that additional unresolved threads may exist beyond what was fetched.
- **Priority**: Minor — a real gap against a stated spec Edge Case, but low likelihood/low blast-radius (100+ open unresolved threads on one PR is an extreme case) and easy to add alongside Fix 1/2.

---

## Requirement Traceability Update

**Status as of iteration 2 (current)**: SSF-02 and SSF-18 upgraded to fully ✅ Verified — their iteration-1 caveats (full-failure gap, stale Guardrails text) are both closed, confirmed with fresh evidence in [Re-verification (iteration 2)](#re-verification-iteration-2) below. Table below is iteration 1's original traceability update, left as the historical record.

| Requirement | Previous Status | New Status (iteration 1) |
| --- | --- | --- |
| SSF-01 | Pending | ✅ Verified |
| SSF-02 | Pending | ⚠️ Verified with gap (full-failure path — see Fix 1) — **upgraded to ✅ Verified in iteration 2** |
| SSF-03 | Pending | ✅ Verified |
| SSF-04 | Pending | ✅ Verified |
| SSF-05 | Pending | ✅ Verified |
| SSF-06 | Pending | ✅ Verified |
| SSF-07 | Pending | ✅ Verified |
| SSF-08 | Pending | ✅ Verified |
| SSF-09 | Pending | ✅ Verified |
| SSF-10 | Pending | ✅ Verified |
| SSF-11 | Pending | ✅ Verified |
| SSF-12 | Pending | ✅ Verified |
| SSF-13 | Pending | ✅ Verified |
| SSF-14 | Pending | ✅ Verified |
| SSF-15 | Pending | ✅ Verified |
| SSF-16 | Pending | ✅ Verified |
| SSF-17 | Pending | ✅ Verified |
| SSF-18 | Pending | ✅ Verified (see Consistency Sweep #2 for an adjacent, non-blocking Guardrails contradiction) — **contradiction closed in iteration 2** |

---

## STATE.md Decision Accuracy Check

- **AD-003** (one pending review per PR — GitHub platform constraint): Accurate and fully reflected in the implementation. `skills/ship-spec/SKILL.md:38` restates the same HTTP 422 constraint verbatim; Step 6 (`:116-123`) implements exactly the single-merged-POST mechanism AD-003 mandates. No drift between the decision log and shipped behavior.
- **AD-004** (model-tier scope boundary: judgment-bearing vs. mechanical-execution subagents): Accurate. Its stated scope ("`skills/ship-spec/` Comment-Triage fix-drafting today") matches exactly what was implemented — Haiku only for drafting (`:143`), default model explicitly preserved for classification/reply/pushback-validation (`:143`, `:171`). No scope drift found.
- Both entries remain **active** and require no correction.

## `fix-code-review.md` Format Cross-Check

`design.md`'s Data Models section (`## Parallel` / `## Sequential`, entries with `thread:<id>`, `[classification]`, `path:<file>:<line>`, one-line direction) is consistent with `skills/ship-spec/SKILL.md:141`'s actual instruction to Comment-Triage step 3. SKILL.md's wording is a strict superset (it additionally clarifies that answer-only/pushback entries appear for audit-trail purposes only and are excluded from drafting/commit) — no contradiction found.

---

## Summary

**Overall (iteration 2, current)**: ✅ PASS — all 3 gaps from iteration 1 confirmed fixed with fresh evidence; no regressions introduced. See [Re-verification (iteration 2)](#re-verification-iteration-2) below for the full re-check.

**Overall (iteration 1, historical)**: ⚠️ Issues — 3 concrete, well-evidenced gaps found (1 Major, 1 Medium, 1 Minor); the core architecture (concurrent Step 6 dispatch + single merged POST, uniform comment-presence classification, plan-file generation with staleness re-check, split-phase Haiku-tiered fix execution) is correctly, thoroughly, and consistently implemented across all 8 tasks

**Spec-anchored check**: 23/24 AC bullets matched spec outcome exactly (grouped under 18 allocated SSF IDs); 1 confirmed gap (Step 6 full-failure handling, adjacent to SSF-02)
**Consistency Sweep**: 5/7 clean, 2/7 confirmed defects (both-fail handling gap; stale Sonnet/Haiku Guardrails contradiction)
**Gate**: N/A (markdown-only feature, no test runner)

**What works**: The one-subagent-with-internal-concurrency Step 6 redesign is a well-justified, cleanly-executed SPEC_DEVIATION that improves on the original two-subagent design without losing any coverage. Comment-presence classification (T4) is uniformly and correctly worded with no origin-based leftovers anywhere. Plan-file generation, the no-approval-gate execution flow, and the re-fetch staleness check (T5) are all explicit and match `design.md`'s Data Model exactly. Split-phase concurrent drafting with Haiku tiering, capped-4 batching, serialized commits, and per-item narrow test scope (T6) are all unambiguously stated. T7's mid-task discovery and fix of the missing pending-review guard (SSF-07 AC1) is exactly the kind of self-correcting rigor this workflow is designed to reward. AD-003/AD-004 in `.specs/STATE.md` accurately reflect the shipped implementation.

**Issues found**:
1. **(Major)** Step 6 has no defined behavior for "both `code-review` and `tests-code-review` invocations fail" — risks an empty-payload POST or a silently-successful-looking failure; T3's own Done-when criterion for this was left unticked and unmet. Fix 1 above.
2. **(Medium)** Guardrails `:36` still claims the comment-triage fix step runs on "an isolated Sonnet subagent," contradicting the Haiku drafting model introduced by T6/SSF-17 — the operative Step 5 text is correct, but the Guardrails bullet is stale and misleading. Fix 2 above.
3. **(Minor)** The >100-unresolved-threads page-cap reporting note (`spec.md`'s Edge Case, explicitly committed to in `design.md`'s Out of Scope table) was never added to any task's scope and doesn't appear anywhere in the Comment-Triage report step. Fix 3 above.

**Next steps**: Apply Fix 1, Fix 2, and Fix 3 (all three are small, targeted text additions to `skills/ship-spec/SKILL.md` — no architecture changes, no re-opened design questions), then re-run this Verifier's Spec-Anchored (SSF-02 row) and Consistency Sweep (#1, #2) checks, plus the Edge Cases row for the page-cap note, against the fixed file.

---

## Re-verification (iteration 2)

**Date**: 2026-08-08
**Verifier**: fresh independent sub-agent (author ≠ verifier; did not write the iteration-1 report or the T9 fix commit)
**Fix commit reviewed**: `e379915` — `fix(ship-spec): address Verifier gaps — full-failure handling, stale Guardrails, page-cap note`
**Scope**: narrow re-check of the 3 iteration-1 gaps only, plus an independent regression sweep of the same three sections (Guardrails, Step 6, Comment-Triage Mode) and a `tasks.md` T1–T4 bookkeeping check. Full validation was **not** re-run from scratch, per instructions.

### Gap re-check

| # | Gap (iteration 1) | Severity | Fresh evidence | Status |
| --- | --- | --- | --- | --- |
| 1 | Step 6 had no defined behavior when both `code-review` and `tests-code-review` invocations fail | Major | All three claimed fix sites confirmed present and consistent: Guardrails `skills/ship-spec/SKILL.md:39` — "On a **full failure** (both invocations fail even after their scoped retry): do NOT issue any POST — there is no review to publish. Report both failure reasons and stop; never proceed as if a review was posted." Step 6b `:118` — "if **both** failed, do **not** issue any `POST` call — there is nothing to post." Step 6c `:119` — "If **both** failed, return both failure reasons and no counts — `ship-spec`'s Step 7 must then report the failure, never claim a review was published." Step 7 `:127` — "If Step 6 hit a full failure (both invocations failed, no review posted — see Guardrails), report the PR URL alongside both failure reasons instead — never claim findings were published when they weren't." | ✅ Fixed |
| 2 | Guardrails `:36` (pre-fix line) still named "Sonnet" for the whole comment-triage fix step, contradicting T6's Haiku drafting | Medium | `grep -n -i sonnet skills/ship-spec/SKILL.md` → 3 hits, none stale: `:30` and `:116`/`:159` all describe **Step 6's outer subagent**, which genuinely runs on `model: sonnet` (`:116`) — accurate, not a contradiction. The former stale line (old `:36`) now reads: "delegate fix-drafting to a Haiku subagent (capped at 4 concurrent) and commit-application to its own subagent call, per Comment-Triage Mode's fix step; keep only classification and reply/reject reasoning here." (`:36`) — matches Comment-Triage step 5's actual Haiku mechanism (`:143`) with zero remaining "Sonnet" mislabeling anywhere in the file. | ✅ Fixed |
| 3 | Comment-Triage Mode never noted the >100-thread GraphQL page-cap condition | Minor | `grep -n "page-size cap"` → 2 hits, both present as required: fetch step `:134` — "If the fetched thread count hits the query's page-size cap (100), note in the final report (step 8) that additional unresolved threads may exist beyond what was fetched..." and report step `:146` — "...and — if step 1 hit the page-size cap — a note that additional unresolved threads may exist beyond what was fetched." Matches `spec.md:141`'s WHEN/THEN exactly. | ✅ Fixed |

### Regression check (independent, not diff-based)

Did a fresh full-file read of Guardrails, Step 6, and Comment-Triage Mode in `skills/ship-spec/SKILL.md` for prose coherence (not just a diff against the fix commit):

- **Guardrails `:39` partial-vs-full-failure adjacency**: the partial-failure sentence ("retry ONLY the failed invocation once... Issue the single merged POST only after both invocations have resolved... never post twice, and never post before both have resolved.") and the new full-failure sentence sit in the same bullet, back to back. Read together they form a clean if/else: resolve both → if one succeeded, merge-and-post-once; if both failed, don't post. No contradiction, no gap between the two clauses.
- **Step 6 `:118`/`:119` internal coherence**: `:118`'s "if both failed, do not issue any POST... if at least one succeeded, merge... and issue exactly one POST" and `:119`'s matching "if one failed, return its failure reason... if both failed, return both failure reasons and no counts" are parallel in structure and don't diverge from Guardrails `:39`. No stale "merge both arrays" language survives that would imply a POST is always issued.
- **Step 7 `:127` new sentence beside the existing success sentence**: reads naturally — "Report the PR URL, and the finding count from each skill (...). If Step 6 hit a full failure (...), report the PR URL alongside both failure reasons instead — never claim findings were published when they weren't. Stop. Wait for the user." The "instead" clearly signals it replaces the finding-count report only in the full-failure branch; "Stop. Wait for the user." still applies to both branches. No ambiguity.
- **Step-number / terminology drift**: Comment-Triage Mode's step sequence (0 pending-guard → 1 fetch → 2 classify → 3 write plan → 4 re-fetch/diff → 5 draft+commit → 6 reply/resolve → 7 push → 8 report) is unchanged by this fix round — the fix only inserted a clause into existing steps 1 and 8, no renumbering, no new steps. Cross-references ("step 8", "step 4's staleness check") still point at the correct steps. No drift found.
- **No new stale text introduced**: grepped for leftover "two separate pending reviews", "always-fix", "never in parallel", "classify by finding origin" — zero hits, consistent with iteration 1's Consistency Sweep #3.

**Result: no regressions found.**

### `tasks.md` T1–T4 bookkeeping check

- T1 (`tasks.md:80-83`), T2 (`:104-107`), T4 (`:154-156`): all Done-when boxes now `[x]`, confirmed via direct read — the iteration-1 "bookkeeping gap" (complete work, unticked boxes) is closed.
- T3 (`:128-133`): all boxes now `[x]`, and the Done-when text itself was rewritten (not just ticked) to describe the actual shipped mechanism — "Step 6's **one subagent** issues two concurrent tool calls within its own turn... entirely inside its own context" — accurately reflecting the one-subagent-with-internal-concurrency SPEC_DEVIATION rather than the original two-top-level-subagents design it was originally scoped against. The new L131 ("Full-failure case (both fail) stops before any POST, reports both failures — fixed post-Verifier (Fix 1, see validation.md)") and L133 ("Step 7... except now also handles the full-failure report case (Fix 1)") both accurately cross-reference this fix round rather than silently rewriting history.

### Verdict

**PASS.** All 3 gaps from iteration 1 (1 Major, 1 Medium, 1 Minor) are confirmed fixed with fresh, independently-derived evidence — not just trusted from the fix commit's own message. No new regressions were introduced by the fix round: the full-failure and partial-failure text read as a coherent single rule, Step 7's new sentence is unambiguous alongside the existing one, and no step-numbering or terminology drift resulted from the edits. `tasks.md` T1–T4's Done-when checkboxes are ticked and accurate, and T3's rewritten Done-when text now correctly documents its own SPEC_DEVIATION. No remaining gaps to report.
