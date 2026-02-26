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

## Scope

When invoked:
- Review **only** files changed in the git workspace
- **Do NOT make changes** — only share findings with explanations
- Skip deleted files
- Focus on actionable feedback

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

Then identify the project's language and framework from `PROJECT_DETAILS.md` and load **all**
matching technology-specific review checklists from `references/`. Reference files follow the naming
convention `<language>-<framework>-review-checklist.md`. If the stack uses multiple layers (e.g.
Python + Django, or Go + Gin), load every file that matches — combining them all.

The dedicated security and performance workflows below layer additional depth on top of all loaded checklists.

## Review Areas

### Architecture & Design

Check that changes:
- Follow the architectural layers and data flow described in `ARCHITECTURE.md`
- Do not introduce patterns inconsistent with the existing structure
- Respect defined responsibilities per layer or module
- Maintain appropriate separation of concerns

### Code Quality

Check that changes:
- Follow naming conventions and formatting rules from `CODING_STYLE.md`
- Are readable and maintainable
- Avoid unnecessary complexity or duplication
- Use project dependencies and abstractions appropriately
- Include comments where logic is non-obvious

### Security Review

Perform a security review scoped strictly to the changed files.

**Workflow:**
1. Always load the generic security baseline from `references/review-checklist.md`
2. Identify the project's language and framework from `PROJECT_DETAILS.md`
3. Additionally load any matching reference files from the `security-best-practices` skill:
   - Location: `.claude/skills/security-best-practices/references/` (global) or `.agents/skills/security-best-practices/references/` (project)
   - Load all files matching the detected stack (e.g. `python-django-web-server-security.md`, `javascript-typescript-react-web-frontend-security.md`)
   - Also load the `<language>-general-<stack>-security.md` file if present
4. Apply both sources of guidance together — the generic checklist sets the baseline, the framework-specific references deepen it
5. Scope findings strictly to the changed files — do not expand to the rest of the codebase
6. Report security findings as rows in the review table with appropriate severity

### Performance Review

Perform a performance review scoped strictly to the changed files.

**Workflow:**
1. Always load the generic performance baseline from the `performance-review` skill: `references/performance-checklist.md`
2. Identify the project's language and framework from `PROJECT_DETAILS.md`
3. Additionally load any matching technology-specific reference files from the `performance-review` skill's `references/` directory if they exist
4. Apply both sources of guidance together — the generic checklist sets the baseline, the technology-specific references deepen it
5. Scope findings strictly to the changed files — do not expand to the rest of the codebase
6. Report performance findings as rows in the review table with appropriate severity


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
4. Load ALL matching `security-best-practices` and `performance-review` references for the detected stack
5. Run `git diff` to identify changed non-test files
6. Review each file against all loaded checklists
7. Produce the findings table — flag all P0/P1 items with specific line numbers and concrete suggestions
8. After fixes, update the table and mark resolved items — continue until all P0/P1 are addressed

## What NOT to Review

- Files that haven't changed in this workspace
- Deleted files
- Third-party libraries or generated code (e.g. migrations, lock files)
- Files explicitly marked as "do not review"
- Test files — use the **tests-code-review** skill for those
