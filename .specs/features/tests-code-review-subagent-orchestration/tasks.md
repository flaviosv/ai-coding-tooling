# Tasks — Tests Code Review Subagent Orchestration (TCR-SUBAGENT)

**Spec:** [spec.md](spec.md)  
**Pattern reference:** CR-SUBAGENT (`skills/code-review/SKILL.md`) — same orchestration model, adapted dimensions  
**Target file:** `skills/tests-code-review/SKILL.md`  
**Status:** Ready

---

## Task Index

| ID | Title | Depends on | Status |
|----|-------|------------|--------|
| T01 | Rewrite Steps 1–5: mode detection, context collection, availability map, diff collection, quick mode check | — | Pending |
| T02 | Write Step 6: parallel dispatch + 5 agent roster + prompt template + return schema | T01 | Pending |
| T03 | Write Steps 7–8: await/fallback, consolidation (report header + at-a-glance table + zone letters), GitHub posting | T02 | Pending |
| T04 | Update examples: update existing 2 + add multi-commit example | T03 | Pending |

All tasks are sequential — same file, each section builds on the previous.

---

## T01 — Rewrite Steps 1–5

**What:** Replace the current Steps 1–4 with the orchestrator's five pre-flight steps.

**Where:** `skills/tests-code-review/SKILL.md` — from the top of the step-by-step section through the end of the old Step 4 (Collect Changed Files).

**Covers:** REQ-01, REQ-07 (availability map), REQ-08 (quick mode), REQ-10 (multi-commit triggers), REQ-11 (modes)

**Content to produce:**

- **Step 1 — Mode Detection:** priority-ordered table: Multi-commit → GitHub PR → Local workspace (no Performance Audit mode). Multi-commit triggers: "review test commits X Y Z", "review test commits X..Y", "review last N test commits".
- **Step 2 — Context Collection:** load all 7 `.specs/codebase/` files (adding `CONCERNS.md`, `INTEGRATIONS.md`, `STRUCTURE.md` which are currently absent) + mandatory checklist + tech-specific checklist + `docs/TECH_DEBTS.md`. Each item: load if present, note as absent if not. Fallback paths unchanged.
- **Step 3 — Context Availability Map + Bundle Assembly:** build availability map (10 fields). Assemble per-agent context bundles using only present items relevant to each agent's dimension. Flag missing required items as `degraded`. `TESTING.md` absent → `isolation-reviewer` and `performance-reviewer` run degraded, fall back to inferring framework from `STACK.md` or file patterns.
- **Step 4 — Diff Collection:** same table as CR-SUBAGENT for Local / GitHub PR / Multi-commit (hashes) / Multi-commit (range). Filter to test files in all modes. Collect `git diff --stat` and changed test file list. Multi-commit: also collect commit list (hash + subject).
- **Step 5 — Quick Mode Check:** condition is ≤ 5 test files **AND** < 100 total diff lines (higher threshold than CR-SUBAGENT). If triggered: skip Steps 6–7; fall back to inline review. In multi-commit mode: apply to combined diff totals.

**Done when:**
- [ ] Step 1 lists 3 modes in priority order (multi-commit before GitHub PR) with correct trigger phrases
- [ ] Step 2 lists all 10 context items including `CONCERNS.md`, `INTEGRATIONS.md`, `STRUCTURE.md`
- [ ] Step 3 defines availability map and per-agent bundle assembly; `TESTING.md` degraded fallback is explicit
- [ ] Step 4 has diff commands for all 3 modes with test-file filter noted
- [ ] Step 5 uses ≤ 5 files / < 100 lines threshold (not ≤ 2 as in CR-SUBAGENT)

---

## T02 — Write Step 6: Parallel Dispatch

**What:** Write the parallel dispatch section with the 5 test-dimension agents.

**Where:** `skills/tests-code-review/SKILL.md` — Step 6 section, replacing the old "Step 5: Review All Test Files".

**Depends on:** T01

**Covers:** REQ-02, REQ-03, REQ-04, REQ-05

**Content to produce:**

- Opening rule: "All 5 agents MUST be fired in a single parallel message. Never sequentially."
- **Prompt template structure** (4 sections per agent — same as CR-SUBAGENT):
  ```
  ## Role
  ## Context   ← inlined content from bundle (present items only)
  ## Diff      ← full test-file diff (all agents receive it; scoping is in context, not code)
  ## Return format
  ```
- **Agent roster table:** 5 rows — `clarity-reviewer`, `coverage-reviewer`, `isolation-reviewer`, `maintainability-reviewer`, `performance-reviewer` — with Dimension / Required context / Optional context / Degrades without columns (from spec REQ-02).
- **Return schema** (REQ-04) reproduced inline so it can be injected into each agent's prompt.
- **Reviewer stance** (injected into every agent): villain stance from current SKILL.md — "weak tests are worse than no tests", flag every gap, state problems directly.
- **Quick mode inline fallback** note: when Step 5 triggers, skip dispatch and apply all 5 dimensions inline without agents.

**Done when:**
- [ ] Mandatory parallelism rule is explicit and prominent
- [ ] 4-section prompt template is defined for all agents
- [ ] Agent roster table lists all 5 agents with correct context bundle specs matching spec REQ-02
- [ ] Return schema is reproduced for inline injection
- [ ] Reviewer stance (villain) is included for injection into every agent

---

## T03 — Write Steps 7–8: Await, Consolidation, GitHub Posting

**What:** Write the post-dispatch steps — await/fallback, consolidation into report, and GitHub posting.

**Where:** `skills/tests-code-review/SKILL.md` — Steps 7 and 8 sections, replacing old Steps 6–8.

**Depends on:** T02

**Covers:** REQ-06, REQ-07, REQ-09

**Content to produce:**

- **Step 7 — Await + Fallback:** 4-outcome table (returned normally / failed+timed out / degraded / n/a). Status markers: ✅ / ⚠️ not executed / ⚠️ degraded.
- **Step 8 — Consolidation:**
  - **Report header** (always first):
    ```
    # <branch or TASK-ID> — Test Code Review
    Scope: <test files reviewed>
    Branch: <branch>
    Commits: <hash — subject>, ...   ← multi-commit mode only
    Diff: <N files changed, +X insertions, -Y deletions>
    Run: <date>
    Mode: local | GitHub PR #N | multi-commit
    ```
  - **At-a-glance table** (always second): Dimension / Status / Findings / Critical / High / Summary. One row per agent.
  - **Output format selection:** flat (few findings) vs zoned (many/multi-zone). Zone letter assignment: C=Clarity, V=Coverage, I=Isolation, M=Maintainability, P=Performance. Finding IDs: `<Letter><N>` (e.g. `C1`, `V3`). Status/severity/priority/type labels unchanged.
  - Iterative review behaviour unchanged.
- **Step 9 — Post to GitHub** (GitHub PR mode only): content identical to current Step 8 — renumbered only.

**Done when:**
- [ ] Step 7 covers all outcome states with correct status markers
- [ ] Report header includes diff stat line and multi-commit commit-list variant
- [ ] At-a-glance table has correct columns and 5 agent rows
- [ ] Zone letters C/V/I/M/P are defined and used for finding IDs
- [ ] Step 9 content matches current Step 8 verbatim (renumber only)

---

## T04 — Update Examples

**What:** Update both existing examples to reference the new step numbering and add a multi-commit example.

**Where:** `skills/tests-code-review/SKILL.md` — Examples section.

**Depends on:** T03

**Covers:** REQ-10, REQ-11

**Content to produce:**

- **Example 1 (local workspace):** update step references to 8-step flow; note quick mode exemption threshold (≤ 5 files).
- **Example 2 (GitHub PR):** update step references; note parallel dispatch of 5 agents.
- **Example 3 (multi-commit) — new:** "review test commits abc123 def456" → Step 1 detects multi-commit → Step 4 aggregates test-file diffs → Step 6 dispatches 5 agents against combined diff → Step 8 single report with commit list in header.

**Done when:**
- [ ] Examples 1–2 reference correct step numbers matching the new 8-step flow
- [ ] Example 3 exists and covers trigger, diff aggregation, and single-report output
- [ ] No example references old step numbering (old Steps 5/6/7/8 = new Steps 6/7/8/9)
