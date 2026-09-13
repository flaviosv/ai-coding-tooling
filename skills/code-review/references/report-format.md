# Report Format

The consolidated review report, written at the end of the review stage for every entry except Batch Mode (which reports per PR). One report covers every active scope. On a PR, it is also the source of the comments `post` publishes; the checkpoint shows the user its header and at-a-glance table.

---

## Header (always first)

```
# <TASK-ID or branch> — Code Review
Scope: code (<N> files) · tests (<M> test files)[ · <X> excluded as generated/lockfiles/snapshots]
Branch: <branch>
Commits: <hash — subject>, <hash — subject>, ...   ← multi-commit only
Diff: <N files changed, +X insertions, -Y deletions>
Run: <date>
Mode: local | GitHub PR #N | multi-commit
Sonar: <line from sonar.md, or "skipped — no project key found">
[Code tier: <tier> | Type: <content_type>]         ← only when type ≠ general OR tier ∈ {Large, Complex}
[Tests tier: <tier>]                               ← only when tier ∈ {Large, Complex}
[⚠️ Complex review (<scope>: N files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.]  ← Complex tier only
Duplicates collapsed: <N> clusters                  ← always, 0 included — a missing count is indistinguishable from never having looked
```

Show only the active scopes in `Scope`.

## At-a-Glance Table (always second)

One row per **active** dimension. Inactive dimensions have no row — their absence is intentional, never shown as skipped. The exceptions are the explicit skip states the dimension files define (Coverage Gaps with no implementation changes).

| Scope | Dimension | Status | Findings | Critical | High | Summary |
|---|---|---|---|---|---|---|
| Code | Architecture | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Code | Code Quality & Docs | … | N | N | N | 1-line |
| Code | Performance | … | N | N | N | 1-line |
| Code | Regression & Hallucination | … | N | N | N | 1-line |
| Code | Requirements | ✅ / ⚠️ (only with a spec/JIRA) | — | — | — | coverage summary |
| Code | Security | … | N | N | N | 1-line |
| Tests | Clarity | … | N | N | N | 1-line |
| Tests | Coverage | … | N | N | N | 1-line |
| Tests | Coverage Gaps | ✅ / ⚠️ skipped — no implementation changes / ⚠️ not executed | N | N | N | 1-line |
| Tests | Isolation | … | N | N | N | 1-line |
| Tests | Maintainability | … | N | N | N | 1-line |
| Tests | Performance | … | N | N | N | 1-line |

## Findings

**Flat format** — few findings, one dimension:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|---|---|---|---|---|---|

**Zoned format** — many findings or several dimensions (the default whenever agents were dispatched). One section per zone, `## Zone <Letter> — <Dimension>`:

| # | Severity | Priority | Title | Type | File:Line | Status | Explanation |
|---|---|---|---|---|---|---|---|

| Scope | Zone | Letter |
|---|---|---|
| Code | Architecture | A |
| Code | Code Quality & Docs | Q |
| Code | Performance | P |
| Code | Regression & Hallucination | H |
| Code | Requirements | R |
| Code | Security | S |
| Tests | Clarity | C |
| Tests | Coverage | V |
| Tests | Coverage Gaps | G |
| Tests | Isolation | I |
| Tests | Maintainability | M |
| Tests | Performance | E |

Tests Performance is `E`, not `P` — `P` is the code scope's, and IDs must stay unique within one report.

Finding IDs are `<ZoneLetter><N>` (`A1`, `Q3`, `V2`, `E1`). A finding folded in from a collapsed cluster keeps only the surviving instance's ID. All findings start as `Open`.

```
✓ Fixed | ✓ Resolved (no change needed) | Tracked (moved to tech-debts) | Ignored (user-confirmed) | Pending (awaits decision) | Open (not triaged)
```

At the very bottom: an open/untriaged summary table of every finding with no disposition.

- **Severity:** Critical, High, Medium, Low.
- **Priority and Type:** per scope — see [Code Dimensions](code-dimensions.md#priority-and-type) and [Test Dimensions](test-dimensions.md#priority-and-type).
- Give specific line numbers and concrete solutions; keep explanations concise.

With `human_review: true`, a local report shown at the checkpoint ends with one line: "Drop any finding by ID (e.g. `drop Q2, H1`), then say continue to fix what remains."

## Markdown File Output

When asked to save the review, always use the zoned format and write it into the current feature's folder, alongside the artifacts `tlc-spec-driven` owns:

1. Active TLC feature (match the changed files / TASK-ID to a directory under `.specs/features/`) → `.specs/features/<TASK-ID>-<slug>/code-review.md`.
2. No feature folder → ask where to save it (default: the project root).

Subsequent passes use `code-review_phase2.md`, then `_phase3`, and so on.

## Iterative Review

After fixes:

1. Update the table — mark fixed items with ✓.
2. Re-review only the changed code and tests.
3. Continue until every P0/P1 is addressed.
