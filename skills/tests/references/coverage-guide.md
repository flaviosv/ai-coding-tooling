# Code Coverage Guide

Coverage measures what percentage of code is executed during tests. It is a useful signal,
not a goal in itself.

---

## Coverage Types

**Line coverage** — tracks which lines were executed. The default in most tools.

**Branch coverage** — tracks which conditional branches were taken. More thorough; catches
untested `else` paths and early returns that line coverage misses.

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

---

## Coverage Best Practices

- Use coverage reports to find untested code paths, not to hit a percentage
- Track coverage trends over time — a sustained drop signals untested new code
- Do not write tests purely to raise the number
- Prioritise coverage on new code and recently changed code
- Exclude generated files, vendored code, and third-party dependencies from reports
