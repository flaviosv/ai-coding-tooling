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

## Step 1: Determine Review Mode

Parse the user's request:

- **No PR number** → local workspace mode. Proceed to Step 2.
- **PR number provided** (e.g. "review tests on PR #123", "check tests PR 42") → GitHub PR mode.

For **GitHub PR mode**, load and apply [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md).

## Step 2: Load Project Context

Load these files if they exist:

| File | Purpose |
|------|---------|
| `docs/ARCHITECTURE.md` | Understand which layers the changed tests cover |
| `docs/CODING_STYLE.md` | Naming conventions that apply to test code too |
| `docs/PROJECT_DETAILS.md` | Tech stack, dependencies, environment config |
| `docs/TECH_DEBTS.md` | Known tech debts and anti-patterns — flag test code that replicates these |
| `docs/TESTS.md` | Project-specific test conventions, base classes, naming patterns |

## Step 3: Load Review Checklists

Load and apply [Reference Loading Constraint](../../templates/reference-loading-constraint.md).

**Mandatory baseline** (always load — generic):

1. `references/test-review-checklist.md` — generic test quality checklist (structure, coverage, isolation, determinism, maintainability, test doubles, anti-patterns)

**Tech-specific checklists**: load ONLY matching `<language>-*` and `<framework>-*` from `references/` whose prefix matches the detected stack. If the stack is Python + Django, load `python-tests-code-review.md` AND `django-tests-code-review.md`. Skip all other tech-specific files. If no matching file exists in `references/`, proceed with the mandatory baseline only.

## Step 4: Collect Changed Files

**Local workspace mode**:

```bash
git diff HEAD --name-only                    # modified tracked files (filter to test files)
git diff --cached --name-only                # staged files (filter to test files)
git ls-files --others --exclude-standard     # untracked new files (filter to test files)
```

**GitHub PR mode**: parse file paths from the diff fetched in Step 1, filter to test files.

In both modes: skip deleted files, non-test files, and generated test code.

## Step 5: Review All Test Files

Apply the villain stance to **every dimension**. A naming violation is as worth flagging as a missing assertion.

### Clarity and Readability

- Test names describe the scenario and expected outcome — a failing name explains itself
- Arrange-Act-Assert structure is clearly visible
- Each test is focused on one behaviour
- Test code reads as documentation of how the system is meant to work

### Coverage and Completeness

- Happy path is tested
- Error paths and failure scenarios are tested
- Edge cases are covered (null, empty, zero, boundary values, invalid input)
- Integration points are tested where the change touches component interactions
- Access-controlled paths tested for both authorized and unauthorized cases

### Independence and Isolation

- Tests do not share mutable state
- Each test can run in any order and in isolation
- External dependencies are mocked appropriately in unit tests
- Any written state (database, filesystem) is reset between tests
- Tests are deterministic — no random values, no time-dependent assertions

### Maintainability

- Common setup is extracted into helpers or shared setup — not copy-pasted
- Data-driven tests used for similar cases instead of duplicated test bodies
- Tests are easy to update as the code evolves
- Mocks are minimal and focused — not mocking the thing under test

### Performance

- Unit tests have no I/O and run fast
- Integration tests are clearly marked or separated
- No unnecessary delays (`sleep`, polling, busy-wait)

### Tech Debt Recurrence

If `docs/TECH_DEBTS.md` was loaded, cross-reference findings against known debts. Test code that introduces or replicates a listed anti-pattern → **Critical / P0** with reference to the specific debt entry.

## Step 6: Present Findings

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Severity:** Critical, High, Medium, Low

**Priority:** P0 (must fix — broken or missing tests on critical paths), P1 (should fix — quality, missing coverage), P2 (nice to have — style, refactoring opportunities)

**Type:** Coverage, Isolation, Pattern, Performance, Quality

Format for CLI readability. Provide specific line numbers. Suggest concrete improvements ("add a test case for null input"). Reference similar patterns from existing tests where helpful.

## Step 7: Iterative Review

After fixes:

1. Update the table — mark fixed items with ✓
2. Re-review only changed test code
3. Continue until all P0/P1 addressed

## Step 8: Post to GitHub (GitHub PR mode only)

Load and apply [GitHub PR Mode — Step B](../../templates/github-pr-review-mode.md).

## Examples

### Example 1: Local workspace review

User: "review my tests"

1. No PR number → local mode
2. Load context: `PROJECT_DETAILS.md`, `TESTS.md`, `CODING_STYLE.md`, `ARCHITECTURE.md`, `TECH_DEBTS.md`
3. Load baseline + tech-specific checklists + test-writing references from `tests` skill
4. `git diff HEAD --name-only` + `git diff --cached --name-only` + `git ls-files --others --exclude-standard` → filter to test files
5. Review each test file against all loaded checklists
6. Present findings table
7. After fixes → update table, continue until P0/P1 resolved

### Example 2: GitHub PR review

User: "review tests on PR #42"

1. PR #42 → GitHub mode
2. Check for GitHub MCP → use it or fall back to `gh pr view 42` + `gh pr diff 42`
3. Load context and checklists (same as local)
4. Review test files in PR diff only — ignore workspace
5. Present findings table in terminal
6. User: "post 1, 3, 5 to GitHub"
7. Create pending review with 3 comments via MCP or `gh api`
8. Report: "3 comments added to pending review on PR #42. Submit manually on GitHub."

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
