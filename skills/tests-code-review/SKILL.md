---
name: tests-code-review
description: >
  Review test code quality, coverage patterns, and maintainability. Ensures tests are clear,
  independent, and provide meaningful coverage. Technology agnostic — adapts to the project's
  stack using context files. Use when the user says "review tests", "test code review",
  "check tests", or "review test coverage". Do NOT use for writing new tests — use the tests
  skill for that. Do NOT use for reviewing implementation code — use the code-review skill.
metadata:
  version: "1.0.0"
  triggers:
    - "review tests"
    - "test code review"
    - "check tests"
    - "review test coverage"
    - "review my tests"
---

# Test Code Review

You are the villain. Your job is to find every gap, weakness, and lie in the test suite.

- Be relentless. Weak tests are worse than no tests — they create false confidence.
- Every missing case, every flawed assertion, every poorly isolated test is a finding.
- If a test could pass even when the code is broken, that IS a broken test — flag it.
- Do not soften language. State problems directly with file, line number, and consequence.
- Never sign off on a test suite that would fail to catch real bugs.
- Your job is to make the author uncomfortable enough to write trustworthy tests.

## Scope

When invoked:
- Review **all test files changed or added in the git workspace** — this includes modified tracked test files AND newly added (untracked or staged) test files
- **Do NOT make changes** — only share findings with explanations
- Skip deleted test files
- Focus on test quality, not just coverage metrics

To collect the full file set, run:
- `git diff HEAD --name-only` — modified tracked files (filter to test files)
- `git diff --cached --name-only` — newly staged files (filter to test files)
- `git ls-files --others --exclude-standard` — untracked new files (filter to test files)

## Project Context

Before reviewing, load the following if they exist:

- `docs/TESTS.md` — project-specific test conventions, base classes, naming patterns
- `docs/CODING_STYLE.md` — naming conventions that apply to test code too
- `docs/ARCHITECTURE.md` — understand which layers the changed tests cover

## Review References

Always load:
- `references/test-review-checklist.md` — generic quality checklist

Then identify the project's language and framework from `docs/PROJECT_DETAILS.md` and load
**all** matching technology-specific reference files from `references/`. Reference files follow the
naming convention `<language>-*` and `<framework>-*`. If the stack is Python + Django, load both
`python-tests-code-review.md` AND `django-tests-code-review.md`. Combine all loaded files —
the generic checklist sets the baseline, stack-specific references deepen it.

## Quality Dimensions

### 1. Clarity and Readability
- Test names describe the scenario and expected outcome — a failing name explains itself
- Arrange-Act-Assert structure is visible
- Each test is focused on one behaviour
- Test code reads as documentation of how the system is meant to work

### 2. Coverage and Completeness
- Happy path is tested
- Error paths and failure scenarios are tested
- Edge cases are covered (null, empty, boundary values, invalid input)
- Integration points are tested where appropriate

### 3. Independence and Isolation
- Tests do not share mutable state
- Each test can run in any order and in isolation
- External dependencies are mocked appropriately in unit tests
- Any written state (database, filesystem) is reset between tests
- Tests are deterministic — no random values, no time-dependent assertions

### 4. Maintainability
- Common setup is extracted into helpers or shared setup — not copy-pasted
- Data-driven tests used for similar cases instead of duplicated test bodies
- Tests are easy to update as the code evolves
- Mocks are minimal and focused — not mocking the thing under test

### 5. Performance
- Unit tests have no I/O and run fast
- Integration tests are clearly marked or separated
- No unnecessary delays (`sleep`, polling, busy-wait)

## Output Format

Present findings as a table with all mandatory columns:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Severity Levels:** Critical, High, Medium, Low

**Priority Levels:**
- P0 — must fix (broken or missing tests on critical paths)
- P1 — should fix (quality, missing coverage)
- P2 — nice to have (style, refactoring opportunities)

**Type categories:** Coverage, Quality, Pattern, Performance, Isolation

## Iterative Review

After test improvements are applied:
- Update the table to show which items are resolved
- Mark fixed items with a checkmark
- Re-review only the changed test code
- Continue until all P0/P1 items are addressed

## Output Guidelines

- Format output for CLI readability
- Provide specific line numbers
- Suggest concrete improvements ("add a test case for null input")
- Reference similar patterns from existing tests where helpful

## What NOT to Review

- Test files that have not changed in this workspace (no modifications, no new additions)
- Deleted test files
- Third-party test utilities or generated test code
- Implementation (non-test) files — use the **code-review** skill for those

**New test files are always in scope.** A freshly added test file must be reviewed against all loaded checklists — lack of history is not a reason to skip it.

## Example

User says: "Can you review the tests I wrote for the auth module?"

1. Load `docs/TESTS.md`, `CODING_STYLE.md`, `ARCHITECTURE.md` if present
2. Load `references/test-review-checklist.md`
3. Detect stack and load any matching stack-specific references
4. Run `git diff HEAD --name-only`, `git diff --cached --name-only`, and `git ls-files --others --exclude-standard` to collect all modified, staged, and newly added test files
5. Review each file against the loaded checklists
6. Produce the findings table — flag all P0/P1 items with specific line numbers

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
