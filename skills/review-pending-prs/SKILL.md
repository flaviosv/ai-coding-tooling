---
name: review-pending-prs
description: Finds every open GitHub PR assigned to you as a requested reviewer in the current repo that you have not reviewed yet, then reviews all of them at once — one isolated Sonnet subagent per PR, running complete-review at high effort in parallel — and reports each PR's result as soon as its subagent finishes, plus a final summary table. Detects owner/repo from the current git remote; asks for one if the working directory isn't a git repo. Skips any PR that already carries a review (any state) authored by you, so re-running it never double-reviews the same PR. Use when the user says "review my pending PRs", "review all PRs assigned to me", "review pending PRs", "review the PRs I haven't reviewed yet", or invokes /review-pending-prs. Do NOT use to review one specific, already-known PR (use complete-review directly) or to triage feedback on PRs you already reviewed (use fix-review).
metadata:
  author: Flavio Studart
  version: "1.0.0"
---

# Review Pending PRs

Finds every open GitHub PR waiting on your review in the current repo, then fans out one `complete-review` run per PR in parallel — reporting each result as it lands, not after the whole batch finishes.

## Guardrails

- This skill only **selects and delegates** — it never reviews a diff itself and never posts to GitHub directly. All actual review work and posting happens inside `complete-review`, invoked once per qualifying PR.
- "Assigned to you" means **requested as a reviewer** (`review-requested:<you>`), not the `assignee` field — on GitHub, PRs "assigned to you" for review purposes are the ones that list you as a review requester. Do not switch to querying `assignee:<you>` — that field tracks who owns fixing the PR, not who owes it a review, and returns the wrong set.
- A PR "qualifies" only if it has **zero reviews of any state** (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`) authored by your identity. If you already left any review — even an old pending draft never submitted — skip it; re-reviewing it is `fix-review`'s or a manual `complete-review PR #N`'s job, not this skill's.
- Never hardcode a PR number as permanently excluded. If the user names an exclusion for this run only (e.g. "review pending PRs except #171", "skip PR 205"), drop those numbers from the qualifying list for this invocation and say so — do not remember it for future runs.
- Each PR's review runs in its own subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: true`) so all qualifying PRs review concurrently. Launch every subagent's `Agent` call in the same message/turn — never one at a time — so they actually run in parallel instead of queued sequentially.
- The `Agent` tool has no reasoning-effort parameter — compensate by putting an explicit "work at high effort: be thorough, verify every finding against the actual diff before including it" instruction in every subagent's prompt.
- Report each PR's result to the user **as soon as its completion notification arrives** — do not batch and wait for all subagents before saying anything. After the last one finishes, add one final summary table across every PR reviewed this run.
- Never submit, approve, or request-changes on a PR — subagents delegate to `complete-review`, which only ever posts a pending review. This skill inherits that constraint by construction.
- If a subagent's `complete-review` run fails outright (PR not found, no review posted), report that PR's failure plainly in both the per-PR update and the final table — never imply a review was posted when it wasn't.

### Before Starting

- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop before touching GitHub: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- Resolve your own GitHub login first (`mcp__github__get_me`, or `gh api user --jq .login`) — every later query and the "already reviewed by you" check depend on it.

## Step 1: Resolve the repo

Detect `owner/repo` from the current working directory's git remote:

```bash
git remote -v
```

Parse `owner/repo` from the `origin` remote (or the only remote, if `origin` doesn't exist). If the working directory is not a git repository, or has no remote pointing at GitHub, ask the user: "Which repo should I check — `owner/repo`?" Do not guess.

## Step 2: Find candidate PRs

Search open PRs where you're a requested reviewer:

```
mcp__github__search_pull_requests
  query: "repo:<owner>/<repo> is:open review-requested:<your-login>"
  fields: ["number", "title", "html_url", "state"]
```

(or, without GitHub MCP: `gh pr list --repo <owner>/<repo> --search "review-requested:<your-login>" --state open`)

If the invocation named any PR numbers to exclude for this run, drop them from this list now (see Guardrails — never persist an exclusion beyond the current run).

If the search returns zero PRs, report "No open PRs are waiting on your review in `<owner>/<repo>`." and stop — do not proceed to Step 3.

## Step 3: Filter to PRs you haven't reviewed yet

For each candidate PR, check whether any review authored by your login already exists:

```
mcp__github__pull_request_read
  method: get_reviews
  owner: <owner>
  repo: <repo>
  pullNumber: <N>
```

(or `gh api repos/<owner>/<repo>/pulls/<N>/reviews --jq '.[].user.login'`)

A PR qualifies only if none of the returned reviews' `user.login` matches your identity, regardless of state (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED` all count as "already reviewed"). Run this check for every candidate before moving on — it's what makes re-running this skill safe (already-reviewed PRs never get reviewed twice).

Present the qualifying list to the user (PR number + title) before fanning out, so the run is transparent. If nothing qualifies (every candidate already has your review), report that and stop.

## Step 4: Fan out one review per qualifying PR

For every qualifying PR, launch one `Agent` call — all of them in the same message, so they run concurrently:

```
Agent
  description: "Complete-review PR <N>"
  subagent_type: general-purpose
  model: sonnet
  run_in_background: true
  prompt: |
    You are working in the repo <owner>/<repo> (current working directory is already
    this repo's checkout).

    Task: run a complete review of GitHub PR #<N> ("<title>").

    Steps:
    1. Invoke the `complete-review` skill via the Skill tool, targeting PR #<N>
       specifically — do not rely on any prior conversation context, there is none.
    2. If this repo has its own CLAUDE.md/CLAUDE.local.md/AGENTS.md instructions that
       override or extend the generic `code-review`/`tests-code-review` skills for this
       repo (a project-specific review skill, extra Tier-2 standards, a restricted
       reviewer role, etc.), follow them — they take precedence over the generic flow.
    3. Work at high effort: be thorough, verify every finding against the actual diff
       before including it, and prefer precision over volume.
    4. complete-review should end by posting exactly one pending GitHub PR review
       (never submit/approve/request-changes on it) containing every verified finding.

    When done, report back concisely:
    - Whether the pending review was successfully posted to PR #<N> (yes/no, and why
      not if it failed)
    - Total finding count, broken down by severity/category
    - A one-line summary of the most important finding, if any
    - Anything that blocked or limited the review
```

## Step 5: Report as each subagent completes

Each subagent's completion arrives as a separate task notification — do not wait for all of them. As soon as one arrives, post a short per-PR update: the pending-review URL (or the failure reason), the finding count by severity, and the one-line most-important-finding highlight from the subagent's report.

Once every subagent for this run has reported, post one final summary table with all PRs reviewed, their finding counts, and top headline each — plus a one-line reminder that every review was posted as **pending**, not submitted, so nothing goes out until you submit it manually on GitHub.

## Examples

### Example 1: Several PRs pending review

User: "review my pending PRs" (in a checkout of `acme/widgets`)

1. Step 1: `git remote -v` → `acme/widgets`
2. Step 2: `review-requested:me` search returns PRs #10, #11, #12, #14 (open)
3. Step 3: #10 already has a `COMMENTED` review from you → dropped. #11, #12, #14 have none → qualify
4. Step 4: three `Agent` calls launched in one message, one per PR, all `model: sonnet`, `run_in_background: true`
5. Step 5: as each finishes, post its result immediately (e.g. "PR #12 — done. 4 findings, 1 High…"); after all three, post the final summary table

### Example 2: Nothing to do

User: "review pending PRs" (in a checkout with no PRs requesting your review)

1. Step 1: repo resolved
2. Step 2: search returns zero PRs
3. Report: "No open PRs are waiting on your review in `acme/widgets`." — stop, no subagents launched

### Example 3: One-off exclusion

User: "review all pending PRs except #205"

1. Step 1–2: repo resolved, candidates found including #205
2. #205 is dropped from the list for this run only per the user's explicit instruction — not remembered for next time
3. Steps 3–5 proceed normally for the remaining PRs

### Example 4: Not a git repo

User: "review pending PRs" (run from a plain directory, no `.git`)

1. Step 1: no git remote found → ask "Which repo should I check — `owner/repo`?"
2. User replies "acme/widgets" → proceed from Step 2 using that repo
