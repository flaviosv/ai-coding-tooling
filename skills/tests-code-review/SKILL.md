---
name: tests-code-review
description: >
  Review test code quality, coverage patterns, and maintainability. Ensures tests are clear,
  independent, and provide meaningful coverage. Technology agnostic — adapts to the project's
  stack using context files. Use when the user says "review tests", "test code review",
  "check tests", "review test coverage", "review my tests", "review tests on PR #123",
  or "check tests PR #42". Do NOT use for writing new tests — use the tests skill for that.
  Do NOT use for reviewing implementation code — use the code-review skill.
metadata:
  version: "2.4.0"
  triggers:
    - "review tests"
    - "test code review"
    - "check tests"
    - "review test coverage"
    - "review my tests"
    - "review tests on PR #123"
---

# Test Code Review

## Reviewer Stance

You are the villain. Find every gap, weakness, and lie in the test suite — not encourage.

- Be relentless. Weak tests are worse than no tests — they create false confidence.
- Every missing case, every flawed assertion, every poorly isolated test is a finding.
- If a test could pass even when the code is broken, that IS a broken test — flag it.
- State problems directly: file, line number, consequence.
- Never sign off on a test suite that would fail to catch real bugs.

## Guardrails

### Review Modes

- **Local workspace** (default): review all changed/added test files in git workspace.
- **GitHub PR**: review only test files in the PR diff from GitHub. Do NOT review local workspace files.
- User must explicitly provide a PR number to activate GitHub PR mode.

### What NOT to Review

- Deleted test files
- Implementation (non-test) files — use **code-review** skill
- Third-party test utilities or generated test code
- Test files that have not changed in this workspace (no modifications, no new additions)
- Noise files excluded by the EXCLUDE constant (Step 4): lockfiles, snapshot files, coverage reports, minified assets, built artifacts — these never enter any agent context

**New test files are always in scope.** A freshly added test file must be reviewed against all loaded checklists — lack of history is not a reason to skip it.

### GitHub PR Constraints

- **Never post comments to GitHub automatically.** Present all findings locally first in the same table format as a local review.
- Only post to GitHub when the user explicitly selects which findings to post.
- **NEVER create GitHub Issues** — all GitHub output goes to the PR as inline review comments only. Creating issues is strictly forbidden, no exceptions.
- Each comment must be anchored to the **exact line number** identified in the finding — never posted as a top-level PR comment or at the top of the file.
- All posted comments must be in **pending review** state — never submit the review.
- The user reviews and submits manually on GitHub.

### Subagent Model (hard requirement)

Every subagent dispatched in Step 6 — in every mode and every tier (Medium, Large, Complex) — **must run on the most recent Sonnet model**, regardless of what model the current session is running on (even if the session is on Opus). When dispatching, explicitly set the model on each agent call; never omit it to let a dispatched agent inherit the session's model.

## Step 1: Mode Detection

Parse the user's request and resolve to exactly one mode before proceeding. Priority order matters — first match wins:

| Priority | Trigger | Mode |
|----------|---------|------|
| 1 | "review test commits X Y Z", "review test commits X..Y", "review last N test commits", comma/space-separated hashes after "review" | Multi-commit |
| 2 | PR number present (e.g. "review tests on PR #42", "check tests PR 456") | GitHub PR |
| 3 | Default | Local workspace |

Mode is fixed for the remainder of the pipeline.

For **GitHub PR mode**, load and apply [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md).

## Step 2: Context Collection

Check presence/absence of the following files before proceeding. Do **NOT** load file content — record only whether each is present or absent. Results feed the availability map in Step 3.

**Codebase docs** — check in `docs/codebase/`:

| File | Availability key |
|------|-----------------|
| `ARCHITECTURE.md` | `architecture` |
| `CONCERNS.md` | `concerns` |
| `CONVENTIONS.md` | `conventions` |
| `INTEGRATIONS.md` | `integrations` |
| `STACK.md` | `stack` |
| `STRUCTURE.md` | `structure` |
| `TESTING.md` | `testing` |

**Review checklists** — check for presence; tech-specific only when stack matches:

| File | Availability key |
|------|-----------------|
| `references/test-review-checklist.md` | `checklist_baseline` |
| `references/<stack>-*-tests-code-review.md` (if match) | `checklist_tech_specific` |

**Sonar project key** — check for presence; extract key if present:

| File | Availability key |
|------|-----------------|
| `sonar-project.properties` | `sonar_props` |
| `.sonarlint/connectedMode.json` | `sonar_sonarlint` |

Extract `sonar.projectKey` from `sonar-project.properties` if present; fall back to `projectKey` field in `.sonarlint/connectedMode.json`. Store the resolved key as `sonar_project_key` (string value, or `absent` if neither file exists).

## Step 3: Context Availability Map

Build the availability map from Step 2 results:

```
availability = {
  // codebase docs (7)
  architecture, concerns, conventions,
  integrations, stack, structure, testing,
  // checklists (2)
  checklist_baseline, checklist_tech_specific,
  // sonar
  sonar_project_key  // resolved key string, or 'absent'
}
// each field: present | absent (except sonar_project_key: string or 'absent')
```

The orchestrator holds **this map only** — no file content. Agents self-load their own context using the `## Before You Begin` block defined in Step 6.

If an agent's required context item is absent from the map, flag that agent as `degraded`: it proceeds without that item, notes the gap in its findings, and the at-a-glance table shows `⚠️ degraded — <missing item>`.

Special case: `TESTING.md` absent → `isolation-reviewer` and `performance-reviewer` run degraded; they fall back to inferring the test framework from `STACK.md` or test file patterns.

## Step 4: Diff Collection

Define the exclusion constant used in every git command:

```
EXCLUDE = [
  ':(exclude)*.lock'           ':(exclude)package-lock.json'  ':(exclude)yarn.lock'
  ':(exclude)pnpm-lock.yaml'   ':(exclude)composer.lock'      ':(exclude)Gemfile.lock'
  ':(exclude)go.sum'           ':(exclude)Cargo.lock'         ':(exclude)poetry.lock'
  ':(exclude)*.min.js'         ':(exclude)*.min.css'          ':(exclude)*.map'
  ':(exclude)dist/**'          ':(exclude)build/**'           ':(exclude)vendor/**'
  ':(exclude)node_modules/**'  ':(exclude)*.generated.*'
  ':(exclude)**/__snapshots__/**'  ':(exclude)*.snap'
  ':(exclude)coverage/**'      ':(exclude).nyc_output/**'
]
```

Collect the diff and test file list based on the mode from Step 1, applying EXCLUDE to every git command. Filter to test files in all modes:

| Mode | Commands |
|------|----------|
| Local workspace | `git diff HEAD -- $EXCLUDE`, `git diff --cached -- $EXCLUDE`, `git ls-files --others --exclude-standard` — filter to test files |
| GitHub PR | `gh` (see [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md)); filter the changed-file list to remove any path matching the EXCLUDE patterns before assembling the diff for agents |
| Multi-commit (hashes) | `git show <h1> -- $EXCLUDE; git show <h2> -- $EXCLUDE; ...` — concatenated in order, filter to test files |
| Multi-commit (range) | `git diff <base>..<tip> -- $EXCLUDE` — filter to test files |

Also collect:
- `git diff --stat -- $EXCLUDE` (or equivalent, filtered to test files) — used in the report header
- Changed test file list (after EXCLUDE applied) — used in complexity assessment and routing
- Count of files excluded by EXCLUDE — stored as `excluded_count` for the report header
- **Multi-commit only:** `git log --oneline <range>` or resolved hash+subject list — used in report header

In all modes (primary test diff): skip deleted files and non-test files. Noise files are already absent because EXCLUDE was applied at the git command level.

**Implementation diff** (`impl_diff`) — collected separately for `gap-detector` only:
Using the same mode-appropriate commands with EXCLUDE applied, filter to non-test, non-deleted implementation files changed in this diff. If `impl_diff` is empty (no implementation files changed), `gap-detector` is skipped entirely.

## Step 4.5: Sonar Context Resolution

Run after Step 4 (diff file list and impl_diff known) and before Step 5 (complexity assessment). Result is stored as `sonar_context`.

**MCP tools**: `search_sonar_issues_in_projects`, `get_component_measures`, `search_files_by_coverage` (from the `sonarqube` MCP server)

```
IF sonar_project_key == 'absent':
    sonar_context = { status: 'skipped', skip_reason: 'no project key found' }
    GOTO Step 5

IF sonarqube MCP tools are unavailable in this session:
    sonar_context = { status: 'skipped', skip_reason: 'MCP not installed' }
    GOTO Step 5

ATTEMPT:
    # Test-quality issues (maintainability smells in diff files)
    issues = search_sonar_issues_in_projects(
        projects=[sonar_project_key],
        branch=<current git branch>,              # omit for PR mode; use pullRequest=<PR key>
        issueStatuses=["OPEN"],
        impactSoftwareQualities=["MAINTAINABILITY"],
        files=[sonar_project_key + ":" + f for f in diff_file_list]
    )

    # Coverage metrics for new code
    measures = get_component_measures(
        projectKey=sonar_project_key,
        branch=<current git branch>,
        metricKeys=["new_coverage", "new_lines_to_cover", "new_uncovered_lines"]
    )

    # Files in diff with worst coverage (for gap-detector)
    low_coverage_files = search_files_by_coverage(
        projectKey=sonar_project_key,
        branch=<current git branch>,
        maxCoverage=80
    )
    # intersect with diff_file_list to keep only changed files

    sonar_context = {
        status: 'active',
        project_key: sonar_project_key,
        branch: <current branch>,
        issues_by_agent: {
            coverage_reviewer: issues[:30]  # test-quality smells, sorted severity desc
        },
        coverage: {
            new_coverage_pct:       measures.new_coverage,
            new_lines_to_cover:     measures.new_lines_to_cover,
            new_uncovered_lines:    measures.new_uncovered_lines,
            low_coverage_diff_files: [f in low_coverage_files that are also in diff_file_list]
        }
    }

ON server unreachable / connection error:
    sonar_context = { status: 'skipped', skip_reason: 'server unreachable' }
ON MCP tool returns empty for this branch:
    sonar_context = { status: 'skipped', skip_reason: 'no data for branch <branch> — run sonar-scanner first' }
ON measures unavailable but issues present (partial):
    set sonar_context.status = 'active', omit coverage block, note in header as 'active (partial)'
ON timeout:
    sonar_context = { status: 'skipped', skip_reason: 'query timeout' }
```

In every skipped state: proceed identically to pre-integration behavior. No agent receives a Sonar block.

## Step 5: Review Complexity Assessment

Using post-exclusion metrics from Step 4 (test file count and diff lines after EXCLUDE applied), produce a **Review Plan** and print a **complexity banner** before any review work begins.

### Size tier → execution mode

Evaluate top-down, first match wins:

| Tier | Condition | Execution mode | Diff cost |
|------|-----------|----------------|-----------|
| **Small** | ≤5 test files **OR** <200 diff lines | **Inline** — orchestrator reviews all dimensions directly, no agents | ~0 |
| **Medium** | ≤15 test files **AND** <800 diff lines | **Parallel** — one specialized subagent per active dimension | N× |
| **Large** | ≤25 test files **AND** <1,500 diff lines | **Parallel** — one specialized subagent per active dimension | N× |
| **Complex** | >25 test files **OR** ≥1,500 diff lines | **Parallel + completeness handling** (see below) | N× |

**Multi-commit mode:** apply tier evaluation against combined diff totals across all commits.

**Complex-tier handling:**
- Report header carries: `⚠️ Complex review (N test files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.`
- Each dispatched agent's prompt includes a thoroughness directive: review every file in its scope thoroughly. Agents return findings only — no coverage roll-call.

### Review Plan

Emit this plan before any dispatch or inline review begins:

```
Review Plan:
  Size tier:        Small | Medium | Large | Complex
  Execution mode:   inline | parallel
  Dimensions:       [active dimension list]
  Agents dispatched: 0 (inline) | N (parallel)
  Gap-detector:     active (impl_diff non-empty) | skipped (no impl changes)
  Complex handling: none | caveat + thoroughness directive
  Excluded files:   N
```

### Complexity Banner

Immediately after the assessment, print this one-line banner to the user **before any dispatch or inline review begins**. Required in every mode and every tier, including Small.

```
🔍 Test review — Complexity: **<Tier>** (<N> test files, <M> lines[· <X> excluded]) · <execution description>
```

Examples:
```
🔍 Test review — Complexity: **Small** (3 test files, 90 lines) · Inline review
🔍 Test review — Complexity: **Medium** (10 test files, 480 lines) · Parallel — 6 agents
🔍 Test review — Complexity: **Medium** (10 test files, 480 lines) · Parallel — 5 agents (no impl changes)
🔍 Test review — Complexity: **Large** (20 test files, 900 lines) · Parallel — 5 agents
🔍 Test review — Complexity: **Complex** (32 test files, 1,840 lines · 2 excluded) · Parallel — 6 agents (⚠️ completeness caveat)
```

### Silent operation

The skill produces **exactly three** user-facing outputs: (1) the skill-invocation announcement, (2) the complexity banner, (3) the final consolidated report. **Nothing else.** No progress narration, no per-agent intermediate output, no analysis commentary between the banner and the final report.

## Step 6: Dispatch

Execute per the size tier determined in Step 5.

**Every agent dispatched below must be pinned to the most recent Sonnet model** (see [Subagent Model](#subagent-model-hard-requirement) in Guardrails) — set this explicitly on every dispatch, independent of the session's own model.

### Execution modes

| Tier | What to do |
|------|------------|
| **Small** | Orchestrator reviews all dimensions inline — no agents. Apply all 5 dimensions (plus coverage gaps if `impl_diff` non-empty) directly, then proceed to Step 8. |
| **Medium / Large** | Dispatch one specialized subagent per active dimension in a **single parallel message**. Never sequentially. |
| **Complex** | Same as Medium/Large + inject the thoroughness directive into each agent's prompt: *"Review every file in your scope thoroughly."* |

For Medium, Large, and Complex: `gap-detector` is dispatched only when `impl_diff` is non-empty; otherwise its at-a-glance row shows `⚠️ skipped — no implementation changes`.

### Prompt template (all non-inline modes)

Each agent receives:

```
## Before You Begin
Read the following files before starting your review (skip any marked absent in the availability map):
<checklist and codebase doc paths — see Agent Roster below>

## Role
<agent name and dimension>

## Reviewer Stance
You are the villain. Find every gap, weakness, and lie in the test suite — not encourage.
- Be relentless. Weak tests are worse than no tests — they create false confidence.
- Every missing case, every flawed assertion, every poorly isolated test is a finding.
- If a test could pass even when the code is broken, that IS a broken test — flag it.
- State problems directly: file, line number, consequence.
- Never sign off on a test suite that would fail to catch real bugs.

## Diff
<full test-file diff from Step 4; gap-detector receives impl_diff instead>

## Sonar Coverage Data
<inject for gap-detector ONLY when sonar_context.status == 'active' AND sonar_context.coverage is present>
<omit this entire section — do not inject an empty block — when coverage data is unavailable>

SonarQube coverage data for new code on branch `<branch>`:
- New code coverage: <new_coverage_pct>%
- New lines to cover: <new_lines_to_cover>
- New uncovered lines: <new_uncovered_lines>

Files in this diff with coverage below 80%:
<list sonar_context.coverage.low_coverage_diff_files>

Use this as a starting point — focus your gap analysis on these uncovered areas.

## Sonar Test Quality Issues
<inject for coverage-reviewer ONLY when sonar_context.status == 'active' AND sonar_context.issues_by_agent.coverage_reviewer is non-empty>
<omit this entire section — do not inject an empty block — when no issues are mapped to this agent>

SonarQube detected the following test quality issues on branch `<branch>` in files within this diff.
Use as additional signal — they do not replace your analysis.

| Severity | Rule | File | Line | Message |
|----------|------|------|------|---------|
<one row per issue from sonar_context.issues_by_agent.coverage_reviewer, sorted severity desc, max 30>

## Return format
Status: Complete | Blocked | Partial
Dimension: <agent name>
Findings: [{severity, title, file, line, explanation, recommendation}]
Issues: <any blockers encountered>
```

### Agent Roster

| Agent | Dimension | `## Before You Begin` — Checklists | `## Before You Begin` — Codebase docs | Degrades without |
|-------|-----------|-------------------------------------|----------------------------------------|-----------------|
| `clarity-reviewer` | Test naming, AAA structure, focus, readability as docs | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set | `conventions` |
| `coverage-reviewer` | Happy path, error paths, edge cases, integration points, access control | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set | — |
| `gap-detector` | Implementation paths and behaviors missing test coverage (receives `impl_diff` only; skipped if `impl_diff` empty) | None | `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` | — |
| `isolation-reviewer` | Shared state, ordering, mocks, determinism, external deps | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set | `testing` |
| `maintainability-reviewer` | Helpers, data-driven patterns, mock minimalism, update cost | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set | — |
| `performance-reviewer` | I/O in unit tests, sleep/polling, suite speed, test separation | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set | `testing` |

**Full 7-doc set** = `STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md`, `INTEGRATIONS.md`, `STRUCTURE.md` — filtered to those marked present in the availability map.

All `## Before You Begin` file paths are filtered to files marked present in the availability map. An absent file is silently omitted from the load list — the agent never attempts to Read a non-existent file.

### Agent: gap-detector

Cross-references `impl_diff` (implementation changes) against the test diff to identify important code paths and behaviors with no corresponding test. Skipped entirely if `impl_diff` is empty.

Flag as findings:
- **Public/exported functions or methods** added or modified with no corresponding new or updated test.
- **Business logic branches** (`if`/`else`, `switch`, `try/catch`, guard clauses) with no test exercising those paths.
- **Error conditions** — exceptions thrown, error codes returned, validation failures — with no test verifying the error path.
- **Integration points** — new external calls, DB queries, event emissions — with no test covering the interaction.
- **Access control / permission checks** added with no test verifying enforcement.
- **Edge cases implied by the implementation** (null/empty/zero/boundary values handled explicitly in code) with no corresponding test case.

This agent receives `impl_diff` only — not the test diff. It does NOT judge the quality of existing tests — it only identifies what is absent from the implementation side.

## Step 7: Await + Fallback

Wait for all dispatched agents to return. For each agent, resolve its outcome:

| Outcome | Action |
|---------|--------|
| Returned normally | Parse structured result |
| Failed or timed out | Mark dimension as `⚠️ not executed — <reason>` |
| Degraded (missing required context) | Mark dimension as `⚠️ degraded — <missing item>` |
| `gap-detector` skipped (`impl_diff` empty) | Mark dimension as `⚠️ skipped — no implementation changes` |

Continue to Step 8 regardless of individual agent outcomes. A failed agent never blocks the report.

## Step 8: Consolidation and Present Findings

This step is the **third and final user-facing output** (after the skill-invocation announcement and complexity banner from Step 5). No intermediate output appears between the banner and this report.

### Report header (always first)

```
# <branch or TASK-ID> — Test Code Review
Scope: <test files reviewed>
Branch: <branch>
Commits: <hash — subject>, <hash — subject>, ...   ← multi-commit mode only
Diff: <N files changed, +X insertions, -Y deletions[, M excluded as snapshots/lockfiles]>
Run: <date>
Mode: local | GitHub PR #N | multi-commit
Sonar: <status line — see variants below>
[⚠️ Complex review (N test files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.]  ← Complex tier only
```

**Sonar status line variants:**

| Condition | Status line |
|-----------|-------------|
| Active with coverage | `Sonar: active — new code coverage <N>% · branch <branch>` |
| Active, no coverage data | `Sonar: active (partial) — issues only, coverage unavailable` |
| Skipped — no project key | `Sonar: skipped — no project key found` |
| Skipped — MCP not installed | `Sonar: skipped — MCP not installed` |
| Skipped — server unreachable | `Sonar: skipped — server unreachable` |
| No branch data | `Sonar: no data for branch <branch> — run sonar-scanner first` |
| Skipped — query timeout | `Sonar: skipped — query timeout` |

### At-a-glance table (always second)

One row per agent dimension:

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Clarity | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Coverage | ... | N | N | N | 1-line |
| Coverage Gaps | ✅ / ⚠️ skipped — no impl changes / ⚠️ not executed | N | N | N | 1-line |
| Isolation | ... | N | N | N | 1-line |
| Maintainability | ... | N | N | N | 1-line |
| Performance | ... | N | N | N | 1-line |

### Output format

**Flat format** — use when findings are few and span a single dimension:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Zoned format** — use when findings are many or span multiple dimensions (default for subagent reviews):

| Zone | Letter | Agent |
|------|--------|-------|
| Clarity | C | `clarity-reviewer` |
| Coverage | V | `coverage-reviewer` |
| Coverage Gaps | G | `gap-detector` |
| Isolation | I | `isolation-reviewer` |
| Maintainability | M | `maintainability-reviewer` |
| Performance | P | `performance-reviewer` |

Finding IDs: `<ZoneLetter><N>` (e.g. `C1`, `V3`, `I2`). All findings start as `Open`.

**Legend:**
```
✓ Fixed | ✓ Resolved (no change needed) | Tracked | Ignored (user-confirmed) | Pending | Open (not triaged)
```

Per-zone section: `## Zone <Letter> — <Dimension>` with findings table:

| # | Severity | Priority | Title | Type | File:Line | Status | Explanation |
|---|----------|----------|-------|------|-----------|--------|-------------|

At the very bottom: open/untriaged summary table.

---

**Severity:** Critical, High, Medium, Low

**Priority:** P0 (must fix — broken or missing tests on critical paths), P1 (should fix — quality, missing coverage), P2 (nice to have — style, refactoring opportunities)

**Type:** Coverage, Isolation, Maintainability, Pattern, Performance, Quality

Provide specific line numbers. Suggest concrete improvements ("add a test case for null input"). Reference similar patterns from existing tests where helpful.

### Iterative review

After fixes:

1. Update the table — mark fixed items with ✓
2. Re-review only changed test code
3. Continue until all P0/P1 addressed

## Step 9: Post to GitHub (GitHub PR mode only)

Load and apply [GitHub PR Mode — Step B](../../templates/github-pr-review-mode.md).

## Examples

### Example 1: Local workspace review

User: "review my tests"

1. Step 1: No PR number, no commit refs → local workspace mode
2. Step 2: Check presence/absence of all 9 context items (7 codebase docs + 2 checklists); no content loaded
3. Step 3: Build availability map (9 keys)
4. Step 4: `git diff HEAD -- $EXCLUDE` + `git diff --cached -- $EXCLUDE` + `git ls-files --others --exclude-standard` → filter to test files; collect `git diff --stat -- $EXCLUDE`; capture `excluded_count`; collect `impl_diff -- $EXCLUDE` filtered to non-test implementation files
5. Step 5: Complexity assessment — e.g. 8 test files / 350 lines → Medium; emit Review Plan; print banner: `🔍 Test review — Complexity: **Medium** (8 test files, 350 lines) · Parallel — 6 agents`
6. Step 6: Dispatch 6 agents in parallel, one per active dimension (including `gap-detector`, since `impl_diff` non-empty); each self-loads its checklists + codebase docs via `## Before You Begin`
7. Step 7: Await result; mark any failures/degraded dimensions
8. Step 8: Report header (with excluded count if any) → at-a-glance table → zoned findings; iterative review until P0/P1 resolved

### Example 2: GitHub PR review

User: "review tests on PR #42"

1. Step 1: PR #42 → GitHub PR mode
2. Step 2: Check presence/absence of all 9 context items; no content loaded
3. Step 3: Build availability map (9 keys)
4. Step 4: Fetch diff via `gh`; filter changed-file list to remove EXCLUDE patterns; filter to test files; capture `excluded_count`; collect `impl_diff` (non-test implementation files, EXCLUDE applied)
5. Step 5: Complexity assessment → emit Review Plan → print banner (e.g. `🔍 Test review — Complexity: **Large** (18 test files, 950 lines) · Parallel — 6 agents`)
6. Step 6: Dispatch 6 agents in parallel (5 test-quality agents receive test diff; `gap-detector` receives `impl_diff` only; each self-loads via `## Before You Begin`)
7. Step 7: Await results; mark failures/degraded agents
8. Step 8: Consolidated report (excluded count in header) → at-a-glance table → zoned findings
9. Step 9: User selects findings to post → create pending review comments via `gh`; user submits manually on GitHub

### Example 3: Multi-commit review

User: "review test commits abc123 def456"

1. Step 1: Commit hashes with "test commits" trigger → multi-commit mode
2. Step 2: Check presence/absence of all 9 context items; no content loaded
3. Step 3: Build availability map (9 keys)
4. Step 4: `git show abc123 -- $EXCLUDE; git show def456 -- $EXCLUDE` → filter to test files, concatenated; collect commit list (hash + subject) for report header; capture `excluded_count`; collect `impl_diff` with EXCLUDE applied
5. Step 5: Complexity assessment against combined diff totals → emit Review Plan → print banner
6. Step 6: Dispatch agents per tier (e.g. Complex → 6 parallel agents, each self-loading via `## Before You Begin`, each receiving thoroughness directive)
7. Step 7: Await results; mark failures/degraded agents
8. Step 8: Single consolidated report — header lists both commits + excluded count; at-a-glance table + zoned findings

## When No Stack-Specific References Exist

If no technology-specific reference file matches the detected stack:
- Apply `references/test-review-checklist.md` in full
- Note in the output that stack-specific guidance was not available
- Flag universal anti-patterns (no assertions, shared state, flakiness, over-mocking)

## Key Reminders

- Tests are documentation — they show how the system is meant to be used
- A few well-written tests are better than many poorly written ones
- If a test is hard to write, it may signal a design problem in the production code
- Flaky tests are worse than no tests — they erode trust in the whole suite
