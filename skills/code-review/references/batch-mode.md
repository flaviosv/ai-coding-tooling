# Batch Mode

Runs the chain across many PRs in the current repo, one worker per PR per stage, in parallel, reporting each PR as it lands. Two sweeps. Loaded only for a batch entry.

| Sweep | Selects | Stages per PR |
|---|---|---|
| Fix sweep ("fix the PRs I requested changes on", "batch-fix my change requests") | Open PRs where your latest non-reply review is `CHANGES_REQUESTED` | Fix only, scoped to threads you commented on |
| Review sweep ("review my pending PRs", "review PRs waiting on my review") | Open PRs where your review is requested and you have no non-reply review yet | Review → checkpoint → fix |

A request that names both, or neither clearly, → ask which sweep. Never guess.

---

## Shared Rules

- **The root conversation only selects, dispatches, checkpoints, and reports** — it never reads a diff or a thread itself. Every stage runs in a Sonnet worker it dispatches (`subagent_type: general-purpose`, `model: sonnet`), and every worker the root can start at the same moment goes in the **same message**. The one exception is the review sweep with `human_review: false`, where a PR's `submit` and fix worker follow as soon as that PR's review lands rather than waiting for the rest. Workers never dispatch workers.
- **Failures recover per PR, exactly as in a single run** — a failed review, `post`, `submit`, or `deliver` follows [SKILL.md — Stage 2](../SKILL.md#stage-2-checkpoint) and [Stage 3](../SKILL.md#stage-3-fix) for that PR only, without holding up the others.
- Pass the login resolved in Step 1 to every worker, for `--login` on every script call.
- The `Agent` tool has no reasoning-effort parameter, so every worker prompt carries an explicit high-effort instruction (see the `subagent-dispatch` skill).
- Load the `subagent-dispatch` wait protocol before the first dispatch. This mode's difference from its default: each PR reports independently — post its update **as soon as its notification arrives**, never batched. A duplicate or stale notification for an already-reported PR is skipped silently.
- A worker that fails outright is reported plainly in its per-PR update and the final table, and retried once; never imply a review posted or a fix landed when it didn't.
- Track every worker's name against its PR and stage for the rest of the conversation, even after it reports — a later new-commit update routes through that mapping.
- Never hardcode a PR as permanently excluded. An exclusion named for this run ("except #171") applies to this invocation only — say so, and never remember it.
- Every fix worker runs with `isolation: worktree` — concurrent PRs must never fight over one checkout. After each fix report, remove that PR's worktree (`git worktree remove <path>`); it has nothing to resume.
- If this repo's own `CLAUDE.md`/`CLAUDE.local.md`/`AGENTS.md` overrides or extends review for this repo (a project-specific review skill, extra standards, a restricted reviewer role), every worker prompt says to follow it — it takes precedence.

## Step 1: Resolve the Repo and Login

`gh auth status` must succeed — every write goes through `github_review.py`, which needs `gh` — otherwise stop: "No way to reach GitHub — install/authenticate `gh`." Resolve your login (`mcp__github__get_me`, or `gh api user --jq .login`). Parse `owner/repo` from `git remote -v` (`origin`, or the only remote). No git repo or no GitHub remote → ask "Which repo should I check — `owner/repo`?"

## Step 2: Find Candidates

| Sweep | MCP query | `gh` fallback |
|---|---|---|
| Fix | `repo:<owner>/<repo> is:open reviewed-by:<login>` | `gh pr list --repo <owner>/<repo> --search "reviewed-by:<login>" --state open` |
| Review | `repo:<owner>/<repo> is:open review-requested:<login>` | `gh pr list --repo <owner>/<repo> --search "review-requested:<login>" --state open` |

Use `mcp__github__search_pull_requests` with fields `number`, `title`, `html_url`, `state`. "Waiting on your review" means **requested as a reviewer**, never `assignee` — that tracks who owns fixing the PR, not who owes it a review. Drop run-only exclusions. Zero results → report it and stop.

## Step 3: Filter

For each candidate, fetch every review authored by your login and drop the reply artifacts first — [Reply-Review Filter](reply-review-filter.md) has the query, the discriminator, and why REST can't do this. Then:

- **Fix sweep:** qualifies only if your **most recent submitted non-reply** review is `CHANGES_REQUESTED` — a later `APPROVED` or `COMMENTED` review of yours disqualifies it; a `PENDING` draft is ignored. Not the PR's aggregate `reviewDecision`, which reflects every reviewer. A PR with no non-reply review of yours doesn't qualify.
- **Review sweep:** qualifies only with **zero non-reply reviews of any state** by you (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`) — even an old unsubmitted draft disqualifies it.

Counting reply artifacts breaks both silently: a PR this skill already fixed once would drop out of every later fix sweep, and a PR you only replied on would never enter a review sweep. Present the qualifying list (number + title) before dispatching. Nothing qualifies → say so and stop.

## Fix Sweep

Dispatch one fix worker per qualifying PR with `isolation: worktree`, prompt per [Fix Stage — Dispatch](fix-stage.md#dispatch-root-conversation), plus:

- `[code-review][batch-fix:PR-<N>]` prefix; "work at high effort: verify every finding against the actual code before acting on it".
- **Scope filter:** only unresolved threads containing at least one comment authored by `<login>`. A thread whose comments are entirely from other reviewers is out of scope — skip it and leave it untouched, even when it's a valid finding, and list it in `skipped` with the reason "not authored by <login>".
- Jira sync only if the user requested it for this run.

A qualifying PR where you also hold an unsubmitted draft review comes back blocked: `deliver` refuses to reply while that pending review exists. Report it with "submit or discard your pending review on PR #N".

Per-PR update: outcomes by class, commits pushed or not, blocked and unclear items, and the Jira outcome when sync was requested. Final table: every PR, outcomes, commits, and a line for any PR where nothing was pushed and why.

## Review Sweep

1. **Review stage:** dispatch one review worker per qualifying PR — prompt per [SKILL.md — Stage 1](../SKILL.md#stage-1-review), `[code-review][batch-review:PR-<N>]` prefix, the run's `scope`, and "work at high effort: be thorough, verify every finding against the actual diff before including it, prefer precision over volume". Each posts a pending review and returns its compact result.
2. **Checkpoint:**
   - `human_review: true` → wait until every review worker has reported, post one table (PR, URL, finding counts by severity, re-anchored, unpostable), and end the turn. The user reviews on GitHub and replies — "continue" for all, or "continue #12, #14" for a subset. For each PR continued: `submit`, then its fix worker. PRs not continued stay pending and get no fix stage.
   - `human_review: false` → as each review worker reports, `submit` that PR and dispatch its fix worker immediately, without waiting for the others.
3. **Fix stage:** one fix worker per continued PR with `isolation: worktree`, prompt per [Fix Stage — Dispatch](fix-stage.md#dispatch-root-conversation); all threads in scope, whoever wrote them.
4. **Per-PR update** after each stage — review: pending-review URL (or failure reason), finding counts by severity, clusters collapsed, re-anchored, unpostable (`0` when none — a re-anchored or unpostable finding's `file:line` can't be trusted without them), the most important finding in one line; fix: outcomes by class and commits pushed. A **final table** after the last fix: PR, findings, collapsed / re-anchored / unpostable, fixed / rejected / blocked, commits pushed.

"Just review" wording ends every PR's run after the checkpoint and no fix worker runs: with `human_review: true` each review stays pending for the user to submit; with `false` each PR is `submit`ted as its review lands.

## New Commits or Comments After Dispatch

When told, later in the same conversation, that a commit was pushed or a comment posted on a PR this conversation already ran a stage for:

1. Look up that PR's tracked workers. None → not this section; treat it as a new request.
2. `SendMessage` the PR's review worker (fix-sweep PR: its fix worker) to find the commits added since the one its stage was based on (`gh pr view <N> --json commits`).
3. **No new commit** (only a comment) → nothing to delta-review: report that and stop; never re-run a stage.
4. **New commit, reviewed PR:** the review worker reviews only the diff the new commits introduce, not the whole PR, and `post`s the results — `post` appends to this identity's pending review or creates one, and skips exact duplicates. Then run the checkpoint and fix stage for that PR as in the Review Sweep. **New commit, fix-sweep PR:** dispatch a fresh fix worker for that PR.
5. A tracked worker that is unreachable (`ListAgents` doesn't show it, or `SendMessage` errors) → fall back once to a fresh worker for the same delta and say explicitly that continuity was lost.
6. Relay the incremental result immediately — new findings by severity and the review's new total — without waiting on anything else in the batch.
