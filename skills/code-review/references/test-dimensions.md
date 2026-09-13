# Test Dimensions

The tests scope's dimension set: which agents review test files, what the implementation-side `gap-detector` does, what each agent self-loads, and how a failure is marked. Loaded whenever the tests scope is active.

---

## Dimensions

| Dimension | Covers |
|---|---|
| Clarity | Test naming, AAA structure, focus, readability as documentation |
| Coverage | Happy path, error paths, edge cases, integration points, access control |
| Coverage Gaps | Implementation paths and behaviors with no test (`gap-detector`, from `impl_diff`) |
| Isolation | Shared state, ordering, mocks, determinism, external dependencies |
| Maintainability | Helpers, data-driven patterns, mock minimalism, update cost |
| Performance | I/O in unit tests, sleep/polling, suite speed, test separation |

Coverage Gaps is active only when `impl_diff` is non-empty; otherwise its row shows `⚠️ skipped — no implementation changes`. The tests scope still runs when no test file changed but `impl_diff` is non-empty — a change with no tests is exactly what `gap-detector` exists to catch.

## Agents

**Small tier** — the orchestrator reviews all five test dimensions inline, plus Coverage Gaps when `impl_diff` is non-empty. With no test files at all, only Coverage Gaps runs (see Step 4's scope activation).

**Medium tier** — one agent covers every dimension, self-loading `review-checklist.tests.md`, `<stack>.tests.md`, and the full 7-doc set. It receives the test diff **and** `impl_diff` when non-empty (6 dimensions, gap analysis included); with an empty `impl_diff` it receives only the test diff (5 dimensions).

**Large / Complex tier** — merged dispatch, 3 agents plus `gap-detector` when active:

- `isolation` + `performance` → one `execution-reviewer`.
- `clarity` + `maintainability` → one `craft-reviewer`.
- `coverage-reviewer` and `gap-detector` are never merged.

Merged agents return findings tagged by original dimension; the report keeps separate rows.

| Agent | Dimension(s) | Checklists (if present) | Codebase docs | Degrades without |
|---|---|---|---|---|
| `coverage-reviewer` | Coverage | `review-checklist.tests.md`, `<stack>.tests.md` | Full 7-doc set | — |
| `craft-reviewer` | Clarity + Maintainability | `review-checklist.tests.md`, `<stack>.tests.md` | Full 7-doc set | `conventions` |
| `execution-reviewer` | Isolation + Performance | `review-checklist.tests.md`, `<stack>.tests.md` | Full 7-doc set | `testing` |
| `gap-detector` | Coverage Gaps — receives `impl_diff` only | None | `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` | — |

**Full 7-doc set** = `STACK`, `ARCHITECTURE`, `CONVENTIONS`, `TESTING`, `CONCERNS`, `INTEGRATIONS`, `STRUCTURE` — present ones only.

**`TESTING.md` absent** → the isolation and performance dimensions run degraded, inferring the test framework from `STACK.md` or test file patterns. At Medium tier that affects the single agent's isolation/performance findings; at Large/Complex, `execution-reviewer` as a whole.

**No stack-specific checklist** (`<stack>.tests.md` absent) → apply `review-checklist.tests.md` in full, note in the report that stack-specific guidance was unavailable, and flag the universal anti-patterns: no assertions, shared state, flakiness, over-mocking.

**Sonar:** `coverage-reviewer` receives test-quality issues; `gap-detector` receives coverage data — see [Sonar](sonar.md).

## gap-detector

Cross-references `impl_diff` against the changed tests to find important code paths with no corresponding test. Flag:

- **Public/exported functions or methods** added or modified with no new or updated test.
- **Business logic branches** (`if`/`else`, `switch`, `try/catch`, guard clauses) with no test exercising them.
- **Error conditions** — exceptions thrown, error codes returned, validation failures — with no test verifying the error path.
- **Integration points** — new external calls, DB queries, event emissions — with no test covering the interaction.
- **Access control / permission checks** added with no test verifying enforcement.
- **Edge cases implied by the implementation** (null/empty/zero/boundary values handled explicitly) with no corresponding test case.

It receives `impl_diff` only and never judges the quality of existing tests — only what is absent.

## Failure Marking

- `execution-reviewer` not executed → both the Isolation and Performance rows show `⚠️ not executed — <reason>`; degraded → both show `⚠️ degraded — <missing item>`.
- `craft-reviewer` not executed or degraded → both the Clarity and Maintainability rows, the same way.

## Priority and Type

- **Priority:** P0 must fix — broken or missing tests on critical paths · P1 should fix — quality, missing coverage · P2 nice to have — style, refactoring opportunities.
- **Type:** Coverage, Isolation, Maintainability, Pattern, Performance, Quality.
- Suggest concrete improvements ("add a test case for null input") and point at similar patterns in existing tests where helpful.
