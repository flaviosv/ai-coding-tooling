# Feature Spec — Tests Code Review Token Efficiency

**Feature ID:** TCR-TOKEN  
**Status:** Implemented  
**Skill target:** `skills/tests-code-review/SKILL.md`  
**Parent pattern:** CR-TOKEN (`skills/code-review/` + spec) — same token-efficiency architecture, adapted for test review

---

## Problem Statement

The `tests-code-review` skill always dispatches 5–6 specialized agents in parallel, each receiving the full test-file diff — with the orchestrator also holding inlined checklist and codebase-doc content. On a large test PR (30 test files, ~1,500 diff lines), this multiplies the diff across agents and keeps all context loaded in the main orchestrator window. Four sources of waste are addressable without compromising review quality:

1. **Indiscriminate agent dispatch**: all agents run regardless of diff size beyond a simple quick-mode check. A small test change (4 files, 80 lines) runs all 5 agents instead of being handled inline by the orchestrator.
2. **No medium tier**: the only alternative to full parallel dispatch is inline review. A moderate test PR (10 files, 500 lines) runs 5 parallel agents (5× the diff) when a single agent covering all dimensions would cost 1× and still produce a complete review.
3. **Context pre-loading in orchestrator**: Step 2 loads all file content (checklists + 7 codebase docs + `docs/TECH_DEBTS.md`). Step 3 assembles per-agent bundles with inlined content. The orchestrator holds all of it permanently, and relevant content gets duplicated into each agent's prompt.
4. **Return-format waste**: agents return a `Files reviewed: [list]` roll-call that is never surfaced to the user and costs output tokens.

**Guiding principle (same as CR-TOKEN):** the orchestrator holds **metadata, never payload** — file list, diff stat, and availability map only. Diff content, checklists, and codebase docs all move into ephemeral agent contexts.

---

## Goals

- [ ] Add a complexity-assessment step that routes each review by size tier (Small/Medium/Large/Complex → inline / single-agent / parallel / parallel+caveat).
- [ ] Use a single-agent execution mode for Medium reviews (1× diff) instead of parallel dispatch — the primary token win for the common case.
- [ ] Exclude test-specific noise files (snapshots, coverage reports) from the diff at the `git diff` level so they never enter any context.
- [ ] Remove checklist AND codebase-doc loading from the orchestrator; agents self-load only what their dimension needs.
- [ ] Remove `docs/TECH_DEBTS.md` from Step 2 and the availability map (consistent with code-review's CR-TOKEN decision).
- [ ] Strip `Files reviewed` roll-call from agent return format.
- [ ] Preserve full review quality for all review modes — no regressions in findings coverage or output format.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Content-type routing (e.g. docs-only vs test-only vs test+impl) | Tests-code-review is already scoped to test files; impl-diff presence/absence already governs gap-detector — no additional routing layer needed |
| Changing the gap-detector's special `impl_diff`-only behavior | That contract is already correct and stable |
| Changing output format, finding schema, or report structure | Not related to token cost |
| Changing GitHub PR posting behavior | Unrelated |
| New review dimensions or new agents | Out of scope for this feature |
| Diff batching / splitting within a single agent for the Complex tier | Complex runs the same parallel dispatch as Large; it only adds a completeness caveat — not fewer/cheaper/batched agents |

---

## User Stories

### P1: Noise File Exclusion at Diff Collection ⭐ MVP

**User Story**: As a developer, I want snapshot files and coverage reports excluded from the diff at the `git diff` command level, so that this high-volume auto-generated content is never captured into any context and never multiplied across agents.

**Why P1**: Highest leverage for lowest risk. A Jest snapshot file updated after a UI change can be several thousand lines — multiplied across 5 agents it costs enormous tokens for content the skill already says not to review. Coverage reports are similarly large and never relevant to a test-quality review.

**Mechanism**: Step 4 diff collection MUST apply git pathspec exclusions. Applies to every git-based mode (local, multi-commit). For GitHub PR mode, excluded paths are filtered from the changed-file list before assembling the diff passed to agents. A single named constant `EXCLUDE` is defined and referenced across all modes.

**Exclusion list** (lives as a named constant in the skill):

```
-- Lockfiles (appear in impl_diff for gap-detector)
':(exclude)*.lock'               ':(exclude)package-lock.json'  ':(exclude)yarn.lock'
':(exclude)pnpm-lock.yaml'       ':(exclude)composer.lock'      ':(exclude)Gemfile.lock'
':(exclude)go.sum'               ':(exclude)Cargo.lock'         ':(exclude)poetry.lock'
-- Minified / generated / built artifacts
':(exclude)*.min.js'             ':(exclude)*.min.css'          ':(exclude)*.map'
':(exclude)dist/**'              ':(exclude)build/**'           ':(exclude)vendor/**'
':(exclude)node_modules/**'      ':(exclude)*.generated.*'
-- Test-specific noise
':(exclude)**/__snapshots__/**'  ':(exclude)*.snap'
':(exclude)coverage/**'          ':(exclude).nyc_output/**'
```

**Why the full list:** The test diff is already filtered to test files, so lockfiles and minified bundles won't appear there regardless. However, `impl_diff` — collected separately for `gap-detector` — includes non-test implementation files, and a PR with a 3,000-line `package-lock.json` change would pass that into gap-detector's context and count toward tier thresholds. EXCLUDE applies to both the test diff AND the `impl_diff` collection. The list is the union of CR-TOKEN's exclusions plus test-specific items.

**Acceptance Criteria:**

1. WHEN Step 4 collects the diff in local or multi-commit mode THEN the `git diff`/`git show` commands SHALL include the pathspec exclusion constant so excluded files contribute zero lines to the captured diff.
2. WHEN an excluded file is the only change in a hunk THEN that file SHALL NOT appear in the diff passed to any agent.
3. WHEN excluded files are removed from the diff THEN they SHALL still be acknowledged in the report header's file count with a note (e.g. `12 files changed (2 excluded as snapshots/generated)`) so the exclusion is transparent, not silent.
4. WHEN GitHub PR mode collects the diff THEN excluded paths SHALL be filtered from the changed-file list before the diff is assembled for agents.
5. WHEN the exclusion constant is defined THEN it SHALL be a single named constant referenced by all modes — not duplicated per mode.

**Independent Test**: Create a local change that modifies a test file, a snapshot file, and `package-lock.json` (3,000+ lines of impl diff). Run the review. Verify: (a) the test diff contains the test file but not the snapshot; (b) the `impl_diff` passed to gap-detector contains the implementation change but not the lockfile content; (c) the report header notes "2 excluded".

---

### P1: Review Complexity Assessment & Routing ⭐ MVP

**User Story**: As a developer, I want a single explicit step that assesses the review's complexity and routes it to the right execution mode, so that small changes are reviewed inline, moderate changes run cheaply through one agent, larger changes get parallel specialists, and the biggest changes are handled with explicit awareness that detail can be missed.

**Why P1**: Today there is only a binary Quick Mode Check (inline vs full parallel). A medium-sized test PR (10 files, 500 lines) runs 5 parallel agents — 5× the diff cost — when one agent covering all dimensions would cost 1× and still produce a thorough review. This story introduces a 4-tier model that matches execution cost to review scope.

#### Size tier → execution mode (from post-exclusion file count + diff lines)

Metrics are measured **after** noise exclusion. Tiers are evaluated **top-down, first match wins**.

| Tier | Condition | Execution mode | Diff cost |
|------|-----------|----------------|-----------|
| **Small** | ≤5 test files **OR** <200 diff lines | **Inline** — orchestrator reviews all active dimensions directly, no agents | ~0 (in orchestrator) |
| **Medium** | ≤15 test files **AND** <800 diff lines | **Single agent** — one delegated subagent reviews ALL dimensions in one instance and returns consolidated findings | 1× |
| **Large** | ≤25 test files **AND** <1,500 diff lines | **Parallel** — one specialized subagent per dimension, dispatched together | N× |
| **Complex** | >25 test files **OR** ≥1,500 diff lines | **Parallel + completeness handling** (see below) | N× |

> **Evaluation order & boundaries.** Check Small → Medium → Large → Complex, first match wins. Small keeps **OR** logic (preserving current quick-mode behavior). Medium and Large use **AND** on their ceilings. Anything exceeding the Large ceiling (>25 files OR ≥1,500 lines) is Complex.

**Why a single-agent Medium tier:** for moderate test PRs a single agent reviewing all dimensions is reliable and costs **1× the diff** instead of N×. The tradeoff — one agent is less specialized per dimension than dedicated reviewers — is acceptable at this size and is exactly why the tier is size-gated; past the Medium ceiling the review escalates to parallel specialists.

**Medium tier — gap-detector handling:**

When the size tier is Medium (single agent), gap-detector is folded into the same agent:
- If `impl_diff` is **non-empty**: the single agent receives BOTH the test diff AND the `impl_diff`, and covers all 6 dimensions (including coverage gaps).
- If `impl_diff` is **empty**: the single agent receives only the test diff and covers 5 dimensions (gap-detector is skipped, same as current behavior).

**Complex-tier handling** (does NOT change the token strategy vs Large — both are parallel):
- The report header carries a **completeness caveat**: `⚠️ Complex review (N test files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.`
- Each dispatched agent's prompt includes a **thoroughness directive**: review every file in its scope thoroughly. The agent does NOT emit a coverage roll-call — it returns findings only.

#### The Review Plan (output of this step)

The assessment step emits an explicit plan consumed by dispatch:

```
Review Plan:
  Size tier:        Small | Medium | Large | Complex
  Execution mode:   inline | single-agent | parallel
  Dimensions:       [list of active dimensions]
  Agents dispatched: 0 (inline) | 1 (single-agent) | N (parallel)
  Gap-detector:     active (impl_diff non-empty) | skipped (no impl changes)
  Complex handling: none | caveat + thoroughness directive
  Excluded files:   N (from noise exclusion)
```

#### Surfacing the detected complexity to the user

Immediately after the assessment step, the skill prints a one-line banner so the user knows which path was chosen and why:

```
🔍 Test review — Complexity: **Complex** (32 test files, 1,840 lines · 2 excluded) · Parallel — 6 agents (⚠️ completeness caveat)
```

```
🔍 Test review — Complexity: **Medium** (10 test files, 480 lines) · Single agent — all 6 dimensions
```

```
🔍 Test review — Complexity: **Small** (3 test files, 90 lines) · Inline review
```

The banner SHALL state: the size tier, the metric that drove it (file count + diff lines, plus excluded count when any), and the resulting execution mode. For Complex it also signals the completeness caveat.

#### Silent operation — only three user-facing outputs

The skill produces **exactly three** user-facing outputs, in this order, and **nothing else**:

1. The **skill-invocation announcement** (required by the skill-transparency convention).
2. The **complexity banner** (above).
3. The **final consolidated report**.

Everything between the banner and the final report is silent. Specifically prohibited:
- Progress narration ("dispatching agents", "consolidating findings", "agent X returned").
- Partial or per-agent findings printed as they arrive.
- Any intermediate commentary.

Agent **return payloads** (agent → orchestrator, not user-facing): each agent returns **findings only** — the `Files reviewed: [list]` roll-call is removed from the return format since it is never surfaced and costs output tokens. The orchestrator consolidates silently and prints the final report as the single analytical output.

**Acceptance Criteria:**

1. WHEN the assessment step runs THEN it SHALL produce a Review Plan stating the size tier, execution mode, active dimensions, agent count, gap-detector status, Complex flag, and excluded-file count — before any agent is dispatched.
2. WHEN the assessment completes THEN the skill SHALL print a user-visible one-line complexity banner (size tier + driving metrics + excluded count + execution mode) BEFORE any agent is dispatched or any inline review begins — in every mode (local, GitHub PR, multi-commit) and every tier including Small.
3. WHEN size tiers are evaluated THEN the order SHALL be Small → Medium → Large → Complex, first match wins, on post-exclusion metrics.
4. WHEN the change is ≤5 test files OR <200 diff lines THEN the tier SHALL be Small and the execution mode SHALL be inline (0 agents).
5. WHEN the change is not Small AND ≤15 test files AND <800 diff lines THEN the tier SHALL be Medium and exactly ONE subagent SHALL be dispatched covering all dimensions (1× diff).
6. WHEN tier is Medium AND `impl_diff` is non-empty THEN the single agent SHALL receive both the test diff AND the `impl_diff`, covering all 6 dimensions including coverage gaps.
7. WHEN tier is Medium AND `impl_diff` is empty THEN the single agent SHALL receive only the test diff, covering 5 dimensions (gap-detector skipped).
8. WHEN the change is not Small/Medium AND ≤25 test files AND <1,500 diff lines THEN the tier SHALL be Large and one subagent per active dimension SHALL be dispatched in parallel.
9. WHEN the change is >25 test files OR ≥1,500 diff lines THEN the tier SHALL be Complex: parallel dispatch + the report header SHALL carry the completeness caveat AND each agent SHALL receive the thoroughness directive.
10. WHEN the skill runs THEN the ONLY user-facing outputs SHALL be, in order: (1) the skill-invocation announcement, (2) the complexity banner, (3) the final consolidated report — with NO intermediate output between the banner and the report.
11. WHEN an agent returns its result THEN it SHALL return findings only — no `Files reviewed` roll-call — and the full detail of each finding SHALL be preserved verbatim in the final report.
12. WHEN the at-a-glance table is assembled THEN gap-detector's row SHALL show `⚠️ skipped — no impl changes` when `impl_diff` is empty, and SHALL be omitted entirely only when the size tier suppresses it (Medium with empty `impl_diff` folds it into the single-agent row, not a separate skipped row).

**Independent Test**: (a) A 4-file/180-line test change → tier Small, inline. (b) A 10-file/500-line test change → tier Medium, **1 agent** covering all dimensions, 1× diff. (c) A 20-file/900-line test change → tier Large, **5–6 parallel agents**. (d) A 30-file/400-line test change → tier Complex, 5–6 parallel agents + caveat. (e) All cases print the complexity banner before any work.

---

### P1: Agent Self-Loaded Context — Checklists + Codebase Docs ⭐ MVP

**User Story**: As a developer, I want each review agent to self-load only the checklists AND codebase docs relevant to its own dimension, so that the orchestrator holds metadata only and never inlines reference material that belongs inside the agents.

**Why P1**: Currently the orchestrator loads all file content in Step 2 and assembles per-agent bundles in Step 3 with inlined content. Moving loading into each agent cleans the orchestrator context (the persistent main window). Checklists are dimension-specific; codebase docs are shared context — both move into ephemeral agent contexts.

**Codebase docs — full set for every reviewing agent:**

All reviewing agents (all agents **except** gap-detector) self-load the **full 7-doc** codebase set, loading each only if present (fall back `.specs/codebase/` → `docs/codebase/` → `docs/`):

`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md`, `INTEGRATIONS.md`, `STRUCTURE.md`

- **`TESTING.md` is included** (unlike code-review, where it is excluded) — it is core context for test-quality review across all dimensions.
- **`gap-detector`** is the exception: it receives only `impl_diff` and loads a focused doc subset — `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` — sufficient to identify uncovered paths and integration points without loading test-specific docs it does not use.

**Remove `docs/TECH_DEBTS.md`:**

Remove `docs/TECH_DEBTS.md` from Step 2's loading table, the availability map, and all agent-prompt injection references ("Tech Debt Recurrence" block). No agent loads or cross-references it. This is consistent with code-review's CR-TOKEN decision.

**Agent → checklist loading:**

There is one baseline checklist (`references/test-review-checklist.md`) and one optional tech-specific file (`references/<stack>-*-tests-code-review.md`). Each reviewing agent (all except gap-detector) self-loads both if present.

| Agent | Self-loads (checklist) | Self-loads (codebase docs) |
|-------|----------------------|---------------------------|
| `clarity-reviewer` | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set |
| `coverage-reviewer` | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set |
| `gap-detector` | None — job is defined in its prompt | `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` |
| `isolation-reviewer` | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set |
| `maintainability-reviewer` | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set |
| `performance-reviewer` | `test-review-checklist.md`, `<stack>-*-tests-code-review.md` (if present) | Full 7-doc set |

**Mechanism**: Each agent's prompt shall include a `## Before You Begin` block listing the exact file paths to Read before starting the review — both its checklist(s) and its codebase docs. The orchestrator SHALL NOT load or inline any checklist or codebase-doc content in Steps 2–3; it retains only the **availability map** (which files exist) so it can tell each agent what is present to load.

**Single-agent (Medium tier) loading**: When Medium tier dispatches one agent covering all dimensions, its `## Before You Begin` block lists the checklist(s) (same as any reviewing agent) plus the full 7-doc codebase set. If `impl_diff` is non-empty, the single agent also handles gap-detector without needing additional doc loading.

**Acceptance Criteria:**

1. WHEN Step 2 (Context Collection) runs THEN the orchestrator SHALL NOT load file *content* from `references/` or `.specs/codebase/` — it only records presence/absence into the availability map.
2. WHEN each agent's prompt is assembled THEN it SHALL include a `## Before You Begin` block listing its assigned checklist files AND its codebase docs — all filtered to those marked present in the availability map.
3. WHEN any reviewing agent (all except gap-detector) is assembled THEN its codebase-doc load SHALL be the FULL 7-doc set — `STACK`, `ARCHITECTURE`, `CONVENTIONS`, `TESTING`, `CONCERNS`, `INTEGRATIONS`, `STRUCTURE`.
4. WHEN `gap-detector` receives its prompt THEN its codebase-doc load SHALL be only `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` — and it SHALL have no checklist load instruction.
5. WHEN any step or agent runs THEN `docs/TECH_DEBTS.md` SHALL NOT be loaded by anything — the `tech_debts` availability key SHALL be removed from Step 2, the Step 3 availability map, and all agent prompt injections. No agent's `## Before You Begin` block references it.
6. WHEN Step 2 builds the availability map THEN it SHALL contain exactly 9 keys: `stack`, `architecture`, `conventions`, `testing`, `concerns`, `integrations`, `structure`, `checklist_baseline`, `checklist_tech_specific`.
7. WHEN a file in an agent's `## Before You Begin` block is absent from the availability map THEN it SHALL be omitted from that agent's load list (the agent never attempts to Read a non-existent file).
8. WHEN the orchestrator Step 2/3 runs THEN it holds only the availability map — no checklist or codebase-doc file content.

**Independent Test**: Inspect each agent's assembled prompt. Verify `gap-detector` loads no checklist and only its 4 focused codebase docs. Verify all other reviewing agents' codebase-doc list is the full 7-doc set. Verify the orchestrator Step 2/3 holds only an availability map — no file content from `references/` or `.specs/codebase/`. Grep the skill for `TECH_DEBTS` and `tech_debts` — both return zero matches.

---

## Edge Cases

- WHEN the changed test file list is empty THEN the size tier SHALL be Small (0 files / 0 lines) → inline.
- WHEN a change is small in file count but large in lines (e.g., 2 test files / 2,000 lines) THEN the size tier SHALL be Small (OR logic: `≤5 test files` is satisfied) — accepted tradeoff consistent with CR-TOKEN.
- WHEN a change sits exactly at a boundary (e.g., 15 test files / 799 lines) THEN first-match-wins top-down evaluation resolves it (15≤15 AND 799<800 → Medium); 16 files / 799 lines → not Medium → Large.
- WHEN `gap-detector` is skipped (impl_diff empty) in Large/Complex tier THEN its at-a-glance row SHALL show `⚠️ skipped — no impl changes` (not omitted entirely — the row communicates intent).
- WHEN tier is Medium AND `impl_diff` is empty THEN the single agent covers 5 dimensions and the banner says `Single agent — 5 dimensions (no impl changes)`.
- WHEN a checklist or codebase-doc file referenced in a `## Before You Begin` block does not exist THEN the agent SHALL proceed without it and note the gap in its findings (same as current degraded-mode behavior).
- WHEN the excluded files are ALL the changed files (e.g., only snapshot files changed) THEN the tier SHALL be Small (0 non-excluded test files / 0 lines) and the review SHALL be inline with a note that only excluded files changed.

---

## Requirement Traceability

| Requirement ID | Story | Description |
|----------------|-------|-------------|
| TCR-TOKEN-01 | P1: Noise Exclusion | `EXCLUDE` pathspec constant defined + applied in Step 4 (local + multi-commit modes) |
| TCR-TOKEN-02 | P1: Noise Exclusion | GitHub PR mode filters excluded paths from changed-file list |
| TCR-TOKEN-03 | P1: Noise Exclusion | Report header notes excluded-file count (transparency) |
| TCR-TOKEN-04 | P1: Complexity Assessment | 4-tier size logic (Small/Medium/Large/Complex), top-down first-match, post-exclusion metrics |
| TCR-TOKEN-05 | P1: Complexity Assessment | Review Plan emitted before any dispatch |
| TCR-TOKEN-06 | P1: Complexity Assessment | Complexity banner printed before any review work, all modes/tiers |
| TCR-TOKEN-07 | P1: Complexity Assessment | Medium single-agent execution (1 agent, all dimensions, 1× diff) |
| TCR-TOKEN-08 | P1: Complexity Assessment | Medium tier gap-detector fold (receives both diffs when impl_diff non-empty) |
| TCR-TOKEN-09 | P1: Complexity Assessment | Complex-tier completeness caveat + thoroughness directive |
| TCR-TOKEN-10 | P1: Complexity Assessment | Silent operation (skill invocation + banner + final report only) |
| TCR-TOKEN-11 | P1: Complexity Assessment | Lean return format — strip `Files reviewed` roll-call from agent return schema |
| TCR-TOKEN-12 | P1: Agent Self-Loaded Context | Orchestrator Step 2 holds availability map only (no content) |
| TCR-TOKEN-13 | P1: Agent Self-Loaded Context | `## Before You Begin` block in each agent prompt (checklists + codebase docs) |
| TCR-TOKEN-14 | P1: Agent Self-Loaded Context | gap-detector loads focused doc subset only (no checklist) |
| TCR-TOKEN-15 | P1: Agent Self-Loaded Context | Remove `tech_debts` key from Step 2, availability map, and all agent injections |
| TCR-TOKEN-16 | P1: Agent Self-Loaded Context | Availability map reduced to 9 keys (no `tech_debts`) |

---

## Success Criteria

- [ ] Snapshot/coverage noise files excluded from diff at `git diff` level — verified by reviewing a PR with a large snapshot update and confirming snapshot content is absent from agent prompts.
- [ ] Report header notes the count of excluded files (transparent, not silent drop).
- [ ] Complexity-assessment step emits an explicit Review Plan (tier + mode + dimensions + agent count + gap-detector status) before any dispatch.
- [ ] Complexity banner is printed at the start of every review (all tiers, all modes).
- [ ] A 4-file/80-line test change is classified Small and reviewed inline (0 agents).
- [ ] A 10-file/500-line test change is classified Medium and runs exactly ONE agent covering all dimensions (1× diff).
- [ ] A 20-file/900-line test change is classified Large and runs parallel agents.
- [ ] A 30-file/2,000-line test change is classified Complex: parallel agents + completeness caveat in header + thoroughness directive in each agent.
- [ ] Medium tier with non-empty `impl_diff`: single agent receives both diffs, gap-detector dimension covered.
- [ ] The skill emits only three user-facing outputs (skill invocation → banner → final report) with nothing in between.
- [ ] Agent returns carry findings only (no `Files reviewed` roll-call); actual findings retain full detail in the final report.
- [ ] Orchestrator Step 2 holds only an availability map — no file content from `references/` or `.specs/codebase/`.
- [ ] Every reviewing agent (all except gap-detector) loads the full 7-doc codebase set including `TESTING.md`.
- [ ] `gap-detector` prompt loads only `STACK.md`, `ARCHITECTURE.md`, `CONCERNS.md`, `INTEGRATIONS.md` and no checklist.
- [ ] `docs/TECH_DEBTS.md` is loaded by nothing — grepping the skill for `TECH_DEBTS`/`tech_debts` returns zero matches.
- [ ] Availability map has exactly 9 keys (no `tech_debts`).
- [ ] Output format (at-a-glance table, zoned findings, finding IDs, severity/priority/type labels) is unchanged.
