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
