---
name: tech-debt-report
description: >
  Create, update, and resolve technical debt reports. Generates individual debt
  documentation in docs/tech-debts/ and maintains an anti-pattern index in
  docs/TECH_DEBTS.md that agents read at session start to avoid replicating
  known bad patterns. Use when the user says "tech debt report", "report tech debt",
  "document tech debt", "add tech debt", "update tech debt", "resolve tech debt",
  or "mark tech debt as resolved". Do NOT use for fixing tech debt, code reviews,
  or refactoring.
metadata:
  version: "1.1.0"
  triggers:
    - "tech debt report"
    - "report tech debt"
    - "document tech debt"
    - "add tech debt"
    - "update tech debt"
    - "resolve tech debt"
    - "mark tech debt as resolved"
---

# Tech Debt Report

Document technical debts and maintain an anti-pattern index so agents avoid replicating known bad patterns in new code.

## Operations

### Create

Trigger: User describes a new tech debt to document.

1. Investigate the code the user references — read the files, understand the problem in context
2. Create `docs/tech-debts/<concise_name>.md` using the Report Template below
3. Add an entry to `docs/TECH_DEBTS.md` using the Index Format below
4. If `docs/TECH_DEBTS.md` does not exist, create it with the Index Header
5. On first run in a project, check if `docs/TECH_DEBTS.md` is in the project's `CLAUDE.md` session-start section — if not, add it

### Update

Trigger: User wants to modify an existing debt report (add files, change risk, update description).

1. Read the existing report in `docs/tech-debts/`
2. Apply the requested changes to the report
3. Sync the corresponding entry in `docs/TECH_DEBTS.md` to reflect the update

### Resolve

Trigger: User marks a debt as resolved.

1. Update the report: set Status to `Resolved`, add a `## Resolved` section with today's date
2. Remove the entry from `docs/TECH_DEBTS.md` — the index only tracks active debts
3. Keep the report file in `docs/tech-debts/` for historical reference

## Report Template

Individual reports go in `docs/tech-debts/<concise_name>.md`. Use snake_case for filenames — concise and descriptive (e.g., `db_connection_overlapping.md`, `circular_auth_imports.md`).

```markdown
# [Title]

## Description

[Clear explanation of the problem — what the code does wrong and why it matters. Be specific, not generic.]

## Affected Code

| File | Lines | Description |
|------|-------|-------------|
| `path/to/file.ts` | 45-67 | [What this code does wrong] |

## Risk

[Concrete impact on the project. Describe what actually happens: "Memory leaks under concurrent load", "Data inconsistency between services", "Increases onboarding time for new developers". Never use generic labels like "High" or "Low".]

## Status

Open

## Reported

[YYYY-MM-DD]
```

## Index Format (`docs/TECH_DEBTS.md`)

This file is read by agents at session start. It must be concise, scannable, and prescriptive. Only active (unresolved) debts appear here.

Header for new files:

```markdown
# Tech Debts

Known technical debts in this project. **Do NOT replicate these patterns in new code.** When writing new code that touches the affected areas listed below, actively avoid the described anti-patterns.

| Debt | Problem | Affected Areas | Risk | Report |
|------|---------|----------------|------|--------|
```

Each row follows this format:

```
| [Title] | [One-line problem statement] | `file1.ts`, `file2.ts` | [One-line concrete risk] | [Report](../docs/tech-debts/<name>.md) |
```

When resolving a debt, remove its row. When updating, sync the row with the report changes. The table should only ever contain active debts.

## Guidelines

- **Never fix the debt.** This skill documents problems. Fixing is out of scope — suggest the user plans a separate refactoring task.
- **Be specific in the Risk field.** "High risk" is useless. "Causes OOM under 100 concurrent connections" is actionable and helps agents understand why the pattern is dangerous.
- **Keep filenames concise.** `db_connection_overlapping.md` not `the_database_connection_pooling_issue_we_found_in_march.md`.
- **The index is for agents.** Write `docs/TECH_DEBTS.md` entries as warnings to a developer about to write similar code — be direct about what pattern to avoid.
- **One debt per report.** If a problem spans multiple concerns, create separate reports for each.
- **Affected Code must have line numbers.** Vague file references without line numbers are not useful. Read the code and pin down the exact locations.

## Examples

### Example 1: Creating a new tech debt report

User says: "report tech debt — we have circular imports in the auth module"

1. Read the auth module files to locate and understand the circular dependency
2. Create `docs/tech-debts/circular_auth_imports.md`:
   - Title: Circular Auth Imports
   - Description: explains the circular dependency chain
   - Affected Code: lists each file and the import lines causing the cycle
   - Risk: "Build tools cannot tree-shake the auth module. Test isolation is impossible — importing any auth utility pulls the entire module graph."
   - Status: Open
   - Reported: today's date
3. Create or update `docs/TECH_DEBTS.md` with a new row
4. If first debt in the project, add `docs/TECH_DEBTS.md` to `CLAUDE.md` session-start list

### Example 2: Updating an existing debt

User says: "update tech debt circular_auth_imports — also affects src/middleware/session.ts lines 20-35"

1. Read `docs/tech-debts/circular_auth_imports.md`
2. Add `src/middleware/session.ts` lines 20-35 to the Affected Code table with a description
3. Update the corresponding row in `docs/TECH_DEBTS.md` to include the new file in Affected Areas

### Example 3: Resolving a debt

User says: "resolve tech debt circular_auth_imports"

1. Update `docs/tech-debts/circular_auth_imports.md`:
   - Set Status to `Resolved`
   - Add `## Resolved` section with today's date
2. Remove the `Circular Auth Imports` row from `docs/TECH_DEBTS.md`
3. The report file stays in `docs/tech-debts/` for history