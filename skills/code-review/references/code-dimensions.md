# Code Dimensions

The code scope's dimension set: which dimensions a change activates, how they merge into agents, what each agent self-loads, and how a failure is marked. Loaded whenever the code scope is active.

---

## Content Type → Active Dimensions

Evaluated on the implementation file list (after EXCLUDE, test files already routed to the tests scope), by file name only — no content is read. "100% match" means every file in that list matches. A single source file makes the type `general`.

| Content type | Detection | Active dimensions |
|---|---|---|
| `config-infra-only` | 100% match: `*.yml`, `*.yaml`, `*.json`, `*.toml`, `Dockerfile*`, `*.tf`, `*.tfvars`, `.github/`, `*.env`, `*.ini`, `*.cfg`, `.eslintrc*`, `.prettier*` | `code-quality`, `regression`, `security` + `requirements` (conditional) |
| `docs-only` | 100% match: `*.md`, `*.txt`, `*.rst`, `*.mdx`, `docs/`, `README*`, `CHANGELOG*`, `*.adoc` | `code-quality` + `requirements` (conditional) |
| `frontend-assets-only` | 100% match: `*.css`, `*.scss`, `*.less`, `*.svg`, `*.png`, `*.jpg`, `*.gif`, `*.ico`, `*.woff*`, `*.ttf` | `code-quality`, `security` + `requirements` (conditional) |
| `general` (default) | Any source file (`*.ts`, `*.js`, `*.py`, `*.go`, `*.rb`, `*.java`, `*.php`, `*.cs`, `*.rs`, `*.kt`, `*.swift`, `*.c`, `*.cpp`, `*.h`, etc.) | `architecture`, `code-quality`, `performance`, `regression`, `security` + `requirements` (conditional) |
| `mixed` | Several non-source types, no source file | Falls through to `general` |

- Source plus docs → `general`; the source file triggers full scope.
- Empty changed list (rename-only) → `general`, Small (0 files / 0 lines), inline.
- `requirements` is active only when the availability map has `requirements` (a spec or JIRA task was found).

## Agents

**Medium tier** — one agent covers every active dimension; its `## Before You Begin` lists the deduplicated union of those dimensions' checklists plus the codebase docs.

**Large / Complex tier** — one agent per active dimension, after two merge rules:

- **Merge rule 1 — design quality.** When `architecture` and `code-quality` are both active (only content type `general`), they dispatch as one `design-quality-reviewer`. Otherwise `code-quality-reviewer` dispatches alone.
- **Merge rule 2 — intent & regression.** When `regression` and `requirements` are both active, they dispatch as one `intent-regression-reviewer`. They ask one question from two directions — does the change still do what was intended, and does it break what already worked; [STATE.md AD-002](../STATE.md) has the measurement behind the merge. Otherwise each dispatches alone.

A merged agent loads the union of both checklists and returns findings tagged by original dimension, so the report keeps separate rows and zones. Together the rules take the all-active `general` case from 6 agents to 4.

| Agent | Dimension(s) | Checklists (if present) | Degrades without |
|---|---|---|---|
| `code-quality-reviewer` | Naming, complexity, SOLID, DRY, KISS, clean code; inline docs, API docs, obsolete or misleading comments | `review-checklist.code.md`, `clean-code-checklist.code.md`, `best-practices.code.md`, `observability.code.md`, `<stack>.code.md` | `conventions` |
| `design-quality-reviewer` | Merged: layer violations, coupling, pattern misuse (**architecture**) + everything `code-quality-reviewer` covers (**code-quality**) | same as `code-quality-reviewer` | `architecture` and/or `conventions` — each tag degrades independently |
| `intent-regression-reviewer` | Merged: everything `regression-reviewer` covers (**regression**) + does the change satisfy the stated spec/task (**requirements**) | same as `code-quality-reviewer`, plus the requirements/spec file | — |
| `performance-reviewer` | N+1, allocations, blocking calls, missing indexes | `performance-checklist.code.md`, `<stack>-performance.code.md` | — |
| `regression-reviewer` | See [regression-reviewer](#regression-reviewer) | same as `code-quality-reviewer` | — |
| `requirements-tracer` | Does the change satisfy the stated spec/task (standalone only when `regression` isn't active) | None — the requirements/spec file only | Skipped entirely without `requirements`; its row is omitted |
| `security-reviewer` | Auth, injection, secrets, data exposure | None — the `security-best-practices` skill plus built-in security knowledge | — |

**Codebase docs:** every code agent except a standalone `requirements-tracer` self-loads `STACK`, `ARCHITECTURE`, `CONVENTIONS`, `STRUCTURE`, `INTEGRATIONS`, `CONCERNS` (present ones only). `TESTING.md` belongs to the tests scope. The merged `intent-regression-reviewer` loads them for its regression half.

**Sonar:** `security-reviewer` receives the security issues; whichever agent covers `code-quality` (`design-quality-reviewer` or `code-quality-reviewer`) receives the quality issues — see [Sonar](sonar.md).

## regression-reviewer

Changes unrelated to the stated purpose, or signs of AI-generated artifacts:

- **Phantom imports** — references to symbols that don't exist in the codebase (🚨 Critical).
- **Unrelated deletions** — code removed with no connection to the stated change (🚨 Critical).
- **Duplicate logic** — functionality already present in the module, re-implemented.
- **Weakened assertions** — error handling, validation rules, or test assertions made less strict.
- **Dead code** — functions or branches introduced but never called.
- **`TODO`/`FIXME` in production** — leftover markers not resolved before merge.
- **Type assertions hiding errors** — `as any` or forced casts masking real type errors.

## Failure Marking

- `design-quality-reviewer` not executed → both the Architecture and Code Quality & Docs rows show `⚠️ not executed — <reason>`. Degraded → both rows show `⚠️ degraded — <missing item>`; when only one tag's doc is missing (e.g. `architecture` absent, `conventions` present), say in the summary that only that tag's findings are degraded.
- `intent-regression-reviewer` not executed → both the Regression & Hallucination and Requirements rows are marked.
- `requirements-tracer` skipped → its row is omitted entirely, never shown as skipped.

## Priority and Type

- **Priority:** P0 must fix before merging · P1 should fix soon · P2 nice to have.
- **Type:** Architecture, Code Quality, Documentation, Performance, Security, Tech Debt.
