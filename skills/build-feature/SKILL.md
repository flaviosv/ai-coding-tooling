---
name: build-feature
description: Delivers a brand-new feature end-to-end with no planning already done — creates a worktree and branch from base_branch, opens a draft PR against target_branch, optionally grills the user on scope, runs tlc-spec-driven's full Specify→Design→Tasks→Execute cycle, updates the PR description, runs complete-review and fix-review, syncs architecture docs and Claude Design (when integrated), then marks the PR ready — through isolated subagents for every step but grilling itself (run live, in this conversation), resumable from any interrupted step via progress.md, self-routing a later re-invocation straight to fresh PR comments once delivered. Requires base_branch, target_branch (defaults to base_branch), task_id, and description; human_review (default yes) gates spec/design/complete-review pauses. Use when the user says "build feature", "start a new feature end to end", "deliver this feature autonomously", or invokes /build-feature. Do NOT use to fix PR comments outside this flow (use fix-review directly).
metadata:
  author: Flavio Studart
  version: "1.2.0"
---

# Build Feature

Takes a feature from nothing but a task ID and a description to a PR marked ready for review, with no human interaction required beyond what `human_review` asks for. An orchestrator that does almost none of the work itself — every step but one delegates to an isolated subagent and reports back a structured result, so this conversation's own context stays small enough to survive a run with a dozen-plus steps. The one exception is grilling (Step 5): it's a live, multi-round conversation with the user, which only this conversation — not an isolated subagent — can actually hold.

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
- `complete-review` owns the review-and-publish mechanics — it always publishes findings as a pending GitHub review immediately (see Step 12); this skill never passes it `human_review` and never uses its Publish Mode. This skill's own `human_review` only decides whether *this* skill pauses, in its own Step 12 checkpoint, before proceeding to `fix-review`.
- `fix-review` owns fetching threads fresh from GitHub, classifying them, and fixing — invoke it, don't duplicate it.
- `architecture-evaluate` owns Incremental/Full mode's own scan and doc-writing logic.
- `not-your-babysitter`: the orchestrator (this conversation) adopts it as a standing mode for genuinely unplanned situations — a tool failure, a dead end, an ambiguity this skill never anticipated. It does not gate anything this skill explicitly defines: `human_review`'s named checkpoints are planned, not the kind of thing not-your-babysitter's stops are for. The two never compete for the same decision.

### State ownership

This conversation (the orchestrator) is the **only** writer of `progress.md` — no subagent ever writes it. Every subagent this skill dispatches returns a structured result, not free prose: `status` (`ok` / `blocked` / `question`), the artifacts it produced (file paths, PR number, commit SHAs — whatever the step calls for), and a `question` or `blocker` field when it hit something requiring a decision it can't make itself. The orchestrator is the only thing that ever decides to pause, resume, or advance `progress.md`.

When handing work to a subagent, pass resolved metadata and file **paths** (branch name, feature folder path, "read `spec.md` at this path") — never inline a file's bulk content into this conversation just to relay it. Each subagent does its own targeted reads inside its own isolated context; the orchestrator stays small by construction, not by discipline alone.

### Worktree

- Ensure `worktree.baseRef` is set to `head` (check `.claude/settings.json`/`~/.claude/settings.json`; if unset, this is a one-time setup gap — stop and tell the user to set it via the `update-config` skill before continuing, rather than guessing a different mechanism).
- `git checkout <base_branch>` first (so "current HEAD" is the branch actually requested), then `EnterWorktree({name: "<task_id>-<slug>"})` — the **native** tool, not raw `git worktree add`. It lands at `.claude/worktrees/<task_id>-<slug>`.
- Immediately after, `git branch -m feature/<task_id>_<description>` inside the new worktree — guarantees the exact naming convention regardless of what `EnterWorktree` itself named the branch.
- If `EnterWorktree` fails for any reason (a symlinked `.claude`, or anything else): stop and report the failure plainly. Do not fall back to raw `git worktree add` — a failure here means something about this repo isn't compatible with the native tool, and that's worth surfacing, not silently working around.
- A branch-name collision (the target branch already exists locally or on the remote) is a not-your-babysitter-style stop regardless of `human_review` — report it and halt; never auto-suffix or guess a resolution.
- After Step 16 (PR marked ready), the worktree **stays** — it is not removed at the end of a successful run. Cleanup is signal-driven only: at the start of any later invocation, check every tracked spec with a `progress.md` marked complete and a worktree still present — for each, `gh pr view <PR> --json state`; if `MERGED` or `CLOSED`, remove that worktree (`ExitWorktree` if it's the current one, or a direct worktree removal for another tracked spec's) before doing anything else this run. Sweep opportunistically across **all** tracked specs found this way, not just the one this invocation is about — a PR merged via the GitHub UI, never re-triggering build-feature itself, would otherwise leave its worktree on disk forever.

### Waiting on dispatched subagents

Every step below that spawns a subagent directly via the `Agent` tool — Steps 4, 7a, 7b, 8, 10, 14, 15 — waits for it the same way: load and apply [Agent Wait Protocol](../../templates/agent-wait-protocol.md). This applies whether the step dispatches one subagent or several; the default single-subagent case is exactly what the protocol already covers, not a special case of it. Step 4 is the one exception in *timing*, not mechanism: it's dispatched at the start of Step 4 but not collected until just before Step 7a starts, once Step 5's grilling session has run its course — the protocol still governs how that eventual wait happens.

Step 5 (grilling) is not a subagent dispatch and the wait protocol does not apply to it: it runs directly in this conversation via the `Skill` tool, and each round ends this turn waiting for the user's actual reply — the same mechanism as the `spec`/`design` checkpoints in Steps 7a/7b, not a background task with a stall ceiling. Steps 12–13 invoke `complete-review`/`fix-review` via the Skill tool rather than a direct `Agent` call — each of those skills' own internal dispatch (if it runs any) already owns its own wait handling; nothing here overrides that.

### gh account resolution

Apply [gh Account Resolution](../../templates/gh-account-resolution.md) once at the start of every invocation (fresh or resumed) — this skill pushes branches, opens/updates PRs, and calls several `gh`-using subagents across a long run, exactly the situation that template exists for. Resolve once, cache the login for the rest of the run, persist only the login (never the token) to `progress.md`.

### PR

- Opened as a draft immediately after the first push (Step 4), with a minimal stub body (task ID and description only — `spec.md` doesn't exist yet at this point). Rewritten in full (Step 11) once tlc-spec-driven's Execute phase completes, sourced from `spec.md`/`tasks.md`/`commits.md`/`validation.md` — invent nothing new.
- Never merged, by this skill, under any circumstance.
- Marked ready (`gh pr ready <PR>`) only as the very last successful step (Step 16) — after every other step, including any `human_review` pause, has actually completed.

### design-sync

Auto-detected only, no override parameter: presence of `.design-sync/config.json` at the worktree root runs Step 15; its absence skips it silently (not a failure, not something to report as missing).

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

## Step 2: Push

`git push -u origin feature/<task_id>_<description>`.

## Step 3: Open the Draft PR (Stub)

`gh pr create --draft --base <target_branch> --head feature/<task_id>_<description> --title "[<task_id>] <description>" --body "<stub — task ID and description only>"`. Fall back to the GitHub MCP tool, then `gh api graphql`'s `createPullRequest` mutation with `draft: true`, only if `gh` itself is unavailable. Record the returned PR number in `progress.md`.

## Step 4: Quick Architecture-Evaluate Gate (Background)

Dispatch a Sonnet subagent: read `architecture-evaluate`'s own "Keeping Docs Up to Date" trigger table plus the recent commit history on `base_branch`, and decide whether Full, Incremental, or no run is warranted. If triggered, invoke `architecture-evaluate` in that mode inside the same subagent call. Returns a structured result — triggered or not, and if triggered, what it changed.

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

## Step 12: complete-review

Invoke `complete-review` for this PR with no `human_review` parameter, ever — it always publishes its findings as a pending GitHub review immediately, its own unchanged default behavior. Findings are never held back from GitHub waiting on this skill's own approval step.

**Checkpoint — `complete-review`:** if `human_review=yes` and `complete-review` not in `human_review_exclude`, show the returned summary (PR URL, each skill's complexity banner, finding counts) to the user and end this turn, waiting for their next message before continuing to Step 13 — the findings are already posted to the PR as a pending review at this point, so the pause is the user's chance to look them over on GitHub (and add their own comments to the same pending review) before `fix-review` runs. Never invent an approval or continue speculatively. Otherwise (`human_review=no`, or `complete-review` excluded) continue immediately to Step 13.

## Step 13: fix-review

Invoke `fix-review` for this PR — it operates inside the already-open worktree (this run's own checkout already matches the PR's branch), so it doesn't need to create one of its own. Never merges or closes the PR.

## Step 14: architecture-evaluate (Incremental, Sonnet)

Spawn a Sonnet subagent to run `architecture-evaluate` in Incremental mode against everything pushed to this branch this run — this is a code-changes-want-docs-reflected sync, not a brownfield re-scan. Classify touched `docs/codebase/` files as new vs. existing (`git status --porcelain -- docs/codebase/`): if every touched file is new, leave them uncommitted for manual review; otherwise commit as one Conventional Commits commit and push.

## Step 15: design-sync (Conditional, Sonnet)

Only if `.design-sync/config.json` exists at the worktree root. Spawn a Sonnet subagent to run `design-sync`'s own list→finalize_plan→write flow. Commit and push whatever it changes, same classification logic as Step 14.

## Step 16: Mark Ready

`gh pr ready <PR>`. Write `progress.md` status `complete`. This is the true end of a fresh delivery run — report the PR URL and a summary of what each step did, and stop.

## Resuming an In-Progress Run

Re-invoking this skill against a `task_id`/feature folder whose `progress.md` shows `in-progress` skips every step already marked done and resumes at the first incomplete one, using the recorded worktree path, branch name, PR number, and gh login rather than re-deriving them. A step that was mid-pause for `human_review` (e.g. `spec` approval pending) resumes by re-showing the same artifact and waiting again — it does not silently auto-approve because time has passed.

See `references/progress-schema.md` for the exact field set `progress.md` tracks and how each step reads/writes it.

## Examples

### Example 1: Fresh delivery run, human_review default

User: `/build-feature base_branch=main task_id=PROJ-42 description="add rate limiting to orders API"`

1. Step 0: no `progress.md` for `PROJ-42-add-rate-limiting` → fresh run
2. Step 1: worktree created at `.claude/worktrees/PROJ-42-add-rate-limiting`, branch renamed to `feature/PROJ-42_add-rate-limiting-to-orders-api`
3. Steps 2–3: pushed, draft PR #512 opened with a stub body
4. Step 4: quick-gate subagent dispatched in the background, finds nothing triggered
5. Step 5: grilling runs live in this conversation — as many rounds as the design tree needs (say, 3), the user answering each round in turn, until the frontier is empty; notes captured, continues straight to Step 6
6. Step 6: `.specs/features/PROJ-42-add-rate-limiting/grilling-session.md` written
7. Step 7a: quick-gate result collected (already returned); Specify writes `spec.md` → `human_review=yes` (default), `spec` not excluded → shown to user, approved
8. Step 7b: Design writes `design.md` (feature sized Large) → shown, approved
9. Step 8: Tasks writes `tasks.md`
10. Step 9: spec artifacts committed and pushed
11. Step 10: Execute runs all tasks, Verifier passes
12. Step 11: Execute's commits pushed; PR #512's description rewritten with problem/what-was-done/test-results
13. Step 12: `complete-review` invoked (no `human_review` param) → posts 9 findings as one pending review on PR #512 immediately → summary shown to user, approved → continues to Step 13
14. Step 13: `fix-review` fixes 6 of 9 findings, replies to and resolves them, leaves 1 answered-only and 2 blocked with reasons
15. Step 14: `architecture-evaluate` Incremental mode updates 2 already-tracked files → committed and pushed
16. Step 15: no `.design-sync/config.json` at the worktree root → skipped silently
17. Step 16: `gh pr ready 512` → `progress.md` marked complete → report: "PR #512 marked ready for review: <url>. 9 findings published, 6 auto-fixed. Worktree left in place."

### Example 2: Fully autonomous run

User: `/build-feature base_branch=main task_id=PROJ-43 description="cache invalidation for job listings" human_review=no`

Same steps, but 7a/7b/12 never pause — Specify and Design proceed immediately without showing anything to the user first, and Step 12's checkpoint doesn't pause either (`complete-review` still publishes its pending review immediately either way — that part never depended on `human_review`), so Step 13 (`fix-review`) starts right after.

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
