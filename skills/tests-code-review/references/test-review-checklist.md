# Test Code Review Checklist

Generic baseline checklist for reviewing test code quality across any technology stack.
Technology-specific guides extend this file.

---

## Structure and Clarity

- [ ] Every test has at least one assertion
- [ ] Test name describes the scenario and the expected outcome
- [ ] Arrange-Act-Assert structure is clearly visible
- [ ] Each test covers one concept or behaviour — not multiple unrelated assertions
- [ ] Test code reads as documentation of intended system behaviour

---

## Coverage and Completeness

- [ ] Happy path is tested
- [ ] Error paths and failure scenarios are tested
- [ ] Edge cases are covered (null, empty, zero, maximum, invalid input)
- [ ] Boundary conditions tested where applicable
- [ ] Integration points tested where the change touches component interactions

---

## Independence and Isolation

- [ ] Tests do not share mutable state across test cases
- [ ] Each test can run independently and in any order
- [ ] External dependencies (network, filesystem, external services) are mocked in unit tests
- [ ] Any side effects (database writes, file creation) are cleaned up or isolated
- [ ] No test relies on another test having run first

---

## Determinism

- [ ] No time-dependent assertions (fixed timestamps, relative time checks)
- [ ] No random values used without a fixed seed
- [ ] No sleeps or polling used to synchronise async behaviour
- [ ] Tests produce the same result on every run

---

## Maintainability

- [ ] Common setup is extracted into shared helpers — not copy-pasted across tests
- [ ] Data-driven tests used for 3+ similar cases instead of duplicated test bodies
- [ ] Mocks only cover external dependencies — not the unit under test
- [ ] Mock setup is minimal and focused — over-mocking hides real behaviour
- [ ] No hardcoded values that would silently break if the code changes

---

## Performance

- [ ] Unit tests have no I/O and run fast
- [ ] Slow or I/O-bound tests are clearly separated or marked
- [ ] No unnecessary delays in test setup or teardown

---

## Anti-Patterns to Flag

| Anti-pattern | Severity |
|---|---|
| Test with no assertions | High |
| Test that mocks the thing under test | High |
| Shared mutable state between tests | High |
| Test name that does not describe the outcome | Medium |
| Multiple unrelated behaviours in one test | Medium |
| Copy-pasted test bodies instead of data-driven tests | Medium |
| Over-mocking (mocking real objects that could be used directly) | Medium |
| Time-dependent or random-dependent assertions | Medium |
| Tests that depend on execution order | High |
| `sleep` used for async synchronisation | Medium |
