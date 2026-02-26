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

Review test code quality, coverage patterns, and maintainability across any technology stack.

## Scope

When invoked:
- Review **only** test files changed in the git workspace
- **Do NOT make changes** — only share findings with explanations
- Skip deleted test files
- Focus on test quality, not just coverage metrics

## Project Context

Before reviewing, load the following if they exist:

- `.agents/TESTS.md` — project-specific test conventions, base classes, naming patterns
- `.agents/CODING_STYLE.md` — naming conventions that apply to test code too
- `.agents/ARCHITECTURE.md` — understand which layers the changed tests cover

## Review References

Always load:
- `references/test-review-checklist.md` — generic quality checklist

Then identify the project's language and framework from `.agents/PROJECT_DETAILS.md` and load
**all** matching technology-specific reference files from `references/`. Reference files follow the
naming convention `<language>-*` and `<framework>-*`. If the stack is Python + Django, load both
`python-test-review-guide.md` AND `django-test-review-guide.md`. Combine all loaded files —
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

- Test files that have not changed in this workspace
- Deleted test files
- Third-party test utilities or generated test code
- Implementation (non-test) files — use the **code-review** skill for those

## Example

User says: "Can you review the tests I wrote for the auth module?"

1. Load `.agents/TESTS.md`, `CODING_STYLE.md`, `ARCHITECTURE.md` if present
2. Load `references/test-review-checklist.md`
3. Detect stack and load any matching stack-specific references
4. Identify changed test files in the git workspace
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
