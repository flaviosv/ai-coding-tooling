---
name: code-review
description: >
  Perform comprehensive code reviews on implementation code. Reviews local workspace changes by
  default, or a GitHub PR when a PR number is provided. Covers architecture, performance, code
  quality, API design, and security. Technology agnostic — adapts to the project's stack using
  context files. Use when the user says "review my code", "code review", "check my code",
  "review my changes", "review this PR", or "review PR #123". Do NOT use for reviewing test
  files — use the tests-code-review skill for that.
metadata:
  version: "2.0.0"
  triggers:
    - "review my code"
    - "code review"
    - "check my code"
    - "review my changes"
    - "review this PR"
    - "review PR #123"
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
- **GitHub PR**: review only the PR diff from GitHub. Do NOT review local workspace files.
- User must explicitly provide a PR number to activate GitHub PR mode.

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

- **No PR number** → local workspace mode. Proceed to Step 2.
- **PR number provided** (e.g. "review PR #123", "code review PR 456") → GitHub PR mode.

For **GitHub PR mode**:

1. Extract the PR number from the user's message.
2. Check if GitHub MCP tools are available in the current session (search for tools matching `github`, `pull_request`, `gh`). MCP is preferred — it respects per-project configuration.
3. Fetch PR metadata and diff:
   - **MCP available**: use the GitHub MCP tools to get PR details, changed files, and diff content.
   - **MCP unavailable**: fall back to `gh` CLI:
     ```bash
     gh pr view <number> --json title,body,baseRefName,headRefName,files
     gh pr diff <number>
     ```
4. If both MCP and `gh` fail, report the error and stop.

## Step 2: Load Project Context

Load these files if they exist:

| File | Purpose |
|------|---------|
| `docs/PROJECT_DETAILS.md` | Tech stack, dependencies, environment config |
| `docs/ARCHITECTURE.md` | System layers, data flow, key components |
| `docs/TECH_DEBTS.md` | Known tech debts and anti-patterns — flag reviewed code that replicates these |

## Step 3: Load Review Checklists

> **CONSTRAINT: Load ONLY stack-relevant references.**
> Detect the tech stack from `docs/PROJECT_DETAILS.md`. Reference files use the naming convention
> `<tech-prefix>-<purpose>.md`. A file is **tech-specific** if its name starts with a known prefix
> (e.g., `python-`, `django-`, `golang-`, `gin-`). A file is **generic** if it has no tech prefix
> (e.g., `review-checklist.md`, `solid-principles.md`). Load ONLY:
> - Generic files (always)
> - Tech-specific files whose prefix matches the detected stack
>
> **Skip all non-matching tech-specific files.** If the project uses Python + Django, do NOT load
> `golang-code-review.md`, `php-code-review.md`, etc. If `docs/PROJECT_DETAILS.md` is missing or
> has no Tech Stack section, do NOT load any tech-specific references — load only generic files.

**Mandatory baselines** (always load — these are generic):

1. `references/review-checklist.md` — generic baseline (architecture, code quality, security, performance, docs)
2. `references/clean-code-checklist.md` — clean code principles (naming, functions, classes, control flow, side effects, abstractions)
3. `references/solid-principles.md` — SOLID design principles and cross-cutting smells

**Tech-specific checklists**: load ONLY matching `<language>-<framework>-code-review.md` from `references/` whose prefix matches the detected stack.

**Coding-guidelines style guides**: load ONLY matching files from the `coding-guidelines` skill's `reference/` directory (global: `~/.claude/skills/coding-guidelines/reference/`, project: `.agents/skills/coding-guidelines/reference/`). Pattern: `<language>-coding-guidelines.md`, `<language>-<framework>-coding-guidelines.md`. Skip non-matching. Deviations are findings.

**Security references**: load ONLY matching files from `security-best-practices` skill's `references/` directory (global or project). Skip non-matching.

**Performance references**: load `performance-review` skill's `references/performance-checklist.md` (generic — always) and ONLY matching tech-specific files. Skip non-matching.

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

Confront every deviation against all loaded references — coding-guidelines style guides and the clean-code checklist:

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

1. Apply generic performance baseline from `performance-review` references
2. Apply all loaded tech-specific performance references
3. Scope to changed files only
4. Flag every inefficiency: N+1 queries, unnecessary allocations, missing indexes, blocking calls

## Step 6: Present Findings

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Severity:** Critical, High, Medium, Low

**Priority:** P0 (must fix before merging), P1 (should fix soon), P2 (nice to have)

**Type:** Security, Performance, Architecture, Code Quality, Documentation, Tech Debt

Format for CLI readability. Provide specific line numbers. Suggest concrete solutions. Keep explanations concise.

## Step 7: Iterative Review

After fixes:

1. Update the table — mark fixed items with ✓
2. Re-review only changed code
3. Continue until all P0/P1 addressed

## Step 8: Post to GitHub (GitHub PR mode only)

Runs **only** when the user explicitly requests after reviewing findings locally.

### 8a. User Selects Findings

Wait for user to specify which findings to post:
- By number: "post 1, 3, 5"
- By filter: "post all", "post all P0", "post all Critical"

### 8b. Create Pending Review Comments

Use GitHub MCP tools if available (preferred), fall back to `gh` CLI.

**Using GitHub MCP**: use the MCP tool for creating pull request reviews. Pass selected comments as inline review comments with `PENDING` event.

**Using `gh` CLI fallback**:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews \
  --input - <<'EOF'
{
  "event": "PENDING",
  "comments": [
    {"path": "<file>", "line": <line>, "body": "**[Severity/Priority]** Title\n\nExplanation\n\n**Suggestion:** fix"}
  ]
}
EOF
```

Parse `{owner}/{repo}` from `gh repo view --json nameWithOwner -q '.nameWithOwner'`.

### 8c. Confirm Result

Report:
- Number of comments added to pending review
- Link to the PR
- Reminder: "Review is pending — submit manually on GitHub."

**Never submit the review.** No `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` event. Pending only.

## Examples

### Example 1: Local workspace review

User: "review my code"

1. No PR number → local mode
2. Load context: `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `TECH_DEBTS.md`
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
