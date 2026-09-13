---
name: build-feature
description: Delivers a brand-new feature end-to-end with no planning already done — creates a worktree and branch from base_branch, opens a draft PR against target_branch, optionally grills the user on scope, runs tlc-spec-driven's full Specify→Design→Tasks→Execute cycle, updates the PR description, runs code-review (review, optional checkpoint, and fixes), syncs architecture docs, then confirms the PR actually merges before marking it ready — through isolated subagents for every step but grilling and code-review, the two that run live in this conversation (code-review keeps its own work in its own workers) — and, when the project uses Claude Design, closes by handing design-sync back to the user as a required follow-up it cannot run itself, resumable from any interrupted step via progress.md, self-routing a later re-invocation straight to fresh PR comments once delivered. Requires base_branch, target_branch (defaults to base_branch), task_id, and description; human_review (default yes) gates spec/design/code-review pauses. Use when the user says "build feature", "start a new feature end to end", "deliver this feature autonomously", or invokes /build-feature. Do NOT use to fix PR comments outside this flow (use code-review's fix-existing-findings entry directly).
metadata:
  author: Flavio Studart
  version: "2.0.0"
---

# Build Feature

Takes a feature from nothing but a task ID and a description to a PR marked ready for review, with no human interaction required beyond what `human_review` asks for. An orchestrator that does almost none of the work itself — every step but two delegates to an isolated subagent and reports back a structured result, so this conversation's own context stays small enough to survive a run with a dozen-plus steps. The exceptions are grilling (Step 4), a live multi-round conversation with the user that only this conversation can hold, and `code-review` (Step 11), whose checkpoint must be able to end this turn — it still does its heavy work in its own workers.

## Parameters

Required, never inferred — ask if missing, do not guess:

- `base_branch` — branch the feature branch is cut from.
- `task_id` — used in the branch name, PR title, and feature folder name.
- `description` — short text; becomes a kebab-case slug for the branch/folder name.

Optional:

- `target_branch` — the PR's merge target. Defaults to `base_branch` when omitted (a superset of a same-branch delivery, not a different default).
- `human_review` — `yes` (default) or `no`. `yes` pauses after Specify, after Design (when Design runs at all), and at `code-review`'s checkpoint, after its findings are posted to GitHub as a pending review and before anything is fixed (see Step 11), waiting for approval before continuing each time. `no` runs the whole pipeline without pausing anywhere this parameter controls.
- `human_review_exclude` — comma-separated subset of `spec`, `design`, `code-review` to skip pausing on even when `human_review=yes` (e.g. `human_review_exclude=code-review`). Ignored when `human_review=no`.

## Guardrails

### Composability — do not reimplement what other skills own

- tlc-spec-driven owns Specify/Design/Tasks/Execute's own internal mechanics (auto-sizing, atomic commits, gate checks, the Verifier). Invoke it; don't duplicate its logic.
- `code-review` owns reviewing, its checkpoint, submitting the review, fixing, and replying — Step 11 invokes it once and passes `human_review` through (`false` when `code-review` is in `human_review_exclude`); this skill never posts, submits, fixes, or replies itself.
- `not-your-babysitter`: the orchestrator (this conversation) adopts it as a standing mode for genuinely unplanned situations — a tool failure, a dead end, an ambiguity this skill never anticipated. It does not gate anything this skill explicitly defines: `human_review`'s named checkpoints are planned, not the kind of thing not-your-babysitter's stops are for. The two never compete for the same decision.

### State ownership

This conversation (the orchestrator) is the **only** writer of `progress.md` — no subagent ever writes it. The orchestrator is the only thing that ever decides to pause, resume, or advance `progress.md`.

Every dispatch this skill makes (Steps 3, 6a, 6b, 7, 9, 12, and Step 14's conflict-resolution dispatch) follows the `subagent-dispatch` skill's contract in full — its own return-shape field (`status`: `ok`/`blocked`/`question`, the artifacts produced, a `question`/`blocker` field) is this skill's return-shape convention, so state it that way rather than restating it per step. Two things to get right at every one of those sites: the **completion condition** is a concrete artifact each step already produces (a file written, a PR number returned, `mergeable: true` confirmed) — never "when the subagent decides it's done" — and **delegation depth** defaults to no further dispatch, except where a step's own sub-skill already fans out independently by design (`tlc-spec-driven` Execute's per-task subagents) — say so explicitly rather than leaving it to be discovered later. `code-review` (Step 11) is invoked, not dispatched, and dispatches its own review and fix workers under its own rules — never add a wrapper around it. The observability prefix/scale-estimate field is informational only, per that contract — never a reason for a dispatched step to stop short of its completion condition.

Write and update `progress.md` with `scripts/progress.mjs` — see the script's own usage header for exact invocation — rather than hand-editing it with `Edit`: it bumps `last_completed_step`, writes that step's `Step Log` line, and applies any `Run State` field updates in one call, and re-running the same `--step` overwrites that step's own line instead of duplicating it. Reserve `Edit`/`Write` on this file for a shape the script doesn't cover.

When handing work to a subagent, pass resolved metadata and file **paths** (branch name, feature folder path, "read `spec.md` at this path") — never inline a file's bulk content into this conversation just to relay it. Never `Read` a file for the sole purpose of pasting its contents into an `Agent` prompt: that pays for the content twice, once on the way in and again in every cached turn afterward. Each subagent does its own targeted reads inside its own isolated context; the orchestrator stays small by construction, not by discipline alone.

This binds every step, including Step 11, which runs `code-review`. If a sub-skill's mechanics call for reading bulk file content, editing source files, or looping over a list of items one tool call at a time, that work belongs in a dispatched subagent — not here. This conversation's own tool calls are limited to git/gh state, `progress.md`, dispatching, and the checkpoints.

### Worktree

- The worktree tools are **deferred**. Load them in a single `ToolSearch` call before anything else in Step 1 — `select:EnterWorktree,ExitWorktree,Monitor` — not one call per tool as each is first needed. All three are used by a normal run (Step 1 enters, the cleanup sweep exits, Step 14's `UNKNOWN` mergeability wait uses `Monitor`), and every extra `ToolSearch` is a full round-trip that re-sends the whole conversation.
- Ensure `worktree.baseRef` is set to `head` (check `.claude/settings.json`/`~/.claude/settings.json`; if unset, this is a one-time setup gap — stop and tell the user to set it via the `update-config` skill before continuing, rather than guessing a different mechanism).
- `git checkout <base_branch>` first (so "current HEAD" is the branch actually requested), then `EnterWorktree({name: "<task_id>-<slug>"})` — the **native** tool, not raw `git worktree add`. It lands at `.claude/worktrees/<task_id>-<slug>`.
- Immediately after, `git branch -m feature/<task_id>_<description>` inside the new worktree — guarantees the exact naming convention regardless of what `EnterWorktree` itself named the branch.
- If `EnterWorktree` fails for any reason (a symlinked `.claude`, or anything else): stop and report the failure plainly. Do not fall back to raw `git worktree add` — a failure here means something about this repo isn't compatible with the native tool, and that's worth surfacing, not silently working around.
- A branch-name collision (the target branch already exists locally or on the remote) is a not-your-babysitter-style stop regardless of `human_review` — report it and halt; never auto-suffix or guess a resolution.
- Every Bash call for the rest of this run is isolation-guarded inside the worktree. Use absolute paths rooted at `worktree_path` (recorded in `progress.md`) — never a relative `cd`, and never `cd ..` — and keep each call single-purpose: the guard refuses `&&` chains, `$(...)` substitution, heredocs, and redirects combined with `git`/`gh`, even when every target was already inside the worktree. When real shell logic is needed, write a script file into the worktree and invoke it with one plain command. Do not retry a refused command in the same shape — restructure on the first refusal. Treat a DesignSync authorization error (`Run /design-login`) the same way: terminal for that step, not a retry target — it's exactly what Step 13 hands back to the user, not something this run can resolve itself.
- After Step 14 (PR marked ready), the worktree **stays** — it is not removed at the end of a successful run. Cleanup is signal-driven only: at the start of any later invocation, check every tracked spec with a `progress.md` marked complete and a worktree still present — for each, `gh pr view <PR> --json state`; if `MERGED` or `CLOSED`, remove that worktree (`ExitWorktree` if it's the current one, or a direct worktree removal for another tracked spec's) before doing anything else this run. Sweep opportunistically across **all** tracked specs found this way, not just the one this invocation is about — a PR merged via the GitHub UI, never re-triggering build-feature itself, would otherwise leave its worktree on disk forever.

### Architecture context in the worktree

`architecture-evaluate`'s output (`docs/codebase/`) is frequently untracked or gitignored, and a fresh `EnterWorktree` checkout carries neither untracked nor ignored files — so the worktree looks like a project with no context docs even when the repo has a current, complete set. Unhandled, that misfires at both ends of the run: Step 3's gate reads the absence as "this project has no context docs" and escalates to a Full brownfield scan inside the live feature worktree, and Step 12's output then dies with the worktree, because the path it wrote to is ignored and never committed.

Sync it explicitly, in both directions:

- **In — Step 1, immediately after the worktree exists.** Check whether the path is tracked (`git ls-files --error-unmatch docs/codebase`). Tracked → nothing to do; the worktree already has it and Step 12 commits it normally. Untracked or ignored → copy it in from the repo's **main working tree** (the first entry of `git worktree list` — never a sibling feature worktree, which may hold another run's stale copy). Record in `progress.md` that the copy happened, and from where.
- **Out — immediately after Step 12, not at Step 14**, so an early stop still lands the docs. Only when the copy-in actually happened. Before writing back, confirm the source hasn't changed since Step 1; if it has, another session updated it mid-run — do not overwrite. Report both paths and leave the worktree's version in place for the user to reconcile.
- If neither the worktree nor the main working tree has `docs/codebase/` at all, the project genuinely has none. Step 3's gate decides what to do about that.

When the repo tracks `docs/codebase/` in git, none of this runs and none of it is needed — that is the better arrangement wherever the user controls the repo, since it makes the docs versioned, reviewable, and carried by every worktree for free. Say so once in the final report when a run had to fall back to copying.

### Subagent models

Every `Agent` dispatch this skill makes takes its model from the `subagent-dispatch` skill's model matrix — load it before the first dispatch; that table is the authority, and the model named in each step below restates it for readability, never overrides it. Set `model` explicitly on every dispatch (never let a subagent inherit this conversation's model), per that skill's own rules for how.

The model a step runs on **never depends on `human_review`**. That parameter decides where this skill pauses, not how capable the work is.

### Waiting on dispatched subagents

Every step below that spawns a subagent directly via the `Agent` tool — Steps 3, 6a, 6b, 7, 9, 12, and Step 14's conflict-resolution dispatch — waits for it the same way: **load the `subagent-dispatch` skill's wait protocol before the first dispatch, not once the first wait has already started** — improvised waiting is this skill's largest avoidable cost, and the protocol's rules are not guessable from first principles. This applies whether the step dispatches one subagent or several; the default single-subagent case is exactly what the protocol already covers, not a special case of it. Step 3 is the one exception in *timing*, not mechanism: it's dispatched at the start of Step 3 but not collected until just before Step 6a starts, once Step 4's grilling session has run its course — the protocol still governs how that eventual wait happens.

Step 11 is the exception to delegating through a wrapper subagent: it invokes `code-review` via the `Skill` tool in this conversation, because `code-review`'s checkpoint must be able to end this turn and a subagent cannot pause for the user. That is safe here only because `code-review`, run from a root conversation, keeps nothing but compact results in it — its review worker and fix worker do the heavy work in their own contexts. The rule this replaces existed because the old standalone fix skill ran its whole fixing pass in whatever context invoked it: invoked from the orchestrator, that cost 39–60% of the orchestrator's entire token cost across four real runs — in one case 83M tokens to move 80 comments onto a PR. Never invoke via `Skill` here a skill that does its heavy work inline.

Step 4 (grilling) is not a subagent dispatch and the wait protocol does not apply to it: it runs directly in this conversation via the `Skill` tool, and each round ends this turn waiting for the user's actual reply — the same mechanism as the `spec`/`design` checkpoints in Steps 6a/6b, not a background task with a stall ceiling.

### gh account resolution

`gh` account resolution: mandatory, once at the start of every invocation (fresh or resumed) — this skill pushes branches, opens/updates PRs, and calls several `gh`-using subagents across a long run, exactly the situation that resolution exists for.

### PR

- Opened as a draft once the branch has its first real commit — right after Step 8 pushes the spec/design/tasks artifacts — with a body sourced from what's already on disk at that point (`spec.md`'s problem statement, plus `tasks.md`'s checklist). GitHub refuses `gh pr create` against a branch with zero commits ahead of `base_branch` (`No commits between <base> and <head>`), which is why this doesn't happen any earlier and why it's never an empty placeholder commit seeded just to open the PR sooner. Rewritten in full (Step 10) once tlc-spec-driven's Execute phase completes, sourced from `spec.md`/`tasks.md`/`commits.md`/`validation.md` — invent nothing new.
- Never merged, by this skill, under any circumstance.
- Marked ready (`gh pr ready <PR>`) only as the very last successful step (Step 14) — after every other step, including any `human_review` pause, has actually completed.
- Never marked ready while GitHub reports it unmergeable. "Ready for review" is a claim about the PR's state, and a PR nobody can merge doesn't meet it — asserting readiness without checking is a false completion, which a real run produced: the PR was announced ready and delivered, and the user came back hours later asking for the merge conflicts to be fixed. Step 14 checks, and resolves, before it marks.

### design-sync

Auto-detected only, no override parameter: presence of `.design-sync/config.json` at the worktree root makes Step 13 emit its handoff; its absence skips it silently (not a failure, not something to report as missing).

**This skill never runs design-sync — it cannot.** The skill is marked `disable-model-invocation`, so the `Skill` tool refuses it no matter who asks; `DesignSync` is an interactively-authenticated claude.ai tool that doesn't propagate into dispatched subagents either. Both routes are closed, and both have been tried: two real runs made the inline `Skill` call and got back `Skill design-sync cannot be used with Skill tool due to disable-model-invocation`, and an earlier one burned a subagent searching `ToolSearch` four different ways for a tool it could never see. The only thing that starts design-sync is the user typing `/design-sync` as a literal command.

So Step 13 hands it back, and **does not gate delivery**: design-sync pushes to an external design project and touches neither the PR's content nor its mergeability, so Step 14 marks the PR ready without waiting for it. Running it afterwards is required, not optional — Step 13's only job is to make sure the user leaves the run knowing that. Never reconstruct the flow by hand from `.design-sync/NOTES.md` or the config: the pipeline scripts live inside the skill, and improvising them risks pushing malformed content to a live external design project.

### Credentials

Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.

## Before Starting

- All three required parameters present. Missing any → ask; never guess a value or derive `task_id` from anything else.
- `gh auth status` must succeed (after account resolution above), or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- `git status --porcelain` must be clean in the current checkout before `EnterWorktree` runs. Dirty → stop and report exactly what's uncommitted; never stash, commit, or discard it yourself.
- `base_branch` must actually exist (local or fetchable from remote). Missing → stop and report; do not substitute a different branch.

## Step 0: Resume or Start Fresh

Before anything else, look for `.specs/features/<task_id>-<slug>/progress.md` (derive `<slug>` from `description` the same way Step 5 would).

- **Not found** → fresh run, continue to Step 1.
- **Found, status `complete`, PR merged or closed** → this is the cleanup case described under Worktree above; report and stop, nothing else to do for this spec.
- **Found, status `complete`, PR still open** → this is a later re-invocation for fresh review comments, not a new delivery. Invoke `code-review`'s fix-existing-findings entry ("fix the review comments on PR #<N>") via the `Skill` tool, from this conversation, for the tracked PR, passing the recorded `worktree_path` and feature folder — its fix worker runs inside that existing worktree (already on the PR branch, so no new one is needed — see `references/progress-schema.md` for exactly what `progress.md` records to make this possible without re-deriving anything). Once it returns, run Step 12 (architecture-evaluate) if it reports any commits pushed, then report and stop. Do not re-mark the PR ready (it already is) and do not touch Steps 1–11 or 13–14.
- **Found, status `in-progress`** → resume at the first step `progress.md` marks incomplete, using the state it recorded (worktree path, branch name, PR number, resolved gh login, feature folder path, which of `spec`/`design`/`code-review` already completed or is mid-pause). Grilling (Step 4) has no partial-round state to recover — nothing is logged for it until the session concludes — so an interruption mid-grilling simply resumes by restarting Step 4 from round 1; Step 3's quick-gate result, if it already reported back before the interruption, is not redispatched. See `references/progress-schema.md` for the exact field set.

## Step 1: Worktree and Branch

Per the Worktree guardrail above. Record `worktree_path` and the exact branch name in `progress.md` once this succeeds.

Then run the context sync-in described under Architecture context in the worktree — before Step 3's gate, so it decides against the docs this project actually has.

## Step 2: Push

`git push -u origin feature/<task_id>_<description>`.

## Step 3: Architecture-Evaluate Gate (Background, decision only)

Dispatch a Haiku subagent to **decide only**: read `architecture-evaluate`'s own "Keeping Docs Up to Date" trigger table plus the recent commit history on `base_branch`, and return `full`, `incremental`, or `none` with its reasoning. It does not invoke `architecture-evaluate`, write any file, or touch the worktree.

Judge the trigger against what the worktree actually holds after Step 1's context sync — by this point an absent `docs/codebase/` means the project genuinely has none, not that a fresh worktree failed to carry them.

- `none` or `incremental` → record it. Step 12's Incremental run is the sync; nothing else happens here.
- `full` → the project has no context docs at all. That is a brownfield mapping job, not a gate: report it and continue the feature without it. Never run Full mode inside a feature delivery — it takes tens of minutes, writes into the live worktree while later steps are working in it, and Step 12 re-scans the same files afterward regardless.

Dispatch it and move straight to Step 4 without waiting — it only touches `docs/codebase/`, never git the feature branch is on, and nothing until Step 6a depends on its result. Collect that result (per the Agent Wait Protocol) once Step 4 concludes, before Step 6a starts.

## Step 4: Grilling (Interactive — this conversation, not a subagent)

Grilling is a live, multi-round conversation: each round ends by waiting for the user's actual answers before the next one starts (see the `grilling` skill — rounds, frontier, "wait for the user's answers"). A subagent can't do that — dispatched via the `Agent` tool it runs once, in the background, to completion, and reports a single result on its own schedule; it has no way to pause mid-run for a reply from the actual user. So run `grilling` directly, via the `Skill` tool, in this conversation, using `task_id` and `description` as the seed.

Always attempted regardless of `human_review` — grilling is a scoping aid, not a review gate, and generalizes the "if there are no questions, skip it" rule to "if there's no one to usefully ask, skip it": if the frontier is empty on round 1, it exits immediately rather than being pre-judged as unnecessary. Where the `grilling` skill itself calls for dispatching a sub-agent to find an environmental fact, follow its own guidance — that's internal to how grilling resolves one question, not a substitute for the live conversation with the user.

Each round after the first ends this turn, waiting for the user's next message before continuing — the same mechanism as the `spec`/`design` checkpoints in Steps 6a/6b, never invented or advanced speculatively. The moment the frontier is empty (or empty already on round 1), grilling is done — continue straight to Step 5 in that same turn, no separate pause beyond what its own rounds already required. Keep the session's notes; they become `grilling-session.md`'s content in Step 5.

## Step 5: Pre-Create the Feature Folder

Derive `<slug>` (kebab-case, 2–4 words) from `description`. Create `.specs/features/<task_id>-<slug>/` and write `grilling-session.md` into it from Step 4's grilling notes — before Specify runs, so Specify's own folder-creation logic (if any) finds it already there rather than colliding with it.

## Step 6a: Specify (Sonnet)

First, collect Step 3's quick-gate result (per the Agent Wait Protocol) if it hasn't already reported back — a multi-round grilling session almost always outlasts it, so this is typically an instant check, not a real wait. Then spawn a Sonnet subagent to run tlc-spec-driven's Specify phase against the pre-created feature folder path. Writes `spec.md`.

**Checkpoint — `spec`:** if `human_review=yes` and `spec` is not in `human_review_exclude`, show `spec.md` to the user and end this turn, waiting for their next message before continuing to 6b — never invent an approval or continue speculatively. Otherwise continue immediately. (Every other checkpoint in this skill — `design` in 7b, `code-review` in Step 11 — pauses the same way.)

## Step 6b: Design (Sonnet)

Spawn a second, separate Sonnet subagent — reads `spec.md` fresh from disk (no shared conversation state with 6a's subagent; the file is the handoff). Runs tlc-spec-driven's Design phase. Respect its native auto-sizing: for a Small/Medium-scoped feature, Design may legitimately produce nothing — record that in `progress.md` rather than treating it as a failure.

**Checkpoint — `design`:** only meaningful if Design actually ran. If `human_review=yes`, `design` not excluded, and `design.md` was produced, show it and wait for approval before continuing. Otherwise continue immediately.

## Step 7: Tasks (Haiku)

Spawn a Haiku subagent — reads `spec.md` and `design.md` (if present) fresh from disk. Runs tlc-spec-driven's Tasks phase. Writes `tasks.md`, respecting the same auto-sizing as Design.

## Step 8: Commit and Push Spec Artifacts, Open the Draft PR

Commit whatever Steps 5–7 produced (`grilling-session.md`, `spec.md`, `design.md` if present, `tasks.md`) as one Conventional Commits commit (e.g. `docs(spec): add PROJ-42 feature spec`), push to the feature branch.

This is the branch's first real commit, so open the draft PR now: `gh pr create --draft --base <target_branch> --head feature/<task_id>_<description> --title "[<task_id>] <description>" --body "<sourced from spec.md's problem statement and tasks.md's checklist>"`. Fall back to the GitHub MCP tool, then `gh api graphql`'s `createPullRequest` mutation with `draft: true`, only if `gh` itself is unavailable. Record the returned PR number in `progress.md`.

## Step 9: Execute (Sonnet)

Spawn a Sonnet subagent to run tlc-spec-driven's Execute phase for every task in `tasks.md`. It owns its own gate checks, atomic Conventional-Commits commits, and the end-of-feature Verifier — do not add parallel logic for any of that here. If Execute's fix-loop can't converge: stop, report, do not proceed to Step 10.

## Step 10: Push Execute's Commits and Rewrite the PR Description

`git push` — Step 9's commits are local-only until this point; push them now so the PR (and `code-review`, next) reflect what Execute actually did, not a stale remote branch.

Then rewrite the PR description, sourced from existing artifacts, invent nothing new: **Problem** ← `spec.md`; **What was done** ← `tasks.md`'s completed checklist and `commits.md`; **Test results** ← `validation.md` (the Verifier's report). `gh pr edit <PR> --body "..."`.

## Step 11: code-review (review → checkpoint → fix)

Invoke `code-review` via the `Skill` tool **directly in this conversation** — not through a wrapper subagent — for this PR: pass the PR number, owner/repo, the run's resolved gh login, the feature folder path (`.specs/features/<task_id>-<slug>/`, so its fix worker writes `fix-code-review.md` there), the worktree path, and `human_review`: `true` when this skill's `human_review=yes` and `code-review` is not in `human_review_exclude`, otherwise `false`. `gh auth status` must succeed here even if earlier steps fell back to GitHub MCP — `code-review` writes to GitHub only through `gh`. This conversation is `code-review`'s root: `code-review` dispatches its own Sonnet review worker and fix worker and keeps only their compact results here, so the heavy work never enters this context. It must run here rather than in a subagent because a subagent cannot pause for the user, and `code-review`'s checkpoint ends this turn.

`code-review` runs its whole chain: the review worker posts a pending review; at its checkpoint, `human_review: true` shows the summary and ends this turn (the user edits, deletes, or submits comments on GitHub, then replies), `false` continues; it submits the review as `COMMENT`; then a fresh fix worker — dispatched without worktree isolation, since this run's worktree already has the PR branch checked out — fixes what remains, runs the validation gate, pushes, and replies to and resolves every thread. Never post, submit, fix, or reply from this conversation yourself, and never re-implement any of that here.

**Before ending a turn at `code-review`'s checkpoint**, record `code_review: pending` in `progress.md` (`scripts/progress.mjs --step 11 --label "code-review, paused at checkpoint" --detail "review posted on PR #<N>" --set code_review=pending`), so an interruption resumes correctly — `pr_number` is already in Run State. **Resuming** with `code_review: pending` means the review is already posted: show the PR URL and wait for the user's reply again (never auto-approve because time passed), then invoke `code-review`'s continue-after-checkpoint entry ("continue the code review on PR #<N>") — it submits the review and runs the fix stage, and never re-runs the review.

When `code-review` returns, record Step 11 done with `code_review: approved` (or `n/a` when it didn't pause) and its final report's counts: findings, fixed / rejected / answered / blocked, and commits pushed. If it reports it could not publish or deliver, invoke its continue-after-checkpoint entry once more for the same PR (its scripts skip anything already posted or replied); if that is blocked too, stop and report its raw result. Never take the posting or delivery loop over yourself.

## Step 12: architecture-evaluate (Incremental, Sonnet)

Spawn a Sonnet subagent to run `architecture-evaluate` in Incremental mode against everything pushed to this branch this run — this is a code-changes-want-docs-reflected sync, not a brownfield re-scan. **Incremental always, never Full**, regardless of how much this run changed or how stale the docs look; Step 3's gate is the only place in this skill that may conclude Full is warranted, and its answer there is to report it, not to run it. If Incremental genuinely looks insufficient, say so in the final report and let the user trigger `architecture-evaluate` Full separately.

Classify touched `docs/codebase/` files as new vs. existing (`git status --porcelain -- docs/codebase/`): if every touched file is new, leave them uncommitted for manual review; otherwise commit as one Conventional Commits commit and push. If the path is untracked or ignored, nothing here can commit it — run the context sync-out described under Architecture context in the worktree instead, immediately, so the update survives this worktree.

## Step 13: design-sync Handoff (Conditional, no work here)

Only if `.design-sync/config.json` exists at the worktree root — otherwise skip silently and go to Step 14.

Nothing runs in this step, and nothing can (see the design-sync guardrail). Record `design_sync: pending-user-action` in `progress.md`, then carry the handoff into the final report as a **required follow-up, not a suggestion** — the user runs it themselves once this run has finished. Do not attempt the `Skill` tool, and do not spend a `ToolSearch` checking whether `DesignSync` is reachable: its reachability was never what blocked this.

Put the handoff last in the final report, as its closing instruction, in two steps:

1. **`/compact`** first. design-sync reads components, previews, and bundle listings, and by this point this conversation is carrying the entire build. On a real run it executed at ~250k average context and took 65% of the conversation's total turns; compacting immediately before it cut the same work to roughly half the tokens, because design-sync re-derives everything it needs from disk and loses nothing to the summary.
2. **`/design-sync`** — typed literally, as the user's own next message.

## Step 14: Confirm It Merges, Then Mark Ready

First, ask GitHub whether the PR can actually merge: `gh pr view <PR> --json mergeable,mergeStateStatus`.

- **`MERGEABLE`/`CLEAN`** → proceed.
- **`UNKNOWN`** → GitHub computes mergeability asynchronously and often hasn't finished right after a push. Wait once — a single timed wait, per the `subagent-dispatch` skill's clock rule, never a poll loop — and re-query. Still `UNKNOWN` → proceed, and say in the final report that the check was inconclusive rather than implying it passed.
- **`CONFLICTING`** → dispatch a Sonnet subagent to resolve it: merge `origin/<target_branch>` into the feature branch, resolve every conflict, verify per Test Execution Scope — merges scope by what they bring in, never by conflict size — commit the merge, push — state the verification tier explicitly in the subagent's prompt, per that rule's own delegation requirement. It returns the conflicted file list, how each was resolved, and which verification tier it ran. Re-query afterwards, then proceed. Conflict resolution reads and edits files, so it belongs in a subagent, not here — this conversation only detects, dispatches, and re-checks. If a conflict is genuinely ambiguous — both sides implement the same behavior differently and either choice changes what ships — the subagent leaves it unresolved and says so: stop there, report exactly which files conflict and why, and leave the PR as a draft. Never guess at a merge resolution to reach a green state.

Record the outcome in `progress.md` (`merge_check`), so a resumed run doesn't repeat it blindly.

Then `gh pr ready <PR>`. Write `progress.md` status `complete`. This is the true end of a fresh delivery run — report the PR URL and a summary of what each step did, and stop. Note that mergeability was true at that moment, not forever: the target branch keeps moving, and a later conflict isn't a failure of this run.

## Resuming an In-Progress Run

Re-invoking this skill against a `task_id`/feature folder whose `progress.md` shows `in-progress` skips every step already marked done and resumes at the first incomplete one, using the recorded worktree path, branch name, PR number, and gh login rather than re-deriving them. A step that was mid-pause for `human_review` (e.g. `spec` approval pending) resumes by re-showing the same artifact and waiting again — it does not silently auto-approve because time has passed.

See `references/progress-schema.md` for the exact field set `progress.md` tracks and how each step reads/writes it.

## Examples

### Example 1: Fresh delivery run, human_review default

User: `/build-feature base_branch=main task_id=PROJ-42 description="add rate limiting to orders API"`

1. Step 0: no `progress.md` for `PROJ-42-add-rate-limiting` → fresh run
2. Step 1: worktree created at `.claude/worktrees/PROJ-42-add-rate-limiting`, branch renamed to `feature/PROJ-42_add-rate-limiting-to-orders-api`
3. Step 2: pushed (empty branch, no PR yet — GitHub won't accept one until there's a commit ahead of `main`)
4. Step 3: gate subagent dispatched in the background, returns `none` — nothing to sync beyond Step 12
5. Step 4: grilling runs live in this conversation — as many rounds as the design tree needs (say, 3), the user answering each round in turn, until the frontier is empty; notes captured, continues straight to Step 5
6. Step 5: `.specs/features/PROJ-42-add-rate-limiting/grilling-session.md` written
7. Step 6a: quick-gate result collected (already returned); Specify writes `spec.md` → `human_review=yes` (default), `spec` not excluded → shown to user, approved
8. Step 6b: Design writes `design.md` (feature sized Large) → shown, approved
9. Step 7: Tasks writes `tasks.md`
10. Step 8: spec artifacts committed and pushed — the branch's first real commit, so the draft PR #512 opens now, body sourced from `spec.md`/`tasks.md`
11. Step 9: Execute runs all tasks, Verifier passes
12. Step 10: Execute's commits pushed; PR #512's description rewritten with problem/what-was-done/test-results
13. Step 11: `code-review` invoked via `Skill` in this conversation with `human_review: true` → its review worker posts 9 findings as a pending review on PR #512 → checkpoint: `code_review: pending` recorded, summary shown, turn ends → user deletes one wrong finding on GitHub and replies → `code-review` submits the review, its fix worker fixes 5 of the 8 remaining, replies to and resolves them, leaves 1 answered-only and 2 blocked with reasons, pushes → returns those counts and the SHAs
14. Step 12: `architecture-evaluate` Incremental mode updates 2 already-tracked files → committed and pushed
15. Step 13: no `.design-sync/config.json` at the worktree root → skipped silently
16. Step 14: `gh pr view 512 --json mergeable,mergeStateStatus` → `MERGEABLE`/`CLEAN` → `gh pr ready 512` → `progress.md` marked complete → report: "PR #512 marked ready for review: <url>. 8 findings after your review, 5 fixed. Mergeable against `main` as of now. Worktree left in place."

### Example 2: Fully autonomous run

User: `/build-feature base_branch=main task_id=PROJ-43 description="cache invalidation for job listings" human_review=no`

Same steps, but nothing pauses — Specify and Design proceed immediately without showing anything to the user first, and Step 11 passes `human_review: false` to `code-review`, which posts its review, submits it as `COMMENT`, and runs its fix stage straight away.

### Example 3: Resuming after an interruption

User: `/build-feature task_id=PROJ-42` (session was interrupted mid-Execute)

1. Step 0: `progress.md` for `PROJ-42-add-rate-limiting-to-orders-api` shows `in-progress`, last completed step 8, worktree/branch/PR recorded
2. Resume directly at Step 9 (Execute) — Steps 1–8 are not re-run

### Example 4: Re-invocation after delivery, PR still open

User: `/build-feature task_id=PROJ-42` (weeks later; a reviewer left new comments on PR #512, which is still open)

1. Step 0: `progress.md` shows `complete`, `gh pr view 512 --json state` → `OPEN`
2. `code-review`'s fix-existing-findings entry invoked for PR #512 — its fix worker runs in the still-present worktree, fixes 2 new comments, pushes
3. Step 12 runs once (commits were pushed) → no doc changes needed
4. Report: "2 new review comments fixed and pushed to PR #512. Still open, not re-marked (already ready)."

### Example 5: Re-invocation after the PR merged

User: `/build-feature task_id=PROJ-42` (PR #512 was merged last week)

1. Step 0: `progress.md` shows `complete`, `gh pr view 512 --json state` → `MERGED`
2. Worktree cleanup fires: `PROJ-42-add-rate-limiting-to-orders-api`'s worktree removed. While sweeping, also finds `PROJ-40-...`'s worktree (a different, unrelated completed spec) whose PR is also merged — removes that one too.
3. Report: "PR #512 is merged — nothing left to do. Cleaned up 2 stale worktrees (PROJ-42, PROJ-40)."

