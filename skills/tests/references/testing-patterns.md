# Testing Patterns

Generic patterns for organising, writing, and maintaining tests across any technology stack.
Technology-specific guides extend this file.

---

## Test Organisation

Group tests by the unit or feature they cover. Two common approaches:

**Mirror source structure** — one test file per source file, placed alongside or in a sibling `tests/` directory:
```
<module>/
  <source-file>
  tests/
    <test-file-for-source>
```

**Group by feature** — tests for a cross-cutting concern live together:
```
tests/
  <feature-a>/
  <feature-b>/
```

Keep unit test files close to the code they test. Integration tests may span modules and can live
in a top-level `tests/` directory.

---

## Test Naming

Test names must communicate intent — a failing test name should tell you what broke without
reading the body. Follow whatever naming convention the project uses (check `.agents/TESTS.md`).

Patterns that work across languages:
- `<subject>_<scenario>_<expected_outcome>`
- `<subject> when <condition> returns <expected_outcome>` (describe/it style)

Examples:
- `createUser_withValidData_succeeds`
- `createUser_whenEmailMissing_returnsValidationError`
- `calculateTotal_withEmptyCart_returnsZero`
- `"when email is missing, returns a validation error"` (BDD style)

Avoid:
- Generic names that say nothing: `test1`, `testUser`, `testFeature`
- Names that describe the action but not the outcome: `createsUser`
- Overly long names (keep under 100 characters)

---

## Arrange–Act–Assert (AAA)

Structure every test with three clearly separated phases:

```
Arrange — set up preconditions and inputs
Act     — invoke the unit under test
Assert  — verify the outcome
```

Keep each phase minimal. If arrange grows large, extract it into a helper or setup function.

---

## Test Setup and Teardown

Use the framework's setup/teardown mechanisms to avoid repeating code across tests.

Principles:
- Each setup helper has a single responsibility
- Build complex state by composing simple helpers
- Prefer small, focused setup over one large shared initialisation
- Always clean up side effects — reset state so tests do not affect each other
- Avoid global mutable state shared across test files

---

## Mocking

### Mock when:
- Isolating a unit from external dependencies (network, filesystem, database in unit tests)
- The dependency has non-deterministic behaviour (time, randomness, external services)
- Testing that a specific call was made, without caring about its result

### Use real dependencies when:
- Writing integration tests — actual behaviour must be verified end-to-end
- The dependency is fast and deterministic (in-memory store, test database)
- Mocking would hide the behaviour being tested

### Best practices:
- Mock at the boundary closest to the unit under test
- Verify mock calls only when the interaction itself is what is being tested
- Keep mock setup simple — complex mocks are a signal the unit under test is too large

---

## Data-Driven / Parametrized Tests

When multiple inputs share the same test structure, use the framework's data-driven or
parametrize feature instead of duplicating test bodies.

Concept:
```
for each (input, expected) in test_cases:
  result = subject(input)
  assert result == expected
```

Label each case so failures are identifiable without reading the parameter values.

Use when:
- 3 or more similar cases with the same assertion structure
- Testing validation rules or boundary conditions systematically

Skip when:
- Only 1–2 cases — the overhead is not worth it
- Cases require significantly different setup or assertions

---

## Test Independence

- Tests must not share mutable state
- Each test must be able to run in any order and in isolation
- Any state written to a database, filesystem, or external service must be reset between tests
- Never rely on a previous test having run or on test execution order
