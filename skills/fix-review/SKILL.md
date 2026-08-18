---
name: fix-review
description: Fixes GitHub PR review findings — from complete-review/code-review/tests-code-review or added manually — by fetching every open review thread fresh from GitHub (always the source of truth), reading each thread's full exchange to decide what it's actually asking for and whether it holds up against the current code, and committing fixes onto the PR's existing branch — never a new PR. A comment or suggested approach that doesn't hold up is rejected with reasoning instead of applied by rote, even when nobody pushed back on it. Also handles findings that exist only in the current conversation and were never posted to GitHub — fixes all of them on a branch you name (asks if none known) and leaves commits unpushed. A third mode batches this across every open PR where you, as reviewer, requested changes — one isolated Sonnet subagent per PR, each fixing only your own comments, fanned out in parallel with results reported as each lands. Every fix is evaluated for test impact — coverage added, updated, or removed as the fix actually warrants, never left to drift incidentally — and validated with a passing directly-relevant test, no full spec-verification cycle. Anything unclear is reported back unfixed rather than guessed at. Use when the user says "fix review findings", "fix review comments", "triage PR feedback", "resolve review comments", "apply the review fixes", "fix the PRs I requested changes on", "batch-fix my change requests", or invokes /fix-review — if it's unclear which mode a request means, ask. Do NOT use to generate findings or post a review (use complete-review / code-review / tests-code-review) or for spec planning (use tlc-spec-driven).
metadata:
  author: Flavio Studart
  version: "1.2.0"
---

# Fix Review

Fixes review findings — on GitHub, or in this conversation only — straight on the existing branch. Never posts new findings, never creates a new PR. Batch Mode fans this out across every PR where you requested changes as a reviewer.

## Guardrails

### Scope

- Do NOT create new PRs — always fix on the PR's existing branch (GitHub Mode, and each PR fixed under Batch Mode) or the branch you're given/asked for (Session-Only Mode).
- Do NOT resolve a thread that still carries a live, unanswered question — reply with the answer instead; only resolve once the thread's current ask is a clear recommended action with no open question.
- Do NOT trust a remembered list of what was posted earlier in this conversation — GitHub is the source of truth. Always fetch review threads fresh (GraphQL `reviewThreads`) before acting; a manual comment may have been added since anything was last posted, and this must be picked up.
- When a thread has more than one comment, read the whole exchange to determine what must actually be done — don't act on the first comment in isolation when a later one revises or replaces it, and don't mechanically grab only the last line either; understand how the conversation actually resolved.
- If you're not confident how to fix an item after reading it in full (the thread, in GitHub Mode; the finding, in Session-Only Mode), do NOT guess — report it back unfixed, with the reason, instead of applying a fix you're unsure of.
- Never fix a finding just because it exists — a comment on GitHub, or a finding stated in this conversation, is a claim to evaluate against the actual current code, not a mandate to act on unread. This applies to every item, not only the ones with a suggested direction to weigh (apply-as-directed/pushback): an **auto-fix** item (no reply on it) still needs its underlying claim checked against the real diff before you touch anything — silence from other reviewers isn't evidence it's correct, only that nobody happened to object. If an item doesn't actually hold up (stale, based on a misread of the diff, already addressed, or simply wrong), give it the same treatment as an unsound suggested approach: explain why, on the thread if one exists, and leave it unfixed rather than mechanically applying it. This is what keeps fix coverage — including the test additions/updates/removals below — grounded in findings that are actually real, instead of propagating every claim at face value.
- Do NOT add explanatory code comments when fixing a finding, unless the code is genuinely non-obvious (complex algorithm, subtle invariant, external constraint) — the fix should read as self-explanatory, same standard as any other change.
- Do NOT implement a fix directly in this conversation — delegate fix-drafting to a Haiku subagent (capped at 4 concurrent) and commit-application to its own subagent call; keep only classification and reply/reject reasoning here.
- Do NOT set `isolation: worktree` on the drafting or commit-application subagents — they must share the current checkout, so a fix lands ready for GitHub Mode's `git push`, or sits ready in the working tree for Session-Only Mode's local commits.
- Every fix must be evaluated for test impact, not just coverage-added: write a new test if the change isn't already covered (follow this project's `tests` skill conventions for how to write it well); update an existing test whose assertions the fix invalidates; remove a test outright only when it was asserting the very behavior the fix corrects (e.g. it locked in the bug), and replace it with a test of the corrected behavior whenever the fix leaves anything worth covering. Coverage should move up or down only as a direct, stated consequence of the fix — never let it drift incidentally; a removal with nothing added back to replace it needs a one-line reason in the report. Then run only that fix's directly relevant test(s) to confirm it passes. Do NOT invoke tlc-spec-driven's full Verifier or gate-check cycle for this — that's unnecessary weight for a fix-triage pass; a straightforward relevant-test run is the bar here.
- Use the PR's own title/body/diff to understand what a finding is actually asking for — not just the isolated comment text on its own.
- If a tlc-spec-driven feature is already active for this work (this skill was invoked by `ship-spec`, or the user names one): write the audit-trail plan to `.specs/features/<feature>/fix-code-review.md`, same as tlc-spec-driven's own conventions expect. If no spec feature is active: do NOT create anything under `.specs/` — keep the classified plan in this conversation only; the staleness re-check (GitHub Mode step 4) still runs against that in-conversation record, just without a file backing it.
- GitHub Mode: never act on a review that's still `PENDING` (unsubmitted) — stop and tell the user to submit it first.
- Session-Only Mode: never push automatically — commit locally only and tell the user what's ready to push.
- Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.
- If a drafted change no longer matches current file state at commit time (GitHub Mode's staleness re-check, or an equivalent conflict in Session-Only Mode): mark the item blocked instead of force-applying it.
- If a drafting or commit-application subagent reports it could not complete (a blocker it can't resolve): retry once with a fresh subagent. If it fails a second time, stop and report the failure — do not fabricate a result or mark an item resolved on a failed fix.

### Batch Mode

- Batch Mode only **selects and delegates** — it never reads a thread or commits a fix itself in this conversation; every PR's actual fix work happens inside its own subagent, running the exact same GitHub Mode flow above (and inheriting every Scope guardrail above, including the test-coverage and no-worktree-isolation rules).
- "Requested changes" means **your own most recently submitted review** on that PR has state `CHANGES_REQUESTED` — not the PR's aggregate `reviewDecision` (which reflects every reviewer, not just you), and not an older review of yours since superseded by a later approval or comment from you. Always take your latest submitted review, chronologically, to decide whether a PR currently qualifies.
- Batch Mode acts only on review threads containing **at least one comment authored by your own identity** — never fix, reply to, or resolve a thread whose comments are entirely from other reviewers, even if unresolved and even if it's clearly a valid finding. Fixing someone else's feedback is out of scope for this mode; each subagent must apply this filter before classifying anything (see Batch Mode Step 4).
- Never hardcode a PR number as permanently excluded. If the user names an exclusion for this run only (e.g. "batch-fix my change requests except #171"), drop it from the qualifying list for this invocation and say so — do not remember it for future runs.
- Each qualifying PR's fix run happens in its own subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: true`) so all qualifying PRs fix concurrently. Launch every subagent's `Agent` call in the same message/turn — never one at a time.
- Report each PR's result to the user **as soon as its completion notification arrives** — do not batch and wait for all subagents before saying anything. After the last one finishes, add one final summary table across every PR fixed this run.
- If a subagent's run fails outright (PR not found, nothing pushed), report that PR's failure plainly in both the per-PR update and the final table — never imply a fix landed when it didn't.

### Before Starting

- GitHub Mode: `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- Session-Only Mode: `git status --porcelain` must be clean before switching to the target branch, if it isn't already checked out. Dirty → stop and report the exact output (which files, staged or not) — do not stash, commit, discard, or otherwise touch them yourself; wait for the user to decide.
- Batch Mode: `gh auth status` must succeed, or GitHub MCP tools must be available (same as GitHub Mode). Resolve your own GitHub login first (`mcp__github__get_me`, or `gh api user --jq .login`) — the "requested changes by you" and "comments authored by you" checks both depend on it.

## Step 1: Mode Detection

1. If the request names no specific PR and instead asks for a batch sweep across PRs where you, as reviewer, requested changes (e.g. "fix the PRs I requested changes on", "batch-fix my change requests", "fix all my pending change requests") → **Batch Mode**.
2. Resolve a PR number the same way `complete-review` does: only from what's already established in this conversation (stated explicitly, or produced by an earlier step, e.g. `complete-review` or `ship-spec` opening/reviewing one). Do not infer it from git/gh branch state.
3. If a PR is known: check whether it has at least one **submitted** (non-pending) review with comments (`gh pr view <PR> --json reviews`, or the GraphQL query in [GitHub Delivery Mechanics](references/github-delivery.md)).
   - At least one submitted review exists → **GitHub Mode**.
   - The only review found is still `PENDING` → stop and tell the user: "Your review is still pending on GitHub — submit it before asking me to fix findings."
   - No review exists yet at all → fall through to **Session-Only Mode**.
4. If no PR is known at all and the request has no batch intent either → **Session-Only Mode** — the findings to fix exist only in this conversation.
5. If neither a PR number nor batch intent is clear → ask the user: "Should I fix one specific PR (give me the number), or batch-fix every open PR where you requested changes?" Do not guess.

## GitHub Mode

Findings live on GitHub — this is the mode `ship-spec`'s own comment-triage round runs, and the mode each Batch Mode subagent runs per PR.

1. Fetch open review threads via GraphQL `reviewThreads` (see [GitHub Delivery Mechanics](references/github-delivery.md)). Skip threads already `isResolved: true`. Skip any thread whose review is still `PENDING`. If the fetched thread count hits the query's page-size cap (100), note in the final report that additional unresolved threads may exist beyond what was fetched.
2. For each unresolved, published thread, read the full exchange — every comment on it, in order, not just the first or the last — check the underlying finding or suggested approach against the actual current code (see Guardrails), and classify what it's actually asking for right now:
   - **auto-fix** — no user comment on the thread at all, and the finding holds up against the current code on inspection. Fix it directly.
   - **answer-only** — the thread's current ask, once you've read the whole exchange, is a question. Reply with the answer; don't fix unless the answer implies a change. Leave the thread unresolved.
   - **apply-as-directed** — the thread's current direction suggests an approach, and it validates (confirms/directs the fix, or holds up as sound on inspection). Fix it as directed.
   - **pushback** — the thread's direction (a suggested approach that doesn't validate, or an unreplied finding that turns out not to hold up) doesn't survive inspection. Reply rejecting it with your reasoning (and the approach you're taking instead, if any). Leave the thread unresolved.
   - **unclear** — even after reading the full thread, you're not confident what it's actually asking for. Do not fix or reply — record it for the report (thread id, `path:line`, why it's unclear) so the user can clarify.
   - **standalone comment, not anchored to a finding** — same apply-as-directed / pushback / unclear treatment as above.
3. If a tlc-spec-driven feature is active for this work, write the classified plan to `.specs/features/<feature>/fix-code-review.md` — a flat list grouped `## Parallel` (independent items, no two touching the same file) and `## Sequential` (items sharing a file, encounter order); each entry has thread id, classification, `path:line`, and a one-line fix/reply direction. If no feature is active, keep the same classified plan in this conversation only — do not write it to `.specs/`. Either way: **unclear** items are recorded for the report but never enter the draft/commit steps. If zero threads were found, stop here.
4. Immediately after — no approval gate; invoking GitHub Mode is itself the go-ahead — refetch the same `reviewThreads` query, diff against the plan just made, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch.
5. For the auto-fix and apply-as-directed items surviving step 4: draft fixes concurrently, capped at 4 subagents at a time (`Agent` tool, `agentType: general-purpose`, `model: claude-haiku-4-5-20251001`, `run_in_background: false`) — one per item in the `## Parallel` bucket; `## Sequential`-bucket items one at a time, in order, same subagent shape. Each drafting subagent uses the PR's own title/body/diff for context, performs no file edits or git operations, and returns its proposed change — including any test it wrote, updated, or removed to keep coverage aligned with the fix, with a one-line reason for any removal — or a blocker/unclear reason if it can't confidently complete. Apply and commit each via its own subagent call, one item at a time — never two commits concurrently — following Conventional Commits, running only that item's own directly relevant test(s) to validate (no full gate/verify cycle). If a drafted change no longer matches current file state at commit time, mark it blocked instead of force-applying. For answer-only, pushback, or unclear items: no commit, no drafting subagent — compose the reply (or the "here's what's unclear" note) directly in this conversation, on the default model.
6. Reply on the thread, or resolve it silently, per its classification: **auto-fix** and **apply-as-directed** — resolve via GraphQL `resolveReviewThread` (see [GitHub Delivery Mechanics](references/github-delivery.md)), no reply comment posted — the fix is the answer. **pushback** — reply with the rejection reasoning (and the approach taken instead, if any), then resolve. **answer-only** — reply with the answer only; leave unresolved, only the user resolves it once satisfied. **unclear** — post a clarifying reply only if you have a specific question; leave unresolved either way.
7. If any commits were made: `git push` to the existing branch — this updates the same open PR, never a new one.
8. Report: threads processed by classification (including unclear and blocked items, with reasons), commits pushed, any test additions/updates/removals with their reasons, and — if step 1 hit the page-size cap — a note that additional unresolved threads may exist beyond what was fetched.

## Session-Only Mode

Findings exist only in this conversation — nothing has been posted to GitHub.

1. Resolve the target branch the same conversation-context-only way as the PR number above: only from what's already established (the user named it, or it's the branch a prior review ran against). If none is known, ask which branch to fix on before continuing.
2. If the resolved branch isn't currently checked out, check it out (subject to the clean-tree guard in Before Starting).
3. Take every finding already known from this conversation — their presence in the conversation is the go-ahead to evaluate and act, same as a published GitHub review comment is in GitHub Mode, not a mandate to apply them unread. Check each against the actual current code (see Guardrails) before fixing: a finding that holds up gets fixed; one that doesn't (stale, already addressed, or simply wrong) is reported unfixed with the reason instead, same as GitHub Mode's pushback treatment.
4. Draft and apply fixes with the same mechanics as GitHub Mode step 5 (Haiku subagents capped at 4, one commit at a time, Conventional Commits, test coverage required, unclear items reported unfixed rather than guessed at) — minus anything about threads, since there are none here.
5. Do NOT push. Commits stay local for the user to review and push themselves.
6. Report: findings fixed (with the commit list), any test additions/updates/removals with their reasons, any left unfixed and why (unclear, rejected on inspection, or a blocker), and a reminder that nothing was pushed.

## Batch Mode

Finds every open GitHub PR where you, as reviewer, requested changes, then fans out one GitHub Mode run per PR in parallel — each scoped to only your own comments — reporting each result as it lands, not after the whole batch finishes.

### Step 1: Resolve the repo

Detect `owner/repo` from the current working directory's git remote:

```bash
git remote -v
```

Parse `owner/repo` from the `origin` remote (or the only remote, if `origin` doesn't exist). If the working directory is not a git repository, or has no remote pointing at GitHub, ask the user: "Which repo should I check — `owner/repo`?" Do not guess.

### Step 2: Find candidate PRs

Search open PRs where you're a reviewer:

```
mcp__github__search_pull_requests
  query: "repo:<owner>/<repo> is:open reviewed-by:<your-login>"
  fields: ["number", "title", "html_url", "state"]
```

(or, without GitHub MCP: `gh pr list --repo <owner>/<repo> --search "reviewed-by:<your-login>" --state open`)

If the invocation named any PR numbers to exclude for this run, drop them from this list now (see Guardrails — never persist an exclusion beyond the current run).

If the search returns zero PRs, report "You have no open PRs with a submitted review in `<owner>/<repo>`." and stop — do not proceed to Step 3.

### Step 3: Filter to PRs where your latest review requested changes

For each candidate PR, fetch all reviews and keep only those authored by your login, ordered by submission time:

```
mcp__github__pull_request_read
  method: get_reviews
  owner: <owner>
  repo: <repo>
  pullNumber: <N>
```

(or `gh api repos/<owner>/<repo>/pulls/<N>/reviews --jq '[.[] | select(.user.login=="<your-login>")] | sort_by(.submitted_at) | last | .state'`)

A PR qualifies only if your **most recent** submitted review on it has state `CHANGES_REQUESTED` — a later `APPROVED` or `COMMENTED` review of yours means it no longer qualifies, even if an earlier one requested changes. Run this check for every candidate before moving on.

Present the qualifying list to the user (PR number + title) before fanning out, so the run is transparent. If nothing qualifies, report that and stop.

### Step 4: Fan out one fix run per qualifying PR

For every qualifying PR, launch one `Agent` call — all of them in the same message, so they run concurrently:

```
Agent
  description: "Fix-review PR <N>"
  subagent_type: general-purpose
  model: sonnet
  run_in_background: true
  prompt: |
    You are working in the repo <owner>/<repo> (current working directory is already
    this repo's checkout).

    Task: fix your own review findings on GitHub PR #<N> ("<title>"), where your most
    recently submitted review requested changes.

    Steps:
    1. Invoke the `fix-review` skill via the Skill tool, GitHub Mode, targeting PR #<N>
       specifically — do not rely on any prior conversation context, there is none.
    2. When fetching and classifying review threads (GitHub Mode steps 1-2), restrict
       to only unresolved threads that contain at least one comment authored by
       <your-login> — skip any thread whose comments are entirely from other
       reviewers, even if unresolved. Only your own feedback is in scope for this run.
    3. Apply every other GitHub Mode guardrail as normal: read each thread's full
       exchange before classifying, require a passing directly-relevant test per fix,
       commit one item at a time, and report unclear items unfixed rather than guessed at.

    When done, report back concisely:
    - Threads processed by classification (fixed, answered, rejected, unclear), scoped
      to your own comments only
    - Whether any commits were pushed to PR #<N>'s branch
    - Anything that blocked or limited the run
```

### Step 5: Report as each subagent completes

Each subagent's completion arrives as a separate task notification — do not wait for all of them. As soon as one arrives, post a short per-PR update: classification breakdown, commits pushed (or not), and any blocked/unclear items.

Once every subagent for this run has reported, post one final summary table with all PRs fixed this run, their classification breakdown, and commit counts — plus a one-line reminder of any PR where nothing was pushed and why.

## Examples

### Example 1: GitHub Mode, invoked by ship-spec

`ship-spec`'s Comment-Triage Mode invokes `fix-review` for PR #128, stating the active feature (`PROJ-42_rate-limiting`).

1. Step 1: PR #128 known, has a submitted review → GitHub Mode
2. Fetch 7 threads: 1 still `PENDING` on a newer review → skipped; 6 published and unresolved. Reading each in full and checking it against the current code: Thread 1 (`tests-code-review` finding, no comment) holds up → **auto-fix**; Thread 2 (`code-review` finding, no comment) turns out to already be handled by a later commit on the same branch → doesn't hold up, reclassified **pushback**; Thread 3 ("why didn't you use a token bucket here?") → **answer-only**; Thread 4 (`code-review` finding, then "yes, fix this") → **apply-as-directed**; Thread 5 (`code-review` finding, then a weaker suggested approach that doesn't hold up) → **pushback**; Thread 6 (`code-review` finding, no comment) holds up → **auto-fix**
3. Feature is active → write `fix-code-review.md`: `## Parallel` — T1, T4, T6 (no two share a file); `## Sequential` — none. T2, T3, T5 listed for audit, excluded from drafting.
4. Re-fetch: nothing changed — all 6 items proceed
5. Draft T1, T4, T6 concurrently (3 Haiku subagents), each including a test for its fix. Apply + commit one at a time: `test(orders): cover rate-limit edge case` (T1), then T4's directed fix, then T6's fix — each running only its own relevant test first.
6. Resolve T1, T4, T6 silently. Reply to T2 explaining it's already handled by a later commit, then resolve. Reply to T3 with the sliding-window tradeoff explanation, left unresolved. Reply to T5 with the rejection reasoning, then resolve.
7. Push (3 new commits)
8. Report: "6 threads processed (3 fixed, 2 rejected on inspection — one already handled, one an unsound suggested approach — 1 answered and left open), 1 pending thread left untouched."

### Example 2: Session-Only Mode

User ran `code-review` locally (no PR involved), got 4 findings, then said "fix these on branch `feature/cleanup`."

1. Step 1: no PR known, no batch intent → Session-Only Mode
2. Branch `feature/cleanup` named explicitly → resolved without asking; checked out (tree was clean)
3. All 4 findings taken, unfiltered
4. Draft and fix 3 of them (Haiku subagents, each with its own test); the 4th is genuinely ambiguous about which of two valid approaches the user wants — reported unclear instead of guessed at. 3 commits made, one at a time, each with its relevant test passing.
5. No push.
6. Report: "3 of 4 findings fixed and committed locally on `feature/cleanup` (not pushed). 1 left unfixed — unclear whether to use a cache or a recompute for the derived field; let me know which and I'll finish it."

### Example 3: Batch Mode, several PRs qualify

User: "fix the PRs I requested changes on" (in a checkout of `acme/widgets`)

1. Step 1 (Mode Detection): batch language, no PR number → Batch Mode
2. Batch Mode Step 1: `git remote -v` → `acme/widgets`
3. Batch Mode Step 2: `reviewed-by:me` search returns PRs #30, #31, #33 (open)
4. Batch Mode Step 3: #30's latest review from you is `APPROVED` (superseded an earlier change request) → dropped. #31 and #33's latest review from you is `CHANGES_REQUESTED` → qualify
5. Batch Mode Step 4: two `Agent` calls launched in one message, one per PR, both `model: sonnet`, `run_in_background: true` — each running GitHub Mode scoped to only the user's own comments
6. Batch Mode Step 5: as each finishes, post its result immediately (e.g. "PR #33 — done. 2 threads fixed, 1 answered, 2 commits pushed."); after both, post the final summary table

### Example 4: Batch Mode, thread has both your comment and another reviewer's

`fix-review` Batch Mode is running GitHub Mode inside a subagent for PR #33. A thread on `orders.py:42` has a comment from another reviewer flagging a naming issue, and a separate comment from the user (the batch owner) flagging a missing null check on the same line, both unresolved.

1. The naming-issue-only thread (no comment from the user) is skipped entirely — out of scope for this run.
2. The user's null-check thread is read in full, classified **auto-fix** (no reply on it), fixed with a test, committed, and resolved.
3. Report notes: "1 thread fixed (your null-check comment on `orders.py:42`); 1 other-reviewer thread on the same file left untouched — not yours."

### Example 5: Batch Mode, nothing qualifies

User: "batch-fix my change requests" (no PR where your latest review requested changes)

1. Step 1 (Mode Detection): batch language → Batch Mode
2. Batch Mode Step 1–2: repo resolved, candidates found
3. Batch Mode Step 3: every candidate's latest review from you is `APPROVED` or `COMMENTED` → none qualify
4. Report: "No open PRs currently have a change-request review from you." — stop, no subagents launched
