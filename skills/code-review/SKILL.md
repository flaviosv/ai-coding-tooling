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
- Only report a finding when confidence is ≥ 80%. If uncertain whether a pattern is a violation, skip it — do not guess.

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

## Step 1: Mode Detection

Parse the user's request and resolve to exactly one mode before proceeding. Priority order matters — first match wins:

| Priority | Trigger | Mode |
|----------|---------|------|
| 1 | "performance audit", "performance review", "optimize performance", "slow code", "performance bottleneck", "slow query" | Performance Audit |
| 2 | "review commits X Y Z", "review commits X..Y", "review last N commits", comma/space-separated hashes after "review" | Multi-commit |
| 3 | PR number present (e.g. "review PR #42", "code review PR 456") | GitHub PR |
| 4 | Default | Local workspace |

Mode is fixed for the remainder of the pipeline.

For **GitHub PR mode**, load and apply [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md).

## Step 2: Context Collection

Load all of the following in one pass before spawning any subagent. Each item is either **present** (loaded) or **absent** (noted for Step 3).

**Codebase docs** — load from `.specs/codebase/`; fall back to `docs/codebase/` then `docs/` if not yet migrated. If old structure found, suggest migrating to `.specs/codebase/`:

| File | Availability key |
|------|-----------------|
| `STACK.md` | `stack` |
| `ARCHITECTURE.md` | `architecture` |
| `CONVENTIONS.md` | `conventions` |
| `TESTING.md` | `testing` |
| `CONCERNS.md` | `concerns` |
| `INTEGRATIONS.md` | `integrations` |
| `STRUCTURE.md` | `structure` |

**Review checklists** — mandatory baselines always loaded; tech-specific only when stack matches:

| File | Availability key |
|------|-----------------|
| `references/review-checklist.md` | `checklist_baseline` |
| `references/clean-code-checklist.md` | `checklist_clean_code` |
| `references/best-practices-code-review.md` | `checklist_best_practices` |
| `references/performance-checklist.md` | `checklist_performance` |
| `references/<stack>-*-code-review.md` (if match) | `checklist_tech_specific` |
| `references/<stack>-*-performance-review.md` (if match) | `checklist_tech_perf` |

**Other:**

| Item | Availability key |
|------|-----------------|
| `docs/TECH_DEBTS.md` | `tech_debts` |
| Active spec or task description (`.specs/features/*/spec.md`, task body, or user-provided) | `requirements` |

## Step 3: Context Availability Map + Bundle Assembly

Build the availability map from Step 2 results:

```
availability = {
  // codebase docs
  stack, architecture, conventions, testing,
  concerns, integrations, structure,
  // checklists
  checklist_baseline, checklist_clean_code,
  checklist_best_practices, checklist_performance,
  checklist_tech_specific, checklist_tech_perf,
  // other
  tech_debts, requirements
}
// each field: present | absent
```

Use this map to assemble a **context bundle** for each subagent — a structured text block injected into the agent's prompt containing only the items marked `present` and relevant to that agent's dimension. Bundle definitions are in Step 6.

If a bundle is missing a **required** item for an agent, flag that agent as `degraded`: it proceeds without that item, notes the gap in its findings, and the at-a-glance table shows `⚠️ degraded — <missing item>`.

## Step 4: Diff Collection

Collect the diff and file list based on the mode from Step 1:

| Mode | Commands |
|------|----------|
| Local workspace | `git diff HEAD`, `git diff --cached`, `git ls-files --others --exclude-standard` |
| GitHub PR | `gh pr diff <PR#>` (prefer GitHub MCP if available) |
| Multi-commit (hashes) | `git show <h1>; git show <h2>; ...` — concatenated in order |
| Multi-commit (range) | `git diff <base>..<tip>` |
| Performance Audit | No diff — full codebase scan |

Also collect:
- `git diff --stat` (or equivalent) — used in the report header
- Changed file list — used to route context slices to agents
- **Multi-commit only:** `git log --oneline <range>` or resolved hash+subject list — used in report header

In all modes: skip deleted files, test files, and generated code when building the changed file list.

## Step 5: Quick Mode Check

**Condition:** changed file count ≤ 2 **AND** total diff lines < 100

**If triggered:** skip Steps 6–8; fall back to inline review — proceed directly to [Review All Files](#step-6-review-all-files) and [Present Findings](#step-7-present-findings).

**Multi-commit mode:** apply this check against the combined diff totals across all commits.

If the condition is not met, proceed to Step 6 (parallel subagent dispatch).

## Step 6: Parallel Subagent Dispatch

**All 8 agents MUST be fired in a single parallel message. Never sequentially.**

Each agent receives a prompt with four sections:

```
## Role
<agent name and dimension>

## Context
<inlined content from the agent's context bundle — present items only, relevant to this dimension>

## Diff
<full diff from Step 4 — all agents receive the full diff; scoping is in the context, not the code>

## Return format
Status: Complete | Blocked | Partial
Dimension: <agent name>
Findings: [{severity, title, file, line, explanation, recommendation}]
Files reviewed: [list]
Gate check: pass | fail | skipped — <detail>
Issues: <any blockers encountered>

## Second Pass
After your initial findings pass, re-read the full diff from top to bottom.
For every file or hunk you did not comment on, explicitly state either
"clean — no violations in my dimension" or flag it. Only skip a file
when you can state concretely why it is clean for your dimension.
```

### Agent Roster

| Agent | Dimension | Required context | Optional context | Degrades without |
|-------|-----------|-----------------|------------------|-----------------|
| `architecture-reviewer` | Layer violations, coupling, pattern misuse | `checklist_baseline` | `architecture`, `structure`, `stack`, `concerns` | `architecture` |
| `code-quality-reviewer` | Naming, complexity, SOLID, DRY, KISS, clean code | `checklist_clean_code`, `checklist_best_practices` | `conventions`, `stack`, `concerns`, `tech_debts`, `checklist_tech_specific` | `conventions` |
| `security-reviewer` | Auth, injection, secrets, data exposure | `checklist_baseline` (security section) | `integrations`, `stack`, `concerns` | — |
| `performance-reviewer` | N+1, allocations, blocking calls, missing indexes | `checklist_performance` | `stack`, `integrations`, `concerns`, `checklist_tech_perf` | — |
| `docs-comments-reviewer` | Inline docs, API docs, obsolete/misleading comments | `checklist_baseline` (docs section) | `conventions`, `stack` | — |
| `build-test-validator` | Run gate check commands, verify tests pass | — | `testing` | `testing` (falls back to standard commands: `npm test`, `pytest`, etc.) |
| `regression-reviewer` | Unrelated deletions, phantom imports, AI hallucination artifacts, weakened assertions | `checklist_baseline` | `stack`, `concerns` | — |
| `requirements-tracer` | Does the change satisfy the stated spec/task | `requirements` | — | **Skip entirely** if `requirements` absent — mark as ➖ skipped |

### Reviewer Stance (injected into every agent)

You are the villain. Find every flaw, violation, and risk — not encourage.

- Be relentless. Code is guilty until proven innocent.
- Every principle violated is worth flagging — no "minor" issues.
- Flag issues even if possibly intentional — surface them regardless.
- State problems directly: file, line number, consequence.
- Never sign off on violations just because they are small.
- Only report a finding when confidence is ≥ 80%. If uncertain whether a pattern is a violation, skip it — do not guess.

### Performance Audit mode exception

In Performance Audit mode: `architecture-reviewer` and `performance-reviewer` scan the full codebase. All other agents scope to changed files only. `build-test-validator` and `requirements-tracer` are skipped.

### Agent: regression-reviewer

**Dimension:** Regression & Hallucination Detection

Review the diff for changes unrelated to the PR's stated purpose or showing signs of AI-generated artifacts:

- **Phantom imports** — references to symbols that do not exist in the codebase (🚨 Critical).
- **Unrelated deletions** — code removed with no connection to the stated change (🚨 Critical).
- **Duplicate logic** — functionality already present in the module, re-implemented.
- **Weakened assertions** — error handling, validation rules, or test assertions made less strict.
- **Dead code** — functions or branches introduced but never called.
- **`TODO`/`FIXME` in production** — leftover markers not resolved before merge.
- **Type assertions hiding errors** — `as any` or forced casts masking real type errors.

### Quick mode inline fallback (from Step 5)

When Quick Mode Check triggered: skip subagent dispatch. Apply the reviewer stance directly inline across all six dimensions (architecture, code quality, security, performance, docs, requirements) without spawning agents. Proceed to Step 7 (Present Findings).

## Step 7: Await + Fallback

Wait for all dispatched agents to return. For each agent, resolve its outcome:

| Outcome | Action |
|---------|--------|
| Returned normally | Parse structured result |
| Failed or timed out | Mark dimension as `⚠️ not executed — <reason>` |
| Degraded (missing required context) | Mark dimension as `⚠️ degraded — <missing item>` |
| `requirements-tracer` skipped (no requirements) | Mark as `➖ skipped — no requirements available` |

Continue to Step 8 regardless of individual agent outcomes. A failed agent never blocks the report.

## Step 8: Consolidation and Present Findings

### Report header (always first)

```
# <TASK-ID or branch> — Code Review
Scope: <files reviewed>
Branch: <branch>
Commits: <hash — subject>, <hash — subject>, ...   ← multi-commit mode only
Diff: <N files changed, +X insertions, -Y deletions>
Run: <date>
Mode: local | GitHub PR #N | multi-commit | performance audit
```

### At-a-glance table (always second)

One row per agent dimension — always present regardless of output format:

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Architecture | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Code Quality | ... | N | N | N | 1-line |
| Security | ... | N | N | N | 1-line |
| Performance | ... | N | N | N | 1-line |
| Docs & Comments | ... | N | N | N | 1-line |
| Regression & Hallucination | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Build & Tests | ✅ pass / ❌ fail / ⚠️ | — | — | gate result |
| Requirements | ✅ / ➖ skipped | — | — | coverage summary |

### Output format

**Flat format** — use when findings are few and span a single dimension:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Zoned format** — use when findings are many or span multiple dimensions (default for subagent reviews):

Agent dimensions map directly to zones. Zone letter assignment:

| Zone | Letter | Agent |
|------|--------|-------|
| Architecture | A | `architecture-reviewer` |
| Code Quality | Q | `code-quality-reviewer` |
| Docs & Comments | D | `docs-comments-reviewer` |
| Performance | P | `performance-reviewer` |
| Regression & Hallucination | H | `regression-reviewer` |
| Requirements | R | `requirements-tracer` |
| Security | S | `security-reviewer` |
| Build & Tests | B | `build-test-validator` |

Finding IDs: `<ZoneLetter><N>` (e.g. `A1`, `Q3`, `S2`). All findings start as `Open`.

**Legend:**
```
✓ Fixed | ✓ Resolved (no change needed) | Tracked (moved to tech-debts) | Ignored (user-confirmed) | Pending (awaits decision) | Open (not triaged)
```

Per-zone section: `## Zone <Letter> — <Dimension>` with findings table:

| # | Severity | Priority | Title | Type | File:Line | Status | Explanation |
|---|----------|----------|-------|------|-----------|--------|-------------|

At the very bottom: open/untriaged summary table — all findings with no disposition.

---

**Severity:** Critical, High, Medium, Low

**Priority:** P0 (must fix before merging), P1 (should fix soon), P2 (nice to have)

**Type:** Architecture, Code Quality, Documentation, Performance, Security, Tech Debt

Provide specific line numbers. Suggest concrete solutions. Keep explanations concise.

#### Markdown file output

When the user asks to save the review as a markdown file, always use the zoned format and write it
into the **current feature's folder, co-located with the artifacts the `tlc-spec-driven` skill owns**.
Resolve the destination in this order:

1. **Active TLC feature** → `.specs/features/<TASK-ID>-<slug>/code-review.md`
2. **Active TLC quick task** → `.specs/quick/<TASK-ID>-<slug>/code-review.md`
3. **No TLC feature folder** → `docs/plans/<TASK-ID>/code-review.md`

Match the changed files / TASK-ID to an existing directory under `.specs/features/` or `.specs/quick/`. If none exists, use the fallback. Use `code-review_phase2.md` (then `_phase3`, …) for subsequent passes.

### Iterative review

After fixes:

1. Update the table — mark fixed items with ✓
2. Re-review only changed code
3. Continue until all P0/P1 addressed

## Step 9: Post to GitHub (GitHub PR mode only)

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

1. Step 1: No PR number, no commit refs → local workspace mode
2. Step 2: Load all `.specs/codebase/` docs + all checklists + `docs/TECH_DEBTS.md`
3. Step 3: Build availability map; assemble context bundles per agent
4. Step 4: `git diff HEAD` + `git diff --cached` + `git ls-files --others --exclude-standard`; collect `git diff --stat`
5. Step 5: Quick mode check — if ≤ 2 files and < 100 lines, review inline; otherwise continue
6. Step 6: Dispatch all 8 agents in parallel, each with their context bundle + full diff
7. Step 7: Await all results; mark any failures/degraded agents
8. Step 8: Report header → at-a-glance table → zoned findings; iterative review until P0/P1 resolved

### Example 2: GitHub PR review

User: "review PR #42"

1. Step 1: PR #42 → GitHub PR mode
2. Step 2: Load all context + checklists (same as local)
3. Step 3: Build availability map + bundles
4. Step 4: `gh pr diff 42` (prefer GitHub MCP); collect changed file list
5. Step 5: Quick mode check
6. Step 6: Dispatch 8 agents in parallel against PR diff only — ignore local workspace
7. Step 7: Await results
8. Step 8: Consolidated report with at-a-glance table
9. Step 9: User selects findings to post → create pending review comments via MCP or `gh api`; user submits manually on GitHub

### Example 3: Performance audit

User: "do a performance audit of the orders module"

1. Step 1: Trigger phrase matches → Performance Audit mode
2. Step 2: Load all context + checklists
3. Step 3: Build availability map + bundles
4. Step 4: No diff — full codebase scan
5. Step 5: Quick mode check skipped (Performance Audit always uses subagents)
6. Step 6: Dispatch `architecture-reviewer` and `performance-reviewer` against full codebase; all other agents scope to changed files only; `build-test-validator` and `requirements-tracer` skipped
7. Step 7: Await results
8. Step 8: Produce Performance Audit Report in the format above

### Example 4: Multi-commit review

User: "review commits abc123 def456 ghi789"

1. Step 1: Commit hashes detected → multi-commit mode
2. Step 2: Load all context + checklists
3. Step 3: Build availability map + bundles
4. Step 4: `git show abc123; git show def456; git show ghi789` — concatenated into one combined diff; collect commit list (hash + subject) for report header
5. Step 5: Quick mode check applied against combined diff totals
6. Step 6: Dispatch 8 agents in parallel against the combined diff
7. Step 7: Await results
8. Step 8: Single consolidated report — header lists all 3 commits; at-a-glance table + findings as normal
