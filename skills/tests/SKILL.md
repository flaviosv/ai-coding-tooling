---
name: tests
description: >
  Write and maintain tests for any project. Covers unit tests, integration tests, code coverage
  analysis, and TDD (test-driven development). Technology agnostic — adapts to the project's
  stack using context files. Use when the user says "write tests", "add tests", "missing tests",
  "test coverage", "unit test", "integration test", "TDD", "test-driven", "red-green-refactor",
  "write test first", or "test-first". Do NOT use for reviewing existing test quality — use
  tests-code-review for that. Do NOT use just to run tests.
metadata:
  version: "2.0.0"
  triggers:
    - "write tests"
    - "test coverage"
    - "unit test"
    - "integration test"
    - "add tests"
    - "missing tests"
    - "TDD"
    - "test-driven"
    - "red-green-refactor"
    - "write test first"
    - "test-first"
---

# Testing

Guidelines for writing, maintaining, and running tests across any technology stack.

## Testing Philosophy

- For test-first methodology (red-green-refactor), choose TDD strategy in Step 0
- Write tests alongside or immediately after implementation when adding features
- Tests define success criteria and enable confident refactoring
- Focus on meaningful tests over coverage metrics
- **Tests are documentation** — a test name and body should explain how the system is meant to work, without needing comments
- A few well-written tests are better than many poorly written ones
- If a test is hard to write, it signals a design problem in the production code — surface it

## Step 0: Determine Testing Strategy

Ask the user (unless they already stated a preference):

> "Should I use **TDD** (write failing tests first, red-green-refactor cycle) or **regular** testing (write tests alongside or after implementation)?"

- **Regular** → skip to Step 1.
- **TDD** → apply the TDD section below, then continue to Step 1 for reference/convention loading.

### TDD Methodology (apply only when TDD strategy is chosen)

#### Test First, Always

Never write implementation before a failing test. The test defines what success looks like before a single line of production code exists.

- Start every task by writing a test that describes the expected behavior.
- The test must fail for the right reason — not because of a syntax error or missing import.
- If you cannot write a test first, the requirement is not clear enough. Clarify before coding.
- A test written after the code is confirmation bias, not TDD.

#### Red-Green-Refactor

The three-step cycle: **Red** — write a failing test. **Green** — write the minimum code to pass. **Refactor** — clean up while all tests stay green.

- Red: one test, one behavior. Run it. Watch it fail. Read the failure message.
- Green: write the simplest code that makes the test pass. No cleverness, no extras.
- Refactor: improve structure, remove duplication, rename for clarity. Tests must stay green.
- Never skip refactor. The green phase produces ugly code on purpose — refactor is where design emerges.

#### Small Steps

Each cycle adds one behavior. Write one test, make it pass, clean up, repeat.

- If you write more than ~10 lines of production code to pass a test, the test covers too much. Split it.
- Commit after each green-refactor cycle. Small commits are cheap insurance.

#### When NOT to Apply TDD

- **Spiking / prototyping** — exploring a new library or API. Throw the spike away and TDD the real implementation.
- **Trivial code** — getters, setters, simple data classes with no logic.
- **UI exploration** — visual layout, styling, design iteration. TDD the behavior behind the UI, not the pixels.

---

## Step 1: Load project test conventions

Check whether the project has a test conventions file:

- `docs/codebase/TESTING.md` — project test conventions, frameworks, coverage matrix, gate commands, fixtures, and naming patterns

If this file exists, follow it precisely. It takes precedence over the generic guidance below.

Then load the reference files:

1. Always load `references/testing-patterns.md` — FIRST principles, test structure, test doubles, design rules (generic)
2. Always load `references/coverage-guide.md` — coverage goals and what not to test (generic)
3. Identify the project's language and framework from `docs/codebase/STACK.md`
4. List files in `references/` and load ONLY those whose prefix matches the detected stack.
   If the stack is Python + Django, load `python-tests.md` AND `django-tests.md` if they exist.
   Skip all other tech-specific files.
5. If no matching technology-specific reference file exists in `references/`, proceed using only
   the generic references already loaded — do not look outside the `references/` folder.

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

> For TDD methodology (red-green-refactor, test-first workflows), choose TDD in Step 0.

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

## Example

User says: "Write tests for the new payment processor module."

1. Check `docs/codebase/TESTING.md` for project conventions
2. Load `references/testing-patterns.md` and `references/coverage-guide.md`
3. Detect stack from `docs/codebase/STACK.md` and load ALL matching stack-specific references
4. Write unit tests for the payment processor's core logic in isolation
5. Write integration tests for the database and external service interactions
6. Verify the completion checklist before finishing

## References

- `references/coverage-guide.md` — coverage goals, what to test, what to skip
- `references/testing-patterns.md` — FIRST principles, test structure, test doubles, design rules, anti-patterns