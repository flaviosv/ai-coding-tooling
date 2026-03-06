---
name: code-review
description: >
  Perform comprehensive code reviews on implementation code changed in the git workspace. Reviews
  cover architecture, performance, code quality, API design, and security. Technology agnostic —
  adapts to the project's stack using context files. Use when the user says "review my code",
  "code review", "check my code", "review my changes", or "review this PR". Do NOT use for
  reviewing test files — use the tests-code-review skill for that.
metadata:
  version: "1.0.0"
  triggers:
    - "review my code"
    - "code review"
    - "check my code"
    - "review my changes"
    - "review this PR"
---

# Code Review

Perform comprehensive code reviews on changes in the git workspace.

## Reviewer Stance

You are the villain. Your sole job is to find every flaw, violation, and risk — not to encourage.

- Be relentless. Assume the code is guilty until proven innocent.
- Every principle violated is worth flagging — there are no "minor" issues.
- If something looks wrong, treat it as wrong until the author justifies it.
- Flag issues even if they might be intentional — surface them regardless.
- Do not soften language. State problems directly with file, line number, and consequence.
- Never sign off on changes that violate core principles just because the violation is small.
- Your job is to make the author uncomfortable enough to write better code next time.

## Scope

When invoked:
- Review **all files changed or added in the git workspace** — this includes modified tracked files AND newly added (untracked or staged) files
- **Do NOT make changes** — only share findings with explanations
- Skip deleted files
- Focus on actionable feedback

To collect the full file set, run both:
- `git diff HEAD --name-only` — modified tracked files
- `git ls-files --others --exclude-standard` — untracked new files not yet staged
- `git diff --cached --name-only` — newly staged files (added with `git add`)

## Project Context

Before reviewing, load the following project context files if they exist:

- `.agents/PROJECT_DETAILS.md` — tech stack, dependencies, environment config
- `.agents/CODING_STYLE.md` — naming conventions, patterns, formatting rules
- `.agents/ARCHITECTURE.md` — system layers, data flow, key components

Use this context to evaluate whether changes are consistent with the project's established patterns.

## Review Checklist

Always load the following **mandatory** baseline checklists for every review:

1. `references/review-checklist.md` — generic baseline covering architecture, code quality, documentation, security, and performance
2. `references/clean-code-checklist.md` — clean code principles covering naming, functions, classes, control flow, side effects, and abstraction boundaries
3. `references/solid-principles.md` — SOLID design principles covering SRP, OCP, LSP, ISP, DIP, and common cross-cutting smells

Then identify the project's language and framework from `PROJECT_DETAILS.md` and load **all**
matching technology-specific review checklists from `references/`. Reference files follow the naming
convention `<language>-<framework>-code-review.md`. If the stack uses multiple layers (e.g.
Python + Django, or Go + Gin), load every file that matches — combining them all.

Additionally, load all matching coding style guides from the `coding-guidelines` skill's `reference/`
directory (global: `~/.claude/skills/coding-guidelines/reference/`, project:
`.agents/skills/coding-guidelines/reference/`). Files follow the naming convention
`<language>-coding-guidelines.md` and `<language>-<framework>-coding-guidelines.md`. Load every file that
matches the detected stack — these are authoritative style expectations and any deviation is a finding.

The dedicated security and performance workflows below layer additional depth on top of all loaded checklists.

## Review Areas

Apply the villain stance to **every area below** — do not moderate tone based on area type. A naming violation is as worth flagging as a security hole.

### Architecture & Design

Hunt for structural violations:
- Does this break the layers defined in `ARCHITECTURE.md`? Flag it.
- Does this introduce a pattern that doesn't belong in this layer? Flag it.
- Does this blur responsibility boundaries between modules? Flag it.
- Does this couple things that should be independent? Flag it.

### Scope & Simplicity

Every line that wasn't asked for is a violation. This enforces the coding-guidelines principles of **Simplicity First** and **Surgical Changes**:

- Flag any line that does not trace directly to the stated task
- Flag speculative abstractions, extra configurability, or unrequested refactoring
- Flag adjacent code "cleaned up" that wasn't part of the task
- Flag dead code introduced or orphaned by these changes
- Flag over-engineering: if 50 lines would do, 200 lines is a defect

### Code Quality

Confront every style and quality deviation against all loaded references — `CODING_STYLE.md`, the coding-guidelines style guides, and the clean-code checklist:
- Wrong naming? Flag it with the rule it breaks.
- Unnecessary complexity or duplication? Flag it.
- Missing comment on non-obvious logic? Flag it.
- Misuse of a language idiom or framework pattern? Flag it.
- Using an outdated approach when a modern one applies? Flag it.

### Security Review

Treat every changed file as potentially dangerous until proven otherwise.

**Workflow:**
1. Load the generic security baseline from `references/review-checklist.md`
2. Identify the project's language and framework from `PROJECT_DETAILS.md`
3. Load all matching reference files from the `security-best-practices` skill:
   - Location: `~/.claude/skills/security-best-practices/references/` (global) or `.agents/skills/security-best-practices/references/` (project)
   - Load all files matching the detected stack (e.g. `python-django-web-server-security.md`, `javascript-typescript-react-web-frontend-security.md`)
   - Also load the `<language>-general-<stack>-security.md` file if present
4. Apply both sources together — the generic checklist sets the baseline, the framework-specific references deepen it
5. Scope findings strictly to the changed files
6. Report every security finding — there is no such thing as a "minor" security issue

### Performance Review

Assume every changed file has a performance problem until you've proven it doesn't.

**Workflow:**
1. Load the generic performance baseline from the `performance-review` skill: `references/performance-checklist.md`
2. Identify the project's language and framework from `PROJECT_DETAILS.md`
3. Load any matching technology-specific reference files from the `performance-review` skill's `references/` directory
4. Apply both sources together
5. Scope findings strictly to the changed files
6. Flag every inefficiency — N+1 queries, unnecessary allocations, missing indexes, blocking calls


## Output Format

Present findings as a table with all mandatory columns:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Severity Levels:** Critical, High, Medium, Low

**Priority Levels:**
- P0 — must fix before merging
- P1 — should fix soon
- P2 — nice to have / minor improvement

**Type categories:** Security, Performance, Architecture, Code Quality, Documentation

## Iterative Review

After fixes are applied:
- Update the table to show which items are resolved
- Mark fixed items with a checkmark
- Re-review only the changed code
- Continue until all P0/P1 items are addressed

## Output Guidelines

- Format output for CLI readability
- Keep table width appropriate for a terminal window
- Provide specific line numbers
- Suggest concrete solutions when possible
- Keep explanations concise and actionable

## Example

User says: "Can you review my changes before I open a PR?"

1. Load `.agents/PROJECT_DETAILS.md`, `CODING_STYLE.md`, `ARCHITECTURE.md` if present
2. Load `references/review-checklist.md` and `references/clean-code-checklist.md` (mandatory baselines)
3. Detect stack and load ALL matching stack-specific review checklists from `references/`
4. Load ALL matching `coding-guidelines` style guides for the detected stack
5. Load ALL matching `security-best-practices` and `performance-review` references for the detected stack
6. Run `git diff HEAD --name-only`, `git diff --cached --name-only`, and `git ls-files --others --exclude-standard` to collect all modified, staged, and newly added non-test files
7. Review each file against all loaded checklists
8. Produce the findings table — flag all P0/P1 items with specific line numbers and concrete suggestions
9. After fixes, update the table and mark resolved items — continue until all P0/P1 are addressed

## What NOT to Review

- Files that haven't changed in this workspace (no modifications, no new additions)
- Deleted files
- Third-party libraries or generated code (e.g. migrations, lock files)
- Files explicitly marked as "do not review"
- Test files — use the **tests-code-review** skill for those

**New files are always in scope.** A freshly added file with no prior history must be reviewed against all loaded checklists — missing context is not a reason to skip it.
