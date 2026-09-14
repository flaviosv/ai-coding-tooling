---
name: build-feature
description: Delivers a brand-new feature end-to-end with no planning already done — creates a worktree and branch from base_branch, opens a draft PR against target_branch, optionally grills the user on scope, runs tlc-spec-driven's full Specify→Design→Tasks→Execute cycle, updates the PR description, runs code-review (review, optional checkpoint, and fixes), syncs architecture docs, then confirms the PR actually merges before marking it ready — delegating the heavy steps to isolated subagents while the orchestrator runs git/gh plumbing, writes grilling-session.md, and copies docs/codebase, with grilling and code-review running live in this conversation (code-review keeps its own work in its own workers) — and, when the project uses Claude Design, closes by handing design-sync back to the user as a required follow-up it cannot run itself, resumable from any interrupted step via progress.md, self-routing a later re-invocation straight to fresh PR comments once delivered. Requires task_id, plus base_branch and description on a fresh run (target_branch defaults to base_branch); human_review (default yes) gates spec/design/code-review pauses. Use when the user says "build feature", "start a new feature end to end", "deliver this feature autonomously", or invokes /build-feature. Do NOT use to fix PR comments outside this flow (use code-review's fix-existing-findings entry directly).
metadata:
  author: Flavio Studart
  version: "3.0.0"
---

# Build Feature

Takes a feature from nothing but a task ID and a description to a PR marked ready for review, with no human interaction required beyond what `human_review` asks for. Every heavy step — Specify, Design, Tasks, Execute, docs sync, and conflict resolution — is delegated to an isolated subagent that reports back a structured result, so this conversation's own context stays small enough to survive a run with a dozen-plus steps. The orchestrator itself runs git/gh plumbing, writes `progress.md` and `grilling-session.md`, and copies `docs/codebase/`. Two steps run live in this conversation: grilling (Step 3), a multi-round conversation with the user that only this conversation can hold, and `code-review` (Step 10), whose checkpoint must be able to end this turn — it still does its heavy work in its own workers.

## Parameters

Required, never inferred — ask if missing, do not guess:

- `task_id` — used in the branch name, PR title, and feature folder name. Always required; a re-invocation of an existing run needs nothing else, since Step 0 reads every other parameter from `progress.md`.
- `base_branch` — branch the feature branch is cut from. Required on a fresh run.
- `description` — short text. Required on a fresh run. Two names derive from it: `<desc-kebab>`, the kebab-case of the full description, used in the branch name `feature/<task_id>_<desc-kebab>`; and `<slug>` (kebab-case, 2–4 words), chosen once at Step 1 for the worktree and feature folder name `<task_id>-<slug>`. `<slug>` is never re-derived: Step 0 finds an existing run by `<task_id>-*`.

Optional:

- `target_branch` — the PR's merge target. Defaults to `base_branch` when omitted (a superset of a same-branch delivery, not a different default).
- `human_review` — `yes` (default) or `no`. `yes` pauses after Specify, after Design (when Design runs at all), and at `code-review`'s checkpoint, after its findings are posted to GitHub as a pending review and before anything is fixed (see Step 10), waiting for approval before continuing each time. `no` runs the whole pipeline without pausing anywhere this parameter controls. It decides where the run pauses, never which model a step runs on.
- `human_review_exclude` — comma-separated subset of `spec`, `design`, `code-review` to skip pausing on even when `human_review=yes` (e.g. `human_review_exclude=code-review`). Ignored when `human_review=no`.

## Guardrails

### Composability — do not reimplement what other skills own

- tlc-spec-driven owns Specify/Design/Tasks/Execute's own internal mechanics (auto-sizing, atomic commits, gate checks, the Verifier). Invoke it; don't duplicate its logic.
- `code-review` owns reviewing, its checkpoint, submitting the review, fixing, and replying — Step 10 invokes it once and passes `human_review` through (`false` when `code-review` is in `human_review_exclude`); this skill never posts, submits, fixes, or replies itself.
- `not-your-babysitter`: the orchestrator (this conversation) adopts it as a standing mode for genuinely unplanned situations — a tool failure, a dead end, an ambiguity this skill never anticipated. It does not gate anything this skill explicitly defines: `human_review`'s named checkpoints are planned, not the kind of thing not-your-babysitter's stops are for. The two never compete for the same decision.

### State ownership

This conversation (the orchestrator) is the **only** writer of `progress.md` — no subagent ever writes it. The orchestrator is the only thing that ever decides to pause, resume, or advance `progress.md`.

Every dispatch this skill makes (Steps 5a, 5b, 6, 8, 11, and Step 13's conflict-resolution dispatch) returns `status` (`ok`/`blocked`/`question`), the artifacts produced, and a `question`/`blocker` field. Its **completion condition** is a concrete artifact the step already produces (a file written, a PR number returned, `mergeable` confirmed) — never "when the subagent decides it's done" — and its **delegation depth** is no further dispatch, except Step 8, where tlc-spec-driven Execute runs its own per-batch workers and the Verifier — say so in that prompt. `code-review` (Step 10) is invoked, not dispatched, and dispatches its own review and fix workers under its own rules — never add a wrapper around it.

A `question` status from a tlc-spec-driven phase (Steps 5a, 5b, 6, 8): answer it from `grilling-session.md` when that already settles it, and re-dispatch with the answer; otherwise show the question to the user, end the turn, and re-dispatch with their answer. With `human_review=no`, don't pause: re-dispatch telling the subagent to record its best answer as an assumption in `spec.md`. Step 11's questions go into the final report instead (see Step 11).

Write and update `progress.md` with `scripts/progress.mjs` — see the script's own usage header for exact invocation — rather than hand-editing it with `Edit`: it bumps `last_completed_step`, writes that step's `Step Log` line, and applies any `Run State` field updates in one call, and re-running the same `--step` overwrites that step's own line instead of duplicating it. Reserve `Edit`/`Write` on this file for a shape the script doesn't cover.

When handing work to a subagent, pass resolved metadata and file **paths** (branch name, feature folder path, "read `spec.md` at this path") — never inline a file's bulk content into this conversation just to relay it. Never `Read` a file for the sole purpose of pasting its contents into an `Agent` prompt: that pays for the content twice, once on the way in and again in every cached turn afterward. Each subagent does its own targeted reads inside its own isolated context; the orchestrator stays small by construction, not by discipline alone.

This binds every step, including Step 10, which runs `code-review`. If a sub-skill's mechanics call for reading bulk file content, editing source files, or looping over a list of items one tool call at a time, that work belongs in a dispatched subagent — not here. This conversation's own tool calls are limited to git/gh plumbing, `progress.md`, writing `grilling-session.md`, copying `docs/codebase/`, dispatching, and the checkpoints.

### Worktree

- The worktree tools are **deferred**. Load them in a single `ToolSearch` call before anything else in Step 1 — `select:EnterWorktree,ExitWorktree,Monitor` — not one call per tool as each is first needed (Step 1 enters, `ExitWorktree` leaves a worktree entered in this same session, Step 13's `UNKNOWN` mergeability wait uses `Monitor`); every extra `ToolSearch` is a full round-trip that re-sends the whole conversation.
- Ensure `worktree.baseRef` is set to `head` (check `.claude/settings.json`/`~/.claude/settings.json`; if unset, this is a one-time setup gap — stop and tell the user to set it via the `update-config` skill before continuing, rather than guessing a different mechanism).
- `git checkout <base_branch>` first (so "current HEAD" is the branch actually requested), then `EnterWorktree({name: "<task_id>-<slug>"})` — the **native** tool, not raw `git worktree add`. It lands at `.claude/worktrees/<task_id>-<slug>`.
- Immediately after, `git branch -m feature/<task_id>_<desc-kebab>` inside the new worktree — guarantees the exact naming convention regardless of what `EnterWorktree` itself named the branch.
- If `EnterWorktree` fails for any reason (a symlinked `.claude`, or anything else): stop and report the failure plainly. Do not fall back to raw `git worktree add` — a failure here means something about this repo isn't compatible with the native tool, and that's worth surfacing, not silently working around.
- A branch-name collision (the target branch already exists locally or on the remote) is a not-your-babysitter-style stop regardless of `human_review` — report it and halt; never auto-suffix or guess a resolution.
- Every Bash call for the rest of this run is isolation-guarded inside the worktree. Use absolute paths rooted at `worktree_path` (recorded in `progress.md`) — never a relative `cd`, and never `cd ..`. Treat a DesignSync authorization error (`Run /design-login`) as terminal for that step, not a retry target — it's exactly what Step 12 hands back to the user, not something this run can resolve itself.
- After Step 13 (PR marked ready), the worktree **stays** until its PR is merged or closed. Cleanup is signal-driven only: Step 0's cleanup sweep removes it on a later invocation, across **all** tracked specs, not just the one that invocation is about — a PR merged via the GitHub UI, never re-triggering build-feature itself, would otherwise leave its worktree on disk forever.

### Architecture context in the worktree

`architecture-evaluate`'s output (`docs/codebase/`) is frequently untracked or gitignored, and a fresh `EnterWorktree` checkout carries neither untracked nor ignored files — so the worktree looks like a project with no context docs even when the repo has a current, complete set. Unhandled, Step 11's docs sync treats the project as having no context docs, and its output then dies with the worktree, because the path it wrote to is ignored and never committed.

Sync it explicitly, in both directions:

- **In — Step 1, immediately after the worktree exists.** Check whether the path is tracked (`git ls-files --error-unmatch docs/codebase`). Tracked → nothing to do; the worktree already has it and Step 11 commits it normally. Untracked or ignored → copy it in from the repo's **main working tree** (the first entry of `git worktree list` — never a sibling feature worktree, which may hold another run's stale copy). Record in `progress.md` that the copy happened, and from where.
- **Out — immediately after Step 11, not at Step 13**, so an early stop still lands the docs. Only when the copy-in actually happened. Before writing back, confirm the source hasn't changed since Step 1; if it has, another session updated it mid-run — do not overwrite. Report both paths and leave the worktree's version in place for the user to reconcile.
- If neither the worktree nor the main working tree has `docs/codebase/` at all, the project genuinely has none. `architecture-evaluate` decides at Step 11 what to do about that.

When the repo tracks `docs/codebase/` in git, none of this runs and none of it is needed — that is the better arrangement wherever the user controls the repo, since it makes the docs versioned, reviewable, and carried by every worktree for free. Say so once in the final report when a run had to fall back to copying.

### PR

- Opened as a draft once the branch has its first real commit — right after Step 7 pushes the spec artifacts — with a body sourced from what's already on disk at that point: `spec.md`'s problem statement, plus `tasks.md`'s checklist, or, when auto-sizing skipped Tasks, `spec.md`'s acceptance criteria and the branch's commits. GitHub refuses `gh pr create` against a branch with zero commits ahead of `base_branch` (`No commits between <base> and <head>`), which is why this doesn't happen any earlier and why it's never an empty placeholder commit seeded just to open the PR sooner. Rewritten in full (Step 9) once tlc-spec-driven's Execute phase completes, sourced from `spec.md`, `tasks.md` when present, `validation.md`, and the branch's own commits — invent nothing new.
- Never merged, by this skill, under any circumstance.
- Marked ready (`gh pr ready <PR>`) only as the very last successful step (Step 13) — after every other step, including any `human_review` pause, has actually completed.
- Never marked ready while GitHub reports it unmergeable. "Ready for review" is a claim about the PR's state, and a PR nobody can merge doesn't meet it. Step 13 checks, and resolves, before it marks.

### design-sync

Auto-detected only, no override parameter: presence of `.design-sync/config.json` at the worktree root makes Step 12 emit its handoff; its absence skips it silently (not a failure, not something to report as missing).

**This skill never runs design-sync — it cannot.** The skill is marked `disable-model-invocation`, so the `Skill` tool refuses it no matter who asks; `DesignSync` is an interactively-authenticated claude.ai tool that doesn't propagate into dispatched subagents either. The only thing that starts design-sync is the user typing `/design-sync` as a literal command.

So Step 12 hands it back, and **does not gate delivery**: design-sync pushes to an external design project and touches neither the PR's content nor its mergeability, so Step 13 marks the PR ready without waiting for it. Running it afterwards is required, not optional — Step 12's only job is to make sure the user leaves the run knowing that. Never reconstruct the flow by hand from `.design-sync/NOTES.md` or the config: the pipeline scripts live inside the skill, and improvising them risks pushing malformed content to a live external design project.

### Credentials

Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.

## Before Starting

- `task_id` present. Missing → ask; never guess a value or derive it from anything else.
- A fresh run (Step 0 finds no run for `task_id`) also needs `base_branch` and `description`. Missing → ask; never guess. A re-invocation needs only `task_id`.
- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- `git status --porcelain` must be clean in the current checkout before `EnterWorktree` runs. Dirty → stop and report exactly what's uncommitted; never stash, commit, or discard it yourself.
- On a fresh run, `base_branch` must actually exist (local or fetchable from remote). Missing → stop and report; do not substitute a different branch.

## Step 0: Resume or Start Fresh

Before anything else, enumerate every worktree with `git worktree list` (the main checkout included) and look inside each for `.specs/features/*/progress.md`. That one enumeration serves both the cleanup sweep and this run's lookup.

**Cleanup sweep.** For every tracked spec found whose `progress.md` records a `pr_number`, run `gh pr view <pr_number> --json state`. `MERGED` or `CLOSED` → from the main checkout (the first entry of `git worktree list`), remove its `worktree_path`: when `git -C <worktree_path> status --porcelain` lists nothing but that run's own `progress.md` (never committed, so it always blocks a plain removal), run `git worktree remove --force <worktree_path>`; anything else uncommitted → leave the worktree and report it. `ExitWorktree` is only for leaving a worktree entered in this same session.

Then route on this `task_id`'s run, the `.specs/features/<task_id>-*/progress.md` the enumeration found:

- **Not found** → fresh run, continue to Step 1.
- **Found, PR merged or closed** → the sweep already handled it (removed, or left and reported); report and stop, nothing else to do for this spec.
- **Found, status `complete`, PR still open** → this is a later re-invocation for fresh review comments, not a new delivery. Invoke `code-review`'s fix-existing-findings entry ("fix the review comments on PR #<N>") via the `Skill` tool, from this conversation, for the tracked PR, passing the recorded `worktree_path` and the feature folder (the directory holding that `progress.md`) — its fix worker runs inside that existing worktree (already on the PR branch, so no new one is needed — see `references/progress-schema.md` for exactly what `progress.md` records to make this possible without re-deriving anything). Once it returns, run Step 11 (architecture-evaluate) if it reports any commits pushed, then report and stop. Do not re-mark the PR ready (it already is) and do not touch Steps 1–10 or 12–13.
- **Found, status `in-progress`** → resume at the first step `progress.md` marks incomplete, using the state it recorded (worktree path, branch name, PR number, which of `spec`/`design`/`code-review` already completed or is mid-pause). Grilling (Step 3) has no partial-round state to recover — nothing is logged for it until the session concludes — so an interruption mid-grilling simply resumes by restarting Step 3 from round 1. See `references/progress-schema.md` for the exact field set.

## Step 1: Worktree, Branch, and Progress File

Per the Worktree guardrail above. Once the branch is renamed, initialize `<worktree_path>/.specs/features/<task_id>-<slug>/progress.md` with `scripts/progress.mjs <path> --init`, passing every Run State field it takes, with `worktree_path` as an absolute path; `--init` creates the feature folder.

Then run the context sync-in described under Architecture context in the worktree, and log Step 1 with its outcome (setting `context_docs_copied_from` when the copy happened).

## Step 2: Push

`git push -u origin feature/<task_id>_<desc-kebab>`.

## Step 3: Grilling (Interactive — this conversation, not a subagent)

Grilling is a live, multi-round conversation: each round ends by waiting for the user's actual answers before the next one starts (see the `grilling` skill — rounds, frontier, "wait for the user's answers"). A subagent can't do that — dispatched via the `Agent` tool it runs once, in the background, to completion, and reports a single result on its own schedule; it has no way to pause mid-run for a reply from the actual user. So run `grilling` directly, via the `Skill` tool, in this conversation, using `task_id` and `description` as the seed.

Always attempted regardless of `human_review` — grilling is a scoping aid, not a review gate, and generalizes the "if there are no questions, skip it" rule to "if there's no one to usefully ask, skip it": if the frontier is empty on round 1, it exits immediately rather than being pre-judged as unnecessary. Where the `grilling` skill itself calls for dispatching a sub-agent to find an environmental fact, follow its own guidance — that's internal to how grilling resolves one question, not a substitute for the live conversation with the user.

Each round after the first ends this turn, waiting for the user's next message before continuing — the same mechanism as the `spec`/`design` checkpoints in Steps 5a/5b, never invented or advanced speculatively. The moment the frontier is empty (or empty already on round 1), grilling is done — continue straight to Step 4 in that same turn, no separate pause beyond what its own rounds already required. Keep the session's notes; they become `grilling-session.md`'s content in Step 4.

## Step 4: Write grilling-session.md

Write `grilling-session.md` from Step 3's grilling notes into the feature folder Step 1 created, before Specify runs.

## Step 5a: Specify (Sonnet)

Spawn a Sonnet subagent to run tlc-spec-driven's Specify phase against the feature folder path, reading `grilling-session.md` there as its clarification source. Writes `spec.md`.

**Checkpoint — `spec`:** if `human_review=yes` and `spec` is not in `human_review_exclude`, record `spec: pending` (`scripts/progress.mjs --step 5a --label specify --detail spec.md --set spec=pending`), show `spec.md` to the user, and end this turn, waiting for their next message — never invent an approval or continue speculatively. On their approval, set `spec=approved` the same way, then continue to 5b. Otherwise continue immediately. (Every other checkpoint in this skill — `design` in Step 5b, `code-review` in Step 10 — pauses the same way.)

## Step 5b: Design (Sonnet)

Spawn a second, separate Sonnet subagent — reads `spec.md` fresh from disk (no shared conversation state with 5a's subagent; the file is the handoff), with `grilling-session.md` as its clarification source. Runs tlc-spec-driven's Design phase. Respect its native auto-sizing: for a Small/Medium-scoped feature, Design may legitimately produce nothing — record `design: skipped (auto-sizing)` in `progress.md` rather than treating it as a failure.

**Checkpoint — `design`:** only meaningful if Design actually ran. If `human_review=yes`, `design` not excluded, and `design.md` was produced, record `design: pending` (`--step 5b --label design --detail design.md --set design=pending`), show it, and end this turn; on approval set `design=approved`, then continue. Otherwise continue immediately.

## Step 6: Tasks (Haiku)

Spawn a Haiku subagent — reads `spec.md` and `design.md` (if present) fresh from disk. Runs tlc-spec-driven's Tasks phase. Writes `tasks.md`, respecting the same auto-sizing as Design. If auto-sizing skips Tasks, log Step 6 as skipped (`--detail "skipped (Small/Medium scope)"`); Steps 7 and 9 then source their checklist from `spec.md`'s acceptance criteria and the branch's commits.

## Step 7: Commit and Push Spec Artifacts, Open the Draft PR

Commit whatever Steps 4–6 produced (`grilling-session.md`, `spec.md`, `design.md` and `tasks.md` if present) as one Conventional Commits commit (e.g. `docs(spec): add PROJ-42 feature spec`), push to the feature branch.

This is the branch's first real commit, so open the draft PR now: `gh pr create --draft --base <target_branch> --head feature/<task_id>_<desc-kebab> --title "[<task_id>] <description>" --body "<sourced per the PR guardrail>"`. Fall back to the GitHub MCP tool, then `gh api graphql`'s `createPullRequest` mutation with `draft: true`, only if `gh` itself is unavailable. Record the returned PR number in `progress.md`.

## Step 8: Execute (Sonnet)

Spawn a Sonnet subagent to run tlc-spec-driven's Execute phase for the feature — every task in `tasks.md`, or the implicit tasks when Tasks was skipped. It owns its own gate checks, atomic Conventional-Commits commits, and the end-of-feature Verifier — do not add parallel logic for any of that here. State in the dispatch prompt that tlc-spec-driven's per-batch workers and the Verifier are pre-approved (delegation depth: one level), since this subagent has no user to accept the offer. If Execute's fix-loop can't converge: stop, report, do not proceed to Step 9.

## Step 9: Push Execute's Commits and Rewrite the PR Description

`git push` — Step 8's commits are local-only until this point; push them now so the PR (and `code-review`, next) reflect what Execute actually did, not a stale remote branch.

Then rewrite the PR description, sourced from existing artifacts, invent nothing new: **Problem** ← `spec.md`; **What was done** ← `tasks.md`'s completed checklist (or `spec.md`'s acceptance criteria when Tasks was skipped) and the commits made on this worktree's branch (`git log --oneline origin/<base_branch>..HEAD`, run in the worktree); **Test results** ← `validation.md` (the Verifier's report). `gh pr edit <PR> --body "..."`.

## Step 10: code-review (review → checkpoint → fix)

Invoke `code-review` via the `Skill` tool **directly in this conversation** — not through a wrapper subagent — for this PR: pass the PR number, owner/repo, the feature folder path (`.specs/features/<task_id>-<slug>/`, so its fix worker writes `fix-code-review.md` there), the worktree path, and `human_review`: `true` when this skill's `human_review=yes` and `code-review` is not in `human_review_exclude`, otherwise `false`. `gh auth status` must succeed here even if earlier steps fell back to GitHub MCP — `code-review` writes to GitHub only through `gh`. This conversation is `code-review`'s root: its own workers do the heavy work and only their compact results land here. It runs here, not in a subagent, because its checkpoint must end this turn. Never invoke via `Skill` here a skill that does its heavy work inline.

`code-review` owns its review, submit, fix and recovery chain. Never post, submit, fix, or reply from this conversation yourself.

**Before ending a turn at `code-review`'s checkpoint**, record `code_review: pending` in `progress.md` (`scripts/progress.mjs --step 10 --label "code-review, paused at checkpoint" --detail "review posted on PR #<N>" --set code_review=pending`), so an interruption resumes correctly — `pr_number` is already in Run State. **Resuming** with `code_review: pending` means the review is already posted: show the PR URL and wait for the user's reply again (never auto-approve because time passed), then invoke `code-review`'s continue-after-checkpoint entry ("continue the code review on PR #<N>") with the same fields Step 10's first invocation passes — PR number, owner/repo, feature folder path, and `worktree_path`, all from `progress.md` — instead of re-running the review.

When `code-review` returns, record Step 10 done with `code_review: approved` (or `n/a` when it didn't pause) and its final report's counts: findings, fixed / rejected / answered / blocked, and commits pushed.

If `code-review` still reports a failure, stop and report its raw result. Never invoke its continue-after-checkpoint entry for a review or posting failure.

## Step 11: architecture-evaluate (Sonnet)

Spawn a Sonnet subagent to run `architecture-evaluate` inside the worktree over the commits made on this worktree's branch, passing `origin/<base_branch>` as its base ref (the range `origin/<base_branch>...HEAD`). The skill picks its own mode. Tell the subagent not to scaffold packages or ask the user anything: it returns new-package candidates and any other decision it can't make as `status: question` items, which the final report lists for the user.

Classify every file the sync touched — `docs/codebase/`, inline docs in source files, root context files — as new vs. existing (`git status --porcelain`): if every touched file is new, leave them uncommitted for manual review; otherwise commit them together as one Conventional Commits commit and push. If `docs/codebase/` is untracked or ignored, nothing here can commit it — run the context sync-out described under Architecture context in the worktree instead, immediately, so the update survives this worktree.

## Step 12: design-sync Handoff (Conditional, no work here)

Only if `.design-sync/config.json` exists at the worktree root — otherwise log Step 12 silently (`--detail "skipped — no .design-sync/config.json" --set design_sync=skipped`) and go to Step 13.

Nothing runs in this step, and nothing can (see the design-sync guardrail). Record it (`scripts/progress.mjs --step 12 --label "design-sync handoff" --detail "pending-user-action — handed off in the final report" --set design_sync=pending-user-action`), then carry the handoff into the final report as a **required follow-up, not a suggestion** — the user runs it themselves once this run has finished. Do not attempt the `Skill` tool, and do not spend a `ToolSearch` checking whether `DesignSync` is reachable: its reachability was never what blocked this.

Put the handoff last in the final report, as its closing instruction, in two steps:

1. **`/compact`** first — design-sync re-derives everything it needs from disk, so it loses nothing to the summary.
2. **`/design-sync`** — typed literally, as the user's own next message.

## Step 13: Confirm It Merges, Then Mark Ready

First, ask GitHub whether the PR can actually merge: `gh pr view <PR> --json mergeable,mergeStateStatus`. Route on `mergeable` alone; `mergeStateStatus` (`BLOCKED`, `BEHIND`, `UNSTABLE`, …) is informational — mention it in the final report, never route on it.

- **`MERGEABLE`** → proceed.
- **`UNKNOWN`** → GitHub computes mergeability asynchronously and often hasn't finished right after a push. Wait once — a single timed wait with `Monitor`, never a poll loop — and re-query. Still `UNKNOWN` → proceed, and say in the final report that the check was inconclusive rather than implying it passed.
- **`CONFLICTING`** → dispatch a Sonnet subagent to resolve it: merge `origin/<target_branch>` into the feature branch, resolve every conflict, verify with build/typecheck/lint plus the tests covering what the merge brought in, commit the merge, push. It returns the conflicted file list, how each was resolved, and what verification it ran. Re-query afterwards, then proceed. Conflict resolution reads and edits files, so it belongs in a subagent, not here — this conversation only detects, dispatches, and re-checks. If a conflict is genuinely ambiguous — both sides implement the same behavior differently and either choice changes what ships — the subagent leaves it unresolved and says so: stop there, report exactly which files conflict and why, and leave the PR as a draft. Never guess at a merge resolution to reach a green state.

Record the outcome in `progress.md` (`--set merge_check=<clean|resolved|inconclusive|conflicting>`), so a resumed run doesn't repeat it blindly.

Then `gh pr ready <PR>`. Write `progress.md` status `complete`. This is the true end of a fresh delivery run — report the PR URL and a summary of what each step did, and stop. Note that mergeability was true at that moment, not forever: the target branch keeps moving, and a later conflict isn't a failure of this run.

## Examples

### Example 1: Fresh delivery run, human_review default

User: `/build-feature base_branch=main task_id=PROJ-42 description="add rate limiting to orders API"`

1. Step 0: no `.specs/features/PROJ-42-*/progress.md` in any worktree → fresh run
2. Step 1: worktree created at `.claude/worktrees/PROJ-42-add-rate-limiting`, branch renamed to `feature/PROJ-42_add-rate-limiting-to-orders-api`, `.specs/features/PROJ-42-add-rate-limiting/progress.md` initialized
3. Step 2: pushed (empty branch, no PR yet — GitHub won't accept one until there's a commit ahead of `main`)
4. Step 3: grilling runs live in this conversation — as many rounds as the design tree needs (say, 3), the user answering each round in turn, until the frontier is empty; notes captured, continues straight to Step 4
5. Step 4: `.specs/features/PROJ-42-add-rate-limiting/grilling-session.md` written
6. Step 5a: Specify writes `spec.md` → `human_review=yes` (default), `spec` not excluded → `spec: pending` recorded, shown to user, approved → `spec: approved`
7. Step 5b: Design writes `design.md` (feature sized Large) → `design: pending`, shown, approved → `design: approved`
8. Step 6: Tasks writes `tasks.md`
9. Step 7: spec artifacts committed and pushed — the branch's first real commit, so the draft PR #512 opens now, body sourced from `spec.md`/`tasks.md`
10. Step 8: Execute runs all tasks, Verifier passes
11. Step 9: Execute's commits pushed; PR #512's description rewritten with problem/what-was-done/test-results
12. Step 10: `code-review` invoked via `Skill` in this conversation with `human_review: true` → its review worker posts 9 findings as a pending review on PR #512 → checkpoint: `code_review: pending` recorded, summary shown, turn ends → user deletes one wrong finding on GitHub and replies → `code-review` submits the review, its fix worker fixes 5 of the 8 remaining, replies to and resolves them, leaves 1 answered-only and 2 blocked with reasons, pushes → returns those counts and the SHAs
13. Step 11: `architecture-evaluate` runs over `origin/main...HEAD` and updates 2 already-tracked files → committed and pushed
14. Step 12: no `.design-sync/config.json` at the worktree root → skipped silently
15. Step 13: `gh pr view 512 --json mergeable,mergeStateStatus` → `MERGEABLE` (`CLEAN`) → `gh pr ready 512` → `progress.md` marked complete → report: "PR #512 marked ready for review: <url>. 8 findings after your review, 5 fixed. Mergeable against `main` as of now. Worktree left in place."

### Example 2: Re-invocation after delivery, PR still open

User: `/build-feature task_id=PROJ-42` (weeks later; a reviewer left new comments on PR #512, which is still open)

1. Step 0: `.claude/worktrees/PROJ-42-add-rate-limiting/.specs/features/PROJ-42-add-rate-limiting/progress.md` shows `complete`, `gh pr view 512 --json state` → `OPEN`
2. `code-review`'s fix-existing-findings entry invoked for PR #512 — its fix worker runs in the still-present worktree, fixes 2 new comments, pushes
3. Step 11 runs once (commits were pushed) → no doc changes needed
4. Report: "2 new review comments fixed and pushed to PR #512. Still open, not re-marked (already ready)."
