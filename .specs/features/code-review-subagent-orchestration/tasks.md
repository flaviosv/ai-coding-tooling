# Tasks — Code Review Subagent Orchestration (CR-SUBAGENT)

**Spec:** [spec.md](spec.md) | **Design:** [design.md](design.md)  
**Target file:** `skills/code-review/SKILL.md`  
**Status:** Ready

---

## Task Index

| ID | Title | Depends on | Status |
|----|-------|------------|--------|
| T01 | Rewrite Steps 1–5: mode detection, context collection, availability map, diff collection, quick mode check | — | Pending |
| T02 | Write Step 6: parallel dispatch + 7 agent context bundle definitions + prompt template structure | T01 | Pending |
| T03 | Write Steps 7–9: await/fallback, consolidation, GitHub posting | T02 | Pending |
| T04 | Update Examples section to reflect new 9-step flow | T03 | Pending |

All tasks are sequential — same file, each section builds on the previous.

---

## T01 — Rewrite Steps 1–5

**What:** Replace the current Steps 1–4 in SKILL.md with the orchestrator's first five steps.

**Where:** `skills/code-review/SKILL.md` — from the top of the step-by-step section to just before the review execution content.

**Covers:** REQ-01, REQ-04 (mode detection), REQ-09, REQ-10, REQ-11, REQ-12

**Content to produce:**

- **Step 1 — Mode Detection:** priority-ordered table (Performance Audit → Multi-commit → GitHub PR → Local workspace). Multi-commit triggers: "review commits X Y Z", "review commits X..Y", "review last N commits".
- **Step 2 — Context Collection:** load all 7 `.specs/codebase/` files + all mandatory checklists + tech-specific checklists + `docs/TECH_DEBTS.md` + active spec/task description. Each item: load if present, note as absent if not. Fallback paths (`docs/codebase/` → `docs/`) unchanged.
- **Step 3 — Context Availability Map + Bundle Assembly:** build the `availability` map (14 fields from design.md). Assemble per-agent context bundles using only present items relevant to each agent (agent roster table from design.md). Flag missing required items as `degraded` for that agent.
- **Step 4 — Diff Collection:** per-mode commands table from design.md. Collect `git diff --stat` and changed file list. Multi-commit: concatenate `git show <hash>` per hash, or `git diff <base>..<tip>` for ranges. Also collect commit list (hash + subject) for report header.
- **Step 5 — Quick Mode Check:** explicit condition (≤ 2 files AND < 100 total diff lines). If triggered: skip to legacy inline review (former Steps 5–7). In multi-commit mode: apply to combined diff total.

**Done when:**
- [ ] Step 1 enumerates all 4 modes in priority order including multi-commit triggers
- [ ] Step 2 lists all 14 context items with load/skip behaviour and fallback paths
- [ ] Step 3 defines the availability map structure and per-agent bundle assembly rules
- [ ] Step 4 has diff commands for all modes including multi-commit variants
- [ ] Step 5 has the explicit numeric gate and the fallback path clearly stated

---

## T02 — Write Step 6: Parallel Dispatch

**What:** Write the parallel dispatch section — the orchestration boundary where all 7 agents are fired simultaneously.

**Where:** `skills/code-review/SKILL.md` — Step 6 section.

**Depends on:** T01

**Covers:** REQ-02, REQ-03, REQ-05

**Content to produce:**

- Opening rule: "All 7 agents MUST be fired in a single parallel message. Never sequentially."
- **Prompt template structure** (4 sections per agent):
  ```
  ## Role
  ## Context   ← inlined content from bundle (present items only)
  ## Diff      ← full diff (all agents receive full diff — scoping is in context, not code)
  ## Return format  ← structured schema from REQ-04
  ```
- **Agent roster table** with: Agent name | Dimension | Required context | Optional context | Degrades without — pulled from design.md agent bundle definitions.
- **Return schema** (REQ-04) reproduced inline so agents have it in their prompt:
  ```
  Status: Complete | Blocked | Partial
  Dimension: <agent name>
  Findings: [{severity, title, file, line, explanation, recommendation}]
  Files reviewed: [list]
  Gate check: pass | fail | skipped — <detail>
  Issues: <any blockers encountered>
  ```
- Note on `requirements-tracer`: if `requirements` is absent from availability map, this agent is not dispatched (REQ-06 fallback, not degraded mode).

**Done when:**
- [ ] Mandatory parallelism rule is explicit and prominent
- [ ] Prompt template structure (4 sections) is defined for all agents
- [ ] Agent roster table lists all 7 agents with their context bundle specs
- [ ] Return schema is reproduced so it can be injected into each agent's prompt
- [ ] `requirements-tracer` skip condition is clearly stated

---

## T03 — Write Steps 7–9: Await, Consolidation, GitHub Posting

**What:** Write the post-dispatch steps — waiting for results, fallback handling, consolidation into the report, and GitHub posting.

**Where:** `skills/code-review/SKILL.md` — Steps 7, 8, 9 sections.

**Depends on:** T02

**Covers:** REQ-06, REQ-07, REQ-08, REQ-11

**Content to produce:**

- **Step 7 — Await + Fallback:** outcome handling table (returned normally / failed+timed out / degraded / requirements-tracer skipped). Status markers: ✅ / ⚠️ not executed / ⚠️ degraded / ➖ skipped.
- **Step 8 — Consolidation:**
  - **Report header** (always first):
    ```
    # <TASK-ID or branch> — Code Review
    Scope: <files reviewed>
    Branch: <branch> | Commits: <hash list + subjects>  (multi-commit only)
    Diff: <N files changed, +X -Y lines>          (from git diff --stat)
    Run: <date>
    Mode: <local | GitHub PR #N | multi-commit | performance audit>
    ```
  - **At-a-glance table** (always second): columns = Dimension / Status / Findings / Critical / High / Summary. One row per agent. Build/Tests and Requirements rows use "—" for finding counts.
  - **Output format selection:** flat (few findings, single area) vs zoned (many findings or multi-zone). Zone letter assignment: A=Architecture, Q=Quality, S=Security, P=Performance, D=Docs, B=Build, R=Requirements.
  - Finding IDs: `<ZoneLetter><N>` within each zone (e.g. A1, Q3, S2). Status, severity, priority labels unchanged.
- **Step 9 — Post to GitHub:** content unchanged from current SKILL.md Step 8 — renumbered only.

**Done when:**
- [ ] Step 7 covers all four outcome states with correct status markers
- [ ] Report header includes diff stat line and mode field; multi-commit variant shows commit list
- [ ] At-a-glance table structure is defined with correct columns and row variants for each agent type
- [ ] Zone letter scheme is defined and consistent with agent roster
- [ ] Step 9 content is identical to current Step 8 (verify by diffing)

---

## T04 — Update Examples Section

**What:** Update the three examples at the bottom of SKILL.md to reference the new 9-step flow.

**Where:** `skills/code-review/SKILL.md` — Examples section.

**Depends on:** T03

**Covers:** REQ-09, REQ-12

**Content to produce:**

- **Example 1 (local workspace):** update step references to match new numbering; add quick mode exemption note.
- **Example 2 (GitHub PR):** update step references; note that Step 6 fires all 7 agents in parallel.
- **Example 3 (performance audit):** update step references; note which agents run full-codebase vs changed files only.
- **Example 4 (multi-commit) — new:** "review commits abc123 def456 ghi789" → Step 1 detects multi-commit → Step 4 aggregates diffs → Step 6 dispatches 7 agents against combined diff → Step 8 consolidates into single report with commit list in header.

**Done when:**
- [ ] Examples 1–3 reference step numbers that match the new 9-step flow
- [ ] Example 4 exists and covers the multi-commit trigger, diff aggregation, and single-report output
- [ ] No example references the old step numbering (Steps 5/6/7/8 in old = Steps 6/7/8/9 in new)
