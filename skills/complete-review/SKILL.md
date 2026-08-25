---
name: complete-review
description: Runs code-review and tests-code-review together against a GitHub PR and publishes every finding as one pending PR review — either for a single named PR (Single PR Mode), or in batch across every open PR waiting on your review that you haven't reviewed yet (Batch Mode). Single PR Mode resolves the PR number from what's already been established in this conversation (e.g. one just opened by build-feature) or asks for it if none is known. Batch Mode detects owner/repo from the current git remote, finds every open PR where you're a requested reviewer with zero reviews from you yet, and fans out one isolated Sonnet subagent per PR at high effort, reporting each PR's result as its subagent finishes plus a final summary table. Every PR's actual review work is delegated to an isolated subagent so large diffs and findings never enter the caller's context, then merged into exactly one pending gh review per PR — never submits, approves, or requests changes. Use when the user says "complete review", "full review", "run a complete review", "review and post to PR", "review my pending PRs", "review all PRs assigned to me", "review pending PRs", "review the PRs I haven't reviewed yet", or invokes /complete-review — if it's unclear which mode a request means, ask. Do NOT use to review only implementation code (use code-review alone) or only tests (use tests-code-review alone) — this skill exists specifically to run both together and publish combined results in one review, whether for one PR or many.
metadata:
  author: Flavio Studart
  version: "1.4.2"
---

# Complete Review

Runs `code-review` and `tests-code-review` against a GitHub PR and publishes every finding from both as a single pending review — no filtering, no submitting. Single PR Mode does this for one named PR; Batch Mode fans it out across every PR waiting on your review.

## Guardrails

- Do NOT invoke `code-review`/`tests-code-review` directly in this conversation — always delegate through a single isolated Sonnet subagent that runs both (concurrently, inside its own turn), per Single PR Mode Step 2. Both skills self-collect a full diff and produce a full findings report; none of that belongs in this conversation's context — only the subagent's final compact summary does.
- Do NOT auto-fix, filter, or withhold findings before publishing — every finding from both skills is posted, unfiltered, every run.
- Do NOT submit, approve, or request-changes on the PR review — pending state only, same as `code-review`/`tests-code-review`'s own GitHub PR Constraints.
- Do NOT create GitHub Issues.
- Do NOT reply to or resolve existing review threads — this skill only publishes the new pending review; triaging prior comments is a separate concern (e.g. `fix-review`, or `build-feature`'s own re-entry mode for an already-delivered PR).
- Each invocation's Step 5 complexity banner (tier, file/line counts, execution mode) is real signal, not noise to discard — the subagent must capture both skills' banners and return them alongside the finding counts, and the report step must relay them to the user. This is informational only: complete-review does not change how it drives `code-review`/`tests-code-review` based on their own complexity determination — each skill already routes its own execution (inline/single-agent/parallel) internally; nothing here overrides that.
- GitHub allows only **one pending (unsubmitted) review per identity per PR at a time**, and there is no API to incrementally add comments to an already-open pending review — a second `POST .../reviews` call while one is pending returns HTTP 422 ("A review cannot be created because a pending review already exists"). If the subagent finds a pending review already on the PR under the same identity `gh` is authenticated as (e.g. left over from an earlier, still-unsubmitted `complete-review` run), it merges into it automatically instead of failing or asking the user what to do. This means the subagent must issue **exactly one** `POST .../reviews` call per PR, after merging both skills' findings (and any carried-over comments) — never one POST per skill. `code-review` and `tests-code-review`'s analysis invocations MAY run concurrently within the subagent precisely because neither one writes to GitHub — only the single merged POST does.
- Never touch a pending review authored by a **different** identity than the one `gh` is authenticated as — that belongs to a human reviewer mid-draft, not to this skill. Only merge into or delete a pending review you can confirm you (the authenticated identity) created.
- On a partial failure (one invocation's analysis returned findings, the other didn't): retry ONLY the failed invocation once, scoped to that skill alone — never re-run the invocation that already returned findings. Issue the single merged POST only after both invocations have resolved (success or final failure) — never post twice, and never post before both have resolved. On a **full failure** (both invocations fail even after their scoped retry): do NOT issue any POST — there is no review to publish. Report both failure reasons and stop; never proceed as if a review was posted.
- If a subagent reports it could not complete (PR not found, auth failure, skill-invocation error): retry once with a fresh subagent (scoped to the failed skill only, on a partial failure — see above). If it fails a second time, stop and report the failure — do not fabricate a finding count or skip a skill.
- Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only ("authenticated" / "not authenticated").
- For environments with more than one `gh` account logged in, see [gh Account Resolution](../../templates/gh-account-resolution.md) for scoping every `gh` call to the correct account — not applied here by default; adopt it only if this skill starts running somewhere that actually hits the multi-account problem.
- **`human_review` parameter (optional, caller-supplied, Single PR Mode only).** Absent (the default) → behavior is exactly as documented above: Step 2 posts immediately, nothing changes for a plain `/complete-review` invocation or any other caller that doesn't pass it. Passed as `true` by a caller (e.g. a delivery skill threading its own review-gate setting through) → Step 2 assembles findings but withholds the POST; see Single PR Mode Step 2's Human Review branch and the [Publish Mode](#publish-mode) section below. This gate does not apply to Batch Mode — its whole premise is an unattended sweep across many PRs, so Batch Mode always publishes immediately regardless of this parameter.

### Batch Mode

- Batch Mode only **selects and delegates** — it never reviews a diff itself in this conversation; every PR's actual review and posting happens inside its own subagent, each running the exact same Single PR Mode flow (and inheriting every guardrail above).
- "Waiting on your review" means **requested as a reviewer** (`review-requested:<you>`), not the `assignee` field — on GitHub, PRs "assigned to you" for review purposes are the ones that list you as a review requester. Do not switch to querying `assignee:<you>` — that field tracks who owns fixing the PR, not who owes it a review, and returns the wrong set.
- A PR qualifies for Batch Mode only if it has **zero reviews of any state** (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED`) authored by your identity. If you already left any review — even an old pending draft never submitted — skip it; re-reviewing it is `fix-review`'s or a manual Single PR Mode run's job, not Batch Mode's.
- Never hardcode a PR number as permanently excluded. If the user names an exclusion for this run only (e.g. "review pending PRs except #171", "skip PR 205"), drop those numbers from the qualifying list for this invocation and say so — do not remember it for future runs.
- Each qualifying PR's review runs in its own subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: true`) so all qualifying PRs review concurrently. Launch every subagent's `Agent` call in the same message/turn — never one at a time — so they actually run in parallel instead of queued sequentially.
- The `Agent` tool has no reasoning-effort parameter — compensate by putting an explicit "work at high effort: be thorough, verify every finding against the actual diff before including it" instruction in every subagent's prompt.
- Report each PR's result to the user **as soon as its completion notification arrives** — do not batch and wait for all subagents before saying anything. After the last one finishes, add one final summary table across every PR reviewed this run.
- If a subagent's run fails outright (PR not found, no review posted), report that PR's failure plainly in both the per-PR update and the final table — never imply a review was posted when it wasn't.
- Track each qualifying PR's subagent name (returned by the `Agent` tool call in Step 4) against its PR number for the rest of this conversation — don't discard the mapping once a subagent reports back in Step 5. It's what a later "a new commit/comment landed on PR #N" update routes through (see New Commits or Comments After Step 4), and that can happen well after the subagent has already finished.

### Before Starting

- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop before touching GitHub: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- Single PR Mode: the resolved PR must exist and be reachable via `gh pr view <PR>`. If it doesn't, stop and report — do not guess a PR number.
- Batch Mode: resolve your own GitHub login first (`mcp__github__get_me`, or `gh api user --jq .login`) — every later query and the "already reviewed by you" check depend on it.

## Step 1: Mode Detection

1. If the request explicitly asks to publish findings already computed and held by an earlier `human_review: true` run (e.g. "publish complete-review findings for PR #N from `<findings_path>`") — **Publish Mode**.
2. If a specific PR number is already established in this conversation (stated explicitly by the user, e.g. "/complete-review PR #123", or produced by an earlier step, e.g. `build-feature` just opened one) — **Single PR Mode**.
3. If the request names no specific PR and instead asks for a sweep across PRs waiting on your review (e.g. "review my pending PRs", "review all PRs assigned to me", "review pending PRs", "review the PRs I haven't reviewed yet") — **Batch Mode**.
4. If neither is clear — no PR number stated, and the request doesn't clearly ask for a batch sweep — ask the user: "Should I review one specific PR (give me the number), or run a batch review of every open PR waiting on your review?" Do not guess.

## Single PR Mode

### Step 1: Resolve the PR

Use a PR number only if it's already established in this conversation — stated explicitly by the user (e.g. "/complete-review PR #123", "run a complete review on PR 456"), or produced by an earlier step in this same conversation (e.g. build-feature just opened one). Do not infer it from git/gh state (current branch, `gh pr view` against the checkout, etc.) — only what's already known from the conversation counts as "declared."

If no PR number is known from the conversation, ask the user for one before continuing. Do not proceed on an assumption.

### Step 2: Review and Publish

Delegate to a single isolated subagent rather than invoking either skill in this conversation — both skills self-collect a full diff and produce a full findings report internally; none of that needs to live in this conversation's context, only the final compact summary does.

1. Spawn one subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: false`) whose prompt instructs it to, within its own conversation:
   a. Issue two concurrent tool calls in the same turn (not sequential awaits) — one invoking `code-review` in **GitHub PR mode, Return-Only Variant**, against the resolved PR number ("review PR #N; return findings only, do not post"), one invoking `tests-code-review` the same way ("review tests on PR #N; return findings only, do not post"). Neither invocation touches GitHub — each only assembles its `comments` array (`path`/`line`/`body` per finding) and returns it, alongside its own Step 5 complexity banner (tier, file/line counts, execution mode) — capture that banner verbatim, it's part of what this subagent reports back. Every finding is included, for every run — do not filter by severity, do not ask again per finding.
   b. Once both invocations have resolved (success or final failure after the scoped retry — see Guardrails): if **both** failed, do **not** issue any `POST` call — there is nothing to post. If **at least one** succeeded, merge both `comments` arrays into one (or use just the succeeded one's, on a partial failure).

      **Human Review branch.** If this invocation was passed `human_review: true`: do not check for or post to any pending review yet. Instead write the merged `comments` array and both banners to `findings_path` — required whenever `human_review: true` is passed; if the caller passed `human_review: true` without a `findings_path`, stop and ask rather than inventing a location. Return a compact result with `awaiting_approval: true`, the finding counts/banners, and the `findings_path` used, and stop — do not proceed to the POST below. The caller shows these to whoever needs to approve them; publishing happens later via [Publish Mode](#publish-mode), not here.

      Otherwise (the default — `human_review` absent or `false`): before posting, check for an existing pending review on this PR authored by the same identity `gh` is authenticated as (`gh api repos/{owner}/{repo}/pulls/{PR}/reviews --jq '.[] | select(.state=="PENDING" and .user.login==$me)'`, with `$me` from `gh api user --jq .login`). If one exists: fetch its comments (`gh api repos/{owner}/{repo}/pulls/{PR}/reviews/{review_id}/comments`), merge them into this run's comment set — drop exact `path`+`line`+`body` duplicates so re-running against an unsubmitted PR doesn't double-post the same finding — then delete the old pending review (`gh api repos/{owner}/{repo}/pulls/{PR}/reviews/{review_id} --method DELETE`). Either way, issue **exactly one** `gh api repos/{owner}/{repo}/pulls/{PR}/reviews --method POST --input payload.json` call with the fully merged set, `event` field omitted (pending state) — this POST must never fire more than once per run, and never with an empty `comments` array. Never stop to ask the user how to handle an existing pending review — merging into it automatically, as just described, is the only way to add to one, since GitHub has no API to incrementally append comments to a pending review in place.
   c. Return **only** one compact result covering both: each skill's total finding count, a per-severity breakdown, and its complexity banner from step 1a. If one skill's invocation ultimately failed, return its failure reason in place of its counts and banner — the other skill's result, if it succeeded, is still reported normally (see Guardrails for the scoped retry rule). If **both** failed, return both failure reasons and no counts. Note whether step 1b found and merged an existing pending review, and how many comments were carried over from it. (Human Review branch: this step doesn't run — Step 2b's own return already happened.)

Running both analysis invocations concurrently inside one subagent conversation is safe precisely because neither writes to GitHub — the one-pending-review-per-PR constraint (see Guardrails) is respected by construction, since only step 1b's single merged POST ever writes to GitHub.

Each skill assembles its findings via its own existing Step 9 / [GitHub PR Mode — Step B2' Return-Only Variant](../../templates/github-pr-review-mode.md), returning its `comments` array to this subagent instead of posting — this produces exactly ONE pending review covering both skills' findings, not two. Only the one compact summary returns to this conversation — not the underlying diffs, findings text, or comments arrays.

### Step 3: Report

Report the PR URL, each skill's complexity banner from Step 2c, and the finding count from each skill (e.g. "code-review — Complex (32 files, 1,840 lines) · Parallel, 4 agents · 7 findings. tests-code-review — Medium (9 test files, 420 lines) · Single agent · 2 findings. 9 findings published as one pending review — submit manually on GitHub when ready."). If Step 2b merged into an existing pending review, say so and how many comments carried over (e.g. "3 comments carried over from an already-pending review, plus 9 new — 12 total"). If Step 2 hit a full failure (both invocations failed, no review posted — see Guardrails), report the PR URL alongside both failure reasons instead — never claim findings were published when they weren't.

## Publish Mode

Entered when the request explicitly asks to publish findings already computed and held by an earlier Single PR Mode run that was passed `human_review: true`. This mode never re-runs `code-review`/`tests-code-review` — it only posts what's already on disk, exactly as held.

### Step 1: Read the Held Findings

Read `findings_path` — given explicitly by the caller, never inferred. Missing or unreadable → stop and report; do not fabricate a findings set or fall back to re-analyzing the PR. The file holds the merged `comments` array and both skills' banners exactly as Single PR Mode Step 2's Human Review branch wrote them.

### Step 2: Publish

Same mechanics as Single PR Mode Step 2b's non-human-review path: check for an existing pending review under the authenticated identity, merge if found (fetch its comments, drop exact `path`+`line`+`body` duplicates, delete the old one), then issue exactly one `gh api .../reviews --method POST` call with the held `comments` array, `event` field omitted. Never re-analyze the PR — the findings posted are exactly what was held, unfiltered, regardless of how long ago Step 1 of Single PR Mode ran.

### Step 3: Report

Same format as Single PR Mode Step 3, using the banners read from `findings_path` in Step 1.

After a successful publish, the caller is responsible for the `findings_path` file's lifecycle (deleting it if it was meant to be transient) — this skill only reads it once and doesn't manage cleanup.

## Batch Mode

Finds every open GitHub PR waiting on your review in the current repo, then fans out one Single PR Mode run per PR in parallel — reporting each result as it lands, not after the whole batch finishes.

### Step 1: Resolve the repo

Detect `owner/repo` from the current working directory's git remote:

```bash
git remote -v
```

Parse `owner/repo` from the `origin` remote (or the only remote, if `origin` doesn't exist). If the working directory is not a git repository, or has no remote pointing at GitHub, ask the user: "Which repo should I check — `owner/repo`?" Do not guess.

### Step 2: Find candidate PRs

Search open PRs where you're a requested reviewer:

```
mcp__github__search_pull_requests
  query: "repo:<owner>/<repo> is:open review-requested:<your-login>"
  fields: ["number", "title", "html_url", "state"]
```

(or, without GitHub MCP: `gh pr list --repo <owner>/<repo> --search "review-requested:<your-login>" --state open`)

If the invocation named any PR numbers to exclude for this run, drop them from this list now (see Guardrails — never persist an exclusion beyond the current run).

If the search returns zero PRs, report "No open PRs are waiting on your review in `<owner>/<repo>`." and stop — do not proceed to Step 3.

### Step 3: Filter to PRs you haven't reviewed yet

For each candidate PR, check whether any review authored by your login already exists:

```
mcp__github__pull_request_read
  method: get_reviews
  owner: <owner>
  repo: <repo>
  pullNumber: <N>
```

(or `gh api repos/<owner>/<repo>/pulls/<N>/reviews --jq '.[].user.login'`)

A PR qualifies only if none of the returned reviews' `user.login` matches your identity, regardless of state (`PENDING`, `COMMENTED`, `APPROVED`, `CHANGES_REQUESTED` all count as "already reviewed"). Run this check for every candidate before moving on — it's what makes re-running Batch Mode safe (already-reviewed PRs never get reviewed twice).

Present the qualifying list to the user (PR number + title) before fanning out, so the run is transparent. If nothing qualifies (every candidate already has your review), report that and stop.

### Step 4: Fan out one review per qualifying PR

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
    1. Invoke the `complete-review` skill via the Skill tool, Single PR Mode, targeting
       PR #<N> specifically — do not rely on any prior conversation context, there is none.
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

Record the name this `Agent` call returns against PR `<N>` right away — that's the mapping Step 5 and New Commits or Comments After Step 4 depend on.

### Step 5: Report as each subagent completes

Each subagent's completion arrives as a separate task notification — do not wait for all of them. As soon as one arrives, post a short per-PR update: the pending-review URL (or the failure reason), the finding count by severity, and the one-line most-important-finding highlight from the subagent's report. If a notification arrives for a PR already reported in this run (a duplicate or stale re-delivery), skip it silently — do not post a second update for the same PR.

Once every subagent for this run has reported, post one final summary table with all PRs reviewed, their finding counts, and top headline each — plus a one-line reminder that every review was posted as **pending**, not submitted, so nothing goes out until you submit it manually on GitHub.

### New Commits or Comments After Step 4

If, later in this same conversation, you're told a new commit was pushed or a new review comment was posted on a PR this Batch Mode run already spawned a subagent for — whether that subagent is still running or already reported back in Step 5 — do NOT spawn a new `Agent` for it. This applies to Batch Mode only; Single PR Mode's Step 2 subagent is synchronous (`run_in_background: false`) and returns before the conversation continues, so there's no long-lived subagent to route a later update to there.

1. Look up that PR's subagent name from the mapping captured in Step 4. If none exists — the PR wasn't part of this conversation's Batch Mode run — this doesn't apply; treat it as an ordinary new request instead (Mode Detection, Single PR Mode).
2. `SendMessage` to that subagent by name — never a fresh `Agent` call — instructing it to:
   a. Determine what's new since it last posted: the commit SHA(s) added after the commit its own pending review was based on (`gh pr view <N> --json commits`, compared against what it last saw).
   b. If nothing new landed as a commit (e.g. only a comment, no new push), there's nothing to delta-review — reply that and stop; do not re-run either skill.
   c. Otherwise, scope `code-review` and `tests-code-review`'s Return-Only Variant to that delta only — the diff introduced by the new commit(s), not the full PR again — same as Single PR Mode Step 2a but with the commit range narrowed to just what's new.
   d. Merge the resulting findings into its own already-posted pending review, following the same merge procedure as Single PR Mode Step 2b (fetch the existing pending review's comments, merge, delete the old one, repost a single new pending review) — same identity, same one-pending-review-per-PR constraint.
   e. Report back the incremental result: how many new findings, by severity, and the new total on the pending review.
3. Relay that subagent's incremental result to the user the same way Step 5 relays a first-pass result — don't wait for anything else in the batch.

If the subagent's name is no longer reachable (`ListAgents` doesn't show it, or `SendMessage` errors), fall back once to a fresh Single PR Mode run scoped to the same delta described in step 2c, and say explicitly that continuity with the original subagent was lost.

## Examples

### Example 1: Single PR Mode, PR number given

User: `/complete-review PR #456`

1. Step 1 (Mode Detection): PR number given inline → Single PR Mode
2. Single PR Mode Step 1: resolved as #456, no need to ask
3. Single PR Mode Step 2: one Sonnet subagent issues two concurrent calls — `code-review`'s and `tests-code-review`'s Return-Only Variant analysis on PR #456. `code-review` returns 7 findings with banner "Complexity: Medium (9 files, 420 lines) · Type: general · Single agent — all 5 dimensions"; `tests-code-review` returns 2 findings with banner "Complexity: Small (3 test files, 90 lines) · Inline review". No pending review already exists on the PR, so the subagent merges the two `comments` arrays and posts a single pending review covering all 9 findings directly; returns one compact result covering both
4. Single PR Mode Step 3: "code-review — Medium (9 files, 420 lines) · Single agent · 7 findings. tests-code-review — Small (3 test files, 90 lines) · Inline · 2 findings. 9 findings published as one pending review on PR #456 — submit manually on GitHub when ready."

### Example 2: Single PR Mode, no PR known yet

User: `/complete-review`

1. Step 1 (Mode Detection): no PR number and no batch language → ask "Should I review one specific PR (give me the number), or run a batch review of every open PR waiting on your review?"
2. User replies "PR #789" → Single PR Mode, resolved as #789, continue to Step 2
3. Steps 2 and 3 proceed as in Example 1

### Example 3: Single PR Mode, invoked mid-flow by another skill (e.g. build-feature)

The invoking skill states the PR number explicitly when delegating (e.g. "run complete-review for PR #128, just opened") — that statement is what makes the PR "already declared in the conversation," so Mode Detection and Step 1 resolve it without asking, and Steps 2–3 proceed exactly as in Example 1.

### Example 4: Single PR Mode, partial failure

User: `/complete-review PR #202`

1. Step 1 (Mode Detection): PR number given → Single PR Mode; Step 1 resolves PR #202
2. Single PR Mode Step 2: `code-review`'s invocation succeeds (5 findings); `tests-code-review`'s invocation fails (skill-invocation error). Retry `tests-code-review` alone, scoped — it succeeds on retry (2 findings). No existing pending review found. Merge both, post one pending review with 7 findings.
3. Single PR Mode Step 3: "7 findings published as one pending review on PR #202 (5 code-review, 2 tests-code-review) — submit manually on GitHub when ready."

### Example 5: Single PR Mode, merging into an already-pending review

User: `/complete-review PR #310` (a prior `complete-review` run on this PR was never submitted on GitHub)

1. Step 1 (Mode Detection): PR number given → Single PR Mode; Step 1 resolves PR #310
2. Single PR Mode Step 2: both invocations succeed (4 findings, 1 finding). Before posting, the subagent finds a pending review already on PR #310 under its own identity, with 6 comments from the earlier run. It fetches those 6 comments, merges them with this run's 5 new ones (no exact duplicates), deletes the old pending review, and posts one new pending review with all 11 comments — no user prompt at any point.
3. Single PR Mode Step 3: "code-review — Small (2 files, 60 lines) · Inline · 4 findings. tests-code-review — Small (1 test file, 30 lines) · Inline · 1 finding. 6 comments carried over from an already-pending review, plus 5 new — 11 total, published as one pending review on PR #310 — submit manually on GitHub when ready."

### Example 6: Batch Mode, several PRs pending review

User: "review my pending PRs" (in a checkout of `acme/widgets`)

1. Step 1 (Mode Detection): batch language, no PR number → Batch Mode
2. Batch Mode Step 1: `git remote -v` → `acme/widgets`
3. Batch Mode Step 2: `review-requested:me` search returns PRs #10, #11, #12, #14 (open)
4. Batch Mode Step 3: #10 already has a `COMMENTED` review from you → dropped. #11, #12, #14 have none → qualify
5. Batch Mode Step 4: three `Agent` calls launched in one message, one per PR, all `model: sonnet`, `run_in_background: true`
6. Batch Mode Step 5: as each finishes, post its result immediately (e.g. "PR #12 — done. 4 findings, 1 High…"); after all three, post the final summary table

### Example 7: Batch Mode, nothing to do

User: "review pending PRs" (in a checkout with no PRs requesting your review)

1. Step 1 (Mode Detection): batch language → Batch Mode
2. Batch Mode Step 1: repo resolved
3. Batch Mode Step 2: search returns zero PRs
4. Report: "No open PRs are waiting on your review in `acme/widgets`." — stop, no subagents launched

### Example 8: Batch Mode, one-off exclusion

User: "review all pending PRs except #205"

1. Step 1 (Mode Detection): batch language → Batch Mode
2. Batch Mode Step 1–2: repo resolved, candidates found including #205
3. #205 is dropped from the list for this run only per the user's explicit instruction — not remembered for next time
4. Batch Mode Steps 3–5 proceed normally for the remaining PRs

### Example 9: Batch Mode, not a git repo

User: "review pending PRs" (run from a plain directory, no `.git`)

1. Step 1 (Mode Detection): batch language → Batch Mode
2. Batch Mode Step 1: no git remote found → ask "Which repo should I check — `owner/repo`?"
3. User replies "acme/widgets" → proceed from Batch Mode Step 2 using that repo

### Example 10: Human Review gate, held then published

Caller (e.g. `build-feature`) invokes: "run complete-review for PR #512, human_review: true, findings_path: .specs/features/PROJ-9-widget/complete-review-findings.json"

1. Step 1 (Mode Detection): PR number given, not a publish request → Single PR Mode
2. Single PR Mode Step 1: resolved as #512
3. Single PR Mode Step 2: both invocations succeed (6 findings, 1 finding). Step 2b's Human Review branch fires: writes the merged 7-comment set plus both banners to `.specs/features/PROJ-9-widget/complete-review-findings.json`, does not check for or post to any pending review. Returns `awaiting_approval: true`, the counts/banners, and the `findings_path`.
4. Single PR Mode Step 3: "7 findings ready for review (6 code-review, 1 tests-code-review) — held at `.specs/features/PROJ-9-widget/complete-review-findings.json`, not yet published."
5. Later, once the caller's human approves: caller invokes "publish complete-review findings for PR #512 from .specs/features/PROJ-9-widget/complete-review-findings.json" → Step 1 (Mode Detection): explicit publish request → Publish Mode
6. Publish Mode Step 1: reads the 7 held comments and both banners from the file
7. Publish Mode Step 2: no existing pending review found → posts one pending review with all 7 comments
8. Publish Mode Step 3: "7 findings published as one pending review on PR #512 (6 code-review, 1 tests-code-review) — submit manually on GitHub when ready."

### Example 11: New commit lands on a PR whose Batch Mode subagent already reported

Continuing Example 6: PR #12's subagent finished and reported 4 findings (1 High). Ten minutes later, in the same conversation, the user says "a new commit just landed on PR #12."

1. PR #12's subagent name, captured in Batch Mode Step 4, is still tracked from this run.
2. `SendMessage` to that subagent (not a new `Agent` call). It runs `gh pr view 12 --json commits`, finds one commit past what it last reviewed, diffs just that commit, runs `code-review` and `tests-code-review`'s Return-Only Variant against the delta only, and finds 1 new finding. It fetches its own already-posted pending review (7 comments), merges the 1 new one in (8 total), deletes the old pending review, reposts the merged one, and reports back.
3. Reported to the user immediately: "PR #12 — 1 new finding from the latest commit, merged into the existing pending review (8 comments total now) — still pending, not submitted."
