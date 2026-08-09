---
name: ship-spec
description: >
  Delivers a completed tlc-spec-driven feature end-to-end: creates the feature branch, runs
  tlc-spec-driven's Execute phase for every task, pushes and opens a GitHub draft PR once tests
  pass, then runs code-review and tests-code-review against the PR and publishes every finding as
  pending PR comments. Re-invoking it against a feature that already has an open PR switches to
  comment-triage mode — fetches your PR review-thread comments and fixes or replies to each.
  Invoked explicitly via /ship-spec only — it never triggers on natural language (saying "implement
  the spec" routes to tlc-spec-driven's own Execute phase, not here). Requires an existing
  tlc-spec-driven feature (`.specs/features/*/tasks.md`) and the `gh` CLI. Do NOT use for planning
  or task breakdown (use tlc-spec-driven), or for reviewing code outside this delivery flow (use
  code-review / tests-code-review directly).
metadata:
  author: Flavio Studart
  version: "1.3.0"
---

# Ship Spec

Delivers a tlc-spec-driven feature from "tasks are written" to "draft PR open with findings published," then handles the comment-triage round that follows.

## Guardrails

### Scope

- Do NOT run against a feature with no `tasks.md` — that means the Tasks phase never completed.
- Do NOT reimplement anything tlc-spec-driven's Execute phase already owns: task execution, atomic commits, gate checks, the end-of-feature Verifier. Invoke it; don't duplicate it.
- Do NOT auto-fix, filter, or withhold `code-review`/`tests-code-review` findings before publishing — every finding from both skills is posted, unfiltered, every run.
- Do NOT invoke `code-review`/`tests-code-review` directly in this conversation — always delegate through a single isolated Sonnet subagent that runs both (concurrently, inside its own turn), per Step 6. Both skills self-collect a full diff and produce a full findings report; none of that belongs in ship-spec's own context — only the subagent's final compact summary does.
- Do NOT submit, approve, or request-changes on the PR review — pending state only, same as `code-review`/`tests-code-review`'s own GitHub PR Constraints.
- Do NOT create GitHub Issues.
- Do NOT re-run `code-review`/`tests-code-review` after comment-triage fixes — the user reviews those manually.
- Do NOT act on a review thread whose review is still pending/unsubmitted — comment-triage only processes **published** (submitted) review comments. Step 6's own pending review sits untouched until the user submits it.
- Do NOT add explanatory code comments when fixing a finding, unless the code is genuinely non-obvious (complex algorithm, subtle invariant, external constraint) — the fix should read as self-explanatory, same standard as any other change.
- Do NOT implement a comment-triage fix directly in this conversation — delegate the read/edit/test/commit work to an isolated Sonnet subagent per Comment-Triage Mode's fix step; keep only classification and reply/reject reasoning here.
- Do NOT resolve a thread still under discussion — a question you replied to stays open in case the user follows up; only they resolve it once satisfied.
- GitHub allows only **one pending (unsubmitted) review per identity per PR at a time** — a second `POST .../reviews` call while one is already pending returns HTTP 422 ("A review cannot be created because a pending review already exists"), and there is no API to incrementally add comments to an already-open pending review. This means Step 6's subagent must issue **exactly one** `POST .../reviews` call per run, after merging both skills' findings — never one POST per skill. `code-review` and `tests-code-review`'s analysis invocations MAY run concurrently within the subagent (see Step 6) precisely because neither one writes to GitHub — only the single merged POST does.
- On a partial failure (one invocation's analysis returned findings, the other didn't) within Step 6's subagent: retry ONLY the failed invocation once, scoped to that skill alone — never re-run the invocation that already returned findings. Issue the single merged POST only after both invocations have resolved (success or final failure) — never post twice, and never post before both have resolved.
- Do NOT set `isolation: worktree` on the Step 6 or Comment-Triage subagents — they must share the current checkout (the feature branch already checked out locally), not a separate worktree, so a triage fix lands as a commit ready for the existing `git push` step.
- If a Step 6 or Comment-Triage subagent reports it could not complete (PR not found, auth failure, skill-invocation error, or — for a triage fix — a blocker it can't resolve): retry once with a fresh subagent (for a Step 6 partial failure, scoped to the failed skill only — see above). If it fails a second time, stop and report the failure — do not fabricate a finding count, skip a skill, or mark a triage thread resolved on a failed fix.

### Before Starting

- Target feature's `.specs/features/<feature>/tasks.md` must exist. Missing → stop: "No tasks.md for this feature — run tlc-spec-driven's Tasks phase first."
- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop before touching git: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- `git status --porcelain` must be clean before checkout. Dirty → stop: "Uncommitted changes present — commit, stash, or discard them first."

### Before Opening the PR

Execute (Step 3) must have completed with every task committed and the Verifier passed. If Execute's own bounded fix-loop can't converge: stop, report what failed, do not push, do not open a PR. A PR with unresolved implementation problems isn't a draft worth reviewing — it's nothing yet.

### When to Stop and Ask

- No `base` argument and none inferable → ask which branch to check out from.
- No `task_id` argument, and the feature folder has no tracker-ID prefix (e.g. `.specs/features/code-review-subagent-orchestration/` has none) → ask for one. Never fall back to the bare slug silently.
- More than one tlc-spec-driven feature exists and none is unambiguous from session context → list the candidates and ask.

### On Collision

If `feature/<task_id>_<description>` already exists locally or on the remote: ask whether to continue on it or use a different task_id — never silently overwrite or force-push over it.

### Credentials

Never print `gh auth token` output or any token/credential value. Reference `gh`'s own auth state by status only ("authenticated" / "not authenticated").

## Step 1: Mode Detection

Determine which of the two modes this invocation is:

1. Resolve the target feature (see Step 2 for how). If the current branch matches `feature/*` and `gh pr view --json number,isDraft,url` succeeds against it (an open PR exists for this branch): **Comment-Triage Mode** — skip to [Comment-Triage Mode](#comment-triage-mode).
2. Otherwise: **Delivery Mode** — continue to Step 2.

This is the entire mode switch. There is no separate sub-command — re-invoking `/ship-spec` against a feature that already shipped a PR resumes the comment-triage round instead of starting a new delivery.

## Step 2: Feature, Base Branch, and Task ID Resolution

**Feature:** try `.specs/STATE.md`'s Handoff section for an in-progress feature from the current session. If that's absent or ambiguous, and more than one `.specs/features/*/tasks.md` exists, list them and ask. If exactly one exists, use it without asking.

**Base branch:** use the `base=` argument if given (e.g. `/ship-spec base=main task_id=PROJ-42`). Otherwise ask.

**Task ID:** use the `task_id=` argument if given. Otherwise, derive it from the feature folder's tracker-ID prefix (`.specs/features/PROJ-42-user-auth/` → `PROJ-42`). If the folder has no prefix, ask — do not fall back to the bare slug.

**Description slug:** generate a short kebab-case slug (2–4 words) summarizing the feature — reuse the feature folder's own slug portion when present (`.specs/features/PROJ-42-user-auth/` → `user-auth`), otherwise derive one from `spec.md`'s title. This is generated, never asked for.

Guard check: confirm `.specs/features/<feature>/tasks.md` exists for the resolved feature. Missing → stop per Guardrails.

## Step 3: Branch and Execute

1. `git checkout <base>`.
2. `git checkout -b feature/<task_id>_<description>` (see Guardrails → On Collision if it already exists).
3. Invoke tlc-spec-driven's Execute phase for every task in `.specs/features/<feature>/tasks.md`. It owns its own per-task gate checks, atomic Conventional-Commits commits, and the mandatory end-of-feature Verifier — do not add parallel logic for any of that here.
4. If Execute reports success (all tasks committed, Verifier passed): tell the user the implementation is confirmed done and ask them to run `/compact` before continuing — context built up over Execute's task loop is no longer needed for what follows. Wait for their go-ahead, then continue to Step 4. (This is a recommendation, not something `ship-spec` can trigger itself — nothing here forces or verifies that `/compact` actually ran.)
5. If Execute's bounded fix-loop can't converge: stop per Guardrails → Before Opening the PR.

## Step 4: Push

`git push -u origin feature/<task_id>_<description>`.

## Step 5: Open the Draft PR

Use `gh pr create --draft` (fall back to the GitHub MCP tool for PR creation, then to `gh api graphql` with the `createPullRequest` mutation, only if `gh` itself is unavailable — see [GitHub Delivery Mechanics](references/github-delivery.md) for the exact fallback commands).

- Title includes `<task_id>`.
- Body sections, sourced from existing spec artifacts — invent nothing new:
  - **Problem** ← `.specs/features/<feature>/spec.md`
  - **What was done** ← `.specs/features/<feature>/tasks.md` (completed checklist) and `commits.md` (atomic commit log)
  - **Test results** ← `.specs/features/<feature>/validation.md` (the Verifier's report — already captures final pass/coverage state; do not re-run tests separately for this)

Record the returned PR number.

## Step 6: Review and Publish

Delegate to a single isolated subagent rather than invoking either skill in this conversation — both skills self-collect a full diff and produce a full findings report internally; none of that needs to live in ship-spec's own context, only the final compact summary does.

1. Spawn one subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: false`) whose prompt instructs it to, within its own conversation:
   a. Issue two concurrent tool calls in the same turn (not sequential awaits) — one invoking `code-review` in **GitHub PR mode, Return-Only Variant**, against the PR number from Step 5 ("review PR #N; return findings only, do not post"), one invoking `tests-code-review` the same way ("review tests on PR #N; return findings only, do not post"). Neither invocation touches GitHub — each only assembles its `comments` array (`path`/`line`/`body` per finding) and returns it. This satisfies the "user explicitly selects which findings to post" step each skill's GitHub PR Constraints require, satisfied once by `/ship-spec` being invoked at all, for every finding, because this PR was opened specifically to carry them for review (do not filter by severity, do not ask again per finding).
   b. Once both invocations have resolved (success or final failure after the scoped retry — see Guardrails), merge both `comments` arrays into one (or use just the succeeded one's, on an unrecovered partial failure) and issue **exactly one** `gh api repos/{owner}/{repo}/pulls/{PR}/reviews --method POST --input payload.json` call, `event` field omitted (pending state) — GitHub allows only one pending review per identity per PR at a time (see Guardrails), so this POST must never fire more than once per run.
   c. Return **only** one compact result covering both: each skill's total finding count and a per-severity breakdown. If one skill's invocation ultimately failed, return its failure reason in place of its counts — the other skill's result, if it succeeded, is still reported normally (see Guardrails for the scoped retry rule).

Running both analysis invocations concurrently inside one subagent conversation is safe precisely because neither writes to GitHub — the one-pending-review-per-PR constraint (see Guardrails) is respected by construction, since only step 1b's single merged POST ever writes to GitHub.

Each skill assembles its findings via its own existing Step 9 / [GitHub PR Mode — Step B2' Return-Only Variant](../../templates/github-pr-review-mode.md), returning its `comments` array to this subagent instead of posting — this produces exactly ONE pending review covering both skills' findings, not two. Only the one compact summary returns to ship-spec's own conversation — not the underlying diffs, findings text, or comments arrays.

## Step 7: Report

Report the PR URL, and the finding count from each skill (e.g. "12 findings from code-review, 4 from tests-code-review, all posted as pending review comments"). Stop. Wait for the user.

## Comment-Triage Mode

Entered per Step 1 when the target branch already has an open PR. The user has been reviewing and commenting on it directly in GitHub.

1. Fetch open review threads via GraphQL `reviewThreads` (see [GitHub Delivery Mechanics](references/github-delivery.md) for the exact query). Skip threads already `isResolved: true`. Skip any thread whose review is still `PENDING` (unsubmitted) — only threads on a **published** (submitted) review are in scope; a pending review means the user is still triaging, not asking you to act.
2. For each unresolved, published thread, classify by whether the user added a comment and what it says — applied identically regardless of which skill produced the underlying finding (`code-review` and `tests-code-review` findings follow the exact same rule):
   - **auto-fix** — no user comment on the thread. Fix it directly, no exceptions, no pushback.
   - **answer-only** — the comment is phrased as, or amounts to, a question. Reply with the answer; don't fix unless the answer implies a change. Leave the thread unresolved — it's still under discussion; only the user resolves it once satisfied.
   - **apply-as-directed** — the comment suggests an approach and it validates (it confirms/directs the fix, or holds up as sound on inspection). Fix it as directed.
   - **pushback** — the comment suggests an approach that doesn't validate (you disagree with it, or it doesn't hold up on inspection). Don't comply blindly: reply rejecting it with your reasoning (and the approach you're taking instead, if any). Leave the thread unresolved.
   - **standalone comment, not anchored to a code-review/tests-code-review finding** — same apply-as-directed-or-pushback treatment as above: fix it with the approach the user suggested if it validates; otherwise reply rejecting it with your reasoning.
3. Write the classified plan to `.specs/features/<feature>/fix-code-review.md` before any execution — a flat list grouped into `## Parallel` (independent items — no two touch the same file) and `## Sequential` (items sharing a file, processed in encounter order). Each entry: thread ID, classification (auto-fix / answer-only / apply-as-directed / pushback), `path:line`, and a one-line fix direction (or, for answer-only/pushback, the reply direction — these appear in the plan for audit-trail completeness but are excluded from the draft/commit steps below, since they resolve via reply-only, not a commit). If zero threads were found, still write the file noting zero items, then stop — do not proceed to step 4.
4. Immediately after writing the plan — **no approval gate**; invoking this mode with "fix the findings" is itself the user's go-ahead — perform one more GraphQL fetch of the same `reviewThreads` query, diff it against the plan just written, and silently drop from execution any item no longer present, already resolved, or changed since the first fetch. No further per-item GitHub reads follow this; it's the only staleness check performed.
5. For the auto-fix and apply-as-directed items surviving step 4: draft fixes concurrently, capped at 4 subagents at a time (`Agent` tool, `agentType: general-purpose`, `model: claude-haiku-4-5-20251001`, `run_in_background: false`), one per item in the `## Parallel` bucket — each drafting subagent performs only the investigation/fix-drafting for its one item (no file edits, no git operations) and returns its proposed change, or a blocker reason if it can't complete. Batches of more than 4 `## Parallel` items process in successive groups of up to 4 concurrent drafts. `## Sequential`-bucket items are drafted one at a time, in order, using the same subagent shape — no concurrency for this bucket. Once a draft is ready, apply it and commit **one item at a time — never two commits concurrently** on the shared checkout — following tlc-spec-driven's Conventional Commits + atomic-commit convention (same as Step 3 uses), running only that item's own directly relevant test(s), not a full gate/verify cycle. If a drafted change no longer matches current file state at commit time, mark the item blocked instead of force-applying it (see Guardrails for the retry rule). For an answer-only or pushback item: no commit, no drafting subagent — compose the reply directly in this conversation, on the default model (never Haiku) — the classification and reasoning from step 2 stays in this conversation throughout.
6. Reply on that thread, or resolve it silently, per its step-2 classification: **auto-fix** and **apply-as-directed** — resolve via GraphQL `resolveReviewThread` (see [GitHub Delivery Mechanics](references/github-delivery.md)) with **no reply comment posted** — the fix itself is the answer, and posting a confirmatory "done" reply is an avoidable extra write. **pushback** — reply with the rejection reasoning (and the approach taken instead, if any), then resolve — that's a closed decision. **answer-only** — reply with the answer only; leave the thread unresolved, the discussion may still be open; only the user resolves it once satisfied.
7. If any commits were made: `git push` to the existing feature branch — this updates the same open PR, no new PR is created.
8. Report a short summary: threads processed, commits pushed (if any), items blocked after a failed retry (with the reason), and any items dropped by step 4's staleness check. Do not re-run `code-review` or `tests-code-review` — the user does their own manual pass after this.

## Examples

### Example 1: First delivery run

User: `/ship-spec base=main task_id=PROJ-42`

1. Step 1: no `feature/*` branch checked out yet with an open PR → Delivery Mode
2. Step 2: feature resolved from `.specs/STATE.md` Handoff; base=`main`, task_id=`PROJ-42` both given inline; `tasks.md` confirmed present; description slug generated as `rate-limiting` from the feature folder's own slug
3. Step 3: checkout `main` → branch `feature/PROJ-42_rate-limiting` → Execute runs all tasks, Verifier passes
4. Step 4: push
5. Step 5: `gh pr create --draft` → PR #128, title `[PROJ-42] Add rate limiting to the orders API`, body assembled from `spec.md`/`tasks.md`/`commits.md`/`validation.md`
6. Step 6: one Sonnet subagent invokes `code-review` on PR #128 → 9 findings posted as pending comments; then, sequentially within the same subagent, invokes `tests-code-review` on PR #128 → 3 findings posted; returns one compact result covering both
7. Step 7: "PR #128 opened as draft: <url>. 12 findings published as pending review comments (9 code-review, 3 tests-code-review)."

### Example 2: Comment-triage round

User: `/ship-spec` (on branch `feature/PROJ-42_rate-limiting`, PR #128 already open)

1. Step 1: `feature/PROJ-42_rate-limiting` has an open PR → Comment-Triage Mode
2. Fetch 6 review threads: 1 still `PENDING` (not yet submitted) → skipped; 5 published and unresolved → processed
3. Thread 1: a `tests-code-review` finding, no user comment → always fix → Sonnet subagent implements and commits `test(orders): cover rate-limit edge case`, reply + resolve
4. Thread 2: a `code-review` finding, no extra comment → fix directly → Sonnet subagent implements and commits `refactor(orders): extract rate-limit check into helper`, reply + resolve
5. Thread 3: "why didn't you use a token bucket here?" → question → reply explaining the sliding-window choice and its tradeoff (no subagent — no fix involved), left unresolved — discussion may continue
6. Thread 4: `code-review` finding + user comment "yes, fix this" → fix as directed → Sonnet subagent implements and commits, reply + resolve
7. Thread 5: `code-review` finding + user comment suggesting a worse approach → reject in the reply with reasoning, no commit, resolve
8. Push (3 new commits) → "5 threads processed (3 fixed, 1 rejected, 1 answered and left open), 1 pending thread left untouched. PR #128 updated."
