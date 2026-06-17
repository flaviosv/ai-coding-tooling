# Tests Code Review Token Efficiency — Tasks

**Spec:** [spec.md](spec.md) — Feature ID: TCR-TOKEN  
**Target file:** `skills/tests-code-review/SKILL.md` (only file modified)  
**Status:** Complete

---

## Testing note

All tasks edit a markdown skill file. Per project CLAUDE.md ("do not apply test-coverage heuristics to `.md` files"), verification is grep/structural inspection. `Tests: none` is correct for all tasks.

**Tools (all tasks):** `Edit`, `Read`, `Grep`/`Bash` (grep verification). No MCPs. No skills.

---

## Execution Plan

All tasks edit the same file → sequential, top-down by document position.

```
T1 ──→ T2 ──→ T3 ──→ T4 ──→ T5 ──→ T6
```

No parallel-safe tasks (unlike CR-TOKEN — no separate reference file to modify).

---

## Task Breakdown

### T1: Steps 2 + 3 — availability-map-only; purge tech_debts

**What:** Convert Step 2 to record presence/absence only (no content loading). Simplify Step 3 to availability-map only (remove bundle-assembly language). Remove `docs/TECH_DEBTS.md` row and `tech_debts` key.  
**Where:** `skills/tests-code-review/SKILL.md` — Step 2 (Context Collection), Step 3 (Context Availability Map)  
**Depends on:** None (first in chain)  
**Requirement:** TCR-TOKEN-12, TCR-TOKEN-15, TCR-TOKEN-16

**Done when:**
- [ ] Step 2 instructs checking presence/absence only — no content loading from `references/` or `.specs/codebase/`
- [ ] `docs/TECH_DEBTS.md` row and `tech_debts` key removed from Step 2
- [ ] Step 3 availability map has exactly 9 keys (`architecture`, `concerns`, `conventions`, `integrations`, `stack`, `structure`, `testing`, `checklist_baseline`, `checklist_tech_specific`) — no `tech_debts`
- [ ] Step 3 states orchestrator holds map only; agents self-load via `## Before You Begin` in Step 6
- [ ] Bundle-assembly language ("context bundle", "structured text block injected") removed from Step 3

**Verify:**
```bash
grep -ni "tech_debt" skills/tests-code-review/SKILL.md              # → 0
grep -ni "context bundle\|injected\|structured text" skills/tests-code-review/SKILL.md  # → 0 in Steps 2-3
grep -ni "Before You Begin" skills/tests-code-review/SKILL.md       # present (Step 3 cross-reference)
```

**Tests:** none **Gate:** inspection  
**Commit:** `refactor(tests-code-review): orchestrator holds availability map only; drop tech_debts`

---

### T2: Step 4 — EXCLUDE constant + apply to both diffs

**What:** Define the EXCLUDE pathspec constant (full union of CR-TOKEN's list + test-specific noise). Apply it to every git command in the test diff table AND the `impl_diff` collection. Capture `excluded_count`.  
**Where:** `skills/tests-code-review/SKILL.md` — Step 4 (Diff Collection)  
**Depends on:** T1  
**Requirement:** TCR-TOKEN-01, TCR-TOKEN-02, TCR-TOKEN-03

**Done when:**
- [ ] EXCLUDE constant defined before the mode table — containing the full lockfile list, minified/built/generated, AND test-specific noise (`__snapshots__/**`, `*.snap`, `coverage/**`, `.nyc_output/**`)
- [ ] Every `git diff`/`git show` command in the test-diff table applies `-- $EXCLUDE`
- [ ] GitHub PR mode explicitly filters excluded paths from the changed-file list
- [ ] `impl_diff` collection section applies EXCLUDE (not just a filter instruction)
- [ ] Step 4 captures `excluded_count` for use in report header
- [ ] EXCLUDE referenced once — not duplicated per mode

**Verify:**
```bash
grep -ni "EXCLUDE" skills/tests-code-review/SKILL.md | head          # constant + per-mode references
grep -ni "excluded_count\|excluded" skills/tests-code-review/SKILL.md  # count captured
grep -ni "snapshots\|\.snap\|coverage\|nyc" skills/tests-code-review/SKILL.md  # test-specific noise present
```

**Tests:** none **Gate:** inspection  
**Commit:** `feat(tests-code-review): exclude lockfiles/snapshots/coverage from diff at collection`

---

### T3: Step 5 — Complexity Assessment replaces Quick Mode Check

**What:** Replace the binary Quick Mode Check with the 4-tier Complexity Assessment step. Add Review Plan block, complexity banner requirement, and silent-operation rule.  
**Where:** `skills/tests-code-review/SKILL.md` — Step 5  
**Depends on:** T2 (post-exclusion metrics feed the size tier)  
**Requirement:** TCR-TOKEN-04, TCR-TOKEN-05, TCR-TOKEN-06, TCR-TOKEN-09, TCR-TOKEN-10

**Done when:**
- [ ] "Quick Mode Check" heading and binary logic replaced by "Review Complexity Assessment"
- [ ] Size-tier table present with all 4 tiers, exact thresholds, and "top-down, first match wins" rule: Small (≤5 OR <200 → inline), Medium (≤15 AND <800 → single agent), Large (≤25 AND <1,500 → parallel), Complex (>25 OR ≥1,500 → parallel + caveat)
- [ ] Review Plan block defined (tier, mode, dimensions, agent count, gap-detector status, Complex flag, excluded count)
- [ ] Complexity banner specified (prints before any dispatch/inline review, all modes/tiers, with exact format)
- [ ] Silent-operation rule stated: only 3 user-facing outputs (skill invocation → banner → final report)
- [ ] Medium tier gap-detector fold described: receives both diffs when `impl_diff` non-empty

**Verify:**
```bash
grep -ni "Quick Mode Check" skills/tests-code-review/SKILL.md        # → 0
grep -ni "Small\|Medium\|Large\|Complex" skills/tests-code-review/SKILL.md | head
grep -ni "Review Plan\|complexity banner\|silent" skills/tests-code-review/SKILL.md
```

**Tests:** none **Gate:** inspection  
**Commit:** `feat(tests-code-review): complexity assessment routing (4 tiers) + banner`

---

### T4: Step 6 — dispatch rework (modes, self-loading, lean returns)

**What:** Rework dispatch to execute per the size tier's mode. Add `## Before You Begin` block to prompt template (checklists + codebase docs). Update agent roster (remove Required/Optional context columns that implied bundle injection; reflect self-loading). Strip `Files reviewed` from return format. Remove "Tech Debt Recurrence" injection block. Describe gap-detector Medium-fold mechanics.  
**Where:** `skills/tests-code-review/SKILL.md` — Step 6 (Parallel Subagent Dispatch), prompt template, Agent Roster, return format, Tech Debt Recurrence block  
**Depends on:** T3 (tiers/execution modes)  
**Requirement:** TCR-TOKEN-07, TCR-TOKEN-08, TCR-TOKEN-11, TCR-TOKEN-13, TCR-TOKEN-14

**Done when:**
- [ ] Opening dispatch rule describes 4 execution modes and which to use per size tier
- [ ] Inline mode (Small): orchestrator applies all dimensions directly; gap-detector inline if `impl_diff` non-empty
- [ ] Single-agent mode (Medium): ONE subagent, all dimensions; receives test diff + impl_diff if non-empty; agent self-loads union of checklists + full 7-doc codebase set
- [ ] Parallel mode (Large/Complex): one agent per active dimension; Complex adds thoroughness directive
- [ ] `## Before You Begin` block in prompt template: checklists (`test-review-checklist.md` + tech-specific if present) + full 7-doc codebase set — all filtered to present files
- [ ] gap-detector's `## Before You Begin` lists only `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md`; no checklist
- [ ] Return format has NO `Files reviewed: [list]` — findings only
- [ ] "Tech Debt Recurrence" injection block removed
- [ ] Agent Roster updated to reflect self-loading (Required/Optional context columns simplified to "Self-loads" description)

**Verify:**
```bash
grep -ni "Files reviewed\|Tech Debt Recurrence\|tech_debt" skills/tests-code-review/SKILL.md  # → 0
grep -ni "Before You Begin" skills/tests-code-review/SKILL.md   # present in Step 6 template
grep -ni "thoroughness\|second.pass" skills/tests-code-review/SKILL.md  # thoroughness present; second-pass → 0
```

**Tests:** none **Gate:** inspection  
**Commit:** `feat(tests-code-review): execution-mode dispatch + agent self-loading + lean returns`

---

### T5: Step 8 — consolidation header notes + silent operation

**What:** Update the report header to display excluded-file count; add Complex completeness caveat to header; add silent-operation rule to consolidation step.  
**Where:** `skills/tests-code-review/SKILL.md` — Step 8 (Consolidation and Present Findings), report header  
**Depends on:** T4  
**Requirement:** TCR-TOKEN-03 (display), TCR-TOKEN-09, TCR-TOKEN-10

**Done when:**
- [ ] Report header Diff line shows excluded count: `N files changed (M excluded as snapshots/lockfiles)` — when `excluded_count > 0`
- [ ] Complex completeness caveat appears in report header when tier = Complex
- [ ] Silent-operation rule stated at top of Step 8: exactly 3 user-facing outputs; no intermediate narration

**Verify:**
```bash
grep -ni "excluded\|completeness caveat\|silent" skills/tests-code-review/SKILL.md | head
# Manual: report header template includes excluded count and Complex caveat
```

**Tests:** none **Gate:** inspection  
**Commit:** `feat(tests-code-review): consolidation header notes + silent operation`

---

### T6: Examples, Guardrails & metadata version

**What:** Update all 3 examples to show the new flow (complexity assessment, banner, execution mode). Confirm Guardrails reference EXCLUDE. Bump `metadata.version` 2.1.0 → 2.2.0.  
**Where:** `skills/tests-code-review/SKILL.md` — Examples section, Guardrails, frontmatter  
**Depends on:** T1–T5  
**Requirement:** Consistency closeout

**Done when:**
- [ ] Each example includes: complexity assessment step → banner → correct execution mode → report
- [ ] No example references old step numbering or "Quick Mode Check" language
- [ ] Guardrails / What NOT to Review mentions EXCLUDE constant for noise files
- [ ] `metadata.version` bumped to `2.2.0`

**Verify:**
```bash
grep -ni "version:" skills/tests-code-review/SKILL.md             # → 2.2.0
grep -ni "Quick Mode Check" skills/tests-code-review/SKILL.md     # → 0
```

**Tests:** none **Gate:** inspection  
**Commit:** `docs(tests-code-review): update examples, guardrails, version for token-efficiency rework`

---

## Requirement Coverage

| Requirement | Task |
|-------------|------|
| TCR-TOKEN-01 | T2 |
| TCR-TOKEN-02 | T2 |
| TCR-TOKEN-03 | T2 (capture), T5 (display) |
| TCR-TOKEN-04 | T3 |
| TCR-TOKEN-05 | T3 |
| TCR-TOKEN-06 | T3 |
| TCR-TOKEN-07 | T4 |
| TCR-TOKEN-08 | T4 |
| TCR-TOKEN-09 | T3 (at-a-glance), T5 (caveat) |
| TCR-TOKEN-10 | T3 (rule), T5 (enforcement) |
| TCR-TOKEN-11 | T4 |
| TCR-TOKEN-12 | T1 |
| TCR-TOKEN-13 | T4 |
| TCR-TOKEN-14 | T4 |
| TCR-TOKEN-15 | T1 |
| TCR-TOKEN-16 | T1 |

All 16 requirements covered.
