---
name: code-review
description: >
  Reviews code and fixes what the review finds, as one run: a review stage dispatches Sonnet
  agents per dimension (architecture, code quality, performance, regression, security,
  requirements; test coverage, gaps, isolation, clarity, maintainability) over local changes,
  commits, or a GitHub PR; an optional human checkpoint (human_review, default false) lets you
  edit the findings; a fix stage then fixes what remains, runs targeted tests, pushes, and replies
  to and resolves every PR thread. All GitHub writes go through a verifying script. Also fixes
  existing review comments on a PR, and batch-sweeps PRs awaiting your review or where you
  requested changes. Technology agnostic via docs/codebase context. Use when the user says
  "review my code", "review my tests", "review PR #123", "fix review comments", "fix the PRs I
  requested changes on", "review my pending PRs", or invokes /code-review. Do NOT use to write new
  tests or for spec planning (use tlc-spec-driven).
metadata:
  version: "4.0.0"
  triggers:
    - "apply the review fixes"
    - "batch-fix my change requests"
    - "check my code"
    - "check tests"
    - "code review"
    - "code review the"
    - "complete review"
    - "do a code review"
    - "fix review comments"
    - "fix review findings"
    - "fix the PRs I requested changes on"
    - "full review"
    - "resolve review comments"
    - "review all PRs assigned to me"
    - "review my changes"
    - "review my code"
    - "review my pending PRs"
    - "review my tests"
    - "review pending PRs"
    - "review PR #123"
    - "review test coverage"
    - "review tests"
    - "review tests on PR #123"
    - "review the PRs I haven't reviewed yet"
    - "review this PR"
    - "run a code review"
    - "run a complete review"
    - "test code review"
    - "triage PR feedback"
---

# Code Review

One run, three stages. `SKILL.md` holds what every run does; `references/` holds what only some runs need, loaded at the step that needs it. [WORKFLOW.md](WORKFLOW.md) has the diagrams and design notes for human maintainers — it is never needed at runtime.

| Stage | Runs in | Does | Reference |
|---|---|---|---|
| 1. Review | A Sonnet review worker | Steps 2–9: diff, dimension agents, duplicate collapse, report; on a PR, posts a pending review | [github-writes.md](references/github-writes.md) (PR) |
| 2. Checkpoint | The root conversation | `human_review: true` → pause for the user; `false` → continue. On a PR, submits the review as `COMMENT` | — |
| 3. Fix | A fresh Sonnet fix worker | Fixes what remains, tests, validation gate; on a PR, pushes, replies, resolves | [fix-stage.md](references/fix-stage.md) |

## Parameters

| Parameter | Values | Effect |
|---|---|---|
| `human_review` | `false` (default) · `true` | `true` pauses at Stage 2 so the user can check and edit the findings before anything is fixed |
| `scope` | `both` (default) · `code` · `tests` | Which files the review stage covers |

A caller passes these explicitly; `build-feature` passes its own `human_review`. From a user's own words: **`scope`** narrows only on explicit wording — "review tests", "only the tests", "test commits" → `tests`; "only the implementation", "skip tests" → `code`. "Review my code", "complete review", and "full review" mean `both`. **`human_review`** is `true` on wording such as "let me check the findings first" or "pause before fixing". **"Just review"** (or "review only", "don't fix") ends the run after Stage 2.

## Reviewer Stance

Applies to the review stage. You are the villain. Find every flaw, violation, gap, and risk — not encourage.

- Be relentless. Code is guilty until proven innocent, and weak tests are worse than no tests — they create false confidence.
- Every violated principle, missing case, flawed assertion, or poorly isolated test is a finding — no "minor" issues.
- If a test could pass while the code is broken, that IS a broken test.
- Flag issues even when possibly intentional.
- State problems directly: file, line number, consequence.
- Never sign off on a violation because it is small, or on a suite that would fail to catch real bugs.
- Report a finding only at ≥ 80% confidence. If unsure whether a pattern is a violation, skip it — do not guess.

The fix stage takes the opposite stance toward findings: each one is a claim to check against the code, never an order ([fix-stage.md](references/fix-stage.md)).

## Guardrails

- **Not reviewed:** anything outside the target — a GitHub PR review covers only the PR's diff, never local workspace files; deleted files; noise files (removed at the git level by EXCLUDE, Step 4); files marked "do not review"; third-party test utilities and generated test code; files unchanged in the reviewed diff. **New files are always in scope**, against every loaded checklist. Test files belong to the tests scope only, implementation files to the code scope only.
- **Never filter or withhold findings** before the checkpoint — every finding is reported and, on a PR, posted. Merging same-root-cause duplicates (Step 8) is merging, not filtering.
- **Only what remains is a finding.** Whatever the user deletes on GitHub or drops at the checkpoint does not exist for the fix stage.
- **Every GitHub write goes through `scripts/github_review.py`** per [github-writes.md](references/github-writes.md): a review is pending until Stage 2 submits it, the verdict is always `COMMENT`, never a GitHub Issue, never deleting a review, comment, or thread, never touching another identity's pending review.
- **Only the root conversation dispatches stage workers.** The root is a live conversation, or `build-feature`'s orchestrator invoking this skill via `Skill`. A review worker dispatches only its dimension agents; a fix worker dispatches nothing. **When this skill is executed by any subagent** (started via the `Agent` tool for any reason, other than as a stage worker this skill dispatched) — the test is mechanical, never a judgment about why you were started: it is already the isolated context and must never call `Agent` for a stage worker. It runs the review stage inline, then — with `human_review: false` — `submit` and the fix stage inline, in that same context; with `human_review: true` it stops after Stage 1 and returns its result with `awaiting_approval: true`. This is the one case where the fix stage does not start in a fresh worker.
- **A stage worker that fails outright** (crash, auth failure, PR not found — distinct from a dimension agent or item failing) is retried once with a fresh worker; a second failure stops the run and is reported. Never claim a review was posted or a fix landed on a failed run.
- **Every subagent runs on Sonnet** — review workers, fix workers, dimension agents, batch workers — set explicitly on each `Agent` call, whatever model this session runs on. `human_review` never changes the model. Load the `subagent-dispatch` skill for the alias-only `model` rule, the missing reasoning-effort parameter, the dispatch-prompt contract, and the wait protocol.
- Never print `gh auth token` output or any credential — refer to auth state by status only.
- `gh` account resolution: opt-in.
- **Resolving paths.** `references/…` and `scripts/…` resolve inside this skill's directory (`~/.claude/skills/code-review/`, a symlink into the source repo). Read them directly — never `find`: the search surfaces confusing near-matches.

## Step 1: Entry Detection

First match wins:

| # | Trigger | Entry | Then |
|---|---|---|---|
| 1 | A sweep with fix wording ("fix the PRs I requested changes on", "batch-fix my change requests") | Batch fix sweep | [batch-mode.md](references/batch-mode.md), stop here |
| 2 | A sweep with review wording ("review my pending PRs", "review pending PRs", "review all PRs assigned to me", "review the PRs I haven't reviewed yet") | Batch review sweep | [batch-mode.md](references/batch-mode.md), stop here |
| 3 | A caller or user continuing a review this skill already posted ("continue the code review on PR #N") | Continue after checkpoint | Stage 2's continue path, then Stage 3 |
| 4 | Fix wording with no review wording ("fix the review comments on PR #N", "resolve review comments", "fix Q1, H2") | Fix existing findings | Stage 3 only |
| 5 | "review [test] commits X Y Z", "review [test] commits X..Y", "review last N [test] commits", hashes after "review" | Multi-commit | Stages 1–3 |
| 6 | A PR number already established in this conversation | GitHub PR | Stages 1–3 |
| 7 | Default | Local workspace | Stages 1–3 |

- **A PR number counts only when it's established in the conversation** — stated by the user or produced by an earlier step (e.g. `build-feature` just opened one). Never infer it from git or `gh` state.
- **Fix existing findings on a PR** needs at least one submitted review with comments (`gh pr view <N> --json reviews`): the only review is still `PENDING` → stop: "Your review is still pending on GitHub — submit it before asking me to fix findings." No review at all → fall through to local fix mode with the findings already in this conversation, on that PR's branch; none in the conversation either → say there is nothing published to fix and offer to review it. **Without a PR**, the findings are the ones already in this conversation (all of them, or the IDs named); none → ask which branch and which findings.
- **Continue after checkpoint** runs Stage 2's continue path for a PR review this skill posted earlier: `submit` (a `submitted: false` is fine), then Stage 3. It never re-runs the review.
- A fix request that is unclear between one PR and a sweep → ask: "Should I fix one specific PR (give me the number), or batch-fix every open PR where you requested changes?"
- Load the dimension file for each active scope before Stage 1: [code-dimensions.md](references/code-dimensions.md) for code, [test-dimensions.md](references/test-dimensions.md) for tests.

Entry and scope are fixed for the rest of the run.

## Stage 1: Review

**Dispatch (root):** one `Agent` call, `subagent_type: general-purpose`, `model: sonnet`, prompt per the `subagent-dispatch` contract:

- Prefix `[code-review][review:PR-<N>]`, `[code-review][review:commits]`, or `[code-review][review:local]`.
- The entry, PR number or commits, `scope`, and owner/repo for a PR.
- "Load the `code-review` skill and run Stage 1 — Steps 2–9 — as its review worker. Dispatch only dimension agents. Load the `subagent-dispatch` wait protocol before the first dispatch; when waiting on an agent, end your turn with one line of plain text and no tool call — never `sleep`, `echo`, or poll."
- Completion condition: Step 8's report written and, on a PR, Step 9's `post` exited with its JSON captured.
- Return shape, **local or commits:** the full Step 8 report plus the banner. **PR:** the PR URL; the banner verbatim (a Complex caveat with its actual wording); finding counts per scope and severity; the most important finding in one line; clusters collapsed; `post`'s exit code and, from its JSON, `posted_confirmed`, `carried_over`, `reanchored`, `anchor_corrected`, `missing`, `duplicates_found`, any batch that had to be retried, and every `unpostable` entry by `path:line` (report `0` for each count when none — a missing count is indistinguishable from never having looked); dimensions not executed with reasons. Never the diff, the full report, or comment bodies.
- Delegation depth: dimension agents only.

Track the review worker's name (and later the fix worker's) against the PR for the rest of the conversation: a later "a new commit landed on PR #N" routes through them per [batch-mode.md — New Commits or Comments](references/batch-mode.md#new-commits-or-comments-after-dispatch), which applies to single-PR runs too. Wait per the `subagent-dispatch` wait protocol, then go to Stage 2.

### Step 2: Context Collection

Record whether each item exists — `present` or `absent`. **Do not load content**; agents self-load their own.

| Item | Key |
|---|---|
| `docs/codebase/ARCHITECTURE.md` | `architecture` |
| `docs/codebase/CONCERNS.md` | `concerns` |
| `docs/codebase/CONVENTIONS.md` | `conventions` |
| `docs/codebase/INTEGRATIONS.md` | `integrations` |
| `docs/codebase/STACK.md` | `stack` |
| `docs/codebase/STRUCTURE.md` | `structure` |
| `docs/codebase/TESTING.md` | `testing` (tests scope) |
| Code checklists: `references/best-practices.code.md`, `clean-code-checklist.code.md`, `observability.code.md`, `performance-checklist.code.md`, `review-checklist.code.md` | one key each (code scope) |
| `references/<stack>.code.md`, `references/<stack>-performance.code.md` (stack match only) | `checklist_tech_code`, `checklist_tech_perf` (code scope) |
| `references/review-checklist.tests.md`, `references/<stack>.tests.md` (stack match only) | `checklist_tests`, `checklist_tech_tests` (tests scope) |
| An active spec (`.specs/features/*/spec.md`) or a JIRA task ID in the branch name, commit message, or PR description | `requirements` (code scope) |
| `sonar.projectKey` from `sonar-project.properties`, else `projectKey` from `.sonarlint/connectedMode.json` | `sonar_project_key` (the key string, or `absent`) |

Reference file naming: checklists carry their scope as a suffix — `<topic>.code.md`, `<topic>.tests.md`, and stack-specific `<stack>.code.md`, `<stack>-performance.code.md`, `<stack>.tests.md`. Orchestration references have no suffix.

### Step 3: Context Availability Map

The review worker holds **only this map** — no file content. An agent skips any absent file on its `## Before You Begin` list silently. If an agent's **required** item is absent, it runs `degraded`: it notes the gap in its findings, and its at-a-glance row shows `⚠️ degraded — <missing item>`. Each dimension file names what its agents require.

### Step 4: Diff Collection

```
EXCLUDE = [
  ':(exclude)*.lock'           ':(exclude)package-lock.json'  ':(exclude)yarn.lock'
  ':(exclude)pnpm-lock.yaml'   ':(exclude)composer.lock'      ':(exclude)Gemfile.lock'
  ':(exclude)go.sum'           ':(exclude)Cargo.lock'         ':(exclude)poetry.lock'
  ':(exclude)*.min.js'         ':(exclude)*.min.css'          ':(exclude)*.map'
  ':(exclude)dist/**'          ':(exclude)build/**'           ':(exclude)vendor/**'
  ':(exclude)node_modules/**'  ':(exclude)*.generated.*'      ':(exclude)*.snap'
  ':(exclude)**/__snapshots__/**'  ':(exclude)coverage/**'    ':(exclude).nyc_output/**'
]
```

The one noise list for every entry — never duplicate it.

| Entry | Commands |
|---|---|
| GitHub PR | `gh auth status` must succeed — otherwise stop: "No way to reach GitHub — install/authenticate `gh` (`gh auth status` must succeed) before reviewing a PR." Then `gh pr view <PR> --json title,body,baseRefName,headRefName,files` — PR not found → stop and report, never guess another number — and `gh pr diff <PR>`; drop every path matching EXCLUDE before assembling diffs |
| Local workspace | `git diff HEAD -- $EXCLUDE`, `git diff --cached -- $EXCLUDE`, `git ls-files --others --exclude-standard` |
| Multi-commit (hashes) | `git show <h1> -- $EXCLUDE; git show <h2> -- $EXCLUDE; ...`, concatenated in order |
| Multi-commit (range) | `git diff <base>..<tip> -- $EXCLUDE` |

Then, once for every scope:

- **Classify each non-deleted changed file** as a test file (the project's conventions from `TESTING.md` when present, else the stack's usual patterns — `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.go`, `__tests__/`, `tests/`) or an implementation file. This one classification feeds both scopes.
- **`impl_diff`** — the implementation files' diff. The code scope reviews it; the tests scope's `gap-detector` receives it.
- **`test_diff`** — the test files' diff, reviewed by the tests scope.
- `git diff --stat -- $EXCLUDE` (or equivalent) for the header, `excluded_count`, and for multi-commit the resolved hash + subject list.

**Scope activation:**

- **Code** runs when `impl_diff` has files. An empty changed list with no test files either (e.g. a rename-only change) still runs the code scope as content type `general`, Small, inline.
- **Tests** runs when `test_diff` has files. With no test files but a non-empty `impl_diff`, it runs **Coverage Gaps only** — Small tier, inline, banner `Tests: **Small** (0 test files) · Inline — Coverage Gaps only`, and the report carries only the Coverage Gaps row.
- A requested scope with nothing to review at all is shown as `skipped — no <implementation|test> changes` in the banner, never silently dropped.

### Step 4.5: Sonar Context

`sonar_project_key` absent → `sonar_context = { status: 'skipped', skip_reason: 'no project key found' }`. Otherwise load [sonar.md](references/sonar.md) and resolve it there.

### Step 5: Review Complexity Assessment

Assess **each active scope separately**, on its own post-exclusion metrics — implementation files and `impl_diff` lines for code, test files and `test_diff` lines for tests. Multi-commit uses combined totals across commits. First match wins:

| Tier | Condition | Execution mode |
|---|---|---|
| **Small** | ≤5 files **OR** <200 diff lines | **Inline** — the review worker reviews the scope's active dimensions itself, 0 agents |
| **Medium** | ≤15 files **AND** <800 diff lines | **Single agent** — 1 subagent covers every active dimension of the scope (1× diff) |
| **Large** | ≤25 files **AND** <1,500 diff lines | **Parallel** — 1 subagent per active dimension after merge rules (N× diff) |
| **Complex** | >25 files **OR** ≥1,500 diff lines | **Parallel + completeness handling** — as Large, plus the thoroughness directive and the report caveat |

The code scope also determines its content type ([code-dimensions.md](references/code-dimensions.md)); the tests scope whether Coverage Gaps is active.

```
Review Plan:
  Code:   tier <Small|Medium|Large|Complex> · type <content_type> · <inline|single-agent|parallel> · dimensions [..] · agents N
  Tests:  tier <…> · <inline|single-agent|parallel> · dimensions [..] · agents N · gap-detector <active|skipped>
  Complex handling: none | caveat + thoroughness directive (<scope>)
  Excluded files:   N
```

**Complexity banner** — one segment per active scope, returned to the root with the result:

```
🔍 Code review — Code: **<Tier>** (<N> files, <M> lines) · <content_type> · <execution> | Tests: **<Tier>** (<N> test files, <M> lines) · <execution>[ · <X> excluded]
```

```
🔍 Code review — Code: **Complex** (32 files, 1,840 lines) · general · Parallel — 4 agents (⚠️ completeness caveat) | Tests: **Medium** (9 test files, 420 lines) · Single agent — 6 dimensions · 3 excluded
🔍 Code review — Code: **Small** (2 files, 60 lines) · docs-only · Inline (Code Quality only)
🔍 Code review — Tests: **Large** (20 test files, 900 lines) · Parallel — 4 agents
```

The review worker produces no progress narration and no per-agent findings as they arrive — only its final result.

### Step 6: Dispatch

Dispatch **every non-inline agent from every active scope in a single parallel message** — never sequentially — then review the Small-tier scopes inline while they run.

- Every agent is pinned to `model: sonnet`.
- Every prompt follows the `subagent-dispatch` contract: prefix `[code-review][dimension:<agent>]`; completion condition — every checklist item in its `## Before You Begin` checked against its diff, findings written and tagged by dimension; return shape — findings only, never the diff or doc content it read; delegation depth — none.
- **Complex tier** adds to each of that scope's agents: *"This is a Complex review (large change set). Review every file in your scope thoroughly. Do not skip or skim any file. Focus on your assigned dimension(s) across all changed files."*
- Never inline checklist or doc content — `## Before You Begin` is a Read instruction.

```
## Before You Begin
Read these files before reviewing. Skip any marked absent.
<this agent's checklists and codebase docs, from its scope's dimension file, filtered to present>

## Role
<agent name and dimension(s), or "all active <code|test> dimensions" for a Medium-tier agent>

## Reviewer Stance
<the Reviewer Stance section above, verbatim>

## Diff
<impl_diff for code agents · test_diff for test agents · impl_diff only for gap-detector · both for a Medium tests agent when impl_diff is non-empty>

<Sonar blocks from sonar.md — only when this agent has Sonar data>

## Return format
Status: Complete | Blocked | Partial
Dimension: <agent name or "all dimensions">
Findings: [{dimension, severity, title, file, line, anchor, explanation, recommendation}]
Issues: <any blockers>
```

**`line` is the line at the PR head (or working tree), never a diff offset, and `anchor` is that line's exact text, verbatim** — the contract and the measured cost of skipping it are in [GitHub Writes — Comment Shape](references/github-writes.md#comment-shape).

### Step 7: Await + Fallback

**Load the `subagent-dispatch` wait protocol before the first dispatch, not once the first wait has started** — improvised waiting is this skill's largest avoidable cost, and the protocol's rules are not guessable from first principles. Wait for every agent; the 15-minute default stall ceiling applies as-is (a dimension agent is single-purpose).

| Outcome | Action |
|---|---|
| Degraded | Mark `⚠️ degraded — <missing item>` |
| Failed or timed out | Re-dispatch that one agent once. Fails again → mark its dimension(s) `⚠️ not executed — <reason>` |
| Returned normally | Parse the structured result |
| Skipped by rule | As its dimension file says (row omitted, or `⚠️ skipped — <reason>`) |

A merged agent's failure or degradation marks **every** dimension it covered — see each dimension file's Failure Marking. A failed agent never blocks the report. If **every** agent in every active scope failed, post nothing and return `review_failed: true` with every failure reason — never claim findings were published.

### Step 8: Consolidate and Report

**Collapse same-root-cause duplicates first.** Dimension agents across both scopes review overlapping diffs, so several describing one defect — in different words, at different lines or files — is the expected case. Keep the clearest instance of each cluster, fold the others' extra detail into its explanation, drop the rest, and count the clusters collapsed. This is merging, never severity filtering: nothing is dropped for being minor. Measured across four real PRs, ~17% of raw findings restated another dimension's; one bug was reported by five dimensions, and one PR's 43 posted threads were 25 distinct fixes.

Then write the report per [report-format.md](references/report-format.md).

### Step 9: Post (GitHub PR only)

Zero findings → skip `post` entirely and return zero counts; there is nothing to publish and never an empty comments array. Otherwise load [github-writes.md](references/github-writes.md), write `post.json` with every finding from the report (Comment Shape), and run `post`. Capture its JSON — it feeds the return shape. `post` never submits; the review stays pending until Stage 2.

## Stage 2: Checkpoint

Runs in the root conversation.

| Target | `human_review: true` | `human_review: false` |
|---|---|---|
| GitHub PR | Show the PR URL, banner, counts, and unpostable findings, and **end the turn**: "Review posted as pending on PR #N. Edit, delete, or add comments on GitHub (or submit it), then reply to continue." Never invent an approval or continue speculatively. On the user's reply: `submit` (a `submitted: false` because the user already submitted is fine), then Stage 3 | `submit`, then Stage 3 |
| Local or commits | Show the report and **end the turn**; the user drops findings by ID ("drop Q2, H1") and replies. Then Stage 3 with what remains | Stage 3 with every finding |

- **Review failed** (`review_failed: true`) → no pause, no `submit`, no Stage 3; report every failure reason and stop.
- **`post` exit `2`** → nothing was confirmed: the run is blocked; report its JSON and stop. **Exit `1`** → report every `missing`, `duplicates_found`, and error entry explicitly — never rounded to the intended count — and continue; the threads that landed are real.
- **"Just review":** `true` → end the run at the pause (a PR review stays pending for the user to submit); `false` → `submit` on a PR, then end the run.
- **No findings** from the review → no pause, no `submit`, no Stage 3; report. **The user dropped them all** at the pause → no Stage 3; on a PR, `submit` still runs (it leaves a review with no comments pending).
- `submit` exits non-zero → the run is blocked; report its JSON and stop before Stage 3.

## Stage 3: Fix

The root dispatches a fresh fix worker per [Fix Stage — Dispatch](references/fix-stage.md#dispatch-root-conversation), waits per the `subagent-dispatch` wait protocol, and removes any worktree the dispatch created once the worker reports.

## Final Report

The root combines both stages: the review summary (URL or report, banner, counts, collapsed / re-anchored / unpostable) and the fix worker's report (outcomes by class, `deliver` counts verbatim, commits and whether pushed, validation gate, test changes, blocked and unclear items).

## Examples

| Invocation | Entry · `human_review` | What happens |
|---|---|---|
| "review my code" | Local · false | Review worker → report → fix worker edits the working tree, commits nothing |
| "review my tests, let me check the findings first" | Local · true, `scope: tests` | Report shown; user says "drop V2, continue"; fix worker handles the rest |
| "review commits abc123 def456, only the implementation" | Multi-commit · false, `scope: code` | Tiers on combined totals; one local commit per fix, never pushed |
| "review PR #42" | GitHub PR · false | Review posted, submitted as `COMMENT`, fix worker fixes, pushes, replies, resolves |
| "review PR #42, just review" | GitHub PR · false | Review posted and submitted; no fix stage |
| `build-feature` Step 11: PR #128, `human_review: true` | GitHub PR · true | Orchestrator is the root: review worker posts; pause; user edits on GitHub and replies; `submit`; fix worker runs in place on the branch |
| PR #310 already has this identity's pending review (6 comments) | GitHub PR · false | `post` appends new findings to it (`carried_over: 6`), then submit and fix |
| "fix the review comments on PR #201" | Fix existing · — | Stage 3 only; no checkout has the PR branch, so the fix worker gets `isolation: worktree` |
| `build-feature` resuming with `code_review: pending` | Continue after checkpoint · — | `submit`, then Stage 3; the review is not re-run |
| "fix Q1 and H2" after a "just review" local run | Fix existing · — | Stage 3 with exactly those two findings |
| "review my pending PRs except #205" | Batch review sweep | #205 dropped for this run only; per-PR review → checkpoint → fix |
| "fix the PRs I requested changes on" | Batch fix sweep | One worktree fix worker per qualifying PR, scoped to your own threads |
