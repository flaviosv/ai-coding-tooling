---
name: tech-debt-report
description: >
  Create, update, plan, and resolve technical debt reports as a permanent numbered ledger. Reporting a debt adds a TD-XX row to docs/TECH_DEBTS.md (a documentation ledger of known debts — it is NOT auto-loaded into context at session start); the per-debt solution plan is written to docs/tech-debts/TD-XX.md only when you plan the fix. Rows are never deleted — only Status and Solved change. Use when the user says "tech debt report", "report tech debt", "document tech debt", "add tech debt", "update tech debt", "plan tech debt", "resolve tech debt", or "mark tech debt as resolved". Do NOT use for fixing tech debt, code reviews, or refactoring.
metadata:
  version: "2.0.0"
  triggers:
    - "tech debt report"
    - "report tech debt"
    - "document tech debt"
    - "add tech debt"
    - "update tech debt"
    - "plan tech debt"
    - "resolve tech debt"
    - "mark tech debt as resolved"
---

# Tech Debt Report

Maintain a permanent, numbered technical-debt ledger that documents known bad patterns so they can be tracked and resolved over time.

`docs/TECH_DEBTS.md` is **reference documentation, not auto-loaded context.** It is never wired into any session-start list and other skills do not read it ambiently — deliberately, so the ledger can grow without inflating the context window. It is consulted only on demand: when a human reads it, or when this skill (or `code-review`, if it chooses) opens it explicitly.

Two files back this skill:

- **`docs/TECH_DEBTS.md`** — the index/ledger. One `TD-XX` row per debt. Rows are **never deleted**; only `Status` and `Solved` change.
- **`docs/tech-debts/TD-XX.md`** — the per-debt solution plan. Created **only when you plan the fix**, not when the debt is first reported.

### Scope: project-wide vs task-scoped

The project-wide ledger at `docs/TECH_DEBTS.md` is the default. But a task or customer may require the ledger to live **scoped to a specific task folder** instead — e.g. `docs/PS-1029/TECH_DEBTS.md` with detail files in `docs/PS-1029/tech-debts/TD-XX.md`. When that's requested, **follow it** — there is a deliberate reason (the debt belongs to one ticket's scope, not the whole project). The format, numbering, and relative `tech-debts/TD-XX.md` links are identical; only the base folder moves. If the user names a task folder, place both files there; otherwise default to the project root `docs/`.

## Operations

### Report

Trigger: User describes a new tech debt to document.

1. Investigate the code the user references — read the files, understand the problem in context. Confirm which ledger applies — the project-wide `docs/TECH_DEBTS.md` or a task-scoped one (see Scope above); all paths below are relative to that base.
2. Determine the next number: scan the ledger for the highest existing `TD-NN` and increment. Numbers are zero-padded to two digits (`TD-01`, `TD-02`, …). The first debt is `TD-01`.
3. If `docs/TECH_DEBTS.md` does not exist, create it with the Index Header below.
4. Append **one row only** using the Index Row format: `Status` = `Opened`, `Reported` = today, `Solved` = `—`, and the `TD #` cell linking to `tech-debts/TD-NN.md`.
5. **Do NOT create the detail file yet.** Tell the user the solution plan will be written to `docs/tech-debts/TD-NN.md` when they plan the fix.
6. Do **not** wire `docs/TECH_DEBTS.md` into any `CLAUDE.md`/`AGENTS.md` session-start list — it is on-demand documentation, intentionally kept out of auto-loaded context.

### Plan

Trigger: User is building a plan to fix an existing debt (e.g. "plan tech debt TD-03").

1. Read the debt's row in `docs/TECH_DEBTS.md`.
2. Create `docs/tech-debts/TD-NN.md` using the Detail Template below — flesh out Description, Affected Code (with line numbers), Risk, and the Action plan.
3. If the work is being tracked elsewhere (a ticket, another plan file), set the index `Status` to `Tracked in <place>`; otherwise leave it `Opened`.
4. Keep the index row and the detail file in sync.

### Update

Trigger: User wants to modify an existing debt (add files, change risk, refine description).

1. Read the index row, and the detail file if it exists.
2. Apply the requested changes.
3. Sync the other side so the index row and the detail file never diverge.

### Resolve

Trigger: User marks a debt as resolved, ignored, or moved elsewhere.

1. **Resolved:** in `docs/TECH_DEBTS.md` set `Status` = `Resolved` and `Solved` = today. **Keep the row** — this is a permanent ledger. If the detail file exists, set its `Status` to `Resolved`, fill `Solved`, and optionally add a one-line resolution note.
2. **Won't fix:** set `Status` = `Ignored` and state the reason in the row description or detail file.
3. **Moved out:** set `Status` = `Tracked in <place>` (e.g. `Tracked in JIRA GB-2099`).

## Index Format (`docs/TECH_DEBTS.md`)

Reference documentation — keep it concise and scannable. It is a permanent ledger: every debt ever reported stays here with its current status. Not auto-loaded into context; read on demand.

Header for new files:

```markdown
# Tech Debts

Known technical debts in this project — a documentation ledger. **Do NOT replicate these patterns in new code.** When you consult this file before working on an Affected Area below, actively avoid the described anti-pattern. This is a permanent ledger — rows are never deleted; only `Status` and `Solved` change.

Status values: `Opened` · `Resolved` · `Ignored` · `Tracked in <place>`

| TD # | Name | Description | Affected Areas | Status | Reported | Solved |
|------|------|-------------|----------------|--------|----------|--------|
```

Each row follows this format:

```
| [TD-NN](tech-debts/TD-NN.md) | [Short name] | [One-line anti-pattern warning] | `file1.ts`, `file2.ts` | Opened | YYYY-MM-DD | — |
```

Notes:

- The `TD #` cell links to `tech-debts/TD-NN.md`. That file may not exist until the fix is planned — the link is dead until then, which is expected.
- `Affected Areas` lists the files where the pattern must not be replicated. Fill it in at report time so the record is useful even before a detail file exists.
- `Reported` is the date the row was added. `Solved` stays `—` until the debt is resolved.

## Detail Template (`docs/tech-debts/TD-NN.md`)

Created at plan time, not report time. The filename matches the index label exactly (`TD-01.md`).

```markdown
# TD-NN — [Title]

**Status:** Opened
**Reported:** YYYY-MM-DD
**Solved:** —

## Description

[What the code does wrong and why it matters. Be specific, not generic.]

## Affected Code

| File | Lines | Description |
|------|-------|-------------|
| `path/to/file.ts` | 45-67 | [What this code does wrong] |

## Risk

[Concrete impact on the project: "Memory leaks under concurrent load", "Data inconsistency between services". Never use bare labels like "High" or "Low".]

## Action

[The plan/steps to resolve this debt.]
```

On resolve, set `Status: Resolved` and fill `Solved:`, and update the matching index row.

## Guidelines

- **Never fix the debt.** This skill documents and plans. Fixing is out of scope — suggest the user runs a separate refactoring task.
- **Report is index-only.** A new debt adds exactly one row to `docs/TECH_DEBTS.md`. The detail file is born later, in the Plan operation.
- **Never delete a row.** Resolved and ignored debts stay in the ledger with their final status — that is the historical record.
- **Be specific in Risk.** "High risk" is useless. "Causes OOM under 100 concurrent connections" tells agents why the pattern is dangerous.
- **The index Description is a warning.** Write each entry as a direct warning to a developer about to write similar code.
- **Affected Code must have line numbers** in the detail file. Read the code and pin down exact locations.
- **One debt per TD.** If a problem spans multiple concerns, report separate TDs.

## Examples

### Example 1: Reporting a new debt (index-only)

User says: "report tech debt — we have circular imports in the auth module"

1. Read the auth module files to locate and understand the circular dependency.
2. Scan `docs/TECH_DEBTS.md` for the highest `TD-NN` — say the next is `TD-07`.
3. Append one row: `TD-07` linking to `tech-debts/TD-07.md`, name "Circular Auth Imports", a one-line anti-pattern description, Affected Areas `auth/index.ts`, `middleware/session.ts`, `Status` `Opened`, `Reported` today, `Solved` `—`.
4. Do **not** create `docs/tech-debts/TD-07.md`. Tell the user: "Logged as TD-07. The solution plan will go in `docs/tech-debts/TD-07.md` when you plan the fix."

### Example 2: Planning the fix

User says: "plan tech debt TD-07"

1. Read the `TD-07` row in `docs/TECH_DEBTS.md`.
2. Create `docs/tech-debts/TD-07.md` from the Detail Template — Description of the cycle, Affected Code with import line numbers, Risk ("Build tools cannot tree-shake auth; test isolation is impossible"), and an Action plan.
3. Leave `Status` as `Opened` (or set `Tracked in <plan>` if tracked elsewhere); keep the row and file in sync.

### Example 3: Resolving a debt

User says: "resolve tech debt TD-07"

1. In `docs/TECH_DEBTS.md`, set `TD-07` `Status` = `Resolved` and `Solved` = today. Keep the row.
2. If `docs/tech-debts/TD-07.md` exists, set its `Status` to `Resolved`, fill `Solved`, and add a one-line resolution note.
