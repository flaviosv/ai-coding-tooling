# Code Coverage Guide

Coverage measures what percentage of code is executed during tests. It is a useful signal,
not a goal in itself.

---

## Coverage Types

**Line coverage** — tracks which lines were executed. The default in most tools.

**Branch coverage** — tracks which conditional branches were taken. More thorough; catches
untested `else` paths and early returns that line coverage misses.

**Mutation coverage** — runs the test suite against systematically mutated versions of the
production code (flipped conditions, removed returns, changed operators). A mutant that
survives means the test suite did not catch the change — i.e., the code was executed but
not meaningfully asserted on. High line coverage with low mutation score reveals tests that
touch code without verifying it. Mutation testing is expensive to run; apply it selectively
to the most critical business logic paths.

Prefer branch coverage when the testing framework supports it easily.

---

## Coverage Goals

These are generic baselines. Adjust per project based on criticality and context.

| Component type | Suggested target |
|---|---|
| Core business logic | 80%+ |
| Data access / storage layer | 75%+ |
| API / interface layer | 65%+ |
| Utilities and helpers | 80%+ |
| Configuration and bootstrapping | opportunistic |

Coverage is a metric, not a goal. A poorly written test that touches every line is worth less
than a well-designed test that verifies real behaviour.

---

## Test Pyramid and Coverage by Layer

Healthy coverage comes from a balanced test pyramid, not from maximising a single number across
all test types. A typical structure:

- **Unit tests** — pure logic, all external dependencies mocked or stubbed. Fast, numerous. These
  drive coverage of business logic, validation, and domain rules.
- **Integration tests** — real dependencies (database, filesystem, external services where safe).
  Fewer than unit tests. These drive coverage of data access, service boundaries, and middleware.
- **End-to-end / contract tests** — full stack or API-level assertions. Fewest in number.
  These drive coverage of API contracts and critical user flows.

Coverage targets should reflect this layering: aim for high unit-test coverage on business logic,
and use integration tests to cover paths that only make sense with real dependencies. Do not try
to achieve high overall percentages by writing integration tests for code that should be unit-tested.

Slow, external, or live-environment tests (e.g. tests that call real APIs or spin up containers)
should be marked and excluded from the default CI run. Collect coverage from the fast unit and
integration suites; run the expensive tests separately on a scheduled or pre-release basis.

---

## What to Test

Focus testing effort on:
- Business logic and domain rules
- Validation and input handling
- Error paths and failure modes
- Boundary conditions (zero, null, max, empty, overflow)
- Security-relevant code paths
- Code that is expensive to debug in production

---

## What NOT to Test

Do not spend time testing:
- Third-party libraries and frameworks — trust their own test suites
- Auto-generated or scaffolded code — unless custom logic was added to it
- Trivial getters and setters with no logic
- Configuration parsing — test the behaviour it enables, not the parsing itself
- Framework or runtime internals
- Test helpers, factories, and fixture builders — exclude these from coverage reports

---

## Coverage Best Practices

- Use coverage reports to find untested code paths, not to hit a percentage
- Track coverage trends over time — a sustained drop signals untested new code
- Do not write tests purely to raise the number
- Prioritise coverage on new code and recently changed code
- Exclude generated files, vendored code, and third-party dependencies from reports
- Exclude test infrastructure files (fixture factories, builder helpers, test utilities) from
  coverage measurement — they are not production code
- Configure CI to produce coverage reports in a machine-readable format (e.g. XML or JSON) so
  that trend tracking and PR diff coverage can be automated
- Consider enforcing a minimum coverage threshold on CI for changed files — this gates regressions
  without requiring an arbitrarily high global percentage

---

## Coverage Anti-Patterns

**Executing without asserting** — the most common failure mode. A test exercises a code path
but asserts only on a loosely related outcome (e.g. asserts the response is non-null but not
its content). Line coverage counts the line as covered; the logic could be completely wrong.
Mutation testing surfaces this pattern.

**Chasing the percentage** — writing tests solely to move a coverage number forces low-value
tests onto code that does not need them (trivial getters, configuration wiring) while the
genuinely risky paths remain undertested.

**Integration tests compensating for missing unit tests** — using slow integration tests to
cover logic that could and should be tested in fast unit tests. This inflates coverage numbers
but makes the suite slow, fragile, and hard to run in isolation.

**Omitting exclusions** — including generated code, vendored dependencies, or test utility files
in coverage totals distorts the metric and may either inflate or deflate it artificially.
