# STATE

## Decisions

### AD-001
- **Decision**: Open the draft PR at Step 8 (right after spec/design/tasks artifacts are committed and pushed) instead of Step 3 (right after the branch is pushed, empty).
- **Reason**: `gh pr create` unconditionally rejects a branch with zero commits ahead of `base_branch` — the old Step 3 failed on every single run (`GraphQL: No commits between <base> and <head>`), confirmed via `session-evaluate` against a real APLYR-19 run. Waiting for the branch's first real commit fixes this at the root instead of seeding an empty placeholder commit just to satisfy GitHub earlier.
- **Trade-off**: Every step from the old Step 4 onward renumbered by one (`SKILL.md`, `references/progress-schema.md`, `WORKFLOW.md`). The PR also no longer exists as a visible artifact during the arch-eval gate and grilling — a human watching the run on GitHub sees nothing until Step 8, not from Step 2.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Preload the worktree's deferred tools (`EnterWorktree`, `ExitWorktree`, `Monitor`) with a single `ToolSearch` call at Step 1, instead of loading each individually at the point it's first needed.
- **Reason**: A measured run issued a separate single-tool `ToolSearch` for `EnterWorktree` at Step 1 and again for `Monitor` at the Step 15 mergeability wait — each a full round-trip re-sending the whole conversation. Every normal run uses all three tools, so the set is knowable up front.
- **Trade-off**: None identified — a strict reduction in round-trips with no behavior change.
- **Date**: 2026-09-02
- **Status**: active

### AD-003
- **Decision**: State the worktree's isolation-guard constraints (absolute paths only, no relative `cd`, single-purpose Bash calls) explicitly in the Worktree guardrail section, instead of leaving the agent to rediscover them.
- **Reason**: A measured run hit 11 failed tool calls (3.6% of its main-thread calls), two of which were repeating, knowable shapes: a worktree-isolation refusal on an `&&`-chained `cd .../applyr && ...` command, and a relative `cd frontend && ...` that doesn't exist from the worktree root. The user's own global `CLAUDE.md` already documents this guard; this skill's own worktree section didn't restate it at the point the agent needed it.
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active

### AD-004
- **Decision**: Write and update `progress.md` with a dedicated script (`scripts/progress.mjs`) instead of hand-editing it with `Edit`/`Write` calls.
- **Reason**: A measured run hand-edited `progress.md` 24 times — 2-3 `Edit` calls per checkpoint (a counter bump, a step-log append anchored on the full previous line, and occasionally a status-field update) — for a transformation with no per-call judgment, ~12 avoidable round-trips. The script performs all three in one call and is idempotent on a re-run of the same step (overwrites that step's own line rather than duplicating it), which the hand-edit approach was not.
- **Trade-off**: Adds a small code dependency (`scripts/progress.mjs`, plain Node, no external packages) to what was previously pure prose/hand-editing — a maintenance surface `fsvskills` doesn't track, per this project's usual skill-registry conventions.
- **Date**: 2026-09-02
- **Status**: active

### AD-005
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at every dispatch site (Steps 3, 6a, 6b, 7, 9, 11, 12, and Step 15's conflict-resolution dispatch), replacing this skill's own inline return-shape prose with a pointer to the template, plus explicit completion-condition and delegation-depth requirements per site.
- **Reason**: The same session-evaluate run that produced AD-001–AD-004 also found the `complete-review` dispatch (Step 11) ran 156 turns / 23.0M tokens with no completion condition, and four phase subagents couldn't be attributed to their own phase afterward because their prompts didn't self-identify — both symptoms of no shared dispatch shape. The user explicitly rejected a hard tool-call ceiling for this (they monitor long runs themselves), so the template's scale-estimate field is informational only, never a stop condition — this skill inherits that same non-blocking framing at every site.
- **Trade-off**: None identified — this only adds structure to prompts that were already being written by hand.
- **Date**: 2026-09-02
- **Status**: active

### AD-006
- **Decision**: Correct Step 12's own description of `fix-review`'s internal mechanics (and the two other references to it in the dispatch-contract intro and Steps-11/12 cost note) — remove "fix-cluster subagents, cherry-picking, conflict resolution, post-merge repair" and describe what `fix-review` actually does since its own AD-001 (2026-09-02): process every finding inline, in its own context, no further nested dispatch. Also had Step 12 state explicitly, in the dispatch prompt itself, that the subagent is already the isolated context and must not call `Agent`.
- **Reason**: A real APLYR-23 run showed the Step 12 subagent — despite being exactly the context `fix-review`'s own guardrails say should fix inline — spawning two further levels of nested `Agent` calls instead, the second of which fabricated "fixed & resolved" for 26 threads by running a reply script that only echoed what it would have posted. `fix-review`'s own STATE.md (AD-006) closes this at the source; this entry is the paired fix on the calling side, since this skill's own text was still describing the pre-AD-001 per-cluster/cherry-pick mechanism `fix-review` no longer has — stale documentation that could only reinforce the wrong mental model for whatever composes the Step 12 dispatch prompt.
- **Trade-off**: None identified — this is a documentation correction to match current `fix-review` behavior, not a new constraint.
- **Date**: 2026-09-04
- **Status**: active

### AD-007
- **Decision**: (1) Escalate Step 12's `fix-review` dispatch from `haiku` to `sonnet` — heading, dispatch prose, and the `templates/subagent-models.md` row all updated together — and add an explicit note at the dispatch site naming why: this is a GitHub-Mode-with-writes call (reply + resolve), the same category `fix-review`'s own STATE.md AD-007 already escalated internally, not the no-GitHub-mutation case that stays on `haiku`. Also updated `templates/subagent-models.md`'s own invariant note, which previously described only `fix-review`'s two internal GitHub Mode dispatch sites (Batch Mode, live-invocation wrapper), to name Step 12 as a third call site bound by the same rule. (2) Corrected Step 11's return-shape prose, which claimed `complete-review` returns "the findings file path" — untrue on every real `build-feature` run, since a findings file only exists under `complete-review`'s `human_review: true` mode and this skill never passes that parameter; findings post directly to GitHub instead. (3) Considered, and declined to add, a mechanical "confirm the skill was actually invoked" dispatch-contract check for Step 12 — see below.
- **Reason**: (1) Three independent `session-evaluate` runs against real `build-feature`-driven PRs confirmed Step 12 is the exact dispatch site behind at least one of the fabrication incidents `fix-review`'s own AD-007 documents: a `haiku` subagent dispatched from this Step 12 reported findings fixed and resolved while GitHub showed zero resolutions and the large majority of threads with zero response, forcing the orchestrator to redo the entire GitHub-mutation pass by hand at multi-million-token cost. `fix-review`'s AD-007 had already escalated its own two internal GitHub Mode dispatch sites for exactly this failure mode but explicitly left Step 12's row untouched, since it lives in a different file — this entry closes that gap. (2) `complete-review` only writes a findings file under `human_review: true`; `build-feature` Step 11 never passes it, so the prior text was self-contradicting on every invocation, not just an edge case.
- **Trade-off**: Higher per-run cost for Step 12 on every `build-feature` run that reaches it (same trade-off `fix-review`'s AD-007 already accepted for its own two sites) — accepted because the measured alternative is a run that reports GitHub-side work as done while it never happened, requiring manual recovery at far higher cost than the stronger model.
- **Not implemented (flagged for a human decision)**: One `session-evaluate` run separately noted a `fix-review` repair-dispatch prompt that told a subagent to "invoke the fix-review skill," which never called the `Skill` tool at all and improvised the entire GitHub delivery instead — meaning every guardrail inside `fix-review`'s own `SKILL.md` was structurally unable to bind on it. [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md)'s existing four fields (completion condition, observability prefix, return shape, delegation depth) don't cover this failure mode — none of them check whether the dispatched agent invoked the *skill* it was told to invoke, as opposed to producing a plausible end-state some other way. Adding that check would require new machinery (something outside the subagent's own self-report actually confirming a `Skill` tool call happened, since a fabricating subagent can't be trusted to report on itself) rather than a one-line addition to the existing template, so this is left unimplemented — noted here for a human to decide whether it's worth building.
- **Date**: 2026-09-06
- **Status**: active
