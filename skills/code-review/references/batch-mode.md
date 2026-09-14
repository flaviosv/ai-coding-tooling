# Batch Mode

Runs the chain across many PRs in the current repo: one review worker per PR, in parallel, then one fix worker for every PR in the sweep. Two sweeps. Loaded for a batch entry, and by the root for its [New Commits or Comments](#new-commits-or-comments-after-dispatch) section after any PR run.

| Sweep | Selects | Stages per PR |
|---|---|---|
| Fix sweep ("fix the PRs I requested changes on", "batch-fix my change requests") | Open PRs where your latest non-reply review is `CHANGES_REQUESTED` | Fix only, scoped to threads you commented on |
| Review sweep ("review my pending PRs", "review PRs waiting on my review") | Open PRs where your review is requested and you have no non-reply review yet | Review → checkpoint → fix |

A request that names both, or neither clearly, → ask which sweep. Never guess.

---

## Shared Rules

- **The root conversation only selects, dispatches, checkpoints, and reports** — it never reads a diff or a thread itself. Every stage runs in a worker it dispatches (`subagent_type: general-purpose`, `model: sonnet`): one review worker per PR, all in the **same message**, and a single fix worker for every PR the sweep fixes. Workers never dispatch workers.
- **Failures recover per PR, exactly as in a single run** — a failed review, `post`, `submit`, or `deliver` follows [SKILL.md — Stage 2](../SKILL.md#stage-2-checkpoint) and [Stage 3](../SKILL.md#stage-3-fix) for that PR only, without holding up the others. A fix worker that fails outright is retried per [SKILL.md — Guardrails](../SKILL.md#guardrails): the retry covers only the PRs it had not yet delivered.
- Each review worker reports independently — post its PR's update **as soon as its notification arrives**, never batched. The fix worker reports every PR at once; post one update per PR from it. A duplicate or stale notification for an already-reported PR is skipped silently.
- A failure is reported plainly in that PR's update and the final table; never imply a review posted or a fix landed when it didn't.
- Track each review worker's name against its PR, and the fix worker's name against every PR it handled, for the rest of the conversation, even after they report — a later new-commit update routes through that mapping.
- Never hardcode a PR as permanently excluded. An exclusion named for this run ("except #171") applies to this invocation only — say so, and never remember it.
- If this repo's own `CLAUDE.md`/`CLAUDE.local.md`/`AGENTS.md` overrides or extends review for this repo (a project-specific review skill, extra standards, a restricted reviewer role), every worker prompt says to follow it — it takes precedence.

## Step 1: Resolve the Repo

`gh auth status` must succeed — every write goes through `github_review.py`, which needs `gh` — otherwise stop: "No way to reach GitHub — install/authenticate `gh`." Parse `owner/repo` from `git remote -v` (`origin`, or the only remote). No git repo or no GitHub remote → ask "Which repo should I check — `owner/repo`?" Read the session's own login once — the reply-review filter and the fix sweep's scope filter compare authors against it: `gh api graphql -f query='{ viewer { login } }' --jq .data.viewer.login`.

## Step 2: Find Candidates

| Sweep | MCP query | `gh` fallback |
|---|---|---|
| Fix | `repo:<owner>/<repo> is:open reviewed-by:@me` | `gh search prs --repo <owner>/<repo> --state=open --reviewed-by=@me --json number,title,url` |
| Review | `repo:<owner>/<repo> is:open review-requested:@me` | `gh search prs --repo <owner>/<repo> --state=open --review-requested=@me --json number,title,url` |

Use `mcp__github__search_pull_requests` with fields `number`, `title`, `html_url`, `state`. "Waiting on your review" means **requested as a reviewer**, never `assignee` — that tracks who owns fixing the PR, not who owes it a review. Drop run-only exclusions. Zero results → report it and stop.

## Step 3: Filter

For each candidate, fetch every review authored by your login and drop the reply artifacts first — [Reply-Review Filter](reply-review-filter.md) has the query, the discriminator, and why REST can't do this. Then:

- **Fix sweep:** qualifies only if your **most recent submitted non-reply** review is `CHANGES_REQUESTED` — a later `APPROVED` or `COMMENTED` review of yours disqualifies it; a `PENDING` draft is ignored. Not the PR's aggregate `reviewDecision`, which reflects every reviewer. A PR with no non-reply review of yours doesn't qualify.
- **Review sweep:** qualifies only with **zero non-reply reviews of any state** by you (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`) — even an old unsubmitted draft disqualifies it.

Counting reply artifacts breaks both silently: a PR this skill already fixed once would drop out of every later fix sweep, and a PR you only replied on would never enter a review sweep. Present the qualifying list (number + title) before dispatching. Nothing qualifies → say so and stop.

## Fix Sweep

Dispatch **one** fix worker for every qualifying PR, prompt per [Fix Stage — Dispatch](fix-stage.md#dispatch-root-conversation), plus:

- `[code-review][batch-fix]` prefix; every qualifying PR; "work at high effort: verify every finding against the actual code before acting on it".
- **Scope filter:** only unresolved threads containing at least one comment authored by `<login>`. A thread whose comments are entirely from other reviewers is out of scope — skip it and leave it untouched, even when it's a valid finding, and list it in `skipped` with the reason "not authored by <login>".
- Jira sync only if the user requested it for this run.

When the worker reports, one update per PR: outcomes by class, commits pushed or not, blocked and unclear items, and the Jira outcome when sync was requested. Final table: every PR, outcomes, commits, and a line for any PR where nothing was pushed and why.

## Review Sweep

1. **Review stage:** dispatch one review worker per qualifying PR — prompt per [SKILL.md — Stage 1](../SKILL.md#stage-1-review), `[code-review][batch-review:PR-<N>]` prefix, the run's `scope`, and "work at high effort: be thorough, verify every finding against the actual diff before including it, prefer precision over volume". Each posts a pending review and returns its compact result.
2. **Checkpoint:**
   - `human_review: true` → wait until every review worker has reported, post one table (PR, URL, finding counts by severity, re-anchored, `anchor_unverified`, unpostable), and end the turn. The user reviews on GitHub and replies — "continue" for all, or "continue #12, #14" for a subset. `submit` each PR continued. PRs not continued stay pending and get no fix stage.
   - `human_review: false` → as each review worker reports, `submit` that PR without waiting for the others.
3. **Fix stage:** once every continued PR is submitted, one fix worker for all of them, prompt per [Fix Stage — Dispatch](fix-stage.md#dispatch-root-conversation), `[code-review][batch-fix]` prefix; all threads in scope, whoever wrote them.
4. **Per-PR update** — review, as each worker lands: pending-review URL (or failure reason), finding counts by severity, clusters collapsed, re-anchored, `anchor_unverified` and unpostable by `path:line` (`0` when none — those findings' `file:line` can't be trusted without them), the most important finding in one line; fix, when the fix worker reports: outcomes by class and commits pushed, per PR. A **final table** after the fix report: PR, findings, collapsed / re-anchored / `anchor_unverified` / unpostable, fixed / rejected / blocked, commits pushed.

"Just review" wording ends every PR's run after the checkpoint and no fix worker runs: with `human_review: true` each review stays pending for the user to submit; with `false` each PR is `submit`ted as its review lands.

## New Commits or Comments After Dispatch

When told, later in the same conversation, that a commit was pushed or a comment posted on a PR this conversation already ran a stage for:

1. Look up that PR's tracked workers. None → not this section; treat it as a new request.
2. `SendMessage` the PR's review worker (fix-sweep PR: the fix worker) to find the commits added since the one its stage was based on (`gh pr view <N> --json commits`).
3. **No new commit** (only a comment) → nothing to delta-review: report that and stop; never re-run a stage.
4. **New commit, reviewed PR:** the review worker reviews only the diff the new commits introduce, not the whole PR, and `post`s the results — `post` appends to this identity's pending review or creates one, and skips exact duplicates. Then run the checkpoint and fix stage for that PR as in the Review Sweep. **New commit, fix-sweep PR:** dispatch a fresh fix worker for that PR.
5. Relay the incremental result immediately — new findings by severity and the review's new total — without waiting on anything else in the batch.
