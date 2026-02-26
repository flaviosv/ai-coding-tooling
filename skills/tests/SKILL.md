---
name: tests
description: >
  Write and maintain tests for any project. Covers unit tests, integration tests, test-driven
  development practices, and code coverage analysis. Technology agnostic — adapts to the project's
  stack using context files. Use when the user says "write tests", "add tests", "missing tests",
  "TDD", "test coverage", "unit test", or "integration test". Do NOT use for reviewing existing
  test quality — use the tests-code-review skill for that. Do NOT use just to run tests.
metadata:
  version: "1.0.0"
  triggers:
    - "write tests"
    - "test coverage"
    - "TDD"
    - "unit test"
    - "integration test"
    - "add tests"
    - "missing tests"
---

# Testing

Guidelines for writing, maintaining, and running tests across any technology stack.

## Testing Philosophy

- Write tests before implementation when fixing bugs (TDD)
- Write tests alongside or immediately after implementation when adding features
- Tests define success criteria and enable confident refactoring
- Focus on meaningful tests over coverage metrics

---

## Step 1: Load project test conventions

Before writing any tests, check whether the project has a test conventions file:

- `.agents/TESTS.md` — project-specific conventions, base classes, fixtures, naming patterns

If this file exists, follow it precisely. It takes precedence over the generic guidance below.

Then load the reference files:

1. Always load `references/testing-patterns.md` — generic patterns and structure
2. Always load `references/coverage-guide.md` — coverage goals and what not to test
3. Identify the project's language and framework from `.agents/PROJECT_DETAILS.md`
4. Load **all** matching technology-specific reference files from `references/`. Reference files
   follow the naming convention `<language>-*` and `<framework>-*`. If the stack is Python + Django,
   load both `python-testing-guide.md` AND `django-testing-guide.md`. Combine all loaded files.

---

## Test Types

### Unit Tests
Test individual functions, methods, or classes in isolation with no external dependencies.

**Use for:** pure functions, business logic, validation, transformations

### Integration Tests
Test how components work together with real dependencies.

**Use for:** database operations, API endpoints, service boundaries, middleware

### Parametrized Tests
Test multiple scenarios using the testing framework's parametrize feature.

**Use when:**
- 3 or more similar test cases with the same structure
- Testing validation rules with many inputs
- Covering multiple edge cases systematically

**Skip when:**
- Only 1–2 cases (overhead not worth it)
- Test setups differ significantly between cases

---

## TDD Workflow

### Bug fixes
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test now passes and no regressions introduced

### New features
1. Write tests for expected behaviour — they should fail
2. Implement the minimum code to make tests pass
3. Refactor if needed — tests must still pass

### Refactoring
1. Run existing tests — all must pass (establish baseline)
2. Refactor
3. Run tests again — behaviour must be unchanged

---

## Completion Checklist

Before considering a feature or fix complete:

- [ ] Unit tests written for new functions and methods
- [ ] Integration tests written for critical flows
- [ ] Happy path tested
- [ ] Error paths tested
- [ ] Edge cases covered (null, empty, boundary values, invalid input)
- [ ] All tests passing
- [ ] Coverage acceptable for critical paths
- [ ] Test names clearly describe what they verify
- [ ] Tests are independent and do not rely on execution order
- [ ] No flaky patterns (sleeps, random state, time-dependent assertions)

---

## Example

User says: "Write tests for the new payment processor module."

1. Check `.agents/TESTS.md` for project conventions
2. Load `references/testing-patterns.md` and `references/coverage-guide.md`
3. Detect stack from `.agents/PROJECT_DETAILS.md` and load ALL matching stack-specific references
4. Write unit tests for the payment processor's core logic in isolation
5. Write integration tests for the database and external service interactions
6. Verify the completion checklist before finishing

## When No Test Conventions File Exists

If `.agents/TESTS.md` is not present:
- Follow the generic patterns from `references/testing-patterns.md`
- Infer naming conventions from existing test files in the project
- If no existing tests exist, apply the patterns directly and note the assumption

## References

- `references/testing-patterns.md` — test organisation, naming, mocking, parametrize, setup/teardown
- `references/coverage-guide.md` — coverage goals, what to test, what to skip
