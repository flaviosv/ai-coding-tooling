# Batch Mode

Finds every open PR in the current repo waiting on your review that you haven't reviewed yet, and fans out one `post: true` review per PR in parallel — reporting each result as it lands. Loaded only for a Batch target.

---

## Rules

- Batch Mode only **selects and delegates** — it never reviews a diff in this conversation. Every PR's review and posting happens inside its own subagent, which runs this skill's PR flow and inherits every guardrail.
- **Batch Mode always posts** — each PR's full report lives in its subagent and never reaches this conversation, so a report-only sweep would discard the reports. `scope` still applies and is passed through to every subagent.
- "Waiting on your review" means **requested as a reviewer** (`review-requested:<you>`), never the `assignee` field — that tracks who owns fixing the PR, not who owes it a review, and returns the wrong set.
- A PR qualifies only with **zero non-reply reviews of any state** (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`) by your identity. Any real review — even an old unsubmitted pending draft — disqualifies it; re-reviewing is `fix-review`'s or a manual PR run's job. The single-comment reviews GitHub creates for each of your thread replies are not reviews for this purpose ([Reply-Review Filter](../../../templates/reply-review-filter.md)) — counting them would hide a PR you never reviewed from this mode permanently, on the strength of one reply.
- Never hardcode a PR as permanently excluded. An exclusion named for this run ("except #171", "skip PR 205") applies to this invocation only — say so, and never remember it.
- The `Agent` tool has no reasoning-effort parameter, so every subagent's prompt carries an explicit high-effort instruction — the only effort mechanism available (see the `subagent-dispatch` skill).
- Load the `subagent-dispatch` wait protocol before the first dispatch. This mode's difference from the protocol's default: each PR reports independently — report each result **as soon as its notification arrives**, never batch them.
- A subagent that fails outright (PR not found, no review posted) is reported plainly in both the per-PR update and the final table — never imply a review was posted.
- Track each subagent's name against its PR number for the rest of the conversation, even after it reports — a later new-commit update routes through that mapping.

## Step 1: Resolve the Repo

`gh auth status` must succeed, or GitHub MCP tools must be available — neither → stop before touching GitHub: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server." Resolve your GitHub login (`mcp__github__get_me`, or `gh api user --jq .login`) — every later query depends on it. Then parse `owner/repo` from `git remote -v` (`origin`, or the only remote). No git repo, or no GitHub remote → ask "Which repo should I check — `owner/repo`?" Never guess.

## Step 2: Find Candidate PRs

```
mcp__github__search_pull_requests
  query: "repo:<owner>/<repo> is:open review-requested:<your-login>"
  fields: ["number", "title", "html_url", "state"]
```

Without GitHub MCP: `gh pr list --repo <owner>/<repo> --search "review-requested:<your-login>" --state open`.

Drop any PR excluded for this run. Zero results → report "No open PRs are waiting on your review in `<owner>/<repo>`." and stop.

## Step 3: Filter to PRs You Haven't Reviewed

For each candidate, fetch every review authored by your login and drop the reply artifacts before judging — the query, discriminator, and why REST can't do this are in [Reply-Review Filter](../../../templates/reply-review-filter.md). Run the check for every candidate: it is what makes re-running Batch Mode safe.

Present the qualifying list (number + title) before fanning out. Nothing qualifies → say so and stop.

## Step 4: Fan Out

One `Agent` call per qualifying PR, **all in the same message** so they run concurrently:

```
Agent
  description: "Code-review PR <N>"
  subagent_type: general-purpose
  model: sonnet
  prompt: |
    [code-review][batch:PR-<N>] You are working in the repo <owner>/<repo> (the current
    working directory is already this repo's checkout).

    Task: review GitHub PR #<N> ("<title>") with the `code-review` skill, invoked via the
    Skill tool with: PR #<N>, scope: <scope>, post: true. There is no prior conversation
    context to rely on.

    - If this repo's own CLAUDE.md/CLAUDE.local.md/AGENTS.md overrides or extends generic
      review for this repo (a project-specific review skill, extra standards, a restricted
      reviewer role), follow it — it takes precedence.
    - Work at high effort: be thorough, verify every finding against the actual diff before
      including it, prefer precision over volume.
    - You are a subagent: run the review inline and dispatch no publishing worker.
    - When waiting on a dispatched agent, end your turn with one line of plain text and no
      tool call — never sleep, echo, or poll.

    Done when exactly one pending review (never submitted) on PR #<N> holds every finding.
    Report back concisely, and nothing else:
    - pending review posted yes/no (and why not)
    - finding counts by scope and severity; clusters collapsed, re-anchored, unpostable
    - one line on the most important finding
    - anything that blocked or limited the review
```

Record each returned name against its PR immediately.

## Step 5: Report as Each Completes

As each notification arrives, post a short per-PR update: pending-review URL (or failure reason), finding counts by severity, the collapsed / re-anchored / unpostable counts (`0` when none — a re-anchored or unpostable finding's `file:line` can't be trusted without them), the most-important-finding line. A duplicate or stale notification for an already-reported PR is skipped silently.

After the last one, post a summary table of every PR reviewed — finding counts, re-anchored and unpostable counts, and headline each — plus a reminder that every review is **pending**, nothing goes out until submitted on GitHub.

## New Commits or Comments After Dispatch

When told, later in the same conversation, that a commit was pushed or a comment posted on a PR that already has a tracked subagent (running or finished) — from this mode or a single-PR publishing worker — never spawn a new `Agent`:

1. Look up the PR's subagent name. None tracked → this doesn't apply; treat it as a new request.
2. `SendMessage` to it by name, instructing it to:
   a. Find the commits added since the one its pending review was based on (`gh pr view <N> --json commits`).
   b. No new commit (only a comment) → reply that and stop; never re-run the review.
   c. Otherwise review only that delta — the diff the new commits introduce, same scope — not the whole PR.
   d. Merge the new findings into its own pending review via [Posting Mechanics](posting-mechanics.md): fetch its id and existing comments (paginated), skip exact duplicates, append only what's new. No delete, no repost.
   e. Report new findings by severity and the review's new total.
3. Relay that incremental result immediately, without waiting on anything else in the batch.

If the subagent is unreachable (`ListAgents` doesn't show it, or `SendMessage` errors), fall back once to a fresh `post: true` PR run scoped to the same delta, and say explicitly that continuity was lost.
