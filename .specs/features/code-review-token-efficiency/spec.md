# Feature Spec — Code Review Token Efficiency

**Feature ID:** CR-TOKEN  
**Status:** Implemented  
**Skill target:** `skills/code-review/SKILL.md`

---

## Problem Statement

The `code-review` skill always dispatches 5 specialized agents in parallel, each receiving the full diff. On a large PR (60 files, ~10,000 diff lines), this multiplies the diff ~5× and can consume 20% of a Claude Max 5x session usage window. Because every subagent's tokens are billed, the highest-leverage savings either **shrink the payload that gets multiplied across agents** or **remove redundant copies the orchestrator holds**. Four sources of waste are addressable without compromising review quality:

1. **Indiscriminate agent dispatch**: all 5 agents run regardless of what the PR changes. A docs-only or config-only PR runs security, performance, and architecture reviewers that will find nothing.
2. **Checklist pre-loading in main context**: the orchestrator loads all reference checklists into its own context, then inlines them into every agent's prompt. Each agent receives checklists irrelevant to its dimension.
3. **Codebase doc pre-loading in main context**: same problem as checklists — `ARCHITECTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`, etc. are loaded once in the orchestrator and inlined into agent bundles, rather than self-loaded by the agents that need them.
4. **Noise files in the multiplied diff**: lockfiles, generated code, and minified bundles are captured in the full diff and multiplied across all agents — a single 3,000-line lockfile change costs ~120K tokens across 5 agents for content nobody reviews. The skill tells agents not to *review* these, but the tokens are already spent.

**Guiding principle:** the orchestrator should hold **metadata, never payload** — file list, diff stat, and availability map only. Diff content, checklists, and codebase docs all move into the ephemeral agent contexts.

---

## Goals

- [ ] Add one explicit complexity-assessment step that routes each review by size tier (Small/Medium/Large/Complex → inline / single-agent / parallel / parallel+caveat) and content type.
- [ ] Use a single-agent execution mode for Medium PRs (1× diff) instead of parallel dispatch — the primary token win for the common case.
- [ ] Reduce agent dispatch to only the dimensions relevant to the PR's content type.
- [ ] Remove checklist AND codebase-doc loading from the orchestrator; agents self-load only what their dimension needs.
- [ ] Exclude noise files (lockfiles, generated, minified) from the diff at the `git diff` command level so they never enter any context.
- [ ] Preserve full review quality for general code PRs — no regressions in findings coverage or output format.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Triage/routing agent that scopes the diff per agent (sends subsets of files to different agents) | Routing can't safely scope security and regression reviewers — Option A decision. Note: Medium's single agent and the parallel tiers all receive the FULL diff; size only changes how many agents, never which files each sees |
| Diff batching / splitting within a single agent for the Complex tier | Complex runs the same parallel dispatch as Large; it only adds a completeness caveat + thoroughness directive — not fewer/cheaper/batched agents |
| Changing output format, finding schema, or report structure | Not related to token cost |
| Changing how GitHub PR posting works | Unrelated |
| New review dimensions or new agents | Out of scope for this feature |
| Keeping the diff out of the orchestrator's own context (Idea 2 — write-to-file/redirect) | Deferred; GitHub-PR-mode wrinkle needs design. Not in this iteration |

---

## User Stories

### P1: Noise File Exclusion at Diff Collection ⭐ MVP

**User Story**: As a developer, I want lockfiles, generated code, and minified bundles excluded from the diff at the `git diff` command level, so that this high-volume content is never captured into any context and never multiplied across agents.

**Why P1**: Highest leverage for lowest risk. The excluded content is multiplied across every active agent, so shrinking it compounds. A single `package-lock.json` change of ~3,000 lines costs ~120K tokens across 5 agents — for content the skill already says not to review. The current "What NOT to Review" guidance tells agents to ignore these files, but the tokens are already spent because the full diff is captured first.

**Mechanism**: Step 4 diff collection MUST apply git pathspec exclusions so excluded paths never appear in the captured diff. Applies to every git-based mode (local, multi-commit). For GitHub PR mode, the equivalent exclusion is applied by filtering the changed-file list and omitting excluded paths from the diff passed to agents.

**Exclusion list** (lives as a named constant in the skill so it can be tuned):

```
':(exclude)*.lock' ':(exclude)package-lock.json' ':(exclude)yarn.lock'
':(exclude)pnpm-lock.yaml' ':(exclude)composer.lock' ':(exclude)Gemfile.lock'
':(exclude)go.sum' ':(exclude)Cargo.lock' ':(exclude)poetry.lock'
':(exclude)*.min.js' ':(exclude)*.min.css' ':(exclude)*.map'
':(exclude)**/__snapshots__/**' ':(exclude)dist/**' ':(exclude)build/**'
':(exclude)vendor/**' ':(exclude)node_modules/**' ':(exclude)*.generated.*'
```

**Acceptance Criteria:**

1. WHEN Step 4 collects the diff in local or multi-commit mode THEN the `git diff`/`git show` commands SHALL include the pathspec exclusion list so excluded files contribute zero lines to the captured diff.
2. WHEN an excluded file is the only change in a hunk THEN that file SHALL NOT appear in the diff passed to any agent.
3. WHEN excluded files are removed from the diff THEN they SHALL still be acknowledged in the report header's file count with a note (e.g. `60 files changed (4 excluded as generated/lockfiles)`) so the exclusion is transparent, not silent.
4. WHEN GitHub PR mode collects the diff THEN excluded paths SHALL be filtered from the changed-file list before the diff is assembled for agents.
5. WHEN the exclusion list is defined THEN it SHALL be a single named constant referenced by all modes — not duplicated per mode.

**Independent Test**: Create a local change that modifies a source file plus `package-lock.json` (3,000+ lines). Run the review. Verify the diff sent to agents contains the source file but not the lockfile content; verify the report header notes "1 excluded".

---

### P1: Review Complexity Assessment & Routing ⭐ MVP

**User Story**: As a developer, I want a single explicit step that assesses the review's complexity and routes it to the right execution mode, so that trivial changes are reviewed inline, moderate changes run cheaply through one agent, larger changes get parallel specialists, and the biggest changes are handled with explicit awareness that detail can be missed.

**Why P1**: Today the routing logic is implicit and scattered (a quick-mode check, then dispatch). A developer can't see *why* a given review took the path it did. This story consolidates routing into one **Review Complexity Assessment** step that produces a **Review Plan** — making the decision explicit, tunable, and honest about large-PR limitations.

The assessment combines **two independent axes**. Size decides the *execution mode* (how the review runs); content decides *which dimensions* are in scope.

#### Axis 1 — Size tier → execution mode (from post-exclusion file count + diff lines)

Metrics are measured **after** noise exclusion (so lockfiles/generated files never inflate the tier). Tiers are evaluated **top-down, first match wins**.

| Tier | Condition | Execution mode | Diff cost |
|------|-----------|----------------|-----------|
| **Small** | ≤5 files **OR** <200 diff lines | **Inline** — orchestrator reviews the active dimensions directly, no agents | ~0 (in orchestrator) |
| **Medium** | ≤15 files **AND** <800 diff lines | **Single agent** — one delegated subagent reviews ALL active dimensions in one instance and returns consolidated findings | 1× |
| **Large** | ≤25 files **AND** <1,500 diff lines | **Parallel** — one specialized subagent per active dimension, dispatched together | N× |
| **Complex** | >25 files **OR** ≥1,500 diff lines | **Parallel + completeness handling** (below) | N× |

> **Evaluation order & boundaries.** Check Small → Medium → Large → Complex, first match wins. Small keeps the legacy **OR** (either axis small → inline), preserving current quick-mode behavior. Medium and Large use **AND** on their ceilings. Anything exceeding the Large ceiling (>25 files OR ≥1,500 lines) is Complex.

**Why a single-agent Medium tier:** for moderate PRs a single agent reviewing all dimensions is reliable and costs **1× the diff** instead of N×. This is the primary token win for the common case. The tradeoff — one agent is less thorough *per dimension* than dedicated specialists — is acceptable at this size and is exactly why the tier is size-gated; past the Medium ceiling the review escalates to parallel specialists.

**Complex-tier handling** (Complex only — does NOT change the token strategy vs Large, per Option A; both are parallel):
- The report header carries a **completeness caveat**: `⚠️ Complex review (N files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.`
- Each dispatched agent's prompt includes a **thoroughness directive**: review every file in its scope thoroughly. The agent does NOT emit any coverage roll-call or per-file "clean" accounting — it returns findings only (see **Silent operation** below). Thoroughness is an instruction about the review, not about producing output.

#### Axis 2 — Content type (which agents are active)

| PR Type | Detection (changed file list only) | Active agents |
|---------|-----------------------------------|---------------|
| `general` (default) | Any source code file present (`*.ts`, `*.js`, `*.py`, `*.go`, `*.rb`, `*.java`, `*.php`, `*.cs`, `*.rs`, `*.kt`, `*.swift`, `*.c`, `*.cpp`, `*.h`, etc.) | All 5 + `requirements-tracer` (conditional) |
| `docs-only` | ALL changed files are documentation (`*.md`, `*.txt`, `*.rst`, `*.mdx`, `docs/**`, `README*`, `CHANGELOG*`, `*.adoc`) | `code-quality-reviewer` only + `requirements-tracer` (conditional) |
| `config-infra-only` | ALL changed files are configuration or infrastructure (`*.yml`, `*.yaml`, `*.json`, `*.toml`, `Dockerfile*`, `*.tf`, `*.tfvars`, `.github/**`, `*.env`, `*.ini`, `*.cfg`, `.eslintrc*`, `.prettier*`) | `security-reviewer`, `code-quality-reviewer`, `regression-reviewer` + `requirements-tracer` (conditional) |
| `frontend-assets-only` | ALL changed files are styling or static assets (`*.css`, `*.scss`, `*.less`, `*.svg`, `*.png`, `*.jpg`, `*.gif`, `*.ico`, `*.woff*`, `*.ttf`) | `code-quality-reviewer`, `security-reviewer` (XSS in SVG/CSS) + `requirements-tracer` (conditional) |
| `mixed` | Multiple types present but no source code | Fall through to `general` — all 5 dimensions active |

**Detection rule**: "ALL changed files" means 100% of the non-deleted, non-excluded file list matches the pattern. A single source code file in the list → `general`. Uses the changed file list from Step 4. No file content reading required.

#### How the two axes combine

Content type defines the **active dimension set**; the size tier defines **how those dimensions are executed**:

| Execution mode (size tier) | How the active dimensions run |
|----------------------------|-------------------------------|
| Inline (Small) | Orchestrator reviews all active dimensions directly, no subagents |
| Single agent (Medium) | **One** delegated subagent covers ALL active dimensions; it self-loads the **union** of those dimensions' checklists + codebase docs (see Agent Self-Loaded Context story) |
| Parallel (Large) | **One subagent per active dimension**, dispatched together — current behavior |
| Parallel + caveat (Complex) | Same as Large + completeness caveat + thoroughness directive |

So a Medium `general` PR runs **1 agent** covering all 5 dimensions; a Large `general` PR runs **5 parallel agents**; a Medium `docs-only` PR runs **1 agent** covering just the code-quality dimension.

#### The Review Plan (output of this step)

The assessment step emits an explicit plan consumed by dispatch:

```
Review Plan:
  Size tier:        Small | Medium | Large | Complex
  Content type:     general | docs-only | config-infra-only | frontend-assets-only
  Execution mode:   inline | single-agent | parallel
  Active dimensions: [<dimension list from content type>]
  Agents dispatched: 0 (inline) | 1 (single-agent, all dimensions) | N (parallel, one per dimension)
  Complex handling: none | caveat + thoroughness directive
  Excluded files:   N (from noise exclusion)
```

The active dimensions are always scoped by content type regardless of execution mode — a `docs-only` review covers only the code-quality dimension whether it runs inline (Small), as a single agent (Medium), or in parallel (Large/Complex).

#### Surfacing the detected complexity to the user

The detected complexity MUST be announced to the user **before** any review work begins — not kept internal to the orchestrator. Immediately after the assessment step, the skill prints a one-line banner so the user knows which path was chosen and why:

```
🔍 Code review — Complexity: **Complex** (32 files, 1,840 lines · 3 excluded) · Type: general · Parallel — 5 agents (⚠️ completeness caveat)
```

```
🔍 Code review — Complexity: **Medium** (9 files, 420 lines) · Type: general · Single agent — all 5 dimensions
```

```
🔍 Code review — Complexity: **Small** (2 files, 60 lines) · Type: docs-only · Inline review (Code Quality only)
```

The banner SHALL state: the size tier, the metric that drove it (file count + diff lines, plus excluded count when any), the content type, and the resulting execution mode (inline / single agent covering the dimensions / N parallel agents). For the Complex tier it also signals that the completeness caveat applies.

#### Silent operation — only three user-facing outputs

The skill produces **exactly three** user-facing outputs, in this order, and **nothing else**:

1. The **skill-invocation announcement** (required by the skill-transparency convention).
2. The **complexity banner** (above).
3. The **final consolidated report**.

Everything between the banner and the final report is silent. Specifically prohibited:
- Progress narration ("dispatching agents", "consolidating findings", "agent X returned", "now reviewing…").
- Partial or per-agent findings printed as they arrive.
- Any "what was found during analysis" intermediate commentary.

This also applies to the agent **return payloads** (agent → orchestrator, not user-facing): each agent returns **findings only** — the `Files reviewed: [list]` / coverage roll-call is removed from the return format, since it is never surfaced and costs output tokens. The orchestrator consolidates silently and prints the final report as the single analytical output.

**Acceptance Criteria:**

1. WHEN the assessment step runs THEN it SHALL produce a Review Plan stating the size tier, content type, execution mode, active dimensions, agents-dispatched count, Complex-handling flag, and excluded-file count — before any agent is dispatched.
2. WHEN the assessment completes THEN the skill SHALL print a user-visible one-line complexity banner (size tier + driving metrics + excluded count + content type + execution mode) BEFORE any agent is dispatched or any inline review begins — in every mode (local, GitHub PR, multi-commit) and every tier including Small.
3. WHEN size tiers are evaluated THEN the order SHALL be Small → Medium → Large → Complex, first match wins, on post-exclusion metrics.
4. WHEN the change is ≤5 files OR <200 diff lines THEN the tier SHALL be Small and the execution mode SHALL be inline (0 agents).
5. WHEN the change is not Small AND ≤15 files AND <800 diff lines THEN the tier SHALL be Medium and exactly ONE subagent SHALL be dispatched covering all active dimensions (1× diff).
6. WHEN the change is not Small/Medium AND ≤25 files AND <1,500 diff lines THEN the tier SHALL be Large and one subagent per active dimension SHALL be dispatched in parallel.
7. WHEN the change is >25 files OR ≥1,500 diff lines THEN the tier SHALL be Complex: parallel dispatch + the report header SHALL carry the completeness caveat AND each agent SHALL receive the thoroughness directive.
8. WHEN the skill runs THEN the ONLY user-facing outputs SHALL be, in order: (1) the skill-invocation announcement, (2) the complexity banner, (3) the final consolidated report — with NO intermediate output between the banner and the report (no progress narration, no per-agent or partial findings, no analysis commentary).
9. WHEN an agent returns its result THEN it SHALL return findings only — no `Files reviewed`/coverage roll-call — and the full detail of each finding (`{severity, title, file, line, explanation, recommendation}`) SHALL be preserved verbatim in the final report.
10. WHEN the changed file list contains any source code file THEN the content type SHALL be `general` and all 5 dimensions SHALL be active (executed per the size tier's mode).
11. WHEN the changed file list is exclusively docs THEN the content type SHALL be `docs-only` and only the Code Quality dimension SHALL be active (+ requirements if applicable).
12. WHEN the changed file list is exclusively config/infra THEN only the Security, Code Quality, and Regression dimensions SHALL be active.
13. WHEN a dimension is not in the active set THEN its row SHALL be omitted from the at-a-glance table — not shown as "skipped" or "not executed".
14. WHEN content type is anything other than `general`, OR size tier is Large/Complex THEN the at-a-glance header SHALL note it: `Tier: Complex | Type: docs-only`.

**Independent Test**: (a) A 9-file/420-line source change → tier Medium, `general`, **1 agent** covering all 5 dimensions, no caveat. (b) A 20-file/600-line source change → tier Large, `general`, **5 parallel agents**, no caveat. (c) A 30-file/400-line source change → tier Complex, `general`, 5 parallel agents + caveat. (d) A PR adding only `docs/guide.md` → tier Small, `docs-only`, inline, Code Quality only, single at-a-glance row.

---

### P1: Agent Self-Loaded Context — Checklists + Codebase Docs ⭐ MVP

**User Story**: As a developer, I want each review agent to self-load only the checklists AND codebase docs relevant to its own dimension, so that the orchestrator holds metadata only and never inlines reference material that belongs inside the agents.

**Why P1**: Currently both checklists and codebase docs are loaded in the orchestrator's Step 2 context and inlined into each agent's prompt bundle. Moving loading into each agent cleans the orchestrator context (the persistent main window). The two artifact types are then handled differently: **codebase docs are shared project context** (every dimension benefits), so every reviewing agent loads the full set; **checklists are dimension-specific guidance**, so each agent loads only its own (keeps it lean and prevents cross-dimension finding bleed). Both use the same mechanism — a `## Before You Begin` Read instruction — so they are specified together.

**Codebase docs — full set for every reviewing agent:**

All agents **except `requirements-tracer`** self-load the **full** codebase-doc set, loading each only if present (fall back `.specs/codebase/` → `docs/codebase/` → `docs/`):

`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `STRUCTURE.md`, `INTEGRATIONS.md`, `CONCERNS.md`

- **`TESTING.md` is excluded** — it is test-strategy context owned by the `tests-code-review` skill, not relevant to implementation-code review.
- **`requirements-tracer`** loads no codebase docs — only the requirements/spec file (`.specs/features/*/spec.md` or JIRA task).

Rationale: codebase docs are general project context that improves any dimension's review (e.g. `ARCHITECTURE.md` informs security trust boundaries and performance hot-paths alike). The per-agent token cost is small (docs are tiny next to the diff) and the orchestrator still holds none of it. Cross-dimension bleed is driven by *checklists*, not docs, so docs can be shared freely while checklists stay targeted.

**Prerequisite file change — strip Performance section from `review-checklist.md`:**

All 7 items in `review-checklist.md`'s `## Performance` section are already fully covered by `performance-checklist.md`. The section must be removed from `review-checklist.md` so that non-performance agents do not receive performance guidance and `performance-reviewer` is the single owner of that checklist.

**Agent → checklist loading matrix:**

| Agent | Self-loads | Rationale |
|-------|-----------|-----------|
| `architecture-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if stack matches) | Full non-performance baseline |
| `code-quality-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if stack matches) | Full non-performance baseline |
| `performance-reviewer` | `performance-checklist.md`, `<stack>-*-performance-review.md` (if stack matches) | Performance domain only |
| `regression-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if stack matches) | Full non-performance baseline |
| `security-reviewer` | None — relies on `security-best-practices` skill + model's built-in security knowledge | Security coverage comes from the dedicated skill, not checklists |
| `requirements-tracer` | None | Uses requirements context only |

**Stack-specific checklist detection**: The agent checks for files matching `references/<stack>-*-code-review.md` (for general agents) or `references/<stack>-*-performance-review.md` (for performance-reviewer). Stack is inferred from the `stack` availability key loaded in Step 2 from `.specs/codebase/STACK.md`. If no match, the agent proceeds without a tech-specific file.

**Mechanism**: Each agent's prompt shall include a `## Before You Begin` block listing the exact file paths to Read before starting the review — both its `references/` checklists and its `.specs/codebase/` docs. The orchestrator SHALL NOT load or inline any checklist or codebase-doc content in Steps 2–3; it retains only the **availability map** (which files exist) so it can tell each agent what is present to load.

**Single-agent (Medium tier) loading**: When the Medium tier dispatches one agent covering all active dimensions, its `## Before You Begin` block lists the **union** of the per-dimension checklists for the active dimension set (deduplicated), plus the **full codebase-doc set** (same as every reviewing agent). For a Medium `general` review that union is every non-performance checklist + `performance-checklist.md` + all stack-specific files + the full codebase-doc set (security still relies on the `security-best-practices` skill, no checklist).

**Acceptance Criteria:**

1. WHEN Step 2 (Context Collection) runs THEN the orchestrator SHALL NOT load file *content* from `references/` or `.specs/codebase/` — it only records presence/absence into the availability map.
2. WHEN each agent's prompt is assembled THEN it SHALL include a `## Before You Begin` block listing its assigned checklist files (per the checklist matrix) AND its codebase docs (per AC 3 — the full set for every reviewing agent) — all filtered to those marked present in the availability map.
3. WHEN any reviewing agent (all except `requirements-tracer`) is assembled THEN its codebase-doc load SHALL be the FULL set — `STACK`, `ARCHITECTURE`, `CONVENTIONS`, `STRUCTURE`, `INTEGRATIONS`, `CONCERNS` — excluding `TESTING.md`.
4. WHEN `performance-reviewer` receives its prompt THEN its checklist load SHALL be only `performance-checklist.md` (and `<stack>-*-performance-review.md` if available) — no other checklists — plus the full codebase-doc set.
5. WHEN `security-reviewer` receives its prompt THEN it SHALL have no checklist load instruction — it relies on the `security-best-practices` skill and its own training — but SHALL still load the full codebase-doc set if present.
6. WHEN `requirements-tracer` receives its prompt THEN it SHALL load no checklists and no codebase docs — only the requirements/spec file.
7. WHEN `review-checklist.md` is updated THEN it SHALL NOT contain a `## Performance` section — all performance items live exclusively in `performance-checklist.md`.
8. WHEN a file in an agent's `## Before You Begin` block is absent from the availability map THEN it SHALL be omitted from that agent's load list (the agent never attempts to Read a non-existent file).
9. WHEN any step or agent runs THEN `docs/TECH_DEBTS.md` SHALL NOT be loaded by anything — the `tech_debts` availability key SHALL be removed from Step 2, the Step 3 availability map, and the `code-quality-reviewer` optional-context column. No agent's `## Before You Begin` block references it.

**Independent Test**: Inspect each agent's assembled prompt. Verify `performance-reviewer` loads only `performance-checklist.md` (checklist) + the full codebase-doc set. Verify `security-reviewer` has no checklist load but loads the full codebase-doc set when present. Verify every reviewing agent's codebase-doc list is the full set (minus `TESTING.md`) and `requirements-tracer` loads none. Verify `review-checklist.md` has no Performance section. Verify the orchestrator Step 2 holds only an availability map — no file content from `references/` or `.specs/codebase/`. Grep the skill for `TECH_DEBTS` and `tech_debts` — both return zero matches.

---

## Edge Cases

- WHEN the changed file list is empty (e.g., rename-only PR) THEN the content type SHALL be `general` and the size tier SHALL be Small (0 files / 0 lines) → inline.
- WHEN a PR mixes source code AND documentation (e.g., feature + README update) THEN the content type SHALL be `general` — the source code files put all 5 dimensions in scope.
- WHEN a checklist or codebase-doc file referenced in a `## Before You Begin` block does not exist THEN the agent SHALL proceed without it and note the gap in its findings (same as current degraded-mode behavior).
- WHEN the content type is `docs-only` and the size tier is Small THEN the review SHALL be inline and cover only the Code Quality dimension (size tier governs the execution mode; content type governs which dimensions).
- WHEN the content type is `docs-only` and the size tier is Medium THEN one single agent SHALL review just the Code Quality dimension (the active set has one dimension).
- WHEN a change is small in file count but huge in lines (e.g., 1 file / 4,000 lines) THEN the size tier SHALL be Small (OR logic: `≤5 files` is satisfied) — accepted tradeoff: a single large file takes the inline path.
- WHEN a change sits exactly at a boundary (e.g., 15 files / 799 lines) THEN first-match-wins top-down evaluation resolves it (15≤15 AND 799<800 → Medium); 16 files / 799 lines → not Medium → Large.
- WHEN `requirements-tracer` is conditionally excluded (no spec/JIRA) THEN it is omitted regardless of content type or size tier.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|----------------|-------|-------|--------|
| CR-TOKEN-01 | P1: Noise File Exclusion — pathspec exclusion constant + apply in Step 4 (git modes) | Tasks | Pending |
| CR-TOKEN-02 | P1: Noise File Exclusion — filter excluded paths in GitHub PR mode | Tasks | Pending |
| CR-TOKEN-03 | P1: Noise File Exclusion — report header notes excluded count (transparency) | Tasks | Pending |
| CR-TOKEN-04 | P1: Complexity Assessment — 4-tier size logic (Small/Medium/Large/Complex → inline/single-agent/parallel/parallel+caveat), top-down first-match on post-exclusion metrics | Tasks | Pending |
| CR-TOKEN-05 | P1: Complexity Assessment — content-type detection + active dimension set; axis combination (mode × dimensions) | Tasks | Pending |
| CR-TOKEN-06 | P1: Complexity Assessment — emit explicit Review Plan before dispatch | Tasks | Pending |
| CR-TOKEN-07 | P1: Complexity Assessment — Medium single-agent execution (1 agent, all active dimensions, union loading) | Tasks | Pending |
| CR-TOKEN-08 | P1: Complexity Assessment — Complex-tier completeness caveat + thoroughness directive | Tasks | Pending |
| CR-TOKEN-09 | P1: Complexity Assessment — omit inactive dimensions from at-a-glance table; tier/type header note | Tasks | Pending |
| CR-TOKEN-10 | P1: Complexity Assessment — print user-visible complexity banner before any review work | Tasks | Pending |
| CR-TOKEN-11 | P1: Agent Self-Loaded Context — strip Performance section from `review-checklist.md` | Tasks | Pending |
| CR-TOKEN-12 | P1: Agent Self-Loaded Context — orchestrator Step 2 holds availability map only (no content) | Tasks | Pending |
| CR-TOKEN-13 | P1: Agent Self-Loaded Context — add `## Before You Begin` (targeted checklists + FULL codebase-doc set for every reviewing agent) to each agent prompt; Medium single-agent loads the union | Tasks | Pending |
| CR-TOKEN-14 | P1: Agent Self-Loaded Context — update agent roster Required/Optional context columns; purge `tech_debts`/`docs/TECH_DEBTS.md` from Step 2, availability map, and roster | Tasks | Pending |
| CR-TOKEN-15 | P1: Complexity Assessment — silent operation (only skill-invocation + banner + final report); strip `Files reviewed`/coverage roll-call from agent return format; findings detail preserved verbatim | Tasks | Pending |

---

## Success Criteria

- [ ] Lockfiles/generated/minified files are excluded from the diff at the `git diff` level — verified by reviewing a PR with a 3,000-line lockfile change and confirming the lockfile content is absent from agent prompts.
- [ ] Report header notes the count of excluded files (transparency, not silent drop).
- [ ] The complexity-assessment step emits an explicit Review Plan (tier + content type + execution mode + active dimensions + agent count) before any dispatch.
- [ ] A user-visible complexity banner is printed at the start of every review (all tiers, all modes) stating the detected tier, driving metrics, content type, and execution mode.
- [ ] A 9-file/420-line general change is classified Medium and runs exactly ONE agent covering all 5 dimensions (1× diff).
- [ ] A 20-file/600-line general change is classified Large and runs 5 parallel agents, no caveat.
- [ ] A 30-file/400-line general change is classified Complex: 5 parallel agents + completeness caveat in the header + thoroughness directive in each agent.
- [ ] The skill emits only three user-facing outputs (skill invocation → complexity banner → final report) with nothing in between — verified by running a review and confirming no progress/partial output appears.
- [ ] Agent returns carry findings only (no `Files reviewed`/coverage roll-call), and actual findings retain full detail in the final report.
- [ ] A docs-only PR scopes to the Code Quality dimension only (1 agent in Medium/Large, inline in Small) — not 5.
- [ ] A config-infra-only PR scopes to Security + Code Quality + Regression only.
- [ ] A general Large/Complex PR dispatches all 5 agents in parallel — no regression vs current behavior.
- [ ] Orchestrator Step 2 holds only an availability map — no file content from `references/` or `.specs/codebase/`.
- [ ] `review-checklist.md` has no `## Performance` section.
- [ ] `performance-reviewer` prompt contains a `## Before You Begin` block loading only `performance-checklist.md` (+ tech-specific perf file if available) for checklists, plus the full codebase-doc set.
- [ ] `security-reviewer` prompt has no checklist load but loads the full codebase-doc set when present.
- [ ] Every reviewing agent (all except `requirements-tracer`) loads the full codebase-doc set (`STACK`, `ARCHITECTURE`, `CONVENTIONS`, `STRUCTURE`, `INTEGRATIONS`, `CONCERNS`; not `TESTING.md`), filtered to present files.
- [ ] `requirements-tracer` prompt loads no checklists and no codebase docs.
- [ ] `docs/TECH_DEBTS.md` is loaded by nothing — grepping the skill for `TECH_DEBTS`/`tech_debts` returns zero matches.
- [ ] All non-performance reviewing agents load the full non-performance checklist baseline (review, clean-code, best-practices, observability) + stack-specific file, all on demand and filtered to present files.
- [ ] Output format (at-a-glance table, zoned findings, finding IDs) is unchanged for general PRs.
- [ ] At-a-glance table correctly omits rows for inactive agents (no "skipped" phantom rows).
