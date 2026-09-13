# STATE

## Decisions

> **Note on token figures.** Absolute token counts in the entries below were produced by
> `session-evaluate`'s `session_metrics.py` before the counting fix recorded in that skill's
> STATE.md AD-006, and are inflated by roughly 2x (measured 1.98x-2.64x, varying with per-turn
> parallelism). Counts, rates and shares — findings fixed, duplication rate, invalid rate, turn
> counts, share of spend — are unaffected, and no decision below rests on an absolute total.
> Read the token magnitudes as approximate and about half of what is written.

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
- **Trade-off**: Adds a small code dependency (`scripts/progress.mjs`, plain Node, no external packages) to what was previously pure prose/hand-editing — a maintenance surface `fs-harness` doesn't track, per this project's usual skill-registry conventions.
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
- **Decision**: Replace the State ownership section's inline `node scripts/progress.mjs <path> --init ...` full CLI usage block with a short pointer to the script's own usage header, keeping only the behavioral rule (use the script, never hand-edit `progress.md`).
- **Reason**: The 2026-09-12 `harness-eval` run (`docs/harness-evaluation.md`, Skills section, row #4) flagged the inline block as a verbatim duplicate of `scripts/progress.mjs`'s own header docstring (Track B, dual REDUNDANT-CODE, cost ≤1, claim C016) — cheaply rediscoverable by reading the script, and a drift risk if the two copies diverge.
- **Trade-off**: None identified — this only removes a duplicated text block; the behavioral rule and the script's own usage documentation are unchanged.
- **Date**: 2026-09-12
- **Status**: active

### AD-008
- **Decision**: Following human review of the 2026-09-12 `harness-eval` run's 6 disputed claims (`docs/harness-evaluation.md`, Skills section, row #5): cut `C011`/`C012` (the `fix-review`/`architecture-evaluate` ownership bullets in Composability) entirely; trim `C033` (Subagent models), `C038` (gh account resolution), and `C099` (Step 15 `CONFLICTING` handling) to pointers at their respective templates (`templates/subagent-models.md`, `templates/gh-account-resolution.md`, `templates/test-execution-scope.md`), dropping the mechanics each template already states in full; keep `C046` (the `gh auth token` credential-hygiene line under Credentials) as-is, unedited.
- **Reason**: `C011`/`C012` were near-verbatim restatements of `fix-review`'s and `architecture-evaluate`'s own frontmatter `description` fields — content already surfaced automatically in the skill listing. `C033`/`C038`/`C099` restated mechanics (the four model aliases and no-effort-parameter fact; gh-resolution's resolve-once/cache/never-persist-token steps; merge-conflict verification scoping and the "auto-merge produces semantic breakage" rationale) that already live verbatim in the linked templates, so this skill only needed to keep the routing instruction to read/apply each template plus its own behavioral rule, not a copy of the template's content. `C046` was kept because a repo-wide grep of both `CLAUDE.md` (project) and `~/.claude/CLAUDE.md` (user global) found no other statement of this specific `gh auth token` credential rule anywhere in the loaded context — J2's KEEP-POLICY case held up under verification, unlike the other five.
- **Trade-off**: None identified for the cuts/trims — each replaced restatement with a pointer to the file that already states it in full, and the pointers were confirmed to resolve. `C046` has no trade-off since it wasn't touched.
- **Date**: 2026-09-12
- **Status**: active

### AD-009
- **Decision**: Revise AD-008's `C038` handling only (its other four decisions are unaffected). The shared `gh` account resolution mechanism (why `gh auth status`'s active marker can't be trusted, the resolve/cache/never-persist-token algorithm) moved out of `templates/gh-account-resolution.md`-as-linked-from-skills and into the user's global `CLAUDE.md` (`CLAUDE.global.md`, symlinked to `~/.claude/CLAUDE.md`) as a standing rule, since that mechanism is a fact about the user's own `gh` CLI environment, not something scoped to this repo's skills. This skill's two references (Steps 84-86 and 200) drop the `../../templates/gh-account-resolution.md` link and become a one-line `gh` account resolution: mandatory tag, keeping only the skill-local reasoning for why it's mandatory here (long run, multiple `gh`-using subagents, branch pushes and PR writes).
- **Reason**: A pointer repeated at every one of the 4 consuming skills was fan-out from one file, not true duplication, but it still meant the *mechanism* lived behind a link that only these 4 skills knew to follow — an ad-hoc `gh` call outside all 4 skills had no trigger to consider account resolution at all. Promoting the mechanism to global `CLAUDE.md` (loaded in every session, including this skill's own subagents) closes that gap without leaking skill-specific knowledge into a user-global file: the mandatory-vs-opt-in *application* decision, which is genuinely skill-local, stays in each skill as a short tag instead.
- **Trade-off**: This skill's `gh` account resolution mandatory-tag no longer explains the mechanism itself — it depends on the user's global `CLAUDE.md` being loaded in whatever context runs this skill. Accepted since global `CLAUDE.md` load is standard for every Claude Code session and subagent in this environment; if a future execution context ever skips user-global config, this tag alone would not recover the algorithm.
- **Date**: 2026-09-13
- **Status**: active

### AD-010
- **Decision**: Replace the `templates/subagent-models.md` / `templates/subagent-dispatch-contract.md` links (State ownership's dispatch-contract sentence, the Subagent models section, and `WORKFLOW.md`'s diagram note) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-011
- **Decision**: Replace the two `templates/agent-wait-protocol.md` links (the shared wait instruction covering Steps 3, 6a, 6b, 7, 9, 11, 12, 13, 15, and the `UNKNOWN`-mergeability clock-wait note) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-010).
- **Trade-off**: Same dependency as AD-010 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-012
- **Decision**: Step 11 invokes `code-review` with `post: true` instead of `complete-review` with no `human_review` parameter; the checkpoint name in `human_review_exclude` and `progress.md`'s `Checkpoints` key become `code-review` / `code_review` (written by `scripts/progress.mjs`).
- **Reason**: `complete-review` and `tests-code-review` were merged into `code-review` (see `skills/code-review/STATE.md` AD-009). There a PR review reports locally unless `post: true`, so the flag is what preserves this skill's always-publish-immediately behavior — omitting it would leave Step 12 with no review to fix.
- **Trade-off**: No legacy alias: an in-flight run whose `progress.md` or invocation still says `complete-review` / `complete_review` needs that value updated by hand before resuming.
- **Date**: 2026-09-13
- **Status**: active

### AD-013
- **Decision**: Drop the direct `templates/test-execution-scope.md` link in Step 15's `CONFLICTING` handling — state "verify per Test Execution Scope" as a named convention, no file path, no mention of `CLAUDE.md` by name.
- **Reason**: A direct subagent probe confirmed a dispatched subagent inherits the user's global `CLAUDE.md` in full, including the condensed Test Execution Scope tiers/stop-rule already mirrored there. The one piece of the full template not already inline — the Merges-scope-by-content rule this step actually needs — was folded into that global `CLAUDE.md` directly, so nothing this step depended on was lost by cutting the link. This is not a re-litigation of `docs/harness-evaluation.md` row 13's earlier "do not cut" verdict: that review rejected cutting for exactly this gap; closing the gap first is what makes the cut safe now.
- **Trade-off**: This step's own text no longer names any file for a reader wanting the full rationale behind Test Execution Scope (still available at `~/.claude/references/test-execution-scope.md`, just not linked from here); the guarantee now depends on the user's global `CLAUDE.md` staying loaded and in sync wherever this skill runs.
- **Date**: 2026-09-13
- **Status**: active
