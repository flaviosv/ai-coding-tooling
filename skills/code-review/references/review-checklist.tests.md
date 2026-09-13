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
- [ ] Tests verify observable behaviour through the public API — not internal state or implementation details

## Coverage and Completeness

- [ ] Happy path is tested
- [ ] Error paths and failure scenarios are tested
- [ ] Edge cases are covered (null, empty, zero, maximum, invalid input)
- [ ] Boundary conditions tested where applicable
- [ ] Integration points tested where the change touches component interactions
- [ ] Error and exception assertions verify the message or code — not just the type
- [ ] Response/return value structure is verified — not just status codes or boolean success flags
- [ ] Access-controlled paths are tested for both the authorized success case and the unauthorized rejection case

## Independence and Isolation

- [ ] Tests do not share mutable state across test cases
- [ ] Each test can run independently and in any order
- [ ] External dependencies (network, filesystem, external services) are mocked in unit tests
- [ ] Any side effects (database writes, file creation) are cleaned up or isolated
- [ ] No test relies on another test having run first
- [ ] Global or shared configuration mutated during a test is restored in teardown — not left for subsequent tests

## Determinism

- [ ] No time-dependent assertions (fixed timestamps, relative time checks)
- [ ] No random values used without a fixed seed
- [ ] No sleeps or polling used to synchronise async behaviour
- [ ] Tests produce the same result on every run

## Maintainability

- [ ] Common setup is extracted into shared helpers — not copy-pasted across tests
- [ ] Data-driven tests used for 3+ similar cases instead of duplicated test bodies
- [ ] Data-driven test cases have descriptive names or IDs so failures identify the failing scenario — not just an index
- [ ] Mocks only cover external dependencies — not the unit under test
- [ ] Mock setup is minimal and focused — over-mocking hides real behaviour
- [ ] No hardcoded values that would silently break if the code changes
- [ ] Test helper functions that contain assertions are marked to report failures at the call site — not inside the helper

## Performance

- [ ] Unit tests have no I/O and run fast
- [ ] Slow or I/O-bound tests are clearly separated or marked
- [ ] No unnecessary delays in test setup or teardown

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
