# Testing Patterns & Design Principles

General testing principles that apply regardless of language or framework. Always load this file when writing tests.

---

## FIRST Principles

### Fast
Unit tests run in milliseconds. If a test is slow, you've crossed a boundary — mock it or move it to integration tests.

### Independent
No test depends on another. No shared mutable state. Each test sets up and tears down its own world. If tests must run in a specific order, they are broken.

### Repeatable
Same result every run, on every machine. No time-dependent assertions, no unfixed random seeds, no real network calls in unit tests. If a test passes locally but fails in CI, it is flaky and must be fixed immediately.

### Self-Validating
Pass or fail — no manual inspection. If you need to read logs or eyeball output to know whether it passed, add an assertion.

### Timely
Write tests when the code is fresh. For bug fixes, write the failing test first — before touching the implementation.

## Test Structure

- **Arrange-Act-Assert (AAA)** — one setup block, one action, one verification block. Multiple Act sections means split into multiple tests.
- **Single concept per test** — if the test name needs "and", split it.
- **Test behavior, not implementation** — assert WHAT the code does, not HOW. Refactoring should not break tests.
- **Name describes scenario + expected outcome** — `test_expired_token_returns_401` tells you everything. `test_token_error` tells you nothing.
- **Minimal setup** — arrange only what matters. Irrelevant fields use sensible defaults via factories or builders.

## Test Doubles

Over-mocking is the most common testing anti-pattern.

- **Dummy** — fills a required parameter, never called. Use when a dependency is irrelevant to the behavior being tested.
- **Stub** — returns canned data. No verification of how it was called.
- **Spy** — records calls for later verification. Use to verify an interaction happened (e.g., email sent).
- **Mock** — pre-programmed expectations that fail if not met. Use sparingly — prefer stubs + state assertions. Mocks couple tests to implementation.
- **Fake** — simplified working implementation (in-memory DB, in-memory queue). Use for integration tests where real dependencies are too heavy.

**Rules:**
- Don't mock what you don't own — wrap third-party APIs behind your own interface, mock the wrapper.
- Mock at the boundary, not inside the unit — mocking internal methods means the design needs refactoring.
- Prefer state verification over interaction verification — assert end state ("user saved with status=active"), not method calls ("save() called once with these args").

## Test Data

- Use factories or builders for complex objects — never construct test data inline with 15 parameters.
- Use minimal data — only set fields relevant to the test. Every explicit field should matter for the assertion.
- Name test data by intent — `expired_token`, `admin_user`, `empty_cart` — not `token_abc123`, `user_42`.
- Keep test data close to the test — inline if only one test uses it, fixture/factory if shared.
- Never reuse production data — tests use controlled, deterministic data.

## Anti-Patterns

- **Assertion-free tests** — executing code without asserting anything only proves the code doesn't throw.
- **Ice cream cone** — more E2E tests than unit tests. Invert the pyramid: unit-heavy, fewer integrations, minimal E2E.
- **Shared mutable state** — setUp populates shared variables, tests mutate them and assume execution order.
- **Testing private methods** — test through the public API. If unreachable through public methods, the class has too many responsibilities.
- **Copy-paste test bodies** — if three tests differ by one parameter, parametrize. Duplicated test code rots like duplicated production code.
- **Over-mocking** — mocking more than one layer deep means the test is testing the mocks. Complex mock choreography signals design needs simplification.
- **Testing framework internals** — don't test that the ORM saves to the DB. Test that YOUR code calls the ORM correctly and handles its responses.
- **Sleep-based synchronization** — never use `sleep()` for async results. Use proper waits, callbacks, or fake clocks.

## Application Rules

### When writing new tests

1. Can you describe the test in one sentence without "and"?
2. Would the test still pass if you refactored the implementation without changing behavior?
3. Does the test name explain the failure without reading the body?
4. Are you mocking only at external boundaries, not internal details?
5. Could this test fail for exactly one reason?
6. Is every field in the setup relevant to the assertion?
7. Does the test use AAA structure with a clear single action?

### When reviewing existing tests

1. Remove tests that verify implementation details (method call counts, internal state, private method calls).
2. Merge tests that test the same concept with only slightly different setup — parametrize instead.
3. Extract repeated setup into shared helpers, fixtures, or factories.
4. Replace manual object construction with factories or builders.
5. Replace `sleep()` calls with proper waits, fakes, or deterministic patterns.
6. Flag assertion-free tests for immediate fix or deletion.
7. Flag tests with more than 3 mocks — the design likely needs simplification.
