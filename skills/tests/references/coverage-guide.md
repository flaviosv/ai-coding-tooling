# Code Coverage Guide

Coverage measures what percentage of code is executed during tests. A useful signal, not a goal in itself.

---

## Coverage Types

**Line coverage** — tracks which lines were executed. Default in most tools.

**Branch coverage** — tracks which conditional branches were taken. Catches untested `else` paths and early returns that line coverage misses.

**Mutation coverage** — runs tests against systematically mutated production code (flipped conditions, removed returns, changed operators). A surviving mutant means the test suite did not catch the change — code was executed but not meaningfully asserted on. High line coverage with low mutation score reveals tests that touch code without verifying it. Expensive to run; apply selectively to critical business logic.

Prefer branch coverage when the testing framework supports it easily.

## Coverage Goals

Adjust per project based on criticality and context.

| Component type | Suggested target |
|---|---|
| Core business logic | 80%+ |
| Data access / storage layer | 75%+ |
| API / interface layer | 65%+ |
| Utilities and helpers | 80%+ |
| Configuration and bootstrapping | opportunistic |

A poorly written test that touches every line is worth less than a well-designed test that verifies real behaviour.

## Test Pyramid and Coverage by Layer

Healthy coverage comes from a balanced test pyramid, not from maximising a single number.

- **Unit tests** — pure logic, all external dependencies mocked/stubbed. Fast, numerous. Drive coverage of business logic, validation, and domain rules.
- **Integration tests** — real dependencies (database, filesystem, external services). Fewer than unit tests. Drive coverage of data access, service boundaries, and middleware.
- **End-to-end / contract tests** — full stack or API-level assertions. Fewest. Drive coverage of API contracts and critical user flows.

Aim for high unit-test coverage on business logic; use integration tests for paths that only make sense with real dependencies. Do not achieve high percentages by writing integration tests for code that should be unit-tested.

Slow or live-environment tests (real APIs, containers) should be marked and excluded from the default CI run. Collect coverage from fast unit and integration suites; run expensive tests separately on a scheduled or pre-release basis.

## What to Test

- Business logic and domain rules
- Validation and input handling
- Error paths and failure modes
- Boundary conditions (zero, null, max, empty, overflow)
- Security-relevant code paths
- Code expensive to debug in production

## What NOT to Test

- Third-party libraries and frameworks — trust their own test suites
- Auto-generated or scaffolded code — unless custom logic was added
- Trivial getters and setters with no logic
- Configuration parsing — test the behaviour it enables, not the parsing
- Framework or runtime internals
- Test helpers, factories, and fixture builders — exclude from coverage reports

## Coverage Best Practices

- Use coverage reports to find untested code paths, not to hit a percentage
- Track coverage trends over time — a sustained drop signals untested new code
- Do not write tests purely to raise the number
- Prioritise coverage on new and recently changed code
- Exclude generated files, vendored code, and third-party dependencies from reports
- Exclude test infrastructure files (fixture factories, builder helpers, test utilities) from coverage measurement
- Configure CI to produce coverage reports in machine-readable format (XML/JSON) for trend tracking and PR diff coverage
- Consider enforcing minimum coverage threshold on CI for changed files — gates regressions without requiring arbitrarily high global percentage

## Coverage Anti-Patterns

**Executing without asserting** — test exercises a code path but asserts only on a loosely related outcome (e.g. non-null but not content). Line coverage counts the line as covered; logic could be completely wrong. Mutation testing surfaces this.

**Chasing the percentage** — writing tests solely to move a coverage number forces low-value tests onto code that does not need them while genuinely risky paths remain undertested.

**Integration tests compensating for missing unit tests** — using slow integration tests to cover logic that should be unit-tested. Inflates coverage numbers but makes the suite slow, fragile, and hard to run in isolation.

**Omitting exclusions** — including generated code, vendored dependencies, or test utility files in coverage totals distorts the metric artificially.
