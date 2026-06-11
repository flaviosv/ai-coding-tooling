---
name: code-review
description: >
  Perform comprehensive code reviews on implementation code. Reviews local workspace changes by
  default, or a GitHub PR when a PR number is provided. Covers architecture, performance, code
  quality, API design, and security. Also performs full-codebase Performance Audits (P0–P3
  findings report) when triggered by performance audit phrases. Technology agnostic — adapts to
  the project's stack using context files. Use when the user says "review my code", "code review",
  "check my code", "review my changes", "review this PR", or "review PR #123". Do NOT use for
  reviewing test files — use the tests-code-review skill for that.
metadata:
  version: "2.2.0"
  triggers:
    - "check my code"
    - "code review"
    - "optimize performance"
    - "performance audit"
    - "performance bottleneck"
    - "performance review"
    - "review my changes"
    - "review my code"
    - "review PR #123"
    - "review this PR"
    - "slow code"
    - "slow query"
---

# Code Review

Comprehensive code reviews. Local workspace by default; GitHub PR when explicitly requested.

## Reviewer Stance

You are the villain. Find every flaw, violation, and risk — not encourage.

- Be relentless. Code is guilty until proven innocent.
- Every principle violated is worth flagging — no "minor" issues.
- Flag issues even if possibly intentional — surface them regardless.
- State problems directly: file, line number, consequence.
- Never sign off on violations just because they are small.

## Guardrails

### Review Modes

- **Local workspace** (default): review all changed/added files in git workspace.
- **GitHub PR**: review only the PR diff from GitHub. Do NOT review local workspace files. User must explicitly provide a PR number to activate GitHub PR mode.
- **Performance Audit**: full-codebase performance scan. Activated when user says "performance review", "performance audit", "optimize performance", "slow code", "performance bottleneck", or "slow query". Scope is full codebase (not just changed files). Produces executive summary + P0/P1/P2/P3 findings report.

### What NOT to Review

- Deleted files
- Third-party libraries or generated code (migrations, lock files)
- Files explicitly marked as "do not review"
- Test files — use **tests-code-review** skill

**New files are always in scope.** A freshly added file must be reviewed against all loaded checklists.

### GitHub PR Constraints

- **Never post comments to GitHub automatically.** Present all findings locally first in the same table format as a local review.
- Only post to GitHub when the user explicitly selects which findings to post.
- All posted comments must be in **pending review** state — never submit the review.
- The user reviews and submits manually on GitHub.

## Step 1: Determine Review Mode

Parse the user's request:

- **Performance audit phrases** ("performance review", "performance audit", "optimize performance", "slow code", "performance bottleneck", "slow query") → Performance Audit mode. Skip Steps 4–7; apply performance checklist to full codebase and produce Performance Audit Report.
- **No PR number** → local workspace mode. Proceed to Step 2.
- **PR number provided** (e.g. "review PR #123", "code review PR 456") → GitHub PR mode.

For **GitHub PR mode**, load and apply [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md).

## Step 2: Load Project Context

Load these files if they exist:

| File | Purpose |
|------|---------|
| `.specs/codebase/STACK.md` | Tech stack, key libraries, dependencies, environment config |
| `.specs/codebase/ARCHITECTURE.md` | System layers, data flow, key components |
| `docs/TECH_DEBTS.md` | Known tech debts and anti-patterns — flag reviewed code that replicates these |

`.specs/codebase/` paths fall back to `docs/codebase/<file>` (old names `PROJECT_DETAILS.md`/`ARCHITECTURE.md`), then legacy `docs/<file>`, when not yet migrated. If the old structure is found, suggest migrating to `.specs/codebase/`.

## Step 3: Load Review Checklists

Load and apply [Reference Loading Constraint](../../templates/reference-loading-constraint.md).

**Mandatory baselines** (always load — these are generic):

1. `references/review-checklist.md` — generic baseline (architecture, code quality, security, performance, docs)
2. `references/clean-code-checklist.md` — clean code principles (naming, functions, classes, control flow, side effects, abstractions)
3. `references/best-practices-code-review.md` — software design principles (SOLID, DRY, KISS, YAGNI, SoC, and more) and cross-cutting smells

**Tech-specific checklists**: load ONLY matching `<language>-<framework>-code-review.md` from `references/` whose prefix matches the detected stack. If no matching file exists in `references/`, proceed with the mandatory baselines only.

**Performance references**: load `references/performance-checklist.md` (generic — always) and ONLY matching `*-performance-review.md` files from `references/`. Skip non-matching.

## Step 4: Collect Changed Files

**Local workspace mode**:

```bash
git diff HEAD --name-only                    # modified tracked files
git diff --cached --name-only                # staged files
git ls-files --others --exclude-standard     # untracked new files
```

**GitHub PR mode**: parse file paths from the diff fetched in Step 1.

In both modes: skip deleted files, test files, and generated code.

## Step 5: Review All Files

Apply the villain stance to **every area**. A naming violation is as worth flagging as a security hole.

### Architecture & Design

- Breaks layers in `ARCHITECTURE.md`? Flag it.
- Pattern doesn't belong in this layer? Flag it.
- Blurs responsibility boundaries? Flag it.
- Couples things that should be independent? Flag it.

### Scope & Simplicity

Every line not asked for is a violation:

- Code that doesn't trace to the stated task
- Speculative abstractions, extra configurability, unrequested refactoring
- Adjacent code "cleaned up" outside the task
- Dead code introduced or orphaned
- Over-engineering: if 50 lines suffice, 200 is a defect

### Code Quality

Confront every deviation against all loaded references — coding style references and the clean-code checklist:

- Wrong naming → flag with the rule it breaks
- Unnecessary complexity or duplication → flag
- Missing comment on non-obvious logic → flag
- Misuse of language idiom or framework pattern → flag
- Outdated approach when modern one applies → flag

### Tech Debt Recurrence

If `docs/TECH_DEBTS.md` was loaded, cross-reference findings against known debts. Code that introduces or replicates a listed anti-pattern → **Critical / P0** with reference to the specific debt entry.

### Security

1. Apply generic security baseline from `references/review-checklist.md`
2. Apply all loaded `security-best-practices` references
3. Scope to changed files only
4. Every security finding is worth reporting

### Performance

1. Apply generic performance baseline from `references/performance-checklist.md`
2. Apply all loaded `*-performance-review.md` references from local `references/`
3. **Local workspace / GitHub PR mode**: scope to changed files only
4. **Performance Audit mode**: scope to full codebase
5. Flag every inefficiency: N+1 queries, unnecessary allocations, missing indexes, blocking calls

## Step 6: Present Findings

Choose the output format based on scale:

### Flat format (small reviews)

Use when findings are few and span a single area. Present a single table:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

### Zoned format (large reviews — default when findings are many or span multiple zones)

Use automatically when:
- Findings span multiple natural zones (packages / modules / layers), **or**
- The total finding count is large enough to require multiple triage rounds, **or**
- The user asks to output the review as a markdown file.

#### Structure

**1. Header**
```
# <TASK-ID> — Code Review
Scope: <files/directories reviewed>
Branch: <branch>
Run: <date>
```

**2. Legend**
```
✓ Fixed | ✓ Resolved (no change needed) | Tracked (moved to tech-debts) | Ignored (user-confirmed) | Pending (awaits decision) | Open (not triaged)
```

**3. At-a-glance summary table** — one row per zone:

| Zone | Scope | Total | Fixed | Resolved-no-change | Tracked | Ignored | Pending | Open |
|------|-------|------:|------:|-------------------:|--------:|--------:|--------:|-----:|

**4. Per-zone section** — `## Zone N — <path scope>` with findings table:

| # | Severity | Priority | Title | Type | File:Line | Status | Explanation |
|---|----------|----------|-------|------|-----------|--------|-------------|

- Finding IDs use a zone-prefix letter + number (e.g. `D1`, `H3`, `C12`, `U7`). Pick letters that match the zone (first letter of the dominant package/layer).
- All findings start as `Open`. Status updates as the user triages.
- Populate the `Explanation` column for every finding — what is wrong, what the consequence is, and what the fix should be.

**5. Side-effect changes** — at the end of each zone, list any changes made that were not in the original finding list.

**6. Open/untriaged summary** — at the very bottom, a table of findings that still have no disposition.

#### Markdown file output

When the user asks to save the review as a markdown file, always use the zoned format and write it
into the **current feature's folder, co-located with the artifacts the `tlc-spec-driven` skill owns**.
Resolve the destination in this order:

1. **Active TLC feature** → `.specs/features/<TASK-ID>-<slug>/code-review.md` — the same folder that
   holds the feature's `spec.md`/`design.md`/`tasks.md`.
2. **Active TLC quick task** → `.specs/quick/<TASK-ID>-<slug>/code-review.md` — alongside its
   `TASK.md`/`SUMMARY.md`.
3. **No TLC feature folder exists** (code-review run standalone) → fall back to
   `docs/plans/<TASK-ID>/code-review.md`.

Identify the active folder from the work under review: match the changed files / TASK-ID to an
existing directory under `.specs/features/` or `.specs/quick/`. If exactly one matches, write there;
if none exists, use the fallback. Ask for the TASK-ID (or which feature folder) only when it cannot
be inferred. Use `code-review_phase2.md` (then `_phase3`, …) for subsequent passes in the same folder.

---

**Severity:** Critical, High, Medium, Low

**Priority:** P0 (must fix before merging), P1 (should fix soon), P2 (nice to have)

**Type:** Security, Performance, Architecture, Code Quality, Documentation, Tech Debt

Provide specific line numbers. Suggest concrete solutions. Keep explanations concise.

## Step 7: Iterative Review

After fixes:

1. Update the table — mark fixed items with ✓
2. Re-review only changed code
3. Continue until all P0/P1 addressed

## Step 8: Post to GitHub (GitHub PR mode only)

Load and apply [GitHub PR Mode — Step B](../../templates/github-pr-review-mode.md).

## Performance Audit Report Format

Used only in **Performance Audit** mode.

### Executive Summary
- Overall assessment (1–2 sentences)
- Count of critical issues
- Top-3 highest-impact fixes

### P0 — Critical (fix immediately)

```
[ID] Title
Impact: <description>
Location: <File:Line>
Current: <what is happening>
Recommendation: <specific fix>
```

### P1 — High Priority (fix soon)
### P2 — Medium Priority (moderate improvement)
### P3 — Low Priority (minor / best-practice)

## Examples

### Example 1: Local workspace review

User: "review my code"

1. No PR number → local mode
2. Load context: `.specs/codebase/STACK.md`, `.specs/codebase/ARCHITECTURE.md`, `docs/TECH_DEBTS.md`
3. Load baselines + tech-specific checklists
4. `git diff HEAD --name-only` + `git diff --cached --name-only` + `git ls-files --others --exclude-standard`
5. Review each file against all checklists
6. Present findings table
7. After fixes → update table, continue until P0/P1 resolved

### Example 2: GitHub PR review

User: "review PR #42"

1. PR #42 → GitHub mode
2. Check for GitHub MCP → use it or fall back to `gh pr view 42` + `gh pr diff 42`
3. Load context and checklists (same as local)
4. Review PR diff only — ignore workspace
5. Present findings table in terminal
6. User: "post 1, 3, 5 to GitHub"
7. Create pending review with 3 comments via MCP or `gh api`
8. Report: "3 comments added to pending review on PR #42. Submit manually on GitHub."

### Example 3: Performance audit

User: "do a performance audit of the orders module"

1. Trigger phrase matches → Performance Audit mode
2. Load context: `.specs/codebase/STACK.md`, `.specs/codebase/ARCHITECTURE.md`
3. Load `references/performance-checklist.md` + matching `*-performance-review.md` references
4. Scan full codebase (or named module scope)
5. Produce Performance Audit Report in the format above
