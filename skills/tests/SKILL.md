---
name: tests
description: >
  Write and maintain tests for any project. Covers unit tests, integration tests, and code
  coverage analysis. Technology agnostic — adapts to the project's stack using context files.
  Use when the user says "write tests", "add tests", "missing tests", "test coverage", "unit test",
  or "integration test". Do NOT use for reviewing existing test quality — use the tests-code-review
  skill for that. Do NOT use for TDD methodology — use the tests-tdd skill. Do NOT use just to
  run tests.
metadata:
  version: "1.0.0"
  triggers:
    - "write tests"
    - "test coverage"
    - "unit test"
    - "integration test"
    - "add tests"
    - "missing tests"
---

# Testing

Guidelines for writing, maintaining, and running tests across any technology stack.

## Testing Philosophy

- For test-first methodology (red-green-refactor), use the **tests-tdd** skill
- Write tests alongside or immediately after implementation when adding features
- Tests define success criteria and enable confident refactoring
- Focus on meaningful tests over coverage metrics
- **Tests are documentation** — a test name and body should explain how the system is meant to work, without needing comments
- A few well-written tests are better than many poorly written ones
- If a test is hard to write, it signals a design problem in the production code — surface it

---

## Step 1: Load project test conventions

Before writing any tests, check whether the project has a test conventions file:

- `docs/TESTS.md` — project-specific conventions, base classes, fixtures, naming patterns

If this file exists, follow it precisely. It takes precedence over the generic guidance below.

Then load the reference files:

> **CONSTRAINT: Load ONLY stack-relevant references.**
> Reference files use `<tech-prefix>-<purpose>.md` naming. A file is tech-specific if its name
> starts with a known prefix (e.g., `python-`, `django-`). A file is generic if it has no tech
> prefix (e.g., `testing-patterns.md`). Skip all non-matching tech-specific files.
> If `docs/PROJECT_DETAILS.md` is missing or has no Tech Stack section, do NOT load any
> tech-specific references — load only generic files.

1. Always load `references/testing-patterns.md` — FIRST principles, test structure, test doubles, design rules (generic)
2. Always load `references/coverage-guide.md` — coverage goals and what not to test (generic)
3. Identify the project's language and framework from `docs/PROJECT_DETAILS.md`
4. Load ONLY matching technology-specific reference files from `references/` whose prefix matches
   the detected stack. If the stack is Python + Django, load `python-tests.md` AND `django-tests.md`.
   Skip all other tech-specific files (e.g., `golang-tests.md`, `php-tests.md`).

If no matching technology-specific reference file exists for the detected stack, STOP and output:

---
> ⚠️ **No tech-specific test reference found for: [detected stack]**
>
> No matching reference file was found in `references/`. Generic testing principles will apply,
> but stack-specific patterns (fixtures, assertion styles, framework idioms) will NOT be enforced.
>
> **Options:**
> 1. Run `tech-reference-add` to generate test guidelines for this stack, then retry.
> 2. Proceed with generic principles only.
>
> _Reply with **1** or **2** to continue._
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

> For TDD methodology (red-green-refactor, test-first workflows), see the **tests-tdd** skill.

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
- [ ] Test names clearly describe the scenario AND the expected outcome — a failing name explains itself
- [ ] Tests are independent and do not rely on execution order
- [ ] No flaky patterns (sleeps, random state, time-dependent assertions)
- [ ] Arrange-Act-Assert structure is visible in each test
- [ ] Mocks only cover external dependencies — do NOT mock the unit under test
- [ ] Mock setup is minimal — over-mocking hides real behaviour
- [ ] Common setup is extracted into helpers — not copy-pasted across tests
- [ ] Test code reads as documentation of how the system is meant to work

---

## Example

User says: "Write tests for the new payment processor module."

1. Check `docs/TESTS.md` for project conventions
2. Load `references/testing-patterns.md` and `references/coverage-guide.md`
3. Detect stack from `docs/PROJECT_DETAILS.md` and load ALL matching stack-specific references
4. Write unit tests for the payment processor's core logic in isolation
5. Write integration tests for the database and external service interactions
6. Verify the completion checklist before finishing

## References

- `references/testing-patterns.md` — FIRST principles, test structure, test doubles, design rules, anti-patterns
- `references/coverage-guide.md` — coverage goals, what to test, what to skip
