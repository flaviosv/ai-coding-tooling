# Test Code Review Checklist

Generic baseline checklist for reviewing test code quality across any technology stack.
Technology-specific guides extend this file.

---

## Structure and Clarity

- [ ] At least one assertion; the name states the scenario and expected outcome; Arrange-Act-Assert is visible
- [ ] One behaviour per test, verified through the public API — not internal state or implementation details

## Coverage and Completeness

- [ ] Happy path, error paths, edge cases (null, empty, zero, maximum, invalid input), and boundaries covered; integration points tested where the change touches component interactions
- [ ] Error and exception assertions verify the message or code — not just the type
- [ ] Response/return value structure is verified — not just status codes or boolean success flags
- [ ] Access-controlled paths tested for both the authorized success and the unauthorized rejection

## Independence and Isolation

- [ ] No shared mutable state and no ordering dependence — each test runs alone, in any order
- [ ] External dependencies mocked in unit tests; side effects cleaned up or isolated; global configuration a test mutates is restored in teardown

## Determinism

- [ ] No time-dependent assertions, unseeded random values, or sleeps/polling to synchronise async behaviour

## Maintainability

- [ ] Common setup is extracted into shared helpers — not copy-pasted across tests
- [ ] Data-driven tests used for 3+ similar cases instead of duplicated test bodies
- [ ] Data-driven test cases have descriptive names or IDs so failures identify the failing scenario — not just an index
- [ ] Mocks only cover external dependencies — not the unit under test
- [ ] Mock setup is minimal and focused — over-mocking hides real behaviour
- [ ] No hardcoded values that would silently break if the code changes
- [ ] Test helper functions that contain assertions are marked to report failures at the call site — not inside the helper

## Performance

- [ ] Unit tests have no I/O; slow or I/O-bound tests are separated or marked; no unnecessary setup or teardown delays

## Test Doubles Quality

- [ ] Stubs (return values only) are distinguished from mocks (interaction assertions) — using a mock where a stub suffices misleads the reader about test intent
- [ ] Partial mocking of the system under test is not used — mock only external dependencies, instantiate the real unit
- [ ] Test doubles implement the same contract (interface/type) as the real dependency — not concrete classes
- [ ] Assertions on test doubles are only present when the interaction itself is the behaviour under test

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
| Asserting only on status code or exception type — ignoring message, body, or structure | Medium |
| Testing internal state or private fields instead of observable behaviour | Medium |
| Partial mock of the system under test (mocking methods on the unit being tested) | High |
| Data-driven test cases with no descriptive name or ID | Low |
| Global configuration or shared state mutated without restoration in teardown | High |
| Missing test for the unauthorized/unauthenticated path on access-controlled behaviour | High |
