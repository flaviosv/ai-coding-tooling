# Feature Spec — Tests Code Review Subagent Orchestration

**Feature ID:** TCR-SUBAGENT  
**Status:** Abandoned — superseded  
**Skill target:** `skills/tests-code-review/SKILL.md`  
**Parent pattern:** CR-SUBAGENT (`skills/code-review/SKILL.md`) — same orchestration architecture, adapted for test review dimensions

> **Superseded (2026-08-08):** this spec's binary quick-mode/full-parallel migration predates and was overtaken by the 4-tier complexity-routing system since implemented directly in `skills/tests-code-review/SKILL.md` (TCR-TOKEN, status Implemented). It never covered tier-level granularity (Small/Medium/Large/Complex) and does not address the Medium-tier single-agent regression fixed the same day. Follow-on token-efficiency work (dimension merges, content-type-detection parity with `code-review`, `ship-spec` dispatcher-wrapper fix) is tracked in a new spec from that session instead of here.

---

## Problem

The current `tests-code-review` SKILL.md runs all review dimensions inline and sequentially, in the main agent context — the same structural problem solved in CR-SUBAGENT. Additionally:

- Only 5 of the 7 `.specs/codebase/` files are loaded (`CONCERNS.md` is missing entirely)
- No graceful degraded mode when context files are absent
- No quick mode exemption for small test diffs
- No diff stat in report header
- No per-dimension at-a-glance table before findings
- No multi-commit mode

---

## Goal

Restructure `tests-code-review` to use the same orchestrator + parallel subagent pattern established in CR-SUBAGENT, adapted to the 5 test review dimensions, with a higher quick-mode threshold appropriate for test file scope.

---

## Requirements

### REQ-01 — Upfront context collection

Before spawning any subagent, the orchestrating agent MUST collect all context in one pass. All `.specs/codebase/` files are in scope (not just the 5 currently loaded):

| File | Availability key | Notes |
|------|-----------------|-------|
| `STACK.md` | `stack` | Tech stack, frameworks |
| `ARCHITECTURE.md` | `architecture` | Layers the tests cover |
| `CONVENTIONS.md` | `conventions` | Naming conventions for test code |
| `TESTING.md` | `testing` | Test frameworks, gate commands, coverage matrix |
| `CONCERNS.md` | `concerns` | Fragile areas and known test debt — **currently missing** |
| `INTEGRATIONS.md` | `integrations` | External service mocks and integration patterns |
| `STRUCTURE.md` | `structure` | Directory layout for locating test files |
| `docs/TECH_DEBTS.md` | `tech_debts` | Known anti-patterns to flag in test code |
| `references/test-review-checklist.md` | `checklist_baseline` | Always loaded |
| `references/<stack>-*-tests-code-review.md` (if match) | `checklist_tech_specific` | Stack-specific only |

Fallback paths unchanged: `.specs/codebase/` → `docs/codebase/` → `docs/`.

### REQ-02 — 5 specialized subagents

The following agents MUST be dispatched in parallel (single message, never sequentially):

| Agent | Dimension | Required context | Optional context | Degrades without |
|-------|-----------|-----------------|------------------|-----------------|
| `clarity-reviewer` | Test naming, AAA structure, focus, readability as docs | `checklist_baseline` (clarity section) | `conventions`, `stack` | `conventions` |
| `coverage-reviewer` | Happy path, error paths, edge cases, integration points, access control | `checklist_baseline` (coverage section) | `architecture`, `stack`, `concerns` | — |
| `isolation-reviewer` | Shared state, ordering, mocks, determinism, external deps | `checklist_baseline` (isolation section) | `testing`, `integrations`, `stack` | — |
| `maintainability-reviewer` | Helpers, data-driven patterns, mock minimalism, update cost | `checklist_baseline` (maintainability section) | `conventions`, `stack`, `checklist_tech_specific` | — |
| `performance-reviewer` | I/O in unit tests, sleep/polling, test suite speed, separation | `checklist_baseline` (performance section) | `testing`, `stack` | — |

### REQ-03 — Minimal context per subagent

Each subagent receives ONLY the context bundle relevant to its dimension — not all loaded docs. The full diff is passed to all agents (same rationale as CR-SUBAGENT: test coverage issues can be in any file).

### REQ-04 — Structured return schema

Each subagent MUST return:

```
Status: Complete | Blocked | Partial
Dimension: <agent name>
Findings: [{severity, title, file, line, explanation, recommendation}]
Files reviewed: [list]
Gate check: pass | fail | skipped — <detail>
Issues: <any blockers encountered>
```

### REQ-05 — Mandatory parallelism

All 5 agents are independent. They MUST be fired in a single parallel dispatch. The orchestrator MUST NOT proceed to consolidation until all return (or fail with a fallback marker).

### REQ-06 — Fallback handling

If a subagent fails or is unavailable:

- Mark its dimension as `⚠️ not executed — <reason>`
- Continue consolidation with the remaining dimensions
- Never block the full review because one agent failed

### REQ-07 — Context availability check

Before dispatch, the orchestrator MUST verify each agent's required context items exist. If a required item is absent:

- The agent runs in **degraded mode** — proceeds without that item, notes the gap in findings
- The at-a-glance table marks that dimension as `⚠️ degraded — <missing item>`
- `TESTING.md` absent → `isolation-reviewer` and `performance-reviewer` run degraded; fall back to inferring test framework from `STACK.md` or file patterns

### REQ-08 — Quick mode exemption

When the changed test file count is ≤ 5 **AND** total diff lines < 100:

- Skip subagent dispatch; fall back to inline review across all 5 dimensions
- In multi-commit mode: apply to combined diff totals

The threshold is higher than CR-SUBAGENT (5 files vs 2) because test files are typically narrower in scope.

### REQ-09 — Consolidation and output

After all agents return:

**Report header (always first):**
```
# <branch or TASK-ID> — Test Code Review
Scope: <test files reviewed>
Branch: <branch>
Commits: <hash — subject>, ...   ← multi-commit mode only
Diff: <N files changed, +X insertions, -Y deletions>
Run: <date>
Mode: local | GitHub PR #N | multi-commit
```

**At-a-glance table (always second):**

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Clarity | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Coverage | ... | N | N | N | 1-line |
| Isolation | ... | N | N | N | 1-line |
| Maintainability | ... | N | N | N | 1-line |
| Performance | ... | N | N | N | 1-line |

**Output format selection:** same rules as current skill — flat for few findings, zoned for many. Zone letter assignment:

| Zone | Letter | Agent |
|------|--------|-------|
| Clarity | C | `clarity-reviewer` |
| Coverage | V | `coverage-reviewer` |
| Isolation | I | `isolation-reviewer` |
| Maintainability | M | `maintainability-reviewer` |
| Performance | P | `performance-reviewer` |

Finding IDs: `<ZoneLetter><N>` (e.g. `C1`, `V3`, `I2`). Severity, priority, type, status labels unchanged.

### REQ-10 — Multi-commit mode

When the user provides commit hashes or a range (e.g. "review test commits abc123 def456"):

- All commit diffs aggregated into one combined diff (`git show` per hash or `git diff <base>..<tip>`)
- Single 7-subagent pipeline runs against the combined diff
- Single consolidated report with commit list in header
- Trigger phrases: "review test commits X Y Z", "review test commits X..Y", "review last N test commits"

### REQ-11 — Mode compatibility

The subagent strategy applies to all supported modes:

- **Local workspace**: diff from `git diff HEAD` (test files only)
- **GitHub PR**: diff from `gh pr diff <PR#>` (test files only)
- **Multi-commit**: defined in REQ-10

No performance audit mode — not applicable to test review.

---

## Out of Scope

- Adding new review dimensions beyond the 5 defined
- Changing finding severity/priority/type/status labels
- Modifying the `code-review` skill (separate feature)
- Changing GitHub PR posting behaviour (Step 8 renumbered, content unchanged)

---

## Success Criteria

- [ ] All 5 subagents fire in parallel for test reviews with > 5 files or ≥ 100 diff lines
- [ ] `CONCERNS.md` is loaded as part of upfront context collection
- [ ] Missing context items trigger degraded mode, not silent skip
- [ ] Report header includes `git diff --stat` summary
- [ ] At-a-glance table appears before findings in every report
- [ ] Zone letters C/V/I/M/P used for finding IDs
- [ ] Quick mode exemption triggers at ≤ 5 test files AND < 100 lines
- [ ] Multi-commit mode aggregates diffs and produces a single report
