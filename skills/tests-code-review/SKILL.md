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
  version: "2.0.0"
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

**New test files are always in scope.** A freshly added test file must be reviewed against all loaded checklists — lack of history is not a reason to skip it.

### GitHub PR Constraints

- **Never post comments to GitHub automatically.** Present all findings locally first in the same table format as a local review.
- Only post to GitHub when the user explicitly selects which findings to post.
- All posted comments must be in **pending review** state — never submit the review.
- The user reviews and submits manually on GitHub.

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

Load all of the following in one pass before spawning any subagent. Each item is either **present** (loaded) or **absent** (noted for Step 3).

**Codebase docs** — load from `.specs/codebase/`; fall back to `docs/codebase/` then `docs/` if not yet migrated. If old structure found, suggest migrating to `.specs/codebase/`:

| File | Availability key |
|------|-----------------|
| `STACK.md` | `stack` |
| `ARCHITECTURE.md` | `architecture` |
| `CONVENTIONS.md` | `conventions` |
| `TESTING.md` | `testing` |
| `CONCERNS.md` | `concerns` |
| `INTEGRATIONS.md` | `integrations` |
| `STRUCTURE.md` | `structure` |

**Review checklists** — mandatory baseline always loaded; tech-specific only when stack matches:

| File | Availability key |
|------|-----------------|
| `references/test-review-checklist.md` | `checklist_baseline` |
| `references/<stack>-*-tests-code-review.md` (if match) | `checklist_tech_specific` |

**Other:**

| Item | Availability key |
|------|-----------------|
| `docs/TECH_DEBTS.md` | `tech_debts` |

## Step 3: Context Availability Map + Bundle Assembly

Build the availability map from Step 2 results:

```
availability = {
  // codebase docs
  stack, architecture, conventions, testing,
  concerns, integrations, structure,
  // checklists
  checklist_baseline, checklist_tech_specific,
  // other
  tech_debts
}
// each field: present | absent
```

Use this map to assemble a **context bundle** for each subagent — a structured text block injected into the agent's prompt containing only the items marked `present` and relevant to that agent's dimension. Bundle definitions are in Step 6.

If a bundle is missing a **required** item for an agent, flag that agent as `degraded`: it proceeds without that item, notes the gap in its findings, and the at-a-glance table shows `⚠️ degraded — <missing item>`.

Special case: `TESTING.md` absent → `isolation-reviewer` and `performance-reviewer` run degraded; they fall back to inferring the test framework from `STACK.md` or test file patterns.

## Step 4: Diff Collection

Collect the diff and test file list based on the mode from Step 1. Filter to test files in all modes:

| Mode | Commands |
|------|----------|
| Local workspace | `git diff HEAD`, `git diff --cached`, `git ls-files --others --exclude-standard` — filter to test files |
| GitHub PR | `gh pr diff <PR#>` (prefer GitHub MCP if available) — filter to test files |
| Multi-commit (hashes) | `git show <h1>; git show <h2>; ...` — concatenated in order, filter to test files |
| Multi-commit (range) | `git diff <base>..<tip>` — filter to test files |

Also collect:
- `git diff --stat` (or equivalent, filtered to test files) — used in the report header
- Changed test file list — used to route context slices to agents
- **Multi-commit only:** `git log --oneline <range>` or resolved hash+subject list — used in report header

In all modes: skip deleted files, non-test files, and generated test code.

## Step 5: Quick Mode Check

**Condition:** changed test file count ≤ 5 **AND** total diff lines < 100

**If triggered:** skip Steps 6–7; fall back to inline review — apply all 5 dimensions directly without spawning agents, then proceed to [Present Findings](#step-8-consolidation-and-present-findings).

**Multi-commit mode:** apply this check against the combined diff totals across all commits.

If the condition is not met, proceed to Step 6 (parallel subagent dispatch).

## Step 6: Parallel Subagent Dispatch

**All 5 agents MUST be fired in a single parallel message. Never sequentially.**

Each agent receives a prompt with four sections:

```
## Role
<agent name and dimension>

## Context
<inlined content from the agent's context bundle — present items only, relevant to this dimension>

## Diff
<full test-file diff from Step 4 — all agents receive the full diff; scoping is in the context, not the code>

## Return format
Status: Complete | Blocked | Partial
Dimension: <agent name>
Findings: [{severity, title, file, line, explanation, recommendation}]
Files reviewed: [list]
Gate check: pass | fail | skipped — <detail>
Issues: <any blockers encountered>
```

### Agent Roster

| Agent | Dimension | Required context | Optional context | Degrades without |
|-------|-----------|-----------------|------------------|-----------------|
| `clarity-reviewer` | Test naming, AAA structure, focus, readability as docs | `checklist_baseline` (clarity section) | `conventions`, `stack` | `conventions` |
| `coverage-reviewer` | Happy path, error paths, edge cases, integration points, access control | `checklist_baseline` (coverage section) | `architecture`, `stack`, `concerns` | — |
| `isolation-reviewer` | Shared state, ordering, mocks, determinism, external deps | `checklist_baseline` (isolation section) | `testing`, `integrations`, `stack` | `testing` |
| `maintainability-reviewer` | Helpers, data-driven patterns, mock minimalism, update cost | `checklist_baseline` (maintainability section) | `conventions`, `stack`, `checklist_tech_specific` | — |
| `performance-reviewer` | I/O in unit tests, sleep/polling, suite speed, test separation | `checklist_baseline` (performance section) | `testing`, `stack` | `testing` |

### Reviewer Stance (injected into every agent)

You are the villain. Find every gap, weakness, and lie in the test suite — not encourage.

- Be relentless. Weak tests are worse than no tests — they create false confidence.
- Every missing case, every flawed assertion, every poorly isolated test is a finding.
- If a test could pass even when the code is broken, that IS a broken test — flag it.
- State problems directly: file, line number, consequence.
- Never sign off on a test suite that would fail to catch real bugs.

### Tech Debt Recurrence (injected into all agents)

If `docs/TECH_DEBTS.md` was loaded, cross-reference findings against known debts. Test code that introduces or replicates a listed anti-pattern → **Critical / P0** with reference to the specific debt entry.

### Quick mode inline fallback (from Step 5)

When Quick Mode Check triggered: skip subagent dispatch. Apply all 5 dimensions inline without spawning agents, then proceed to Step 8 (Present Findings).

## Step 7: Await + Fallback

Wait for all dispatched agents to return. For each agent, resolve its outcome:

| Outcome | Action |
|---------|--------|
| Returned normally | Parse structured result |
| Failed or timed out | Mark dimension as `⚠️ not executed — <reason>` |
| Degraded (missing required context) | Mark dimension as `⚠️ degraded — <missing item>` |

Continue to Step 8 regardless of individual agent outcomes. A failed agent never blocks the report.

## Step 8: Consolidation and Present Findings

### Report header (always first)

```
# <branch or TASK-ID> — Test Code Review
Scope: <test files reviewed>
Branch: <branch>
Commits: <hash — subject>, <hash — subject>, ...   ← multi-commit mode only
Diff: <N files changed, +X insertions, -Y deletions>
Run: <date>
Mode: local | GitHub PR #N | multi-commit
```

### At-a-glance table (always second)

One row per agent dimension:

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Clarity | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Coverage | ... | N | N | N | 1-line |
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
2. Step 2: Load all `.specs/codebase/` docs + baseline checklist + tech-specific checklist + `docs/TECH_DEBTS.md`
3. Step 3: Build availability map; assemble context bundles per agent
4. Step 4: `git diff HEAD` + `git diff --cached` + `git ls-files --others --exclude-standard` → filter to test files; collect `git diff --stat`
5. Step 5: Quick mode check — if ≤ 5 test files and < 100 lines, review inline; otherwise continue
6. Step 6: Dispatch all 5 agents in parallel, each with their context bundle + full test-file diff
7. Step 7: Await all results; mark any failures/degraded agents
8. Step 8: Report header → at-a-glance table → zoned findings; iterative review until P0/P1 resolved

### Example 2: GitHub PR review

User: "review tests on PR #42"

1. Step 1: PR #42 → GitHub PR mode
2. Step 2: Load all context + checklists (same as local)
3. Step 3: Build availability map + bundles
4. Step 4: `gh pr diff 42` (prefer GitHub MCP) → filter to test files; collect changed test file list
5. Step 5: Quick mode check
6. Step 6: Dispatch 5 agents in parallel against PR test-file diff only — ignore local workspace
7. Step 7: Await results
8. Step 8: Consolidated report with at-a-glance table
9. Step 9: User selects findings to post → create pending review comments via MCP or `gh api`; user submits manually on GitHub

### Example 3: Multi-commit review

User: "review test commits abc123 def456"

1. Step 1: Commit hashes with "test commits" trigger → multi-commit mode
2. Step 2: Load all context + checklists
3. Step 3: Build availability map + bundles
4. Step 4: `git show abc123; git show def456` → filter to test files, concatenated; collect commit list (hash + subject) for report header
5. Step 5: Quick mode check applied against combined diff totals
6. Step 6: Dispatch 5 agents in parallel against combined test-file diff
7. Step 7: Await results
8. Step 8: Single consolidated report — header lists both commits; at-a-glance table + findings as normal

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
