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
  version: "1.0.0"
---

# Ship Spec

Delivers a tlc-spec-driven feature from "tasks are written" to "draft PR open with findings published," then handles the comment-triage round that follows.

## Guardrails

### Scope

- Do NOT run against a feature with no `tasks.md` — that means the Tasks phase never completed.
- Do NOT reimplement anything tlc-spec-driven's Execute phase already owns: task execution, atomic commits, gate checks, the end-of-feature Verifier. Invoke it; don't duplicate it.
- Do NOT auto-fix, filter, or withhold `code-review`/`tests-code-review` findings before publishing — every finding from both skills is posted, unfiltered, every run.
- Do NOT submit, approve, or request-changes on the PR review — pending state only, same as `code-review`/`tests-code-review`'s own GitHub PR Constraints.
- Do NOT create GitHub Issues.
- Do NOT re-run `code-review`/`tests-code-review` after comment-triage fixes — the user reviews those manually.

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
4. If Execute reports success (all tasks committed, Verifier passed): continue to Step 4.
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

For each of `code-review` and `tests-code-review`, in turn:

1. Invoke it in **GitHub PR mode** against the PR number from Step 5 (e.g. "review PR #N" / "review tests on PR #N"). It self-collects the diff via `gh` (or MCP), runs its own dimension agents, and returns its local findings report exactly as it does standalone.
2. Immediately instruct it to post **all** findings: this is the "user explicitly selects which findings to post" step each skill's GitHub PR Constraints require — `/ship-spec` being invoked at all *is* that explicit instruction, made once, for every finding, because this PR was opened specifically to carry them for review. Do not filter by severity, do not skip either skill, do not ask again per finding.

Each skill posts via its own existing Step 9 / [GitHub PR Mode — Step B](../../templates/github-pr-review-mode.md) mechanics: pending review state, `event` field omitted, never submitted, each comment anchored to its exact line.

## Step 7: Report

Report the PR URL, and the finding count from each skill (e.g. "12 findings from code-review, 4 from tests-code-review, all posted as pending review comments"). Stop. Wait for the user.

## Comment-Triage Mode

Entered per Step 1 when the target branch already has an open PR. The user has been reviewing and commenting on it directly in GitHub.

1. Fetch open review threads via GraphQL `reviewThreads` (see [GitHub Delivery Mechanics](references/github-delivery.md) for the exact query). Skip threads already `isResolved: true`.
2. For each unresolved thread, read the human's comment and classify it:
   - **Fix instruction** — a directive on what to change.
   - **Question or opinion** — something being asked or solicited.
   For either kind, agree and act (fix the code, or answer as asked) or push back with a better approach / different answer when one exists — never comply blindly.
3. Process threads one at a time, directly — no batch "here's my plan" step first; invoking this mode is itself the user's go-ahead.
4. For a fix: make the change as a normal atomic commit following tlc-spec-driven's Conventional Commits + atomic-commit convention (same as Step 3 uses). For a question: no commit, just an answer.
5. Reply on that thread explaining what changed (or answering the question), then resolve it via GraphQL `resolveReviewThread` (see [GitHub Delivery Mechanics](references/github-delivery.md)).
6. If any commits were made: `git push` to the existing feature branch — this updates the same open PR, no new PR is created.
7. Report a short summary: threads processed, commits pushed (if any). Do not re-run `code-review` or `tests-code-review` — the user does their own manual pass after this.

## Examples

### Example 1: First delivery run

User: `/ship-spec base=main task_id=PROJ-42`

1. Step 1: no `feature/*` branch checked out yet with an open PR → Delivery Mode
2. Step 2: feature resolved from `.specs/STATE.md` Handoff; base=`main`, task_id=`PROJ-42` both given inline; `tasks.md` confirmed present; description slug generated as `rate-limiting` from the feature folder's own slug
3. Step 3: checkout `main` → branch `feature/PROJ-42_rate-limiting` → Execute runs all tasks, Verifier passes
4. Step 4: push
5. Step 5: `gh pr create --draft` → PR #128, title `[PROJ-42] Add rate limiting to the orders API`, body assembled from `spec.md`/`tasks.md`/`commits.md`/`validation.md`
6. Step 6: `/code-review` reviews PR #128 (9 findings) → posted all 9 as pending comments; `/tests-code-review` reviews PR #128 (3 findings) → posted all 3
7. Step 7: "PR #128 opened as draft: <url>. 12 findings published as pending review comments (9 code-review, 3 tests-code-review)."

### Example 2: Comment-triage round

User: `/ship-spec` (on branch `feature/PROJ-42_rate-limiting`, PR #128 already open)

1. Step 1: `feature/PROJ-42_rate-limiting` has an open PR → Comment-Triage Mode
2. Fetch 5 unresolved review threads
3. Thread 1: "extract this into a helper" → fix instruction → refactor, commit `refactor(orders): extract rate-limit check into helper`, reply + resolve
4. Thread 2: "why didn't you use a token bucket here?" → question → reply explaining the sliding-window choice and its tradeoff, resolve
5. Thread 3: reviewer's suggestion is worse than the current approach → push back in the reply with the reasoning, resolve
6. ...remaining threads processed the same way
7. Push (1 new commit) → "3 threads fixed (1 commit pushed), 2 threads answered. PR #128 updated."
