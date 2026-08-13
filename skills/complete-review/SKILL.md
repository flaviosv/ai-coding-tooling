---
name: complete-review
description: Runs code-review and tests-code-review together against a GitHub PR and publishes every finding as one pending PR review. Resolves the PR number from what's already been established in this conversation (e.g. one just opened by ship-spec) or asks for it if none is known. Delegates the actual review work to an isolated subagent so large diffs and findings never enter the caller's context, then merges both skills' findings into exactly one pending gh review — never submits, approves, or requests changes on it. Use when the user says "complete review", "full review", "run a complete review", "review and post to PR", or invokes /complete-review. Do NOT use to review only implementation code (use code-review alone) or only tests (use tests-code-review alone) — this skill exists specifically to run both together and publish combined results in one review.
metadata:
  author: Flavio Studart
  version: "1.0.0"
---

# Complete Review

Runs `code-review` and `tests-code-review` against a GitHub PR and publishes every finding from both as a single pending review — no filtering, no submitting.

## Guardrails

- Do NOT invoke `code-review`/`tests-code-review` directly in this conversation — always delegate through a single isolated Sonnet subagent that runs both (concurrently, inside its own turn), per Step 2. Both skills self-collect a full diff and produce a full findings report; none of that belongs in this conversation's context — only the subagent's final compact summary does.
- Do NOT auto-fix, filter, or withhold findings before publishing — every finding from both skills is posted, unfiltered, every run.
- Do NOT submit, approve, or request-changes on the PR review — pending state only, same as `code-review`/`tests-code-review`'s own GitHub PR Constraints.
- Do NOT create GitHub Issues.
- Do NOT reply to or resolve existing review threads — this skill only publishes the new pending review; triaging prior comments is a separate concern (e.g. ship-spec's own comment-triage mode).
- GitHub allows only **one pending (unsubmitted) review per identity per PR at a time** — a second `POST .../reviews` call while one is already pending returns HTTP 422 ("A review cannot be created because a pending review already exists"), and there is no API to incrementally add comments to an already-open pending review. This means Step 2's subagent must issue **exactly one** `POST .../reviews` call per run, after merging both skills' findings — never one POST per skill. `code-review` and `tests-code-review`'s analysis invocations MAY run concurrently within the subagent precisely because neither one writes to GitHub — only the single merged POST does.
- On a partial failure (one invocation's analysis returned findings, the other didn't) within Step 2's subagent: retry ONLY the failed invocation once, scoped to that skill alone — never re-run the invocation that already returned findings. Issue the single merged POST only after both invocations have resolved (success or final failure) — never post twice, and never post before both have resolved. On a **full failure** (both invocations fail even after their scoped retry): do NOT issue any POST — there is no review to publish. Report both failure reasons and stop; never proceed as if a review was posted.
- If the Step 2 subagent reports it could not complete (PR not found, auth failure, skill-invocation error): retry once with a fresh subagent (scoped to the failed skill only, on a partial failure — see above). If it fails a second time, stop and report the failure — do not fabricate a finding count or skip a skill.
- Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only ("authenticated" / "not authenticated").

### Before Starting

- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop before touching GitHub: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- The resolved PR (see Step 1) must exist and be reachable via `gh pr view <PR>`. If it doesn't, stop and report — do not guess a PR number.

## Step 1: Resolve the PR

Use a PR number only if it's already established in this conversation — stated explicitly by the user (e.g. "/complete-review PR #123", "run a complete review on PR 456"), or produced by an earlier step in this same conversation (e.g. ship-spec's Step 5 just opened one). Do not infer it from git/gh state (current branch, `gh pr view` against the checkout, etc.) — only what's already known from the conversation counts as "declared."

If no PR number is known from the conversation, ask the user for one before continuing. Do not proceed on an assumption.

## Step 2: Review and Publish

Delegate to a single isolated subagent rather than invoking either skill in this conversation — both skills self-collect a full diff and produce a full findings report internally; none of that needs to live in this conversation's context, only the final compact summary does.

1. Spawn one subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: false`) whose prompt instructs it to, within its own conversation:
   a. Issue two concurrent tool calls in the same turn (not sequential awaits) — one invoking `code-review` in **GitHub PR mode, Return-Only Variant**, against the resolved PR number ("review PR #N; return findings only, do not post"), one invoking `tests-code-review` the same way ("review tests on PR #N; return findings only, do not post"). Neither invocation touches GitHub — each only assembles its `comments` array (`path`/`line`/`body` per finding) and returns it. Every finding is included, for every run — do not filter by severity, do not ask again per finding.
   b. Once both invocations have resolved (success or final failure after the scoped retry — see Guardrails): if **both** failed, do **not** issue any `POST` call — there is nothing to post. If **at least one** succeeded, merge both `comments` arrays into one (or use just the succeeded one's, on a partial failure) and issue **exactly one** `gh api repos/{owner}/{repo}/pulls/{PR}/reviews --method POST --input payload.json` call, `event` field omitted (pending state) — GitHub allows only one pending review per identity per PR at a time (see Guardrails), so this POST must never fire more than once per run, and never with an empty `comments` array.
   c. Return **only** one compact result covering both: each skill's total finding count and a per-severity breakdown. If one skill's invocation ultimately failed, return its failure reason in place of its counts — the other skill's result, if it succeeded, is still reported normally (see Guardrails for the scoped retry rule). If **both** failed, return both failure reasons and no counts.

Running both analysis invocations concurrently inside one subagent conversation is safe precisely because neither writes to GitHub — the one-pending-review-per-PR constraint (see Guardrails) is respected by construction, since only step 1b's single merged POST ever writes to GitHub.

Each skill assembles its findings via its own existing Step 9 / [GitHub PR Mode — Step B2' Return-Only Variant](../../templates/github-pr-review-mode.md), returning its `comments` array to this subagent instead of posting — this produces exactly ONE pending review covering both skills' findings, not two. Only the one compact summary returns to this conversation — not the underlying diffs, findings text, or comments arrays.

## Step 3: Report

Report the PR URL, and the finding count from each skill (e.g. "12 findings from code-review, 4 from tests-code-review, all posted as pending review comments — submit manually on GitHub when ready"). If Step 2 hit a full failure (both invocations failed, no review posted — see Guardrails), report the PR URL alongside both failure reasons instead — never claim findings were published when they weren't.

## Examples

### Example 1: Standalone invocation with a PR number given

User: `/complete-review PR #456`

1. Step 1: PR number given inline → resolved as #456, no need to ask
2. Step 2: one Sonnet subagent issues two concurrent calls — `code-review`'s and `tests-code-review`'s Return-Only Variant analysis on PR #456. Once both return (7 findings, 2 findings), the subagent merges them into one `comments` array and posts a single pending review covering all 9 findings; returns one compact result covering both
3. Step 3: "9 findings published as one pending review on PR #456 (7 code-review, 2 tests-code-review) — submit manually on GitHub when ready."

### Example 2: No PR known yet

User: `/complete-review`

1. Step 1: no PR number appears anywhere earlier in the conversation → ask "Which PR should I review?"
2. User replies "PR #789" → resolved as #789, continue to Step 2
3. Step 2 and 3 proceed as in Example 1

### Example 3: Invoked mid-flow by another skill (e.g. ship-spec)

The invoking skill states the PR number explicitly when delegating (e.g. "run complete-review for PR #128, just opened") — that statement is what makes the PR "already declared in the conversation," so Step 1 resolves it without asking, and Steps 2–3 proceed exactly as in Example 1.

### Example 4: Partial failure

User: `/complete-review PR #202`

1. Step 1: PR #202 resolved from the user's message
2. Step 2: `code-review`'s invocation succeeds (5 findings); `tests-code-review`'s invocation fails (skill-invocation error). Retry `tests-code-review` alone, scoped — it succeeds on retry (2 findings). Merge both, post one pending review with 7 findings.
3. Step 3: "7 findings published as one pending review on PR #202 (5 code-review, 2 tests-code-review) — submit manually on GitHub when ready."
