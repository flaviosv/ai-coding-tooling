---
name: fix-review
description: Fixes GitHub PR review findings — from complete-review/code-review/tests-code-review or added manually — by fetching every open review thread fresh from GitHub (always the source of truth), reading each thread's full exchange to decide what it's asking for, and committing fixes onto the PR's existing branch — never a new PR. Also handles findings that exist only in the current conversation and were never posted to GitHub — fixes all of them on a branch you name (asks if none known) and leaves commits unpushed. Every fix needs a passing directly-relevant test — no full spec-verification cycle. Anything unclear is reported back unfixed rather than guessed at. Use when the user says "fix review findings", "fix review comments", "triage PR feedback", "resolve review comments", "apply the review fixes", or invokes /fix-review. Do NOT use to generate findings or post a review (use complete-review / code-review / tests-code-review) or for spec planning (use tlc-spec-driven).
metadata:
  author: Flavio Studart
  version: "1.0.0"
---

# Fix Review

Fixes review findings — on GitHub, or in this conversation only — straight on the existing branch. Never posts new findings, never creates a new PR.

## Guardrails

### Scope

- Do NOT create new PRs — always fix on the PR's existing branch (GitHub Mode) or the branch you're given/asked for (Session-Only Mode).
- Do NOT resolve a thread that still carries a live, unanswered question — reply with the answer instead; only resolve once the thread's current ask is a clear recommended action with no open question.
- Do NOT trust a remembered list of what was posted earlier in this conversation — GitHub is the source of truth. Always fetch review threads fresh (GraphQL `reviewThreads`) before acting; a manual comment may have been added since anything was last posted, and this must be picked up.
- When a thread has more than one comment, read the whole exchange to determine what must actually be done — don't act on the first comment in isolation when a later one revises or replaces it, and don't mechanically grab only the last line either; understand how the conversation actually resolved.
- If you're not confident how to fix an item after reading it in full (the thread, in GitHub Mode; the finding, in Session-Only Mode), do NOT guess — report it back unfixed, with the reason, instead of applying a fix you're unsure of.
- Do NOT add explanatory code comments when fixing a finding, unless the code is genuinely non-obvious (complex algorithm, subtle invariant, external constraint) — the fix should read as self-explanatory, same standard as any other change.
- Do NOT implement a fix directly in this conversation — delegate fix-drafting to a Haiku subagent (capped at 4 concurrent) and commit-application to its own subagent call; keep only classification and reply/reject reasoning here.
- Do NOT set `isolation: worktree` on the drafting or commit-application subagents — they must share the current checkout, so a fix lands ready for GitHub Mode's `git push`, or sits ready in the working tree for Session-Only Mode's local commits.
- Every fix must be covered by a test — if the change isn't already covered, write one (follow this project's `tests` skill conventions for how to write it well), then run only that fix's directly relevant test(s) to confirm it passes. Do NOT invoke tlc-spec-driven's full Verifier or gate-check cycle for this — that's unnecessary weight for a fix-triage pass; a straightforward relevant-test run is the bar here.
- Use the PR's own title/body/diff to understand what a finding is actually asking for — not just the isolated comment text on its own.
- If a tlc-spec-driven feature is already active for this work (this skill was invoked by `ship-spec`, or the user names one): write the audit-trail plan to `.specs/features/<feature>/fix-code-review.md`, same as tlc-spec-driven's own conventions expect. If no spec feature is active: do NOT create anything under `.specs/` — keep the classified plan in this conversation only; the staleness re-check (GitHub Mode step 4) still runs against that in-conversation record, just without a file backing it.
- GitHub Mode: never act on a review that's still `PENDING` (unsubmitted) — stop and tell the user to submit it first.
- Session-Only Mode: never push automatically — commit locally only and tell the user what's ready to push.
- Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.
- If a drafted change no longer matches current file state at commit time (GitHub Mode's staleness re-check, or an equivalent conflict in Session-Only Mode): mark the item blocked instead of force-applying it.
- If a drafting or commit-application subagent reports it could not complete (a blocker it can't resolve): retry once with a fresh subagent. If it fails a second time, stop and report the failure — do not fabricate a result or mark an item resolved on a failed fix.

### Before Starting

- GitHub Mode: `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- Session-Only Mode: `git status --porcelain` must be clean before switching to the target branch, if it isn't already checked out. Dirty → stop and report the exact output (which files, staged or not) — do not stash, commit, discard, or otherwise touch them yourself; wait for the user to decide.

## Step 1: Mode Detection

1. Resolve a PR number the same way `complete-review` does: only from what's already established in this conversation (stated explicitly, or produced by an earlier step, e.g. `complete-review` or `ship-spec` opening/reviewing one). Do not infer it from git/gh branch state.
2. If a PR is known: check whether it has at least one **submitted** (non-pending) review with comments (`gh pr view <PR> --json reviews`, or the GraphQL query in [GitHub Delivery Mechanics](references/github-delivery.md)).
   - At least one submitted review exists → **GitHub Mode**.
   - The only review found is still `PENDING` → stop and tell the user: "Your review is still pending on GitHub — submit it before asking me to fix findings."
   - No review exists yet at all → fall through to **Session-Only Mode**.
3. If no PR is known at all → **Session-Only Mode** — the findings to fix exist only in this conversation.

## GitHub Mode

Findings live on GitHub — this is the mode `ship-spec`'s own comment-triage round runs.

1. Fetch open review threads via GraphQL `reviewThreads` (see [GitHub Delivery Mechanics](references/github-delivery.md)). Skip threads already `isResolved: true`. Skip any thread whose review is still `PENDING`. If the fetched thread count hits the query's page-size cap (100), note in the final report that additional unresolved threads may exist beyond what was fetched.
2. For each unresolved, published thread, read the full exchange — every comment on it, in order, not just the first or the last — and classify what it's actually asking for right now:
   - **auto-fix** — no user comment on the thread at all. Fix it directly, no exceptions.
   - **answer-only** — the thread's current ask, once you've read the whole exchange, is a question. Reply with the answer; don't fix unless the answer implies a change. Leave the thread unresolved.
   - **apply-as-directed** — the thread's current direction suggests an approach, and it validates (confirms/directs the fix, or holds up as sound on inspection). Fix it as directed.
   - **pushback** — the thread's current direction suggests an approach that doesn't validate. Reply rejecting it with your reasoning (and the approach you're taking instead, if any). Leave the thread unresolved.
   - **unclear** — even after reading the full thread, you're not confident what it's actually asking for. Do not fix or reply — record it for the report (thread id, `path:line`, why it's unclear) so the user can clarify.
   - **standalone comment, not anchored to a finding** — same apply-as-directed / pushback / unclear treatment as above.
3. If a tlc-spec-driven feature is active for this work, write the classified plan to `.specs/features/<feature>/fix-code-review.md` — a flat list grouped `## Parallel` (independent items, no two touching the same file) and `## Sequential` (items sharing a file, encounter order); each entry has thread id, classification, `path:line`, and a one-line fix/reply direction. If no feature is active, keep the same classified plan in this conversation only — do not write it to `.specs/`. Either way: **unclear** items are recorded for the report but never enter the draft/commit steps. If zero threads were found, stop here.
4. Immediately after — no approval gate; invoking GitHub Mode is itself the go-ahead — refetch the same `reviewThreads` query, diff against the plan just made, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch.
5. For the auto-fix and apply-as-directed items surviving step 4: draft fixes concurrently, capped at 4 subagents at a time (`Agent` tool, `agentType: general-purpose`, `model: claude-haiku-4-5-20251001`, `run_in_background: false`) — one per item in the `## Parallel` bucket; `## Sequential`-bucket items one at a time, in order, same subagent shape. Each drafting subagent uses the PR's own title/body/diff for context, performs no file edits or git operations, and returns its proposed change — including the test it wrote or updated to cover the fix — or a blocker/unclear reason if it can't confidently complete. Apply and commit each via its own subagent call, one item at a time — never two commits concurrently — following Conventional Commits, running only that item's own directly relevant test(s) to validate (no full gate/verify cycle). If a drafted change no longer matches current file state at commit time, mark it blocked instead of force-applying. For answer-only, pushback, or unclear items: no commit, no drafting subagent — compose the reply (or the "here's what's unclear" note) directly in this conversation, on the default model.
6. Reply on the thread, or resolve it silently, per its classification: **auto-fix** and **apply-as-directed** — resolve via GraphQL `resolveReviewThread` (see [GitHub Delivery Mechanics](references/github-delivery.md)), no reply comment posted — the fix is the answer. **pushback** — reply with the rejection reasoning (and the approach taken instead, if any), then resolve. **answer-only** — reply with the answer only; leave unresolved, only the user resolves it once satisfied. **unclear** — post a clarifying reply only if you have a specific question; leave unresolved either way.
7. If any commits were made: `git push` to the existing branch — this updates the same open PR, never a new one.
8. Report: threads processed by classification (including unclear and blocked items, with reasons), commits pushed, and — if step 1 hit the page-size cap — a note that additional unresolved threads may exist beyond what was fetched.

## Session-Only Mode

Findings exist only in this conversation — nothing has been posted to GitHub.

1. Resolve the target branch the same conversation-context-only way as the PR number above: only from what's already established (the user named it, or it's the branch a prior review ran against). If none is known, ask which branch to fix on before continuing.
2. If the resolved branch isn't currently checked out, check it out (subject to the clean-tree guard in Before Starting).
3. Take every finding already known from this conversation and fix all of them, unfiltered — their presence in the conversation is itself the go-ahead, same as a published GitHub review comment is in GitHub Mode.
4. Draft and apply fixes with the same mechanics as GitHub Mode step 5 (Haiku subagents capped at 4, one commit at a time, Conventional Commits, test coverage required, unclear items reported unfixed rather than guessed at) — minus anything about threads, since there are none here.
5. Do NOT push. Commits stay local for the user to review and push themselves.
6. Report: findings fixed (with the commit list), any left unfixed and why (unclear, or a blocker), and a reminder that nothing was pushed.

## Examples

### Example 1: GitHub Mode, invoked by ship-spec

`ship-spec`'s Comment-Triage Mode invokes `fix-review` for PR #128, stating the active feature (`PROJ-42_rate-limiting`).

1. Step 1: PR #128 known, has a submitted review → GitHub Mode
2. Fetch 6 threads: 1 still `PENDING` on a newer review → skipped; 5 published and unresolved. Reading each in full: Thread 1 (`tests-code-review` finding, no comment) → **auto-fix**; Thread 2 (`code-review` finding, no comment) → **auto-fix**; Thread 3 ("why didn't you use a token bucket here?") → **answer-only**; Thread 4 (`code-review` finding, then "yes, fix this") → **apply-as-directed**; Thread 5 (`code-review` finding, then a weaker suggested approach that doesn't hold up) → **pushback**
3. Feature is active → write `fix-code-review.md`: `## Parallel` — T1, T2, T4 (no two share a file); `## Sequential` — none. T3 and T5 listed for audit, excluded from drafting.
4. Re-fetch: nothing changed — all 5 items proceed
5. Draft T1, T2, T4 concurrently (3 Haiku subagents), each including a test for its fix. Apply + commit one at a time: `test(orders): cover rate-limit edge case` (T1), `refactor(orders): extract rate-limit check into helper` (T2), then T4's directed fix — each running only its own relevant test first.
6. Resolve T1, T2, T4 silently. Reply to T3 with the sliding-window tradeoff explanation, left unresolved. Reply to T5 with the rejection reasoning, then resolve.
7. Push (3 new commits)
8. Report: "5 threads processed (3 fixed, 1 rejected, 1 answered and left open), 1 pending thread left untouched."

### Example 2: Session-Only Mode

User ran `code-review` locally (no PR involved), got 4 findings, then said "fix these on branch `feature/cleanup`."

1. Step 1: no PR known → Session-Only Mode
2. Branch `feature/cleanup` named explicitly → resolved without asking; checked out (tree was clean)
3. All 4 findings taken, unfiltered
4. Draft and fix 3 of them (Haiku subagents, each with its own test); the 4th is genuinely ambiguous about which of two valid approaches the user wants — reported unclear instead of guessed at. 3 commits made, one at a time, each with its relevant test passing.
5. No push.
6. Report: "3 of 4 findings fixed and committed locally on `feature/cleanup` (not pushed). 1 left unfixed — unclear whether to use a cache or a recompute for the derived field; let me know which and I'll finish it."
