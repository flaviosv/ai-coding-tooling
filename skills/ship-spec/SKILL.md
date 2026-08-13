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
  or task breakdown (use tlc-spec-driven), for reviewing code outside this delivery flow (use
  code-review / tests-code-review / complete-review directly), or for fixing PR review comments
  outside this delivery flow (use fix-review directly).
metadata:
  author: Flavio Studart
  version: "1.7.0"
---

# Ship Spec

Delivers a tlc-spec-driven feature from "tasks are written" to "draft PR open with findings published," then handles the comment-triage round that follows.

## Guardrails

### Scope

- Do NOT run against a feature with no `tasks.md` — that means the Tasks phase never completed.
- Do NOT reimplement anything tlc-spec-driven's Execute phase already owns: task execution, atomic commits, gate checks, the end-of-feature Verifier. Invoke it; don't duplicate it.
- Do NOT reimplement anything `complete-review` already owns for Step 6: the subagent-isolation pattern, unfiltered findings, the single merged pending-review POST, partial/full-failure retry handling, and the never-submit/approve/request-changes rule. Invoke it; don't duplicate it — see `complete-review`'s own SKILL.md for those guardrails.
- Do NOT reimplement anything `fix-review` already owns for Comment-Triage Mode: fetching threads fresh from GitHub, classifying by the full thread exchange (not just the newest comment), the never-guess-on-an-unclear-item rule, drafting/committing fixes with test coverage, replying to or resolving threads, and the never-a-new-PR rule. Invoke it; don't duplicate it — see `fix-review`'s own SKILL.md for those guardrails.
- Do NOT re-run `code-review`/`tests-code-review`/`complete-review` after `fix-review`'s fixes — the user reviews those manually.
- Do NOT invoke `architecture-evaluate` directly in this conversation for Step 8 — always delegate through an isolated subagent: its incremental-mode scan and file-by-file doc content don't need to live in ship-spec's own context, only the final compact summary does.
- Do NOT set `isolation: worktree` on the Step 8 subagent — it must share the current checkout (the feature branch already checked out locally), not a separate worktree, so a Step 8 doc-sync commit lands ready for the existing `git push` step.
- Do NOT push Step 8's doc-sync commit when every `docs/codebase/` file it touched came back brand new (untracked) — that signals a first-time full generation the user should review before it lands in the repo. Push only when at least one touched file already existed (was already tracked), even if the rest — say, a newly added file scope — are newly created.
- If the Step 6 `complete-review` invocation itself fails to complete (skill-invocation error — distinct from a partial finding failure, which `complete-review` already retries internally per its own guardrails): retry once with a fresh invocation. If it fails a second time, stop and report the failure — do not fabricate a finding count or claim a review was published.
- If the Comment-Triage `fix-review` invocation itself fails to complete (skill-invocation error — distinct from a per-item blocker, which `fix-review` already retries internally per its own guardrails): retry once with a fresh invocation. If it fails a second time, stop and report the failure — do not fabricate a summary or claim fixes were applied.
- If a Step 8 subagent reports it could not complete (a doc-sync blocker): retry once with a fresh subagent. If it fails a second time, stop and report the failure — do not fabricate a doc-sync outcome.

### Before Starting

- Target feature's `.specs/features/<feature>/tasks.md` must exist. Missing → stop: "No tasks.md for this feature — run tlc-spec-driven's Tasks phase first."
- `gh auth status` must succeed, or GitHub MCP tools must be available. Neither → stop before touching git: "No way to reach GitHub — install/authenticate `gh`, or connect a GitHub MCP server."
- `git status --porcelain` must be clean before checkout. Dirty → stop and report the exact output (which files, staged or not) — do not stash, commit, discard, or otherwise touch them yourself under any circumstance. State that uncommitted changes are present and wait for the user to decide how to handle them (commit, stash, discard, or something else); only resume once they've done so and the tree is clean.

### Before Opening the PR

Execute (Step 3) must have completed with every task committed and the Verifier passed. If Execute's own bounded fix-loop can't converge: stop, report what failed, do not push, do not open a PR. A PR with unresolved implementation problems isn't a draft worth reviewing — it's nothing yet.

### When to Stop and Ask

- No `base` argument and none inferable → ask which branch to check out from.
- No `task_id` argument → always ask for one, even when the feature folder's name carries what looks like a tracker-ID prefix. Never derive it from the folder name and never fall back to the bare slug silently.
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

**Task ID:** use the `task_id=` argument if given. Otherwise, always ask — never derive it from the feature folder's name, even when it carries what looks like a tracker-ID prefix (e.g. `.specs/features/PROJ-42-user-auth/`). Do not fall back to the bare slug.

**Description slug:** generate a short kebab-case slug (2–4 words) summarizing the feature — reuse the feature folder's own slug portion when present (`.specs/features/PROJ-42-user-auth/` → `user-auth`), otherwise derive one from `spec.md`'s title. This is generated, never asked for.

Guard check: confirm `.specs/features/<feature>/tasks.md` exists for the resolved feature. Missing → stop per Guardrails.

## Step 3: Branch and Execute

1. `git checkout <base>`.
2. `git checkout -b feature/<task_id>_<description>` (see Guardrails → On Collision if it already exists).
3. Invoke tlc-spec-driven's Execute phase for every task in `.specs/features/<feature>/tasks.md`. It owns its own per-task gate checks, atomic Conventional-Commits commits, and the mandatory end-of-feature Verifier — do not add parallel logic for any of that here.
4. If Execute reports success (all tasks committed, Verifier passed): tell the user the implementation is confirmed done and continue directly to Step 4 — no `/compact` prompt here; that comes after the PR is opened (see Step 5).
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

Tell the user the PR is open (include the URL) and ask them to run `/compact` before continuing — context built up over Execute's task loop and the push/PR steps is no longer needed for what follows (Step 6's review runs entirely inside its own isolated subagent). Wait for their go-ahead, then continue to Step 6. (This is a recommendation, not something `ship-spec` can trigger itself — nothing here forces or verifies that `/compact` actually ran.)

## Step 6: Review and Publish

Invoke the `complete-review` skill for the PR opened in Step 5 ("run complete-review for PR #N, just opened"), stating the PR number explicitly so its own PR-resolution step doesn't need to ask. `complete-review` owns the full review-and-publish mechanics itself — spawning its own isolated subagent to run `code-review` and `tests-code-review` concurrently in Return-Only Variant, merging their findings, and issuing the single pending-review `POST` — so none of that logic is duplicated here. It returns one compact result: each skill's total finding count and a per-severity breakdown, or a failure reason in place of counts if either or both invocations ultimately failed. See `complete-review`'s own SKILL.md for its exact guardrails (partial-failure retry, the one-pending-review-per-PR constraint, never submitting/approving).

## Step 7: Report

Report the PR URL, and the finding count from each skill (e.g. "12 findings from code-review, 4 from tests-code-review, all posted as pending review comments"). If Step 6 hit a full failure (both invocations failed, no review posted — see Guardrails), report the PR URL alongside both failure reasons instead — never claim findings were published when they weren't. Continue directly to [Step 8: Sync Architecture Docs](#step-8-sync-architecture-docs) — no user wait in between.

## Step 8: Sync Architecture Docs

The shared true end of a ship-spec run — both Step 7 (Delivery Mode) and Comment-Triage Mode's own final step continue here, since either one leaves the codebase with committed changes that `docs/codebase/` may not yet reflect.

Delegate to a single isolated subagent, same rationale as Step 6 — `architecture-evaluate`'s incremental mode reads the full git diff and produces file-by-file doc content; none of that needs to live in ship-spec's own context, only the final compact summary does.

1. Spawn one subagent (`Agent` tool, `agentType: general-purpose`, `model: sonnet`, `run_in_background: false`) whose prompt instructs it to, within its own conversation:
   a. Invoke `architecture-evaluate` in **Incremental mode** ("update docs") to sync `docs/codebase/` and any other context files it owns (inline API docs, root `README.md`/`CLAUDE.md`/`AGENTS.md`) against the current git state. There is no restriction on writing or updating these files — always let architecture-evaluate make whatever updates it determines are needed.
   b. Run `git status --porcelain -- docs/codebase/` and classify every file it touched (created or modified) as **new** (`??`, untracked) or **existing** (already tracked). If nothing under `docs/codebase/` was touched (e.g. nothing relevant changed since the last sync), return a compact result saying no doc changes were needed and stop here — no commit, no push.
   c. If **every** touched `docs/codebase/` file is new: do NOT stage, commit, or push anything from this sync — leave the written files exactly as they are, untracked, for the user to review manually. This is the first-time-full-generation case (see Guardrails).
   d. Otherwise (at least one touched `docs/codebase/` file was already tracked — including a mix where only a few files are newly created and the rest pre-existed, e.g. a newly added file scope alongside routine updates): stage and commit everything `architecture-evaluate` touched in this sync (`docs/codebase/` plus any inline/root doc updates) as one Conventional Commits commit (e.g. `docs: sync codebase context after <task_id>`), then `git push` to the current branch — this updates the same open PR, no new PR created.
   e. Return one compact result: counts of files touched (new vs. existing), whether the sync was committed and pushed or left uncommitted for review, and the commit message if one was made.
2. Report the outcome as part of this run's final report (e.g. "Architecture docs synced: 2 files updated, both already tracked — committed and pushed" or "Architecture docs synced: 9 files generated, all new — left uncommitted for your review"). Stop. Wait for the user — this is the true end of a ship-spec run, delivery or triage.

## Comment-Triage Mode

Entered per Step 1 when the target branch already has an open PR. The user has been reviewing and commenting on it directly in GitHub.

Invoke the `fix-review` skill for this PR ("run fix-review for PR #N; this is a tlc-spec-driven session — the active feature is `<feature>`, use it for the audit-trail plan file"), stating both the PR number and the active feature explicitly so `fix-review`'s own PR-resolution step doesn't need to ask, and so it writes its plan to `.specs/features/<feature>/fix-code-review.md` per its own guardrails. `fix-review` owns the full triage mechanics itself — fetching threads fresh from GitHub, classifying each by its full exchange (not just the newest comment), drafting and committing fixes with test coverage, replying to or resolving threads, and pushing to the existing branch. It returns one compact result: threads processed by classification (including any left unclear or blocked, with reasons), commits pushed, and any page-size-cap note. Report that result, then continue directly to [Step 8: Sync Architecture Docs](#step-8-sync-architecture-docs) — no user wait in between. See `fix-review`'s own SKILL.md for its exact guardrails (GitHub as source of truth, never guessing on an unclear item, the never-a-new-PR rule).

## Examples

### Example 1: First delivery run

User: `/ship-spec base=main task_id=PROJ-42`

1. Step 1: no `feature/*` branch checked out yet with an open PR → Delivery Mode
2. Step 2: feature resolved from `.specs/STATE.md` Handoff; base=`main`, task_id=`PROJ-42` both given inline; `tasks.md` confirmed present; description slug generated as `rate-limiting` from the feature folder's own slug
3. Step 3: checkout `main` → branch `feature/PROJ-42_rate-limiting` → Execute runs all tasks, Verifier passes
4. Step 4: push
5. Step 5: `gh pr create --draft` → PR #128, title `[PROJ-42] Add rate limiting to the orders API`, body assembled from `spec.md`/`tasks.md`/`commits.md`/`validation.md`
6. Step 6: invoke `complete-review` for PR #128 — it spawns its own isolated subagent, runs `code-review`'s and `tests-code-review`'s Return-Only Variant analysis concurrently (9 findings, 3 findings), merges them into one `comments` array, and posts a single pending review covering all 12 findings; returns one compact result covering both
7. Step 7: "PR #128 opened as draft: <url>. 12 findings published as one pending review (9 code-review, 3 tests-code-review)."
8. Step 8: another Sonnet subagent runs `architecture-evaluate` incremental mode → `docs/codebase/ARCHITECTURE.md` and `STACK.md` are updated (both already tracked, 0 new files) → commits `docs: sync codebase context after PROJ-42` and pushes to `feature/PROJ-42_rate-limiting` → returns "2 files updated, both existing, committed and pushed". Final report: "PR #128 opened as draft: <url>. 12 findings published as one pending review (9 code-review, 3 tests-code-review). Architecture docs synced (2 files updated) and pushed."

### Example 2: Comment-triage round

User: `/ship-spec` (on branch `feature/PROJ-42_rate-limiting`, PR #128 already open)

1. Step 1: `feature/PROJ-42_rate-limiting` has an open PR → Comment-Triage Mode
2. Invoke `fix-review` for PR #128, feature `PROJ-42_rate-limiting`. Inside its own conversation, `fix-review` runs its GitHub Mode: the Step-6 review was already submitted (not pending) → fetches 6 threads (1 still `PENDING` on a newer, separate review → skipped; 5 published and unresolved), reads each thread's full exchange and classifies: Thread 1 (`tests-code-review` finding, no comment) → **auto-fix**; Thread 2 (`code-review` finding, no comment) → **auto-fix**; Thread 3 ("why didn't you use a token bucket here?") → **answer-only**; Thread 4 (`code-review` finding, then "yes, fix this") → **apply-as-directed**; Thread 5 (`code-review` finding, then a weaker suggested approach that doesn't hold up) → **pushback** → writes `fix-code-review.md` (feature is active) → re-fetches, nothing changed → drafts T1/T2/T4 concurrently (3 Haiku subagents, each with its own test) → commits one at a time (`test(orders): cover rate-limit edge case`, `refactor(orders): extract rate-limit check into helper`, thread 4's directed fix) → resolves T1/T2/T4 silently, replies to Thread 3 (left unresolved) and Thread 5 (rejection reasoning, then resolved) → pushes 3 commits → returns "5 threads processed (3 fixed, 1 rejected, 1 answered and left open), 1 pending thread left untouched"
3. Report: "5 threads processed (3 fixed, 1 rejected, 1 answered and left open), 1 pending thread left untouched. PR #128 updated."
4. Step 8: a Sonnet subagent runs `architecture-evaluate` incremental mode → the triage fixes touched a new module, so `docs/codebase/INTEGRATIONS.md` is created (new) alongside updates to the already-tracked `ARCHITECTURE.md` and `CONVENTIONS.md` → since not every touched file is new, it commits `docs: sync codebase context after PROJ-42` and pushes → returns "3 files updated, 1 new, 2 existing, committed and pushed". Final report: "5 threads processed (3 fixed, 1 rejected, 1 answered and left open), 1 pending thread left untouched. PR #128 updated. Architecture docs synced (3 files, 1 new) and pushed."
