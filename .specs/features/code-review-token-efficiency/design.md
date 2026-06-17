# Code Review Token Efficiency — Design

**Spec:** [spec.md](spec.md) — Feature ID: CR-TOKEN  
**Status:** Draft  
**Target:** `skills/code-review/SKILL.md` (primary), `skills/code-review/references/review-checklist.md` (T1)

---

## Architecture Overview

The changes rework **three responsibilities** the orchestrator currently owns incorrectly and add **one new routing step**:

| Responsibility | Before | After |
|----------------|--------|-------|
| Checklist + codebase doc loading | Orchestrator loads content into main context | Agents self-load their own slice via `## Before You Begin` |
| Noise file exclusion | Happens at review time (guidance only) | Happens at diff collection time (pathspec exclusion, Step 4) |
| Dispatch routing | Binary: quick-mode inline OR always-5-parallel | 4-tier: inline / single-agent / parallel / parallel+caveat |
| Orchestrator context | Metadata + file content | Metadata only (availability map) |

**Step data flow (post-change):**

```
Step 1: Mode Detection
        ↓  mode
Step 2: Context Collection → availability map only (no file content loaded)
        ↓  availability map
Step 3: (collapsed) availability map passed forward
        ↓  {availability map}
Step 4: Diff Collection + EXCLUDE constant
        ↓  {diff, file list, excluded_count, diff_stat}
Step 5: Complexity Assessment
        ↓  Review Plan {tier, content_type, mode, active_dims, agent_count, excluded_count}
        → print complexity banner to user
Step 6: Dispatch (per Review Plan tier + active dimensions)
        ├─ Small  → inline review in orchestrator
        ├─ Medium → 1 agent (all active dims, union-loaded context)
        ├─ Large  → N agents in parallel (1 per active dim)
        └─ Complex → N agents in parallel + thoroughness directive + caveat flag
        ↓  findings only (no coverage roll-call)
Step 7: Await + Fallback (unchanged)
        ↓
Step 8: Consolidation
        → report header (excluded count, optional Tier/Type note, optional caveat)
        → at-a-glance table (active dims only, no phantom rows)
        → zoned findings
```

---

## Code Reuse Analysis

### Steps retained unchanged

| Step | What stays |
|------|-----------|
| Step 1 — Mode Detection | Unchanged; mode feeds Step 4 commands as before |
| Step 7 — Await + Fallback | Unchanged; degraded/failed handling unchanged |
| Step 8 — report format (shape) | Zoned format, finding IDs, zone letters, severity/priority/type — all unchanged |
| Step 9 — GitHub posting | Unchanged |
| Performance Audit mode | Unchanged; applies the same execution path as today |
| Reviewer stance | Unchanged; still injected into every agent |
| `requirements-tracer` skip logic | Unchanged; still skipped when `requirements` absent |

### Steps modified

| Step | What changes |
|------|-------------|
| Step 2 | Removes file content loading; converts to presence-only availability map; removes `tech_debts` row |
| Step 3 | Collapsed — produces availability map only, no bundle assembly in orchestrator |
| Step 4 | Adds EXCLUDE constant; applies to git commands; captures `excluded_count` |
| Step 5 | Replaces Quick Mode Check with 4-tier Complexity Assessment + Review Plan + banner |
| Step 6 | Reworks dispatch for 4 execution modes; adds `## Before You Begin` to agent template; updates Agent Roster; strips `Files reviewed` from return format |
| Step 8 | Adds excluded count to header; adds optional Tier/Type note; adds Complex caveat; silent-operation rule; omits inactive dimension rows from at-a-glance table |

### Files modified

| File | Change |
|------|--------|
| `skills/code-review/SKILL.md` | Primary target — all step changes above |
| `skills/code-review/references/review-checklist.md` | Remove `## Performance` section (T1) |

---

## Components (new concepts introduced)

### EXCLUDE Constant (Step 4)

- **Purpose:** Single named list of pathspec exclusions applied to every git diff command so noise files never enter any context.
- **Location:** Defined once in Step 4, referenced by all per-mode diff commands.
- **Content:** Lockfiles (`*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `composer.lock`, `Gemfile.lock`, `go.sum`, `Cargo.lock`, `poetry.lock`), minified/sourcemap assets (`*.min.js`, `*.min.css`, `*.map`), generated directories/patterns (`__snapshots__/`, `dist/`, `build/`, `vendor/`, `node_modules/`, `*.generated.*`).
- **Git mode application:** Appended to `git diff`/`git show` as `:(exclude)<pattern>` pathspecs.
- **GitHub PR mode:** Filter the changed-file list against the exclusion patterns before assembling the diff for agents.
- **Output:** `excluded_count` (integer) captured for Step 8 header.

### Review Plan (Step 5 output)

- **Purpose:** Explicit routing object that drives dispatch in Step 6 — makes the routing decision inspectable and auditable.
- **Fields:**

```
Review Plan:
  Size tier:         Small | Medium | Large | Complex
  Content type:      general | docs-only | config-infra-only | frontend-assets-only
  Execution mode:    inline | single-agent | parallel
  Active dimensions: [list]
  Agents dispatched: 0 | 1 | N
  Complex handling:  none | caveat + thoroughness directive
  Excluded files:    N
```

- **Tier logic (top-down, first match, post-exclusion metrics):**

| Tier | Condition | Execution mode |
|------|-----------|----------------|
| Small | ≤5 files **OR** <200 diff lines | Inline (0 agents) |
| Medium | ≤15 files **AND** <800 diff lines | Single agent (1×) |
| Large | ≤25 files **AND** <1,500 diff lines | Parallel (N×) |
| Complex | >25 files **OR** ≥1,500 diff lines | Parallel + caveat (N×) |

- **Content-type logic (all-or-nothing, changed file list only):**

| Content type | Detection |
|-------------|-----------|
| `general` | Any source file present (`.ts`, `.js`, `.py`, `.go`, `.rb`, `.java`, `.php`, `.cs`, `.rs`, `.kt`, `.swift`, `.c`, `.cpp`, `.h`, etc.) |
| `docs-only` | 100% of files match docs patterns (`*.md`, `*.txt`, `*.rst`, `*.mdx`, `docs/`, `README*`, `CHANGELOG*`, `*.adoc`) |
| `config-infra-only` | 100% of files match config/infra patterns (`*.yml`, `*.yaml`, `*.json`, `*.toml`, `Dockerfile*`, `*.tf`, `*.tfvars`, `.github/`, `*.env`, `*.ini`, `*.cfg`, `.eslintrc*`, `.prettier*`) |
| `frontend-assets-only` | 100% of files match styling/static patterns (`*.css`, `*.scss`, `*.less`, `*.svg`, `*.png`, `*.jpg`, `*.gif`, `*.ico`, `*.woff*`, `*.ttf`) |
| `mixed` / fallthrough | Multiple non-source types → `general` (all 5 dims active) |

- **Active dimension set by content type:**

| Content type | Active dimensions |
|-------------|------------------|
| `general` | All 5 + `requirements-tracer` (conditional) |
| `docs-only` | `code-quality-reviewer` + `requirements-tracer` (conditional) |
| `config-infra-only` | `security-reviewer`, `code-quality-reviewer`, `regression-reviewer` + `requirements-tracer` (conditional) |
| `frontend-assets-only` | `code-quality-reviewer`, `security-reviewer` + `requirements-tracer` (conditional) |

### Complexity Banner (Step 5, user-facing)

- **Purpose:** Single line printed to the user before any review work — makes the routing decision visible.
- **Format:** `🔍 Code review — Complexity: **<Tier>** (<N> files, <M> lines[· <X> excluded]) · Type: <content_type> · <Execution mode description>`
- **Complex example:** adds `(⚠️ completeness caveat)` suffix.
- **Constraint:** Printed **before** any agent dispatch or inline review begins, in every mode and tier including Small.

### `## Before You Begin` Block (Step 6 agent template)

- **Purpose:** Moves checklist and codebase-doc loading into each agent's ephemeral context, eliminating orchestrator content pre-loading.
- **Location:** Added to the agent prompt template in Step 6, before `## Role`.
- **Checklist loading matrix (per agent):**

| Agent | Checklists to self-load |
|-------|------------------------|
| `architecture-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if present) |
| `code-quality-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if present) |
| `performance-reviewer` | `performance-checklist.md`, `<stack>-*-performance-review.md` (if present) |
| `regression-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` (if present) |
| `security-reviewer` | None (relies on `security-best-practices` skill) |
| `requirements-tracer` | None |

- **Codebase-doc loading (every reviewing agent except `requirements-tracer`):**
  - Full set: `STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `STRUCTURE.md`, `INTEGRATIONS.md`, `CONCERNS.md`
  - Excluded: `TESTING.md` (test-strategy context, belongs to `tests-code-review`)
  - Filtered to files marked present in the availability map

- **Single-agent (Medium) variant:** loads the union of all active dimensions' checklists (deduplicated) + the full codebase-doc set.

### Medium Single-Agent Mode (Step 6 execution)

- **Purpose:** Reviews all active dimensions in one agent instance (1× diff cost instead of N×). The primary token win for the common case.
- **Trigger:** Review Plan tier = Medium.
- **Agent receives:** union `## Before You Begin` block + `## Role` listing ALL active dimensions + full diff.
- **Returns:** Findings tagged by dimension (same schema as parallel agents) — orchestrator consolidates normally.

---

## Key Behavioral Contracts Between Steps

| Producer → Consumer | Contract |
|--------------------|---------|
| Step 4 → Step 5 | Provides `file_count` and `diff_lines` measured **after** EXCLUDE applied; also `excluded_count` |
| Step 5 → Step 6 | Review Plan specifies exact execution mode and active dimension set; Step 6 executes per the plan, no re-evaluation |
| Step 5 → user | Complexity banner printed synchronously before any Step 6 work begins |
| Step 6 → Step 8 | Agent returns contain `Findings: [{severity, title, file, line, explanation, recommendation}]` — no `Files reviewed` list, no coverage roll-call |
| Step 4 → Step 8 (via plan) | `excluded_count` included in report header |
| Step 5 (Complex flag) → Step 8 | Complex tier → orchestrator adds completeness caveat to report header |

---

## Silent Operation Contract

Exactly **three** user-facing outputs, in order:
1. Skill-invocation announcement (existing transparency convention)
2. Complexity banner (new, from Step 5)
3. Final consolidated report (from Step 8)

Everything between banner and final report is silent. No progress narration, no per-agent partial findings, no intermediate commentary. This applies to all tiers (including Small inline) and all modes.

---

## Tech Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Routing strategy | Size-based (Option A) — NOT file-scope routing | Routing can't safely scope security/regression reviewers; Option A approved in spec |
| Medium tier implementation | Single delegated subagent (not inline) | Keeps orchestrator context lean; 1× diff cost vs N×; quality tradeoff acceptable at Medium size |
| Codebase docs sharing | Full set for every reviewing agent | Small per-agent cost; avoids re-evaluating which agent needs which doc; cross-dimension benefit is real |
| Checklist sharing | Targeted per dimension | Prevents cross-dimension finding bleed; performance-reviewer should not trigger architecture findings |
| Noise exclusion timing | At `git diff` command level (not post-hoc filtering) | Tokens never enter any context; compounds because every active agent would have received the noise |
| Orchestrator holds metadata only | Availability map (keys only), Review Plan, banner | Diff and reference material live only in agent ephemeral contexts — per the guiding principle |
| `requirements-tracer` | No checklists, no codebase docs | Needs only spec/JIRA context; codebase docs and checklists are irrelevant to tracing requirements |
