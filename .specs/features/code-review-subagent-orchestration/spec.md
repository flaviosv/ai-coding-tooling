# Feature Spec — Code Review Subagent Orchestration

**Feature ID:** CR-SUBAGENT  
**Status:** Specifying  
**Skill target:** `skills/code-review/SKILL.md`

---

## Problem

The current `code-review` SKILL.md runs all review dimensions inline, in the main agent context. This means:

- Review output (file reads, checklist matches, findings) accumulates in the main context window
- Dimensions are reviewed sequentially, even though they are fully independent
- A large PR review can exhaust or pollute the context before all dimensions are covered

`skills/code-review/reference.md` already proves this pattern works: 5 specialized parallel subagents, each with a clean, scoped context, consolidated into a single report.

---

## Goal

Refactor the `code-review` skill to orchestrate 7 specialized subagents in parallel, each scoped to one review dimension, with the orchestrator responsible only for context collection, dispatch, and consolidation.

---

## Requirements

### REQ-01 — Upfront context collection

Before spawning any subagent, the orchestrating agent MUST collect all context in one pass:

- `git diff HEAD` (or PR diff via `gh pr diff`) — full diff
- Changed file list (from `git diff --name-only` or PR files)
- All applicable `.specs/codebase/` files (load if they exist, skip gracefully if absent):
  - `STACK.md` — tech stack and language/framework patterns (all agents)
  - `ARCHITECTURE.md` — system layers and component boundaries (`architecture-reviewer`)
  - `CONVENTIONS.md` — naming, style, error handling (`code-quality-reviewer`, `docs-comments-reviewer`)
  - `TESTING.md` — gate check commands and test patterns (`build-test-validator`)
  - `CONCERNS.md` — known fragile areas and tech debt (all agents)
  - `INTEGRATIONS.md` — external service surface area (`security-reviewer`, `performance-reviewer`)
  - `STRUCTURE.md` — directory layout for file location context (all agents)
- Tech debts: `docs/TECH_DEBTS.md` (if exists)
- Applicable checklists per dimension (loaded once, distributed as slices)

Each agent receives only the slice of the above that is relevant to its domain (see REQ-02 and REQ-03).

### REQ-02 — 7 specialized subagents

The following agents MUST be dispatched in parallel (single message, never sequentially):

| Agent | Scope | Context it receives |
|-------|-------|---------------------|
| `architecture-reviewer` | Layer violations, coupling, pattern misuse | Diff slices + ARCHITECTURE.md |
| `code-quality-reviewer` | Naming, complexity, SOLID, DRY, KISS, clean code | Diff slices + clean-code + best-practices checklists |
| `security-reviewer` | Auth, injection, secrets, data exposure | Diff slices + security checklist |
| `performance-reviewer` | N+1, allocations, blocking calls, missing indexes | Diff slices + performance checklist |
| `docs-comments-reviewer` | Inline docs, API docs, obsolete/misleading comments | Diff slices + docs checklist |
| `build-test-validator` | Run gate check commands, verify tests pass | Branch name + gate commands from TESTING.md |
| `requirements-tracer` | Does the change satisfy the spec/task asked for | Diff + spec.md or task description (if available) |

### REQ-03 — Minimal context per subagent

Each subagent receives ONLY what its dimension needs. The orchestrator MUST NOT pass the full diff to all agents indiscriminately — send only the file slices relevant to each agent's domain.

### REQ-04 — Structured return schema

Each subagent MUST return a structured result in this format:

```
Status: Complete | Blocked | Partial
Dimension: <agent name>
Findings: [{severity, title, file, line, explanation, recommendation}]
Files reviewed: [list]
Gate check: pass | fail | skipped — <detail>
Issues: <any blockers encountered>
```

### REQ-05 — Mandatory parallelism

All 7 agents are independent. They MUST be fired in a single parallel dispatch. The orchestrator MUST NOT proceed to consolidation until all agents return (or timeout/fail with a fallback marker).

### REQ-06 — Fallback handling

If a subagent fails or is unavailable:

- Mark its dimension as `⚠️ not executed — <reason>`
- Continue consolidation with the remaining dimensions
- Never block the full review because one agent failed

### REQ-07 — Consolidation and output

After all agents return, the orchestrator consolidates into the existing skill output formats:

- **At-a-glance table**: one row per dimension (Status / Finding count / Summary)
- **Flat format** (small reviews): single findings table — unchanged from current skill
- **Zoned format** (large reviews): per-dimension sections — agents map directly to zones
- Finding IDs, severity, priority, and status behavior remain unchanged

### REQ-08 — Diff in output

The consolidated report MUST include the diff summary:

- Total files changed, insertions, deletions (from `git diff --stat`)
- Diff is NOT reprinted in full — it is the input, not the output
- Each finding MUST reference the specific file:line from the diff

### REQ-09 — Mode compatibility

The subagent strategy applies to all existing review modes:

- **Local workspace**: diff from `git diff HEAD`
- **GitHub PR**: diff from `gh pr diff <PR#>`
- **Performance Audit**: architecture + performance agents run full-codebase; others run on changed files only
- **Multi-commit**: defined separately in REQ-12

### REQ-10 — Quick mode exemption

When the changed file count is ≤ 2 and the diff is < 100 lines, the skill MAY fall back to inline review (no subagents) to avoid orchestration overhead. This must be an explicit check at Step 1.

### REQ-11 — Context availability check

Before dispatch, the orchestrator MUST verify that each agent's required context items exist. If a required item is absent:

- The affected agent runs in **degraded mode** — it proceeds without that item and notes the gap in its findings
- The agent is NOT skipped entirely
- The at-a-glance table marks that dimension as `⚠️ degraded — <missing item>`

Examples:
- No `ARCHITECTURE.md` → `architecture-reviewer` runs on diff only, flags "no architecture reference available"
- No `spec.md` or task description → `requirements-tracer` skips gracefully (treated as REQ-06 fallback, not degraded)
- No `TESTING.md` → `build-test-validator` falls back to standard commands (`npm test`, `pytest`, etc.) or marks as `⚠️ degraded — no gate commands`

### REQ-12 — Multi-commit review mode

When the user provides a set of commit hashes or a commit range (e.g. "review commits abc123, def456" or "review commits abc..def"), the skill operates in **multi-commit mode**:

- All commit diffs are collected upfront and **aggregated into a single combined diff** before dispatch:
  - Individual hashes: `git show <hash>` per commit, concatenated
  - Range: `git diff <base>..<tip>` — the cumulative diff across the range
- The 7-subagent pipeline runs **once** against the combined diff — no per-commit pipelines
- A single consolidated report is produced (flat or zoned, per existing rules)
- The report header lists the commits included (hash + subject line) so findings can be traced back to their origin
- Trigger phrases: "review commits X Y Z", "review commits X..Y", "review last N commits", or a space/comma-separated list of hashes following "review"
- The quick mode exemption (REQ-10) applies to the combined diff (total lines across all commits)

---

## Out of Scope

- Changing the finding format (severity, priority, type, status labels)
- Adding new review dimensions beyond the 7 defined
- Modifying the `reference.md` file (it remains as-is)
- Changing how findings are posted to GitHub (Step 8 is unchanged)
- Modifying the `tests-code-review` skill

---

## Success Criteria

- [ ] All 7 subagents fire in parallel for any review with > 2 files or > 100 diff lines
- [ ] Each subagent's context contains only its domain-relevant slice of `.specs/codebase/` + diff
- [ ] All 7 `.specs/codebase/` files are loaded upfront when present; absent files skip gracefully
- [ ] Consolidated output matches current flat/zoned format — no regressions in structure
- [ ] A failed subagent does not block the report
- [ ] An agent with missing required context runs in degraded mode and surfaces a warning in the at-a-glance table
- [ ] `git diff --stat` summary appears at the top of every consolidated report
- [ ] Requirements-tracer agent runs when a spec or task description is available; skips gracefully when not
- [ ] "review commits X Y" / "review commits X..Y" triggers multi-commit mode: aggregated diff → single 7-subagent pipeline → single consolidated report with commit list in header
