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
- **Status**: superseded by AD-026

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
- **Status**: superseded by AD-024

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
- **Status**: superseded by AD-018

### AD-010
- **Decision**: Replace the `templates/subagent-models.md` / `templates/subagent-dispatch-contract.md` links (State ownership's dispatch-contract sentence, the Subagent models section, and `WORKFLOW.md`'s diagram note) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-024

### AD-011
- **Decision**: Replace the two `templates/agent-wait-protocol.md` links (the shared wait instruction covering Steps 3, 6a, 6b, 7, 9, 11, 12, 13, 15, and the `UNKNOWN`-mergeability clock-wait note) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-010).
- **Trade-off**: Same dependency as AD-010 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-024

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
- **Status**: superseded by AD-017

### AD-014
- **Decision**: Step 11 invokes `code-review` via the `Skill` tool directly from the orchestrator — no wrapper subagent — passing `human_review` through (`false` when `code-review` is in `human_review_exclude`); `code-review` runs review, its own checkpoint, submit, and fix. Step 12 (fix-review) is removed along with this skill's own submit-on-behalf GraphQL call, and Steps 13–15 renumber to 12–14 across `SKILL.md`, `WORKFLOW.md`, and `references/progress-schema.md`. Before ending a turn at `code-review`'s checkpoint the orchestrator records `code_review: pending`; resuming with it waits for the user again, then invokes `code-review`'s continue-after-checkpoint entry instead of re-reviewing, and `progress-schema.md`'s Resume Logic checks a pending checkpoint before `last_completed_step`. Step 0's open-PR re-entry uses the fix-existing-findings entry, passing the recorded worktree and feature folder. A blocked publish or delivery is retried once through the continue entry, replacing the old "dispatch a subagent to retry the posting". This reverses the "Steps 11 and 12 never call `Skill` from the orchestrator" rule.
- **Reason**: `fix-review` was merged into `code-review` as one review → fix run (`skills/code-review/STATE.md` AD-010), and `code-review`'s checkpoint must end the conversation's turn to pause for the user, which a subagent cannot do. The reversed rule existed because `fix-review` ran its whole fixing pass in whatever context invoked it — 39–60% of the orchestrator's cost on four runs; `code-review` run from a root conversation does its heavy work only in its own review and fix workers and keeps compact results here, so the cost reason no longer applies.
- **Trade-off**: `code-review`'s `SKILL.md` is now loaded into the orchestrator's context. The guarantee that heavy work stays out of it rests on `code-review` honoring its own worker rule; if a future measurement shows review or fix bulk landing in the orchestrator, the fix belongs in `code-review`, not a wrapper here. In-flight runs whose `progress.md` logged Steps 12–15 under the old numbering, or `complete_review`/`fix-review` state, need a manual edit before resuming.
- **Date**: 2026-09-13
- **Status**: active

### AD-015
- **Decision**: Step 11 splits `code-review` failures by what failed: a review or posting failure `code-review` could not recover stops the run; only a `submit` or delivery failure retries the continue-after-checkpoint entry once. Resuming at a paused `code_review` passes the same fields as the first invocation (PR number, owner/repo, `gh_login`, feature folder, `worktree_path`).
- **Reason**: The previous rule retried every publishing failure through continue-after-checkpoint, which never posts: after a failed post it submitted nothing, found no threads, reported success, and let Step 14 mark the PR ready with every finding lost (post-merge validation of 954ac76, `skills/code-review/STATE.md` AD-011). The resume invocation also omitted the feature folder and worktree, so the fix worker wrote no plan file.
- **Trade-off**: A posting failure now ends the run instead of limping on, so the user must re-run after the cause (usually a rate-limit block) clears.
- **Date**: 2026-09-13
- **Status**: superseded by AD-016

### AD-016
- **Decision**: Step 11 no longer retries the continue-after-checkpoint entry after a `submit` or delivery failure `code-review` still reports; every failure `code-review` reports after its own retry stops the run. The rule against using the continue entry for a review or posting failure stays.
- **Reason**: `code-review` already retries each failure once (its AD-012: one retry per failure in total). A second retry from here stacked on it, giving a third attempt the second validation flagged — and pre-merge `build-feature` Step 12 never retried the fix skill beyond that skill's own retry.
- **Trade-off**: A delivery that fails twice ends the run; the user re-runs once the cause clears, and `code-review`'s continue entry picks up from the posted, submitted review.
- **Date**: 2026-09-13
- **Status**: active

### AD-017
- **Decision**: Step 14's `CONFLICTING` handling no longer verifies "per Test Execution Scope"; the conflict-resolution subagent now verifies with build/typecheck/lint plus the tests covering what the merge brought in, and reports what verification it ran.
- **Reason**: By the user's decision, the global Test Execution Scope rule set (the `CLAUDE.global.md` subsection and `references/test-execution-scope.md`) was removed from the harness, so this step can no longer name it and must state its own verification.
- **Trade-off**: The step no longer inherits the removed rule's docs-only merge exemption or its explicit-delegation wording; a merge that brings in only docs still runs build/typecheck/lint.
- **Date**: 2026-09-14
- **Status**: active

### AD-018
- **Decision**: Removed the `### gh account resolution` section, the "(after account resolution above)" prerequisite, and every `gh_login` use (Run State field in `progress.md` and `scripts/progress.mjs --init`, the resume field list, and the login passed to `code-review` in Step 11 and on resume). The `scripts/hooks/resolve-gh-account.sh` hook (SessionStart + CwdChanged, registered in `config/hooks.json`) now scopes every `gh` call in the session to the repo's account by exporting `GH_TOKEN` through `CLAUDE_ENV_FILE`. The never-print-credentials rule stays.
- **Reason**: The prose procedure could not be followed as written (its `$(...)` scoping is refused in worktree-isolated sessions, exported env does not persist between Bash calls, and its email match had no supplier — `docs/harness-evaluation.md` References #1-#6, Skills #43). The hook resolves the account deterministically from the repo's own data (SSH key identity, remote owner, push access) before the first tool call, and a live headless test confirmed both the main session's and a dispatched subagent's `gh api user` ran as the resolved account while a different account was active.
- **Trade-off**: The skill now depends on the hook being installed (`fs-harness hooks`, checked by `fs-harness doctor`); when the hook cannot resolve an account it only tells the session to ask the user, and a `progress.md` written before this change still carries a `gh_login` line that nothing reads.
- **Date**: 2026-09-14
- **Status**: active

### AD-019
- **Decision**: The Step 10 PR description sources **What was done** from `tasks.md`'s completed checklist plus the branch's commits (`git log --oneline origin/<target_branch>..HEAD`), and the PR section's sourcing list drops `commits.md` in favor of the branch's own commits.
- **Reason**: By the user's decision, the `tlc-spec-driven` overlay no longer maintains a per-feature `commits.md`; what was pushed can be read from the repository itself, which also removes the log's uncommitted-file and drift problems.
- **Trade-off**: The commit list covers every commit on the branch ahead of the target, including Step 8's spec/design/tasks commit, not only commits traced to a task.
- **Date**: 2026-09-14
- **Status**: superseded by AD-026

### AD-020
- **Decision**: Step 12 passes `origin/<target_branch>` explicitly to `architecture-evaluate` as its base ref, so Incremental mode syncs the commit range `origin/<target_branch>...HEAD`.
- **Reason**: harness-evaluation Skills #1: by Step 12 everything is committed and pushed, so an Incremental run that reads only the working tree finds nothing and stops; `architecture-evaluate` now accepts a caller-supplied base ref (its AD-008).
- **Trade-off**: The sync covers every commit on the branch ahead of the target, including Step 8's spec commit, not only this run's code changes.
- **Date**: 2026-09-14
- **Status**: superseded by AD-026

### AD-021
- **Decision**: Step 3's `full` result means "the project has no context docs at all" only when the gate cites the "No `docs/codebase/` baseline exists" row; any other `full` trigger is reported as "the gate recommends a Full refresh (<trigger>)". The gate subagent returns the triggering row with its answer. Full mode still never runs inside a delivery.
- **Reason**: harness-evaluation Skills #17: the trigger table also maps new dependencies, CI changes, and onboarding to Full, so a branch touching those made this step misreport a missing baseline.
- **Trade-off**: None identified.
- **Date**: 2026-09-14
- **Status**: superseded by AD-023

### AD-022
- **Decision**: Step 0 finds a run by `task_id` alone: it enumerates `git worktree list` and globs `.specs/features/<task_id>-*/progress.md` inside each worktree, and the same enumeration drives the cleanup sweep. `task_id` is always required; `base_branch` and `description` are required only on a fresh run, since a re-invocation reads them from `progress.md`. The sweep removes the worktree of every tracked spec whose PR is `MERGED` or `CLOSED` with `git worktree remove` from the main checkout — `--force` only when the worktree's sole uncommitted file is that run's own `progress.md`, otherwise it leaves the worktree and reports it. `ExitWorktree` is only for leaving a worktree entered in this same session. Examples keep one slug per task.
- **Reason**: harness-evaluation Skills #20, #24, #31. `progress.md` lives only in the worktree and is never committed, so the old repo-relative lookup never found a run from the main checkout; the slug was a free 2–4 word choice that could not be re-derived; and `ExitWorktree` does nothing to worktrees from an earlier session. A plain `git worktree remove` was confirmed to refuse a worktree holding an untracked `progress.md`, so the removal needs `--force` in exactly that case.
- **Trade-off**: A worktree with any other uncommitted change is never swept automatically; the user removes it. Removing it also deletes that run's `progress.md`, so a later invocation for the same `task_id` starts fresh (and stops at the branch collision if the branch still exists).
- **Date**: 2026-09-14
- **Status**: active

### AD-023
- **Decision**: Delete Step 3 (the Haiku architecture-evaluate gate) and renumber: old 4→3, 5→4, 6a→5a, 6b→5b, 7→6, 8→7, 9→8, 10→9, 11→10, 12→11, 13→12, 14→13, across `SKILL.md`, `references/progress-schema.md`, `WORKFLOW.md`, `subagent-dispatch`'s model matrix, and two `code-review` example rows. Step 11 runs `architecture-evaluate` in a Sonnet subagent and lets that skill pick its own mode; the "Incremental always, never Full" rule is gone.
- **Reason**: harness-evaluation Skills #23. No gate result changed any later step, its `full` reading was wrong, and it contradicted itself about touching files. `architecture-evaluate` already selects its mode from the scan's facts and the caller's range, which the user agreed it should own.
- **Trade-off**: A `progress.md` written under the old numbering needs a manual edit before resuming. `architecture-evaluate` may now choose Full inside a delivery (for example when no baseline exists), which the old rule forbade.
- **Date**: 2026-09-14
- **Status**: active

### AD-024
- **Decision**: Delete the `### Subagent models` and `### Waiting on dispatched subagents` sections and every `subagent-dispatch` mention. Each step heading keeps its model; the dispatch return shape, completion condition, and delegation depth are stated inline in State ownership without pointing at another skill. Flow facts only those sections held moved to their places: "never invoke via `Skill` a skill that does its heavy work inline" to Step 10, and "`human_review` never changes a step's model" to the `human_review` parameter. Step 10's Skill-not-subagent reason and Step 3's in-conversation grilling were already stated in their steps. History narratives (the PR-ready incident, the design-sync attempts, the `/compact` measurements) were cut to their rule sentences.
- **Reason**: harness-evaluation Skills #32 and #42, and the user's rule that how to dispatch and wait belongs to the dispatch mechanism, not to this flow, and that the skill mentions only the skills it orchestrates. The narratives are already in this log.
- **Trade-off**: The skill no longer tells the orchestrator to load a wait protocol before dispatching; waiting behavior depends on whatever dispatch guidance the session otherwise has.
- **Date**: 2026-09-14
- **Status**: active

### AD-025
- **Decision**: `progress.md` is created at Step 1 by `scripts/progress.mjs --init`, which now creates the feature folder, with an absolute `worktree_path`; Step 4 writes `grilling-session.md` into that folder. The spec and design checkpoints record `pending` before pausing and `approved` after, like the code-review checkpoint. Run State gains `design_sync` (`pending-user-action` | `skipped`) and `merge_check` (`clean` | `resolved` | `inconclusive` | `conflicting`); Step 12's log line takes the script's `done — pending-user-action …` form; Step 6 (Tasks) gains a `skipped (Small/Medium scope)` value; the feature folder is the directory holding `progress.md`, not a recorded field.
- **Reason**: harness-evaluation Skills #22, #25, #26 (schema part), #37. Step 1 wrote to a file whose folder did not exist until Step 5 and `--init` did not create directories; only the code-review checkpoint was detectable on resume; and the schema lacked fields the steps wrote, with a Step 13 line the script could not produce.
- **Trade-off**: None identified.
- **Date**: 2026-09-14
- **Status**: active

### AD-026
- **Decision**: Remaining harness-evaluation Skills fixes (#21, #26–#30, #34–#36, #38–#41): the Step 9 PR description and the Step 11 docs sync use the commits made on this worktree's branch (`git log --oneline origin/<base_branch>..HEAD` and base ref `origin/<base_branch>`, range `origin/<base_branch>...HEAD`), not `origin/<target_branch>`; when Tasks is skipped, the draft PR body and PR description take their checklist from `spec.md`'s acceptance criteria and the branch's commits; Step 11 commits every file the sync touched under the new-vs-modified rule and returns package candidates and questions as `status: question` items for the final report; Step 13 routes on `mergeable` alone, with `mergeStateStatus` informational; a `question` from a tlc-spec-driven phase is answered from `grilling-session.md`, else asked and re-dispatched (`human_review=no`: recorded as a `spec.md` assumption), and Specify/Design read `grilling-session.md` as their clarification source; Step 8's prompt pre-approves tlc-spec-driven's per-batch workers and the Verifier; Step 10 says `code-review` owns its review, submit, fix and recovery chain, keeping only stop-and-report and never-continue-after-a-review-or-posting-failure; `<desc-kebab>` names the branch; the Resuming section and Examples 2, 3, 5 are deleted; the frontmatter, intro, and allowed-tool list say heavy steps are delegated while the orchestrator runs git/gh plumbing, writes `grilling-session.md`, and copies `docs/codebase/`; the Worktree guardrail drops the command-shape sentences, keeping absolute paths and the `/design-login` rule.
- **Reason**: The branch is cut from `base_branch`, so a range against `target_branch` is wrong whenever the two differ; the rest are the evaluation's findings as decided by the user.
- **Trade-off**: The skill no longer states the worktree guard's command-shape limits, so a refused compound command is rediscovered at runtime.
- **Date**: 2026-09-14
- **Status**: active
