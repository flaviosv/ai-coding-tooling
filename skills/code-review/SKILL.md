---
name: code-review
description: >
  Reviews implementation code and tests together by default — or only one when asked — for local
  workspace changes, specific commits, or a GitHub PR, dispatching Sonnet dimension agents sized to
  the diff (architecture, code quality, performance, regression, security, requirements; test
  coverage, gaps, isolation, clarity, maintainability). A PR review reports locally unless
  post: true, which publishes every finding as one pending PR review (never submitted); findings can
  also be held at findings_path for a later publish. Batch Mode sweeps every open PR awaiting your
  review. Also runs full-codebase Performance Audits. Technology agnostic via docs/codebase context.
  Use when the user says "review my code", "code review", "review my tests", "review PR #123",
  "complete review", "review and post to PR", "review my pending PRs", "performance audit", or
  invokes /code-review. Do NOT use to fix review findings (use fix-review) or to write tests.
metadata:
  version: "3.0.0"
  triggers:
    - "check my code"
    - "check tests"
    - "code review"
    - "code review the"
    - "complete review"
    - "do a code review"
    - "full review"
    - "optimize performance"
    - "performance audit"
    - "performance bottleneck"
    - "performance review"
    - "review all PRs assigned to me"
    - "review and post to PR"
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
    - "slow code"
    - "slow query"
    - "test code review"
---

# Code Review

Work through the steps in order — mode detection, context collection, and dispatch all happen automatically. `SKILL.md` holds what every run does; `references/` holds what only some runs need, loaded at the step that needs it and never otherwise.

## Parameters

| Parameter | Values | Effect |
|---|---|---|
| `findings_path` | path | With a PR target and `post: false`: write the assembled findings there for a later Publish request |
| `post` | `false` (default) · `true` | `true` publishes every finding as one pending review on the PR. PR targets only; Batch Mode always posts |
| `scope` | `both` (default) · `code` · `tests` | Which files are reviewed. Performance Audit is always `code` |

A caller passes these explicitly. From a user's own words: **`scope`** narrows only on explicit wording — "review tests", "only the tests", "test commits" → `tests`; "only the implementation", "skip tests" → `code`. "Review my code" and "code review" mean `both`. **`post`** is `true` only on explicit wording such as "post to the PR" or "publish" — "complete review" and "full review" mean `scope: both`, not publishing.

## Reviewer Stance

You are the villain. Find every flaw, violation, gap, and risk — not encourage.

- Be relentless. Code is guilty until proven innocent, and weak tests are worse than no tests — they create false confidence.
- Every violated principle, missing case, flawed assertion, or poorly isolated test is a finding — no "minor" issues.
- If a test could pass while the code is broken, that IS a broken test.
- Flag issues even when possibly intentional.
- State problems directly: file, line number, consequence.
- Never sign off on a violation because it is small, or on a suite that would fail to catch real bugs.
- Report a finding only at ≥ 80% confidence. If unsure whether a pattern is a violation, skip it — do not guess.

## Guardrails

- **Not reviewed:** anything outside the target — a GitHub PR review covers only the PR's diff, never local workspace files; deleted files; noise files (removed at the git level by EXCLUDE, Step 4); files marked "do not review"; third-party test utilities and generated test code; files unchanged in the reviewed diff. **New files are always in scope**, against every loaded checklist. Test files belong to the tests scope only, implementation files to the code scope only.
- **GitHub writes happen only with `post: true`, a Publish request, or the user's explicit selection after a report** — always through [Posting Mechanics](references/posting-mechanics.md): pending state only, never submitted, never a GitHub Issue, never deleting a pending review or comment, never touching another identity's pending review, never replying to or resolving existing threads.
- **Never auto-fix, filter, or withhold findings** when publishing — every finding is posted, unfiltered. Merging same-root-cause duplicates (Step 8) is merging, not filtering.
- **Every subagent runs on Sonnet** — dimension agents, the publishing worker, Batch Mode's per-PR agents — set explicitly on each `Agent` call, whatever model this session runs on. `post` never changes the model. Load the `subagent-dispatch` skill for the alias-only `model` rule, the missing reasoning-effort parameter, the dispatch-prompt contract, and the wait protocol.
- Never print `gh auth token` output or any credential — refer to auth state by status only.
- `gh` account resolution: opt-in.
- **Resolving links.** `references/…` resolves inside this skill's directory. From a reference file, `../../../templates/<name>.md` resolves to `~/.claude/templates/<name>.md` (not `~/.claude/skills/templates/`). Read those paths directly — never `find`: the installed skill directory is a symlink into the source repo, and a search surfaces confusing near-matches.

## Step 1: Mode Detection

Resolve the target — first match wins — then load that target's references:

| Priority | Trigger | Target | Load |
|---|---|---|---|
| 1 | Explicit request to publish held findings ("publish code-review findings for PR #N from `<findings_path>`") | Publish | [pr-publishing.md](references/pr-publishing.md) → Publish Mode, then stop |
| 2 | A sweep across PRs awaiting your review ("review my pending PRs", "review pending PRs", "review all PRs assigned to me", "review the PRs I haven't reviewed yet") | Batch | [batch-mode.md](references/batch-mode.md), then stop |
| 3 | Performance phrases ("performance audit", "performance review", "performance bottleneck", "optimize performance", "slow code", "slow query") | Performance Audit | [performance-audit.md](references/performance-audit.md) |
| 4 | "review [test] commits X Y Z", "review [test] commits X..Y", "review last N [test] commits", hashes after "review" | Multi-commit | — |
| 5 | A PR number already established in this conversation | GitHub PR | [pr-publishing.md](references/pr-publishing.md) when `post: true` or `findings_path` |
| 6 | Default | Local workspace | — |

- **A PR number counts only when it's established in the conversation** — stated by the user ("review PR #42") or produced by an earlier step (e.g. `build-feature` just opened one). Never infer it from git or `gh` state (current branch, `gh pr view` on the checkout).
- `post: true` with no PR known, and no batch wording → ask: "Should I review one specific PR (give me the number), or run a batch review of every open PR waiting on your review?" Never guess.
- A PR run with `post: true` or `findings_path`, from a root conversation, hands Steps 2–9 to one publishing worker — [pr-publishing.md](references/pr-publishing.md) says when and how. A subagent never dispatches it.
- Then load the dimension file for each active scope: [code-dimensions.md](references/code-dimensions.md) for code, [test-dimensions.md](references/test-dimensions.md) for tests.

Target and scope are fixed for the rest of the run.

## Step 2: Context Collection

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

## Step 3: Context Availability Map

The orchestrator holds **only this map** — no file content. An agent skips any absent file on its `## Before You Begin` list silently. If an agent's **required** item is absent, it runs `degraded`: it notes the gap in its findings, and its at-a-glance row shows `⚠️ degraded — <missing item>`. Each dimension file names what its agents require.

## Step 4: Diff Collection

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

The one noise list for every mode — never duplicate it.

| Target | Commands |
|---|---|
| GitHub PR | `gh auth status` must succeed — otherwise stop: "No way to reach GitHub — install/authenticate `gh` (`gh auth status` must succeed) before reviewing a PR." Then `gh pr view <PR> --json title,body,baseRefName,headRefName,files` — PR not found → stop and report, never guess another number — and `gh pr diff <PR>`; drop every path matching EXCLUDE before assembling diffs |
| Local workspace | `git diff HEAD -- $EXCLUDE`, `git diff --cached -- $EXCLUDE`, `git ls-files --others --exclude-standard` |
| Multi-commit (hashes) | `git show <h1> -- $EXCLUDE; git show <h2> -- $EXCLUDE; ...`, concatenated in order |
| Multi-commit (range) | `git diff <base>..<tip> -- $EXCLUDE` |
| Performance Audit | No diff for the scan — see [performance-audit.md](references/performance-audit.md); changed files still come from the local workspace commands |

Then, once for every scope:

- **Classify each non-deleted changed file** as a test file (the project's conventions from `TESTING.md` when present, else the stack's usual patterns — `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.go`, `__tests__/`, `tests/`) or an implementation file. This one classification feeds both scopes.
- **`impl_diff`** — the implementation files' diff. The code scope reviews it; the tests scope's `gap-detector` receives it.
- **`test_diff`** — the test files' diff, reviewed by the tests scope.
- `git diff --stat -- $EXCLUDE` (or equivalent) for the header, `excluded_count`, and for multi-commit the resolved hash + subject list.

**Scope activation:**

- **Code** runs when `impl_diff` has files. An empty changed list with no test files either (e.g. a rename-only change) still runs the code scope as content type `general`, Small, inline.
- **Tests** runs when `test_diff` has files. With no test files but a non-empty `impl_diff`, it runs **Coverage Gaps only** — Small tier, inline, banner `Tests: **Small** (0 test files) · Inline — Coverage Gaps only`, and the report carries only the Coverage Gaps row.
- A requested scope with nothing to review at all is shown as `skipped — no <implementation|test> changes` in the banner, never silently dropped.

## Step 4.5: Sonar Context

`sonar_project_key` absent → `sonar_context = { status: 'skipped', skip_reason: 'no project key found' }`. Otherwise load [sonar.md](references/sonar.md) and resolve it there.

## Step 5: Review Complexity Assessment

Assess **each active scope separately**, on its own post-exclusion metrics — implementation files and `impl_diff` lines for code, test files and `test_diff` lines for tests. Multi-commit uses combined totals across commits. First match wins:

| Tier | Condition | Execution mode |
|---|---|---|
| **Small** | ≤5 files **OR** <200 diff lines | **Inline** — the orchestrator reviews the scope's active dimensions itself, 0 agents |
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

### Complexity Banner

Print this before any dispatch or inline review, in every mode and tier — one segment per active scope:

```
🔍 Code review — Code: **<Tier>** (<N> files, <M> lines) · <content_type> · <execution> | Tests: **<Tier>** (<N> test files, <M> lines) · <execution>[ · <X> excluded]
```

```
🔍 Code review — Code: **Complex** (32 files, 1,840 lines) · general · Parallel — 4 agents (⚠️ completeness caveat) | Tests: **Medium** (9 test files, 420 lines) · Single agent — 6 dimensions · 3 excluded
🔍 Code review — Code: **Small** (2 files, 60 lines) · docs-only · Inline (Code Quality only)
🔍 Code review — Tests: **Large** (20 test files, 900 lines) · Parallel — 4 agents
```

### Silent Operation

The only user-facing outputs are the skill-invocation announcement, this banner, and the Step 8 report. Nothing in between — no progress narration, no per-agent findings as they arrive, no analytical commentary.

## Step 6: Dispatch

Dispatch **every non-inline agent from every active scope in a single parallel message** — never sequentially — then review the Small-tier scopes inline while they run.

- Every agent is pinned to `model: sonnet`.
- Every prompt follows the `subagent-dispatch` contract: prefix `[code-review][dimension:<agent>]`; completion condition — every checklist item in its `## Before You Begin` checked against its diff, findings written and tagged by dimension; return shape — findings only, never the diff or doc content it read; delegation depth — none.
- **Complex tier** adds to each of that scope's agents: *"This is a Complex review (large change set). Review every file in your scope thoroughly. Do not skip or skim any file. Focus on your assigned dimension(s) across all changed files."*
- The orchestrator never inlines checklist or doc content — `## Before You Begin` is a Read instruction.

### Agent Prompt

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

**`line` is the line at the PR head (or working tree), never a diff offset, and `anchor` is that line's exact text, verbatim** — the full contract and the measured cost of skipping it are in [Posting Mechanics — Comment Shape](references/posting-mechanics.md#comment-shape).

## Step 7: Await + Fallback

**Load the `subagent-dispatch` wait protocol before the first dispatch, not once the first wait has started** — improvised waiting is this skill's largest avoidable cost, and the protocol's rules are not guessable from first principles. Wait for every agent; the 15-minute default stall ceiling applies as-is (a dimension agent is single-purpose).

| Outcome | Action |
|---|---|
| Returned normally | Parse the structured result |
| Failed or timed out | Re-dispatch that one agent once. Fails again → mark its dimension(s) `⚠️ not executed — <reason>` |
| Degraded | Mark `⚠️ degraded — <missing item>` |
| Skipped by rule | As its dimension file says (row omitted, or `⚠️ skipped — <reason>`) |

A merged agent's failure or degradation marks **every** dimension it covered — see each dimension file's Failure Marking. A failed agent never blocks the report; continue to Step 8.

## Step 8: Consolidate and Report

**Collapse same-root-cause duplicates first.** Dimension agents across both scopes review overlapping diffs, so several describing one defect — in different words, at different lines or files — is the expected case. Keep the clearest instance of each cluster, fold the others' extra detail into its explanation, drop the rest, and count the clusters collapsed. This is merging, never severity filtering: nothing is dropped for being minor. Measured across four real PRs, ~17% of raw findings restated another dimension's; one bug was reported by five dimensions, and one PR's 43 posted threads were 25 distinct fixes.

Then write the report per [report-format.md](references/report-format.md) — or [performance-audit.md](references/performance-audit.md) for a Performance Audit.

## Step 9: Publish (GitHub PR only)

- `post: true` or `findings_path` → [pr-publishing.md](references/pr-publishing.md) — Publishing Flow.
- `post: false` → the report ends with the publish offer. If the user selects findings, publish that selection per [pr-publishing.md — Publishing After a Local Report](references/pr-publishing.md#publishing-after-a-local-report).

## Examples

| Invocation | Target · scope · post | Delta from Steps 1–9 |
|---|---|---|
| "review my code" | Local · both · — | Standard run; the report is the output |
| "review my tests" | Local · tests · — | Code scope inactive; `gap-detector` still gets `impl_diff` |
| "review commits abc123 def456, only the implementation" | Multi-commit · code · — | `git show` per commit; tiers on combined totals; header lists every commit |
| "review PR #42" | GitHub PR · both · false | Report ends with the publish offer; "post A1, V2" publishes that selection |
| `build-feature` Step 11: PR #128, `post: true` | GitHub PR · both · true | Already a subagent → runs inline, publishes, returns the compact result |
| "/code-review PR #456 and post it" from a live conversation | GitHub PR · both · true | One Sonnet publishing worker runs Steps 2–9 and returns the compact result |
| A caller with its own approval gate: PR #512, `findings_path: .specs/features/PROJ-9-widget/code-review-findings.json` | GitHub PR · both · false | Findings held at the path, `awaiting_approval: true`; later "publish code-review findings for PR #512 from <path>" → Publish Mode posts exactly what was held |
| "/code-review PR #310 and post it" with this identity's pending review already on the PR (6 comments) | GitHub PR · both · true | New findings appended to that same review (6 + 5 = 11), no delete, no prompt; report says 6 carried over |
| "review my pending PRs except #205" | Batch · both · true | Batch Mode; #205 dropped for this run only; per-PR updates as each lands, then a summary table |
| "a new commit just landed on PR #12" after Batch Mode | — | `SendMessage` to PR #12's tracked subagent → delta-only review appended to its pending review |
| "performance audit of the orders module" | Performance Audit · code · — | Step 5 skipped; full-codebase scan by architecture and performance agents; P0–P3 report |
