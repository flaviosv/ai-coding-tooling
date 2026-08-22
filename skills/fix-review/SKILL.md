---
name: fix-review
description: Fixes GitHub PR review findings — from complete-review/code-review/tests-code-review or added manually — by fetching every open review thread fresh from GitHub (always the source of truth), reading each thread's full exchange to decide what it's actually asking for and whether it holds up against the current code, and committing fixes onto the PR's existing branch — never a new PR. A comment or suggested approach that doesn't hold up is rejected with reasoning instead of applied by rote, even when nobody pushed back on it. Every resolved thread gets a documentation reply describing what was actually changed before it's closed — never resolved silently. Also handles findings that exist only in the current conversation and were never posted to GitHub — fixes all of them on a branch you name (asks if none known) and leaves commits unpushed. A third mode batches this across every open PR where you, as reviewer, requested changes — one isolated Sonnet subagent per PR, each running in its own isolated git worktree (so concurrent PRs never fight over which branch is checked out) and fixing only your own comments, fanned out in parallel with results reported as each lands. Every fix is evaluated for test impact — coverage added, updated, or removed as the fix actually warrants, never left to drift incidentally — and validated with a passing directly-relevant test, no full spec-verification cycle. Anything unclear is reported back unfixed rather than guessed at. When explicitly asked, also syncs progress to a PR's linked Jira ticket (a starting comment plus an in-progress transition before fixing begins, a completion comment after) — opt-in only, never run by default. Use when the user says "fix review findings", "fix review comments", "triage PR feedback", "resolve review comments", "apply the review fixes", "fix the PRs I requested changes on", "batch-fix my change requests", or invokes /fix-review — if it's unclear which mode a request means, ask. Do NOT use to generate findings or post a review (use complete-review / code-review / tests-code-review) or for spec planning (use tlc-spec-driven).
metadata:
  author: Flavio Studart
  version: "1.8.2"
---

# Fix Review

Fixes review findings — on GitHub, or in this conversation only — straight on the existing branch. Never posts new findings, never creates a new PR. Batch Mode fans this out across every PR where you requested changes as a reviewer.

## Guardrails

### Scope

- Do NOT create new PRs — always fix on the PR's existing branch (GitHub Mode, and each PR fixed under Batch Mode) or the branch you're given/asked for (Session-Only Mode).
- Do NOT resolve a thread that still carries a live, unanswered question — reply with the answer instead; only resolve once the thread's current ask is a clear recommended action with no open question.
- Do NOT fix, reply to, or resolve a thread whose current comment is directed at a specific person by name or GitHub handle (e.g. "@alice, can you weigh in on this?", "Bob — thoughts?") rather than at whoever picks up the thread generally — that's a live person-to-person exchange pending that person's answer, not a finding for this skill to act on. Leave it out of scope entirely: skip it in the plan, don't touch it, but note it in the final report so the user knows it's still waiting on that person.
- GitHub is the **only** source of truth for what findings exist and what state they're in — this is absolute, not a soft preference. This skill acts only on review threads and comments that exist on GitHub right now, fetched fresh at the start of every single run. Never let this run be influenced by, reconciled against, or trusted on the say-so of any prior analysis, summary, or reported state from earlier in the conversation — not a remembered list of what was posted, not this skill's own earlier runs, not an earlier report from `code-review`/`complete-review`/`tests-code-review`, nothing. A claim about GitHub's state stops being trustworthy the instant it isn't this run's own fetch: state changes between when something was last observed and when this run acts, so even a claim made minutes ago in this same conversation (e.g. "that review is still pending") must be re-verified against a fresh fetch, never carried forward as still true. Always fetch review threads fresh (GraphQL `reviewThreads`) before acting on anything — a manual comment may have been added, or a thread's state may have changed, since anything was last observed, and this must be picked up. This cuts both ways: in GitHub Mode, fix only threads/comments that actually exist on GitHub right now — never fold in a finding that was only ever mentioned in this conversation (e.g. from an earlier `code-review` run that was never posted) just because it's about the same PR. Conversation history is used only to resolve which PR to act on (Step 1) or, in Session-Only Mode, as the findings themselves — never as an extra source of findings, and never as evidence of current GitHub state, once GitHub Mode is running.
- When a thread has more than one comment, read the whole exchange to determine what must actually be done — don't act on the first comment in isolation when a later one revises or replaces it, and don't mechanically grab only the last line either; understand how the conversation actually resolved.
- If you're not confident how to fix an item after reading it in full (the thread, in GitHub Mode; the finding, in Session-Only Mode), do NOT guess — report it back unfixed, with the reason, instead of applying a fix you're unsure of.
- Never fix a finding just because it exists — a comment on GitHub, or a finding stated in this conversation, is a claim to evaluate against the actual current code, not a mandate to act on unread. This applies to every item, not only the ones with a suggested direction to weigh (apply-as-directed/pushback): an **auto-fix** item (no reply on it) still needs its underlying claim checked against the real diff before you touch anything — silence from other reviewers isn't evidence it's correct, only that nobody happened to object. If an item doesn't actually hold up (stale, based on a misread of the diff, already addressed, or simply wrong), give it the same treatment as an unsound suggested approach: explain why, on the thread if one exists, and leave it unfixed rather than mechanically applying it. This is what keeps fix coverage — including the test additions/updates/removals below — grounded in findings that are actually real, instead of propagating every claim at face value.
- Do NOT add explanatory code comments when fixing a finding, unless the code is genuinely non-obvious (complex algorithm, subtle invariant, external constraint) — the fix should read as self-explanatory, same standard as any other change.
- Do NOT implement a fix directly in this conversation — delegate fixes to Haiku subagents, one subagent per **file cluster**: every auto-fix/apply-as-directed item whose fix would touch a given file belongs to that file's cluster, and one subagent handles its whole cluster, working through its items strictly one at a time inside that single call (edit → that item's relevant test → commit → next item) — never split one cluster's items across two subagents, and never two subagents against the same cluster. Different clusters never share a file, so their subagents run concurrently against each other without any commit race; keep only classification, clustering, and reply/reject reasoning here.
- Do NOT set `isolation: worktree` on these per-cluster subagents — they must operate inside whichever checkout is already in play: the isolated worktree direct GitHub Mode creates for itself before Step 1 when it isn't already on the PR's branch, or the current working directory when it already was (per Before Starting); the per-PR worktree a Batch Mode subagent is already running in (see Batch Mode below); or, for Session-Only Mode, the user's own working directory. Pass that location's path explicitly in every per-cluster subagent's prompt, so a fix lands ready for GitHub Mode's `git push` from the right place, or sits ready in the working tree for Session-Only Mode's local commits. This is distinct from Batch Mode's own outer isolation (per PR, not per cluster) — see Batch Mode's guardrails.
- Before resolving an **auto-fix** or **apply-as-directed** thread, post a reply comment documenting what was actually done — a few sentences on what changed and why (and its test impact, per the guardrail below), not just an acknowledgment — then resolve. Never resolve one of these silently: the thread should read as a record of what happened, not just that it's closed.
- Every fix must be evaluated for test impact, not just coverage-added: write a new test if the change isn't already covered (follow this project's `tests` skill conventions for how to write it well); update an existing test whose assertions the fix invalidates; remove a test outright only when it was asserting the very behavior the fix corrects (e.g. it locked in the bug), and replace it with a test of the corrected behavior whenever the fix leaves anything worth covering. Coverage should move up or down only as a direct, stated consequence of the fix — never let it drift incidentally; a removal with nothing added back to replace it needs a one-line reason in the report. Then run only that fix's directly relevant test(s) to confirm it passes. Do NOT invoke tlc-spec-driven's full Verifier or gate-check cycle for this — that's unnecessary weight for a fix-triage pass; a straightforward relevant-test run is the bar here.
- Use the PR's own title/body/diff to understand what a finding is actually asking for — not just the isolated comment text on its own.
- If a tlc-spec-driven feature is already active for this work (this skill was invoked by `build-feature`, or the user names one): write the audit-trail plan to `.specs/features/<feature>/fix-code-review.md`, same as tlc-spec-driven's own conventions expect. If no spec feature is active: do NOT create anything under `.specs/` — keep the classified plan in this conversation only; the staleness re-check (GitHub Mode step 4) still runs against that in-conversation record, just without a file backing it.
- GitHub Mode: never act on a review that's still `PENDING` (unsubmitted) — stop and tell the user to submit it first.
- Session-Only Mode: never push automatically — commit locally only and tell the user what's ready to push.
- Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only.
- For environments with more than one `gh` account logged in, see [gh Account Resolution](../../templates/gh-account-resolution.md) for scoping every `gh` call to the correct account — not applied here by default; adopt it only if this skill starts running somewhere that actually hits the multi-account problem.
- If a proposed change no longer matches current file state when the subagent goes to commit it (GitHub Mode's staleness re-check, or an equivalent conflict in Session-Only Mode): mark the item blocked instead of force-applying it.
- If a cluster subagent fails outright (crashes, errors, can't proceed at all — distinct from marking one of its own items blocked/unclear and continuing on to the rest, which needs no retry): retry once with a fresh subagent for that cluster. If it fails a second time, stop and report the failure — do not fabricate a result or mark an item resolved on a failed fix.

### Batch Mode

- Batch Mode only **selects and delegates** — it never reads a thread or commits a fix itself in this conversation; every PR's actual fix work happens inside its own subagent, running the exact same GitHub Mode flow above (and inheriting every Scope guardrail above, including the test-coverage and no-worktree-isolation rules).
- "Requested changes" means **your own most recently submitted review** on that PR has state `CHANGES_REQUESTED` — not the PR's aggregate `reviewDecision` (which reflects every reviewer, not just you), and not an older review of yours since superseded by a later approval or comment from you. Always take your latest submitted review, chronologically, to decide whether a PR currently qualifies.
- Batch Mode acts only on review threads containing **at least one comment authored by your own identity** — never fix, reply to, or resolve a thread whose comments are entirely from other reviewers, even if unresolved and even if it's clearly a valid finding. Fixing someone else's feedback is out of scope for this mode; each subagent must apply this filter before classifying anything (see Batch Mode Step 4).
- Never hardcode a PR number as permanently excluded. If the user names an exclusion for this run only (e.g. "batch-fix my change requests except #171"), drop it from the qualifying list for this invocation and say so — do not remember it for future runs.
- Each qualifying PR's fix run happens in its own subagent, in its own isolated git worktree (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: true`, `isolation: 'worktree'`) — this is what lets every qualifying PR fix concurrently without fighting over which branch is checked out in a shared working directory. The subagent's first action inside its worktree is to check out that PR's branch (`gh pr checkout <N>`); this checkout is only safe because the worktree isolates it from the user's own checkout and from every other PR's subagent. A direct (non-batch) GitHub Mode run isolates the same way when it needs to — via a worktree it creates itself with plain `git worktree` commands instead of the `Agent` tool's `isolation` param, since it isn't running inside a subagent to begin with — but skips it entirely when the current working directory is already on the PR's branch, since git won't allow the same branch checked out twice (see Before Starting). Launch every subagent's `Agent` call in the same message/turn — never one at a time.
- Report each PR's result to the user **as soon as its completion notification arrives** — do not batch and wait for all subagents before saying anything. After the last one finishes, add one final summary table across every PR fixed this run.
- If a subagent's run fails outright (PR not found, nothing pushed), report that PR's failure plainly in both the per-PR update and the final table — never imply a fix landed when it didn't.

### Before Starting

- GitHub Mode: `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- GitHub Mode, direct invocation only (not a Batch Mode subagent — those already run isolated, see Batch Mode): before Step 1, resolve the PR's head branch (`gh pr view <PR> --json headRefName --jq .headRefName`) and compare it against `git branch --show-current`. If they already match — e.g. `build-feature`'s re-entry into an already-delivered PR, already sitting on the branch it just delivered — work directly in the current working directory; do not create a worktree (git refuses to check out a branch that's already checked out elsewhere, so this check isn't optional). If they don't match, create an isolated worktree instead of asking the user to switch branches themselves — `git worktree add <tmp-path> <headRefName>` (fetch first with `git fetch origin <headRefName>` if the branch isn't already known locally) — and run every step from here on inside it, leaving the user's own working directory and checked-out branch untouched. If a worktree was created, install this project's dependencies in it once, right away — the command documented in this project's `docs/codebase/STACK.md`/`TESTING.md` if available, otherwise the standard install command for its package manager/lockfile — so no per-cluster subagent has to discover or install them mid-fix. If a worktree was created, remove it (`git worktree remove <tmp-path>`) once the run is fully finished, successful or not — its lifetime is scoped to this skill run. If a blocker leaves the run genuinely unfinished and there's local state worth the user inspecting before cleanup, say so and hold off removal until they confirm.
- Session-Only Mode: `git status --porcelain` must be clean before switching to the target branch, if it isn't already checked out. Dirty → stop and report the exact output (which files, staged or not) — do not stash, commit, discard, or otherwise touch them yourself; wait for the user to decide.
- Batch Mode: `gh auth status` must succeed, or GitHub MCP tools must be available (same as GitHub Mode). Resolve your own GitHub login first (`mcp__github__get_me`, or `gh api user --jq .login`) — the "requested changes by you" and "comments authored by you" checks both depend on it.

### Jira Ticket Sync

- Opt-in only, never default — only run this for a PR when the user's invocation explicitly asked for Jira sync. Fixing findings on a PR with no such request must never touch Jira, since not every repo or PR has a linked ticket and not every user wants this.
- Resolve the Atlassian `cloudId` via `mcp__atlassian__getAccessibleAtlassianResources` once per run — never once per PR.
- If no ticket key can be resolved from a PR's title/body, skip that PR's Jira sync silently and note it in the final report — never block or fail the fix-review run over it.
- Never guess or hardcode a Jira transition id — resolve the correct one by name via `mcp__atlassian__getTransitionsForJiraIssue` first. If no transition matching an active-work status is available from the ticket's current status, skip the transition and note it in the report rather than guessing.
- Exactly one starting comment and one completion comment per PR's ticket — never one per finding, and never more than this pair regardless of how many findings that PR has.
- In Batch Mode, each PR's Jira sync runs independently inside that PR's own subagent, against that PR's own ticket only — never batched or reconciled across PRs.

## Step 1: Mode Detection

1. If the request names no specific PR and instead asks for a batch sweep across PRs where you, as reviewer, requested changes (e.g. "fix the PRs I requested changes on", "batch-fix my change requests", "fix all my pending change requests") → **Batch Mode**.
2. Resolve a PR number the same way `complete-review` does: only from what's already established in this conversation (stated explicitly, or produced by an earlier step, e.g. `complete-review` or `build-feature` opening/reviewing one). Do not infer it from git/gh branch state.
3. If a PR is known: check whether it has at least one **submitted** (non-pending) review with comments (`gh pr view <PR> --json reviews`, or the GraphQL query in [GitHub Delivery Mechanics](references/github-delivery.md)).
   - At least one submitted review exists → **GitHub Mode**.
   - The only review found is still `PENDING` → stop and tell the user: "Your review is still pending on GitHub — submit it before asking me to fix findings."
   - No review exists yet at all → fall through to **Session-Only Mode**.
4. If no PR is known at all and the request has no batch intent either → **Session-Only Mode** — the findings to fix exist only in this conversation.
5. If neither a PR number nor batch intent is clear → ask the user: "Should I fix one specific PR (give me the number), or batch-fix every open PR where you requested changes?" Do not guess.

## GitHub Mode

Findings live on GitHub — this is the mode `build-feature`'s own re-entry into a completed run runs, and the mode each Batch Mode subagent runs per PR.

1. Fetch open review threads via GraphQL `reviewThreads` (see [GitHub Delivery Mechanics](references/github-delivery.md)). Skip threads already `isResolved: true`. Skip any thread whose review is still `PENDING`. If the fetched thread count hits the query's page-size cap (100), note in the final report that additional unresolved threads may exist beyond what was fetched.
2. For each unresolved, published thread, read the full exchange — every comment on it, in order, not just the first or the last — check the underlying finding or suggested approach against the actual current code (see Guardrails), and classify what it's actually asking for right now:
   - **auto-fix** — no user comment on the thread at all, and the finding holds up against the current code on inspection. Fix it directly.
   - **answer-only** — the thread's current ask, once you've read the whole exchange, is a question. Reply with the answer; don't fix unless the answer implies a change. Leave the thread unresolved.
   - **apply-as-directed** — the thread's current direction suggests an approach, and it validates (confirms/directs the fix, or holds up as sound on inspection). Fix it as directed.
   - **pushback** — the thread's direction (a suggested approach that doesn't validate, or an unreplied finding that turns out not to hold up) doesn't survive inspection. Reply rejecting it with your reasoning (and the approach you're taking instead, if any). Leave the thread unresolved.
   - **routed to a person** — the thread's current comment explicitly addresses a specific person by name or GitHub handle, rather than posing a general finding or suggestion. Leave it out of scope entirely: do not fix, reply, or resolve — record it for the report (thread id, `path:line`, who it's addressed to) so the user knows it's still pending that person's answer.
   - **unclear** — even after reading the full thread, you're not confident what it's actually asking for. Do not fix or reply — record it for the report (thread id, `path:line`, why it's unclear) so the user can clarify.
   - **standalone comment, not anchored to a finding** — same apply-as-directed / pushback / unclear treatment as above.
3. Group every auto-fix/apply-as-directed item into **file clusters**: two items land in the same cluster only if their fixes would touch the same file; every other item is its own single-item cluster. Order each cluster's items by encounter order. If a tlc-spec-driven feature is active for this work, write the classified plan to `.specs/features/<feature>/fix-code-review.md` — one `## Cluster: <file path>` section per cluster (a cluster spanning more than one file names all of them in its heading), each listing its items in encounter order with thread id, classification, `path:line`, and a one-line fix/reply direction. If no feature is active, keep the same classified plan in this conversation only — do not write it to `.specs/`. Either way: **unclear** and **routed-to-person** items are recorded for the report but never enter the draft/commit steps. If zero threads were found, stop here.
4. Immediately after — no approval gate; invoking GitHub Mode is itself the go-ahead — refetch the same `reviewThreads` query, diff against the plan just made, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch. If dropping an item empties its cluster, drop the cluster too.
5. For the clusters surviving step 4: launch one subagent per cluster, all in the same message/turn (`Agent` tool, `agentType: general-purpose`, `model: haiku`, `run_in_background: true` when dispatching more than one cluster this run, otherwise `false`) — clusters run concurrently, since by construction no two share a file. A cluster with more than one item is handled entirely by that one subagent, which works through its items strictly one at a time inside the call — never split across subagents, never parallelized within the cluster, since each item ends in its own commit on the shared checkout and concurrent commits touching the same file would race. Each subagent uses the PR's own title/body/diff for context, is told the checkout location resolved in Before Starting (the isolated worktree, or the current working directory if none was needed), and is given its full list of assigned items; it reads the cluster's file(s) once, then for each item in order: makes the edit, follows Conventional Commits for that item's own commit — including any test it wrote, updated, or removed to keep coverage aligned with that fix, with a one-line reason for any removal — and runs only that item's own directly relevant test(s) to validate before committing it (no full gate/verify cycle) — before moving to the cluster's next item. It returns one few-sentence plain-language summary per item — what that item's fix actually does and why, for use as that item's thread documentation reply (step 6) — or a blocker/unclear reason for any item it can't confidently complete, in which case that item gets no edit and no commit but the subagent still continues on to the rest of its cluster. If the file state no longer matches what step 4's re-fetch assumed by the time the subagent reaches a given item, mark that item blocked instead of force-applying — this doesn't stop the rest of the cluster. For answer-only, pushback, routed-to-person, or unclear items: no commit, no subagent — compose the reply (or the "here's what's unclear" note) directly in this conversation, on the default model.
6. Reply on the thread, then resolve where applicable, per its classification: **auto-fix** and **apply-as-directed** — post the subagent's fix summary (what changed, why, and any test impact) as a reply comment, then resolve via GraphQL `resolveReviewThread` (see [GitHub Delivery Mechanics](references/github-delivery.md)) — never resolve without that reply, the thread is meant to read as a record of what was done. **pushback** — reply with the rejection reasoning (and the approach taken instead, if any), then resolve. **answer-only** — reply with the answer only; leave unresolved, only the user resolves it once satisfied. **unclear** — post a clarifying reply only if you have a specific question; leave unresolved either way. **routed to a person** — do not reply, do not resolve; leave the thread completely untouched, it's the addressed person's turn, not this skill's.
7. If any commits were made: `git push` to the existing branch, from wherever Before Starting resolved this run's checkout to — this updates the same open PR, never a new one.
8. If a worktree was created for this run, remove it per Before Starting (unless a blocker left state worth inspecting first — see there). Report: threads processed by classification (including unclear, routed-to-person, and blocked items, with reasons), commits pushed, any test additions/updates/removals with their reasons, and — if step 1 hit the page-size cap — a note that additional unresolved threads may exist beyond what was fetched.

## Session-Only Mode

Findings exist only in this conversation — nothing has been posted to GitHub.

1. Resolve the target branch the same conversation-context-only way as the PR number above: only from what's already established (the user named it, or it's the branch a prior review ran against). If none is known, ask which branch to fix on before continuing.
2. If the resolved branch isn't currently checked out, check it out (subject to the clean-tree guard in Before Starting).
3. Take every finding already known from this conversation — their presence in the conversation is the go-ahead to evaluate and act, same as a published GitHub review comment is in GitHub Mode, not a mandate to apply them unread. Check each against the actual current code (see Guardrails) before fixing: a finding that holds up gets fixed; one that doesn't (stale, already addressed, or simply wrong) is reported unfixed with the reason instead, same as GitHub Mode's pushback treatment.
4. Fix each finding with the same mechanics as GitHub Mode step 5 (group into file clusters, one Haiku subagent per cluster processing its items one at a time within a single call, clusters dispatched concurrently, Conventional Commits, test coverage required, unclear items reported unfixed rather than guessed at) — minus anything about threads, since there are none here.
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
  isolation: worktree
  prompt: |
    You are working in an isolated git worktree of <owner>/<repo>, created fresh for
    this run — no other PR's fix run shares it, and it is separate from the user's
    own working directory.

    Task: fix your own review findings on GitHub PR #<N> ("<title>"), where your most
    recently submitted review requested changes.

    Steps:
    1. Check out this PR's branch in your worktree: `gh pr checkout <N>`. This is safe
       here specifically because the worktree is yours alone.
    2. Install this project's dependencies in the worktree once, right away — the
       command documented in this project's `docs/codebase/STACK.md`/`TESTING.md` if
       available, otherwise the standard install command for its package
       manager/lockfile — so no per-cluster subagent has to discover or install them
       mid-fix.
    3. Invoke the `fix-review` skill via the Skill tool, GitHub Mode, targeting PR #<N>
       specifically — do not rely on any prior conversation context, there is none.
    4. When fetching and classifying review threads (GitHub Mode steps 1-2), restrict
       to only unresolved threads that contain at least one comment authored by
       <your-login> — skip any thread whose comments are entirely from other
       reviewers, even if unresolved. Only your own feedback is in scope for this run.
    5. Apply every other GitHub Mode guardrail as normal: read each thread's full
       exchange before classifying, require a passing directly-relevant test per fix,
       post a documentation reply before resolving an auto-fix/apply-as-directed
       thread, group items into file clusters and dispatch one concurrent subagent per
       cluster (each cluster's own items committed one at a time within its subagent),
       skip any thread addressed to a specific person by name/handle rather than
       fixing it yourself, and report unclear items unfixed rather than guessed at.
    [Include only if the user requested Jira sync for this batch run:]
    6. Run this PR's own Jira Ticket Sync, independently of every other PR's subagent:
       resolve the Atlassian cloudId, resolve this PR's ticket key from its
       title/description (skip silently and note it in your report if none can be
       resolved), post a starting comment plus an active-work transition on the ticket
       before step 3's fixing work begins, then a completion comment after it finishes
       — per the Jira Ticket Sync guardrails and steps, exactly one of each comment for
       this PR's ticket only.

    When done, report back concisely:
    - Threads processed by classification (fixed, answered, rejected, routed to a
      person, unclear), scoped to your own comments only
    - Whether any commits were pushed to PR #<N>'s branch
    - If Jira sync was requested: the ticket key synced (or that none could be
      resolved), and whether the starting/completion comments and transition landed
    - Anything that blocked or limited the run
```

### Step 5: Report as each subagent completes

Each subagent's completion arrives as a separate task notification — do not wait for all of them. As soon as one arrives, post a short per-PR update: classification breakdown, commits pushed (or not), and any blocked/unclear items.

Once every subagent for this run has reported, post one final summary table with all PRs fixed this run, their classification breakdown, and commit counts — plus a one-line reminder of any PR where nothing was pushed and why.

## Jira Ticket Sync

Opt-in only — runs only when the user's invocation explicitly asks for it (e.g. "and update the Jira ticket", "move the ticket to in progress", "comment on the ticket when done"). Never runs on a plain "fix review findings"-style invocation with no such ask: not every repo or PR has a linked Jira ticket, and not every user wants this. When requested, it applies per PR — in GitHub Mode directly, or once per PR inside each Batch Mode subagent (see Batch Mode Step 4 below) — with each PR's own ticket resolved and updated independently; PRs are never batched together for this.

1. Resolve the Atlassian `cloudId` via `mcp__atlassian__getAccessibleAtlassianResources` — once per run, not once per PR.
2. For the PR being synced, resolve its linked Jira ticket key from the PR's title/description — key off whatever ticket-key pattern (e.g. `OIQ-123`) actually appears there, since the project prefix varies by repo; don't hardcode one. If no ticket key can be resolved, skip this PR's Jira sync silently and note it in the final report — never block or fail the fix-review run over it.
3. Before any fixing work begins for this PR (i.e. before GitHub Mode step 5): post one comment on the ticket via `mcp__atlassian__addCommentToJiraIssue` stating that code review found issues on this PR (link it), listing each finding concisely (severity + one-line summary), and that work on fixes is starting.
4. Resolve the correct "active work" transition by name via `mcp__atlassian__getTransitionsForJiraIssue` first — never guess or hardcode a transition id, these are workflow-specific per Jira project. If a transition matching an active-work status (commonly named "In Progress") is available from the ticket's current status, apply it via `mcp__atlassian__transitionJiraIssue`. If none is available, skip the transition and note it in the report instead of guessing.
5. Run the fix work as normal (GitHub Mode steps 5-8), unaffected by Jira sync.
6. After all fixing work for this PR is complete — whether every item got fixed or some were rejected/left unclear — post one follow-up comment on the same ticket confirming what was done: summarize what was fixed, note anything left unfixed and why (rejected on inspection, unclear, blocked), and state the PR is ready for a new review round.

This is per-PR, not per-finding: exactly one starting comment and one completion comment per PR's ticket, never one per finding, regardless of how many findings that PR has.

In Batch Mode, when the user has requested Jira sync for the batch run, each PR's own subagent performs its own PR's Jira sync independently inside its own run, against its own PR's ticket only — this is folded into the fan-out subagent prompt template (Batch Mode Step 4) the same way every other instruction is delegated into the subagent prompt.

## Examples

### Example 1: GitHub Mode, invoked by build-feature

`build-feature`'s re-entry into an already-delivered run invokes `fix-review` for PR #128, stating the active feature (`PROJ-42_rate-limiting`). The working directory is already on PR #128's branch — `build-feature` just delivered it from here and left the worktree in place.

1. Step 1: PR #128 known, has a submitted review → GitHub Mode
2. Before Starting: current branch already matches PR #128's head branch → work directly here, no worktree created
3. Fetch 7 threads: 1 still `PENDING` on a newer review → skipped; 6 published and unresolved. Reading each in full and checking it against the current code: Thread 1 (`tests-code-review` finding, no comment) holds up → **auto-fix**; Thread 2 (`code-review` finding, no comment) turns out to already be handled by a later commit on the same branch → doesn't hold up, reclassified **pushback**; Thread 3 ("why didn't you use a token bucket here?") → **answer-only**; Thread 4 (`code-review` finding, then "yes, fix this") → **apply-as-directed**; Thread 5 (`code-review` finding, then a weaker suggested approach that doesn't hold up) → **pushback**; Thread 6 (`code-review` finding, no comment) holds up → **auto-fix**
4. Feature is active → write `fix-code-review.md`: three single-item clusters — T1, T4, T6 (no two share a file) — plus T2, T3, T5 listed for audit, excluded from drafting.
5. Re-fetch: nothing changed — all 6 items proceed
6. Fix T1, T4, T6 as 3 concurrent Haiku subagents (one per cluster, each combining draft+apply+commit in one call), every subagent including a test for its fix and a plain-language summary of what it changed: `test(orders): cover rate-limit edge case` (T1), T4's directed fix, and T6's fix — each running only its own relevant test before committing.
7. Reply to T1 ("Added a test covering the rate-limit edge case at the window boundary — previously untested."), T4 ("Extracted the rate-limit check into a shared helper as directed, with a test for the shared path."), and T6 (its own fix summary), then resolve each. Reply to T2 explaining it's already handled by a later commit, then resolve. Reply to T3 with the sliding-window tradeoff explanation, left unresolved. Reply to T5 with the rejection reasoning, then resolve.
8. Push (3 new commits) from the current working directory
9. No worktree was created, so nothing to remove. Report: "6 threads processed (3 fixed, 2 rejected on inspection — one already handled, one an unsound suggested approach — 1 answered and left open), 1 pending thread left untouched."

### Example 2: Session-Only Mode

User ran `code-review` locally (no PR involved), got 4 findings, then said "fix these on branch `feature/cleanup`."

1. Step 1: no PR known, no batch intent → Session-Only Mode
2. Branch `feature/cleanup` named explicitly → resolved without asking; checked out (tree was clean)
3. All 4 findings taken, unfiltered
4. Fix 3 of them as 3 concurrent single-item-cluster Haiku subagents (draft+apply+commit combined in each call, each with its own test); the 4th is genuinely ambiguous about which of two valid approaches the user wants — reported unclear instead of guessed at. 3 commits made, each with its relevant test passing.
5. No push.
6. Report: "3 of 4 findings fixed and committed locally on `feature/cleanup` (not pushed). 1 left unfixed — unclear whether to use a cache or a recompute for the derived field; let me know which and I'll finish it."

### Example 3: Batch Mode, several PRs qualify

User: "fix the PRs I requested changes on" (in a checkout of `acme/widgets`)

1. Step 1 (Mode Detection): batch language, no PR number → Batch Mode
2. Batch Mode Step 1: `git remote -v` → `acme/widgets`
3. Batch Mode Step 2: `reviewed-by:me` search returns PRs #30, #31, #33 (open)
4. Batch Mode Step 3: #30's latest review from you is `APPROVED` (superseded an earlier change request) → dropped. #31 and #33's latest review from you is `CHANGES_REQUESTED` → qualify
5. Batch Mode Step 4: two `Agent` calls launched in one message, one per PR, both `model: sonnet`, `run_in_background: true`, `isolation: worktree` — each in its own isolated worktree, checking out its own PR's branch (`gh pr checkout 31` / `gh pr checkout 33`) without touching the other's or the user's own checkout, then running GitHub Mode scoped to only the user's own comments
6. Batch Mode Step 5: as each finishes, post its result immediately (e.g. "PR #33 — done. 2 threads fixed, 1 answered, 2 commits pushed."); after both, post the final summary table

### Example 4: Batch Mode, thread has both your comment and another reviewer's

`fix-review` Batch Mode is running GitHub Mode inside its own isolated worktree for PR #33, already checked out to that PR's branch. A thread on `orders.py:42` has a comment from another reviewer flagging a naming issue, and a separate comment from the user (the batch owner) flagging a missing null check on the same line, both unresolved.

1. The naming-issue-only thread (no comment from the user) is skipped entirely — out of scope for this run.
2. The user's null-check thread is read in full, checked against the current code (it still applies), classified **auto-fix**, fixed with a test, committed.
3. Reply posted to the thread: "Added a null check before dereferencing `order.customer` — it was possible for this to be unset on cancelled orders." Then resolved.
4. Report notes: "1 thread fixed (your null-check comment on `orders.py:42`); 1 other-reviewer thread on the same file left untouched — not yours."

### Example 5: Batch Mode, nothing qualifies

User: "batch-fix my change requests" (no PR where your latest review requested changes)

1. Step 1 (Mode Detection): batch language → Batch Mode
2. Batch Mode Step 1–2: repo resolved, candidates found
3. Batch Mode Step 3: every candidate's latest review from you is `APPROVED` or `COMMENTED` → none qualify
4. Report: "No open PRs currently have a change-request review from you." — stop, no subagents launched

### Example 6: GitHub Mode, a thread is routed to a specific person

`fix-review` is running GitHub Mode on PR #142. One unresolved thread reads: "@bob, you touched this last — can you confirm the timeout value is still right here?" with no reply yet.

1. Reading the thread in full: the current comment explicitly addresses Bob by GitHub handle, not a general finding → classified **routed to a person**.
2. It's recorded for the report (thread id, `path:line`, addressed to `@bob`) but excluded from the cluster plan entirely — no drafting subagent, no reply, no resolve.
3. Report notes: "1 thread left untouched — addressed to @bob, still pending their answer."

### Example 7: GitHub Mode, ad-hoc invocation — worktree created and cleaned up

User: `/fix-review PR #201` — the working directory is currently on `main`, not PR #201's branch (`feature/checkout-retry`), and no other skill has checked it out.

1. Step 1: PR #201 known, has a submitted review → GitHub Mode
2. Before Starting: `git branch --show-current` is `main`, PR #201's head branch is `feature/checkout-retry` — they don't match, so `git worktree add /tmp/.../fix-review-201 feature/checkout-retry` creates an isolated worktree instead of asking the user to switch branches. The user's own checkout on `main` is never touched.
3. Steps 1–6 run entirely inside that worktree: 3 threads fetched, 2 auto-fix, 1 unclear; drafting and commits happen there, then `git push` from the worktree updates PR #201's branch directly on GitHub.
4. Run finished cleanly → `git worktree remove /tmp/.../fix-review-201` — nothing left behind, `main` in the user's own directory is exactly as they left it.
5. Report: "2 threads fixed, 1 left unclear, 1 commit pushed to PR #201. Ran in an isolated worktree — your own checkout on `main` was untouched throughout."

### Example 8: GitHub Mode, ignoring conversation-only findings

Earlier in this same conversation, `code-review` ran locally against PR #305's branch and surfaced 3 findings, but nothing was ever posted to GitHub. Separately, someone else already left a submitted GitHub review on PR #305 with 2 comments of their own. The user then says "fix the review comments on PR #305."

1. Step 1: PR #305 known; a submitted review with comments already exists on GitHub → **GitHub Mode** (per Step 1 rule 3), regardless of the 3 findings sitting in this conversation.
2. GitHub Mode Step 1 fetches threads fresh from GitHub: only the 2 threads from the submitted review. The earlier conversation's 3 `code-review` findings are not folded in, referenced, or fixed — they were never posted to GitHub, so they're out of scope for this run.
3. Report covers only the 2 GitHub threads. If the user wants the other 3 findings fixed too, they'd need to be posted to GitHub first (e.g. via `complete-review`/`code-review`) or handled as a separate Session-Only Mode run on a branch with no submitted review yet.

### Example 9: GitHub Mode, invoked with Jira sync requested

User: "Fix the review on PR #219 and update the Jira ticket." PR #219's title is "OIQ-88: add retry backoff to webhook delivery".

1. Step 1: PR #219 known, has a submitted review → GitHub Mode. Jira sync requested explicitly → Jira Ticket Sync runs alongside it for this PR.
2. Jira Ticket Sync: `cloudId` resolved once; ticket key `OIQ-88` resolved from the PR title.
3. GitHub Mode Steps 1–4 run as normal: 3 threads fetched, all unresolved; classified 2 auto-fix, 1 pushback; re-fetch confirms nothing changed since classification.
4. Before any fixing begins: comment posted on OIQ-88 — "Code review found 2 issues on PR #219 (link): (1) minor — missing backoff cap on retry loop, (2) minor — unclear log level on retry exhaustion. Starting fixes now." — then `getTransitionsForJiraIssue` finds "In Progress" available from the ticket's current status ("To Do") → transitioned via `transitionJiraIssue`.
5. GitHub Mode Steps 5–7 run as normal: both auto-fix items fixed with tests and committed, the pushback item replied to and left unresolved, 2 commits pushed.
6. After fixing work finishes: completion comment posted on OIQ-88 — "PR #219 updated: added a retry cap and clarified the exhaustion log level, both with tests (2 commits pushed). One suggestion (switching to exponential backoff) was left as-is with reasoning on the thread — the fixed linear cap already meets the ticket's requirement. Ready for a new review round."
7. Report: "2 threads fixed, 1 rejected with reasoning, 2 commits pushed to PR #219. Jira: OIQ-88 moved to In Progress, starting and completion comments posted."
