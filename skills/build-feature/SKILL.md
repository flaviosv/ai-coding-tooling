---
name: build-feature
description: Delivers a brand-new feature end-to-end with no planning already done — creates a worktree and branch from base_branch, opens a draft PR against target_branch, optionally grills the user on scope, runs tlc-spec-driven's full Specify→Design→Tasks→Execute cycle, updates the PR description, runs complete-review and fix-review, syncs architecture docs and Claude Design (when integrated), then confirms the PR actually merges before marking it ready — through isolated subagents for every step but grilling and design-sync (both run live, in this conversation), resumable from any interrupted step via progress.md, self-routing a later re-invocation straight to fresh PR comments once delivered. Requires base_branch, target_branch (defaults to base_branch), task_id, and description; human_review (default yes) gates spec/design/complete-review pauses. Use when the user says "build feature", "start a new feature end to end", "deliver this feature autonomously", or invokes /build-feature. Do NOT use to fix PR comments outside this flow (use fix-review directly).
metadata:
  author: Flavio Studart
  version: "1.5.0"
---

# Build Feature

Takes a feature from nothing but a task ID and a description to a PR marked ready for review, with no human interaction required beyond what `human_review` asks for. An orchestrator that does almost none of the work itself — every step but two delegates to an isolated subagent and reports back a structured result, so this conversation's own context stays small enough to survive a run with a dozen-plus steps. The exceptions are grilling (Step 5), a live multi-round conversation with the user that only this conversation can hold, and design-sync (Step 15), whose tool a dispatched subagent cannot reach at all.

## Parameters

Required, never inferred — ask if missing, do not guess:

- `base_branch` — branch the feature branch is cut from.
- `task_id` — used in the branch name, PR title, and feature folder name.
- `description` — short text; becomes a kebab-case slug for the branch/folder name.

Optional:

- `target_branch` — the PR's merge target. Defaults to `base_branch` when omitted (a superset of a same-branch delivery, not a different default).
- `human_review` — `yes` (default) or `no`. `yes` pauses after Specify, after Design (when Design runs at all), and after `complete-review` publishes its findings (already posted to GitHub as a pending review by that point — see Step 12), waiting for approval before continuing each time. `no` runs the whole pipeline without pausing anywhere this parameter controls.
- `human_review_exclude` — comma-separated subset of `spec`, `design`, `complete-review` to skip pausing on even when `human_review=yes` (e.g. `human_review_exclude=complete-review`). Ignored when `human_review=no`.

## Guardrails

### Composability — do not reimplement what other skills own

- tlc-spec-driven owns Specify/Design/Tasks/Execute's own internal mechanics (auto-sizing, atomic commits, gate checks, the Verifier). Invoke it; don't duplicate its logic.
- `complete-review` owns the review-and-publish mechanics — it always publishes findings as a pending GitHub review immediately (see Step 12); this skill never passes it `human_review` and never uses its Publish Mode. This skill's own `human_review` only decides whether *this* skill pauses, in its own Step 12 checkpoint, before proceeding to `fix-review`. When that checkpoint doesn't pause, this skill also submits the pending review itself, right there in Step 12 — `complete-review` never submits its own reviews, by design (see its Guardrails), and `fix-review` refuses to act on a review still sitting `PENDING` (its own Step 1 rule 3), so without a human around to click "submit" on GitHub, this skill has to do it.
- `fix-review` owns fetching threads fresh from GitHub, classifying them, and fixing — invoke it, don't duplicate it.
- `architecture-evaluate` owns Incremental/Full mode's own scan and doc-writing logic.
- `not-your-babysitter`: the orchestrator (this conversation) adopts it as a standing mode for genuinely unplanned situations — a tool failure, a dead end, an ambiguity this skill never anticipated. It does not gate anything this skill explicitly defines: `human_review`'s named checkpoints are planned, not the kind of thing not-your-babysitter's stops are for. The two never compete for the same decision.

### State ownership

This conversation (the orchestrator) is the **only** writer of `progress.md` — no subagent ever writes it. Every subagent this skill dispatches returns a structured result, not free prose: `status` (`ok` / `blocked` / `question`), the artifacts it produced (file paths, PR number, commit SHAs — whatever the step calls for), and a `question` or `blocker` field when it hit something requiring a decision it can't make itself. The orchestrator is the only thing that ever decides to pause, resume, or advance `progress.md`.

When handing work to a subagent, pass resolved metadata and file **paths** (branch name, feature folder path, "read `spec.md` at this path") — never inline a file's bulk content into this conversation just to relay it. Never `Read` a file for the sole purpose of pasting its contents into an `Agent` prompt: that pays for the content twice, once on the way in and again in every cached turn afterward. Each subagent does its own targeted reads inside its own isolated context; the orchestrator stays small by construction, not by discipline alone.

This binds every step, including the ones that delegate to `complete-review` and `fix-review`. If a sub-skill's mechanics call for reading bulk file content, editing source files, or looping over a list of items one tool call at a time, that work belongs in a dispatched subagent — not here. This conversation's own tool calls are limited to git/gh state, `progress.md`, dispatching, and the checkpoints.

### Worktree

- Ensure `worktree.baseRef` is set to `head` (check `.claude/settings.json`/`~/.claude/settings.json`; if unset, this is a one-time setup gap — stop and tell the user to set it via the `update-config` skill before continuing, rather than guessing a different mechanism).
- `git checkout <base_branch>` first (so "current HEAD" is the branch actually requested), then `EnterWorktree({name: "<task_id>-<slug>"})` — the **native** tool, not raw `git worktree add`. It lands at `.claude/worktrees/<task_id>-<slug>`.
- Immediately after, `git branch -m feature/<task_id>_<description>` inside the new worktree — guarantees the exact naming convention regardless of what `EnterWorktree` itself named the branch.
- If `EnterWorktree` fails for any reason (a symlinked `.claude`, or anything else): stop and report the failure plainly. Do not fall back to raw `git worktree add` — a failure here means something about this repo isn't compatible with the native tool, and that's worth surfacing, not silently working around.
- A branch-name collision (the target branch already exists locally or on the remote) is a not-your-babysitter-style stop regardless of `human_review` — report it and halt; never auto-suffix or guess a resolution.
- After Step 16 (PR marked ready), the worktree **stays** — it is not removed at the end of a successful run. Cleanup is signal-driven only: at the start of any later invocation, check every tracked spec with a `progress.md` marked complete and a worktree still present — for each, `gh pr view <PR> --json state`; if `MERGED` or `CLOSED`, remove that worktree (`ExitWorktree` if it's the current one, or a direct worktree removal for another tracked spec's) before doing anything else this run. Sweep opportunistically across **all** tracked specs found this way, not just the one this invocation is about — a PR merged via the GitHub UI, never re-triggering build-feature itself, would otherwise leave its worktree on disk forever.

### Architecture context in the worktree

`architecture-evaluate`'s output (`docs/codebase/`) is frequently untracked or gitignored, and a fresh `EnterWorktree` checkout carries neither untracked nor ignored files — so the worktree looks like a project with no context docs even when the repo has a current, complete set. Unhandled, that misfires at both ends of the run: Step 4's gate reads the absence as "this project has no context docs" and escalates to a Full brownfield scan inside the live feature worktree, and Step 14's output then dies with the worktree, because the path it wrote to is ignored and never committed.

Sync it explicitly, in both directions:

- **In — Step 1, immediately after the worktree exists.** Check whether the path is tracked (`git ls-files --error-unmatch docs/codebase`). Tracked → nothing to do; the worktree already has it and Step 14 commits it normally. Untracked or ignored → copy it in from the repo's **main working tree** (the first entry of `git worktree list` — never a sibling feature worktree, which may hold another run's stale copy). Record in `progress.md` that the copy happened, and from where.
- **Out — immediately after Step 14, not at Step 16**, so an early stop still lands the docs. Only when the copy-in actually happened. Before writing back, confirm the source hasn't changed since Step 1; if it has, another session updated it mid-run — do not overwrite. Report both paths and leave the worktree's version in place for the user to reconcile.
- If neither the worktree nor the main working tree has `docs/codebase/` at all, the project genuinely has none. Step 4's gate decides what to do about that.

When the repo tracks `docs/codebase/` in git, none of this runs and none of it is needed — that is the better arrangement wherever the user controls the repo, since it makes the docs versioned, reviewable, and carried by every worktree for free. Say so once in the final report when a run had to fall back to copying.

### Waiting on dispatched subagents

Every step below that spawns a subagent directly via the `Agent` tool — Steps 4, 7a, 7b, 8, 10, 12, 13, 14, and Step 16's conflict-resolution dispatch — waits for it the same way: load and apply [Agent Wait Protocol](../../templates/agent-wait-protocol.md). This applies whether the step dispatches one subagent or several; the default single-subagent case is exactly what the protocol already covers, not a special case of it. Step 4 is the one exception in *timing*, not mechanism: it's dispatched at the start of Step 4 but not collected until just before Step 7a starts, once Step 5's grilling session has run its course — the protocol still governs how that eventual wait happens.

Steps 12 and 13 dispatch a subagent that then invokes `complete-review`/`fix-review` via the `Skill` tool **inside its own context** — never via the `Skill` tool in this conversation. Those two skills carry the heaviest mechanics in the pipeline (publishing dozens of review comments; fetching threads, dispatching fix clusters, cherry-picking, resolving conflicts, replying per thread), and invoking them here runs all of it in the orchestrator's context, at its largest, in the run's final steps. Measured across four real runs, that single mistake accounted for 39–60% of the orchestrator's entire token cost — in one case 83M tokens to move 80 comments onto a PR, more than the feature's own implementation step. `complete-review` invoked this way costs the orchestrator ~3M for the same work.

Step 5 (grilling) is not a subagent dispatch and the wait protocol does not apply to it: it runs directly in this conversation via the `Skill` tool, and each round ends this turn waiting for the user's actual reply — the same mechanism as the `spec`/`design` checkpoints in Steps 7a/7b, not a background task with a stall ceiling.

### gh account resolution

Apply [gh Account Resolution](../../templates/gh-account-resolution.md) once at the start of every invocation (fresh or resumed) — this skill pushes branches, opens/updates PRs, and calls several `gh`-using subagents across a long run, exactly the situation that template exists for. Resolve once, cache the login for the rest of the run, persist only the login (never the token) to `progress.md`.

### PR

- Opened as a draft immediately after the first push (Step 4), with a minimal stub body (task ID and description only — `spec.md` doesn't exist yet at this point). Rewritten in full (Step 11) once tlc-spec-driven's Execute phase completes, sourced from `spec.md`/`tasks.md`/`commits.md`/`validation.md` — invent nothing new.
- Never merged, by this skill, under any circumstance.
- Marked ready (`gh pr ready <PR>`) only as the very last successful step (Step 16) — after every other step, including any `human_review` pause, has actually completed.
- Never marked ready while GitHub reports it unmergeable. "Ready for review" is a claim about the PR's state, and a PR nobody can merge doesn't meet it — asserting readiness without checking is a false completion, which a real run produced: the PR was announced ready and delivered, and the user came back hours later asking for the merge conflicts to be fixed. Step 16 checks, and resolves, before it marks.

### design-sync

Auto-detected only, no override parameter: presence of `.design-sync/config.json` at the worktree root runs Step 15; its absence skips it silently (not a failure, not something to report as missing).

Step 15 runs **in this conversation**, via the `Skill` tool — the second and last carve-out from the delegation rule above, alongside grilling. It is not a preference: `DesignSync` is an interactively-authenticated claude.ai tool and does not propagate into dispatched subagents, and the bundled `design-sync` skill isn't in a subagent's skill listing either, so a dispatched Step 15 is structurally guaranteed to fail. It did, on a real run: the subagent searched `ToolSearch` four different ways, found nothing, and returned `blocked` — while the same tool sat in the orchestrator's own tool list one level up, and the step later completed fine when invoked here. This carve-out doesn't threaten the context budget the delegation rule protects: the flow is Bash plus a background driver, and the tool reads local paths itself, so no bulk file content lands in this conversation.

### Credentials

Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.

## Before Starting

- All three required parameters present. Missing any → ask; never guess a value or derive `task_id` from anything else.
- `gh auth status` must succeed (after account resolution above), or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- `git status --porcelain` must be clean in the current checkout before `EnterWorktree` runs. Dirty → stop and report exactly what's uncommitted; never stash, commit, or discard it yourself.
- `base_branch` must actually exist (local or fetchable from remote). Missing → stop and report; do not substitute a different branch.

## Step 0: Resume or Start Fresh

Before anything else, look for `.specs/features/<task_id>-<slug>/progress.md` (derive `<slug>` from `description` the same way Step 6 would).

- **Not found** → fresh run, continue to Step 1.
- **Found, status `complete`, PR merged or closed** → this is the cleanup case described under Worktree above; report and stop, nothing else to do for this spec.
- **Found, status `complete`, PR still open** → this is a later re-invocation for fresh review comments, not a new delivery. Invoke `fix-review` directly for the tracked PR, working inside the existing worktree (already checked out, no new one needed — see `references/progress-schema.md` for exactly what `progress.md` records to make this possible without re-deriving anything). Once it returns, run Step 14 (architecture-evaluate) if it reports any commits pushed, then report and stop. Do not re-mark the PR ready (it already is) and do not touch Steps 1–13 or 15–16.
- **Found, status `in-progress`** → resume at the first step `progress.md` marks incomplete, using the state it recorded (worktree path, branch name, PR number, resolved gh login, feature folder path, which of `spec`/`design`/`complete-review` already completed or is mid-pause). Grilling (Step 5) has no partial-round state to recover — nothing is logged for it until the session concludes — so an interruption mid-grilling simply resumes by restarting Step 5 from round 1; Step 4's quick-gate result, if it already reported back before the interruption, is not redispatched. See `references/progress-schema.md` for the exact field set.

## Step 1: Worktree and Branch

Per the Worktree guardrail above. Record `worktree_path` and the exact branch name in `progress.md` once this succeeds.

Then run the context sync-in described under Architecture context in the worktree — before Step 4's gate, so it decides against the docs this project actually has.

## Step 2: Push

`git push -u origin feature/<task_id>_<description>`.

## Step 3: Open the Draft PR (Stub)

`gh pr create --draft --base <target_branch> --head feature/<task_id>_<description> --title "[<task_id>] <description>" --body "<stub — task ID and description only>"`. Fall back to the GitHub MCP tool, then `gh api graphql`'s `createPullRequest` mutation with `draft: true`, only if `gh` itself is unavailable. Record the returned PR number in `progress.md`.

## Step 4: Architecture-Evaluate Gate (Background, decision only)

Dispatch a Sonnet subagent to **decide only**: read `architecture-evaluate`'s own "Keeping Docs Up to Date" trigger table plus the recent commit history on `base_branch`, and return `full`, `incremental`, or `none` with its reasoning. It does not invoke `architecture-evaluate`, write any file, or touch the worktree.

Judge the trigger against what the worktree actually holds after Step 1's context sync — by this point an absent `docs/codebase/` means the project genuinely has none, not that a fresh worktree failed to carry them.

- `none` or `incremental` → record it. Step 14's Incremental run is the sync; nothing else happens here.
- `full` → the project has no context docs at all. That is a brownfield mapping job, not a gate: report it and continue the feature without it. Never run Full mode inside a feature delivery — it takes tens of minutes, writes into the live worktree while later steps are working in it, and Step 14 re-scans the same files afterward regardless.

Dispatch it and move straight to Step 5 without waiting — it only touches `docs/codebase/`, never git the feature branch is on, and nothing until Step 7a depends on its result. Collect that result (per the Agent Wait Protocol) once Step 5 concludes, before Step 7a starts.

## Step 5: Grilling (Interactive — this conversation, not a subagent)

Grilling is a live, multi-round conversation: each round ends by waiting for the user's actual answers before the next one starts (see the `grilling` skill — rounds, frontier, "wait for the user's answers"). A subagent can't do that — dispatched via the `Agent` tool it runs once, in the background, to completion, and reports a single result on its own schedule; it has no way to pause mid-run for a reply from the actual user. So run `grilling` directly, via the `Skill` tool, in this conversation, using `task_id` and `description` as the seed.

Always attempted regardless of `human_review` — grilling is a scoping aid, not a review gate, and generalizes the "if there are no questions, skip it" rule to "if there's no one to usefully ask, skip it": if the frontier is empty on round 1, it exits immediately rather than being pre-judged as unnecessary. Where the `grilling` skill itself calls for dispatching a sub-agent to find an environmental fact, follow its own guidance — that's internal to how grilling resolves one question, not a substitute for the live conversation with the user.

Each round after the first ends this turn, waiting for the user's next message before continuing — the same mechanism as the `spec`/`design` checkpoints in Steps 7a/7b, never invented or advanced speculatively. The moment the frontier is empty (or empty already on round 1), grilling is done — continue straight to Step 6 in that same turn, no separate pause beyond what its own rounds already required. Keep the session's notes; they become `grilling-session.md`'s content in Step 6.

## Step 6: Pre-Create the Feature Folder

Derive `<slug>` (kebab-case, 2–4 words) from `description`. Create `.specs/features/<task_id>-<slug>/` and write `grilling-session.md` into it from Step 5's grilling notes — before Specify runs, so Specify's own folder-creation logic (if any) finds it already there rather than colliding with it.

## Step 7a: Specify (Opus)

First, collect Step 4's quick-gate result (per the Agent Wait Protocol) if it hasn't already reported back — a multi-round grilling session almost always outlasts it, so this is typically an instant check, not a real wait. Then spawn an Opus subagent to run tlc-spec-driven's Specify phase against the pre-created feature folder path. Writes `spec.md`.

**Checkpoint — `spec`:** if `human_review=yes` and `spec` is not in `human_review_exclude`, show `spec.md` to the user and end this turn, waiting for their next message before continuing to 7b — never invent an approval or continue speculatively. Otherwise continue immediately. (Every other checkpoint in this skill — `design` in 7b, `complete-review` in Step 12 — pauses the same way.)

## Step 7b: Design (Opus)

Spawn a second, separate Opus subagent — reads `spec.md` fresh from disk (no shared conversation state with 7a's subagent; the file is the handoff). Runs tlc-spec-driven's Design phase. Respect its native auto-sizing: for a Small/Medium-scoped feature, Design may legitimately produce nothing — record that in `progress.md` rather than treating it as a failure.

**Checkpoint — `design`:** only meaningful if Design actually ran. If `human_review=yes`, `design` not excluded, and `design.md` was produced, show it and wait for approval before continuing. Otherwise continue immediately.

## Step 8: Tasks (Sonnet)

Spawn a Sonnet subagent — reads `spec.md` and `design.md` (if present) fresh from disk. Runs tlc-spec-driven's Tasks phase. Writes `tasks.md`, respecting the same auto-sizing as Design.

## Step 9: Commit and Push Spec Artifacts

Commit whatever Steps 6–8 produced (`grilling-session.md`, `spec.md`, `design.md` if present, `tasks.md`) as one Conventional Commits commit (e.g. `docs(spec): add PROJ-42 feature spec`), push to the feature branch.

## Step 10: Execute (Sonnet)

Spawn a Sonnet subagent to run tlc-spec-driven's Execute phase for every task in `tasks.md`. It owns its own gate checks, atomic Conventional-Commits commits, and the end-of-feature Verifier — do not add parallel logic for any of that here. If Execute's fix-loop can't converge: stop, report, do not proceed to Step 11.

## Step 11: Push Execute's Commits and Rewrite the PR Description

`git push` — Step 10's commits are local-only until this point; push them now so the PR (and `complete-review`, next) reflect what Execute actually did, not a stale remote branch.

Then rewrite the PR description, sourced from existing artifacts, invent nothing new: **Problem** ← `spec.md`; **What was done** ← `tasks.md`'s completed checklist and `commits.md`; **Test results** ← `validation.md` (the Verifier's report). `gh pr edit <PR> --body "..."`.

## Step 12: complete-review (Sonnet)

Spawn a Sonnet subagent whose only job is to invoke `complete-review` for this PR — pass the PR number, repo, branch name, worktree path, and the run's resolved gh login. It returns a structured result: PR URL, each skill's complexity banner, finding counts, and the findings file path. The findings themselves stay on disk and in that subagent's context; this conversation never reads them.

Inside that subagent, `complete-review` is invoked with no `human_review` parameter, ever — it always publishes its findings as a pending GitHub review immediately, its own unchanged default behavior. Findings are never held back from GitHub waiting on this skill's own approval step.

Never post, append, or verify review comments one tool call at a time from this conversation. If `complete-review` reports it could not publish, dispatch a subagent to retry the posting — do not take the loop over yourself.

**Checkpoint — `complete-review`:** if `human_review=yes` and `complete-review` not in `human_review_exclude`, show the returned summary (PR URL, each skill's complexity banner, finding counts) to the user and end this turn, waiting for their next message before continuing to Step 13 — the findings are already posted to the PR as a pending review at this point, so the pause is the user's chance to look them over on GitHub, **submit the review** (required — `fix-review` refuses to act on a review still `PENDING`, its own Step 1 rule 3), and add their own comments to it before `fix-review` runs. Never invent an approval or continue speculatively.

Otherwise (`human_review=no`, or `complete-review` excluded) there's no human around to submit it, so submit the pending review here, on `complete-review`'s behalf, before continuing to Step 13:

1. Resolve the pending review's node ID under the run's own resolved gh login — same query as `complete-review`'s own Posting Mechanics step 1 (`reviews(first: 1, states: PENDING, author: $me)`), `$me` being the login this run already resolved via [gh Account Resolution](../../templates/gh-account-resolution.md).
2. If none is found (`complete-review` hit a full failure and posted nothing — see its own Guardrails — or it was already submitted by an earlier, interrupted run of this same step), skip submission and go straight to Step 13; there's nothing left for it to act on either, and it will report that itself.
3. Otherwise submit it as `COMMENT` — never `APPROVE` or `REQUEST_CHANGES`, this skill isn't rendering a review verdict, only making `complete-review`'s already-decided findings visible so `fix-review` can see them:
   ```
   gh api graphql -f query='
     mutation($reviewId: ID!) {
       submitPullRequestReview(input: { pullRequestReviewId: $reviewId, event: COMMENT }) {
         pullRequestReview { id }
       }
     }' -f reviewId={review_id}
   ```
4. Continue to Step 13.

## Step 13: fix-review (Sonnet)

Spawn a Sonnet subagent to invoke `fix-review` for this PR — pass the PR number, repo, branch name, worktree path, and the run's resolved gh login, and nothing else; it fetches the threads fresh itself. It operates inside the already-open worktree (this run's own checkout already matches the PR's branch), so it doesn't need to create one of its own. Never merges or closes the PR.

It returns a structured result: threads fixed, answered-only, rejected (with reasons), and blocked, plus the commit SHAs it pushed. Everything else — fetching threads, the finding bodies, classification, its own fix-cluster subagents, cherry-picking, conflict resolution, post-merge repair, and per-thread replies — stays inside that subagent. This conversation does not fetch review threads, cherry-pick, edit source files, or post replies.

## Step 14: architecture-evaluate (Incremental, Sonnet)

Spawn a Sonnet subagent to run `architecture-evaluate` in Incremental mode against everything pushed to this branch this run — this is a code-changes-want-docs-reflected sync, not a brownfield re-scan. **Incremental always, never Full**, regardless of how much this run changed or how stale the docs look; Step 4's gate is the only place in this skill that may conclude Full is warranted, and its answer there is to report it, not to run it. If Incremental genuinely looks insufficient, say so in the final report and let the user trigger `architecture-evaluate` Full separately.

Classify touched `docs/codebase/` files as new vs. existing (`git status --porcelain -- docs/codebase/`): if every touched file is new, leave them uncommitted for manual review; otherwise commit as one Conventional Commits commit and push. If the path is untracked or ignored, nothing here can commit it — run the context sync-out described under Architecture context in the worktree instead, immediately, so the update survives this worktree.

## Step 15: design-sync (Conditional, this conversation)

Only if `.design-sync/config.json` exists at the worktree root. Run it **here**, not in a subagent (see the design-sync guardrail for why a dispatched one cannot work): confirm the tool is reachable (`ToolSearch` for `DesignSync`), then invoke `design-sync` via the `Skill` tool and follow its own list→finalize_plan→write flow. Commit and push whatever it changes, same classification logic as Step 14.

If the tool isn't reachable even from here, record `blocked` in `progress.md`, say so in the final report, and continue to Step 16 — it doesn't block delivery. Never reconstruct the flow by hand from `.design-sync/NOTES.md` or the config: the pipeline scripts live inside the skill, and improvising them risks pushing malformed content to a live external design project.

## Step 16: Confirm It Merges, Then Mark Ready

First, ask GitHub whether the PR can actually merge: `gh pr view <PR> --json mergeable,mergeStateStatus`.

- **`MERGEABLE`/`CLEAN`** → proceed.
- **`UNKNOWN`** → GitHub computes mergeability asynchronously and often hasn't finished right after a push. Wait once — a single timed wait, per [Agent Wait Protocol](../../templates/agent-wait-protocol.md)'s clock rule, never a poll loop — and re-query. Still `UNKNOWN` → proceed, and say in the final report that the check was inconclusive rather than implying it passed.
- **`CONFLICTING`** → dispatch a Sonnet subagent to resolve it: merge `origin/<target_branch>` into the feature branch, resolve every conflict, run the project's gate checks, commit the merge, push. It returns the conflicted file list and how each was resolved. Re-query afterwards, then proceed. Conflict resolution reads and edits files, so it belongs in a subagent, not here — this conversation only detects, dispatches, and re-checks. If a conflict is genuinely ambiguous — both sides implement the same behavior differently and either choice changes what ships — the subagent leaves it unresolved and says so: stop there, report exactly which files conflict and why, and leave the PR as a draft. Never guess at a merge resolution to reach a green state.

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
3. Steps 2–3: pushed, draft PR #512 opened with a stub body
4. Step 4: gate subagent dispatched in the background, returns `none` — nothing to sync beyond Step 14
5. Step 5: grilling runs live in this conversation — as many rounds as the design tree needs (say, 3), the user answering each round in turn, until the frontier is empty; notes captured, continues straight to Step 6
6. Step 6: `.specs/features/PROJ-42-add-rate-limiting/grilling-session.md` written
7. Step 7a: quick-gate result collected (already returned); Specify writes `spec.md` → `human_review=yes` (default), `spec` not excluded → shown to user, approved
8. Step 7b: Design writes `design.md` (feature sized Large) → shown, approved
9. Step 8: Tasks writes `tasks.md`
10. Step 9: spec artifacts committed and pushed
11. Step 10: Execute runs all tasks, Verifier passes
12. Step 11: Execute's commits pushed; PR #512's description rewritten with problem/what-was-done/test-results
13. Step 12: subagent invokes `complete-review` (no `human_review` param) → posts 9 findings as one pending review on PR #512 immediately → returns counts and banners; summary shown to user, who reviews and submits the pending review on GitHub, then approves in this conversation → continues to Step 13
14. Step 13: subagent invokes `fix-review`, which fixes 6 of 9 findings, replies to and resolves them, leaves 1 answered-only and 2 blocked with reasons → returns those counts and the pushed SHAs
15. Step 14: `architecture-evaluate` Incremental mode updates 2 already-tracked files → committed and pushed
16. Step 15: no `.design-sync/config.json` at the worktree root → skipped silently
17. Step 16: `gh pr view 512 --json mergeable,mergeStateStatus` → `MERGEABLE`/`CLEAN` → `gh pr ready 512` → `progress.md` marked complete → report: "PR #512 marked ready for review: <url>. 9 findings published, 6 auto-fixed. Mergeable against `main` as of now. Worktree left in place."

### Example 2: Fully autonomous run

User: `/build-feature base_branch=main task_id=PROJ-43 description="cache invalidation for job listings" human_review=no`

Same steps, but 7a/7b/12 never pause — Specify and Design proceed immediately without showing anything to the user first, and Step 12's checkpoint doesn't pause either (`complete-review` still publishes its pending review immediately either way — that part never depended on `human_review`). With no human around to submit it, Step 12 submits the pending review itself (`COMMENT` event, via `gh api graphql`) before Step 13 (`fix-review`) starts right after — otherwise `fix-review` would find only a `PENDING` review and refuse to run.

### Example 3: Resuming after an interruption

User: `/build-feature task_id=PROJ-42` (session was interrupted mid-Execute)

1. Step 0: `progress.md` for `PROJ-42-add-rate-limiting-to-orders-api` shows `in-progress`, last completed step 9, worktree/branch/PR recorded
2. Resume directly at Step 10 (Execute) — Steps 1–9 are not re-run

### Example 4: Re-invocation after delivery, PR still open

User: `/build-feature task_id=PROJ-42` (weeks later; a reviewer left new comments on PR #512, which is still open)

1. Step 0: `progress.md` shows `complete`, `gh pr view 512 --json state` → `OPEN`
2. `fix-review` invoked directly for PR #512, using the still-present worktree — fixes 2 new comments, pushes
3. Step 14 runs once (fix-review pushed commits) → no doc changes needed
4. Report: "2 new review comments fixed and pushed to PR #512. Still open, not re-marked (already ready)."

### Example 5: Re-invocation after the PR merged

User: `/build-feature task_id=PROJ-42` (PR #512 was merged last week)

1. Step 0: `progress.md` shows `complete`, `gh pr view 512 --json state` → `MERGED`
2. Worktree cleanup fires: `PROJ-42-add-rate-limiting-to-orders-api`'s worktree removed. While sweeping, also finds `PROJ-40-...`'s worktree (a different, unrelated completed spec) whose PR is also merged — removes that one too.
3. Report: "PR #512 is merged — nothing left to do. Cleaned up 2 stale worktrees (PROJ-42, PROJ-40)."
