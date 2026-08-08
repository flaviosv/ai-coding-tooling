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
  version: "2.6.0"
  triggers:
    - "check my code"
    - "code review"
    - "code review the"
    - "do a code review"
    - "optimize performance"
    - "performance audit"
    - "performance bottleneck"
    - "performance review"
    - "review my changes"
    - "review my code"
    - "review PR #123"
    - "review this PR"
    - "run a code review"
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
- Noise files (lockfiles, generated code, minified assets) — excluded at the diff level via the EXCLUDE constant in Step 4; they never enter any context
- Files explicitly marked as "do not review"
- Test files — use **tests-code-review** skill

**New files are always in scope.** A freshly added file must be reviewed against all loaded checklists.

### GitHub PR Constraints

- **Never post comments to GitHub automatically.** Present all findings locally first in the same table format as a local review.
- Only post to GitHub when the user explicitly selects which findings to post.
- **NEVER create GitHub Issues** — all GitHub output goes to the PR as inline review comments only. Creating issues is strictly forbidden, no exceptions.
- Each comment must be anchored to the **exact line number** identified in the finding — never posted as a top-level PR comment or at the top of the file.
- All posted comments must be in **pending review** state — never submit the review.
- The user reviews and submits manually on GitHub.

### Subagent Model (hard requirement)

Every subagent dispatched in Step 6 — in every mode and every tier (Medium, Large, Complex, Performance Audit) — **must run on the most recent Sonnet model**, regardless of what model the current session is running on (even if the session is on Opus). When dispatching, explicitly set the model on each agent call; never omit it to let a dispatched agent inherit the session's model.

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

Check for the presence of the following files. Do **not** load their content — record only whether each file exists (`present`) or does not (`absent`). This presence/absence check feeds the availability map in Step 3.

**Codebase docs** — check under `docs/codebase/`:

| File | Availability key |
|------|-----------------|
| `STACK.md` | `stack` |
| `ARCHITECTURE.md` | `architecture` |
| `CONVENTIONS.md` | `conventions` |
| `CONCERNS.md` | `concerns` |
| `INTEGRATIONS.md` | `integrations` |
| `STRUCTURE.md` | `structure` |

**Review checklists** — check for presence only; tech-specific only when stack matches:

| File | Availability key |
|------|-----------------|
| `references/review-checklist.md` | `checklist_baseline` |
| `references/clean-code-checklist.md` | `checklist_clean_code` |
| `references/best-practices-code-review.md` | `checklist_best_practices` |
| `references/observability-code-review.md` | `checklist_observability` |
| `references/performance-checklist.md` | `checklist_performance` |
| `references/<stack>-*-code-review.md` (if match) | `checklist_tech_specific` |
| `references/<stack>-*-performance-review.md` (if match) | `checklist_tech_perf` |

**Other:**

| Item | Availability key |
|------|-----------------|
| Active spec file (`.specs/features/*/spec.md`) OR JIRA task ID detected in branch name, commit message, or PR description | `requirements` |

**Sonar project key** — check for presence; extract key if present:

| File | Availability key |
|------|-----------------|
| `sonar-project.properties` | `sonar_props` |
| `.sonarlint/connectedMode.json` | `sonar_sonarlint` |

Extract `sonar.projectKey` from `sonar-project.properties` if present; fall back to `projectKey` field in `.sonarlint/connectedMode.json`. Store the resolved key as `sonar_project_key` (string value, or `absent` if neither file exists).

## Step 3: Context Availability Map

Build the availability map from Step 2 results:

```
availability = {
  // codebase docs
  stack, architecture, conventions,
  concerns, integrations, structure,
  // checklists
  checklist_baseline, checklist_clean_code,
  checklist_best_practices, checklist_observability,
  checklist_performance, checklist_tech_specific, checklist_tech_perf,
  // other
  requirements,
  sonar_project_key  // resolved key string, or 'absent'
}
// each field: present | absent (except sonar_project_key: string or 'absent')
```

The orchestrator holds **this map only** — no file content. Agents self-load their own context using the `## Before You Begin` block in Step 6.

If a file in an agent's `## Before You Begin` list is absent from the availability map, the agent omits it silently and proceeds. If a **required** item is absent, flag that agent as `degraded`: it notes the gap in its findings and the at-a-glance table shows `⚠️ degraded — <missing item>`.

## Step 4: Diff Collection

### Noise Exclusion Constant

Define the following named constant before running any diff command. Every mode references this single list — never duplicate it:

```
EXCLUDE = [
  ':(exclude)*.lock'           ':(exclude)package-lock.json'  ':(exclude)yarn.lock'
  ':(exclude)pnpm-lock.yaml'   ':(exclude)composer.lock'      ':(exclude)Gemfile.lock'
  ':(exclude)go.sum'           ':(exclude)Cargo.lock'         ':(exclude)poetry.lock'
  ':(exclude)*.min.js'         ':(exclude)*.min.css'          ':(exclude)*.map'
  ':(exclude)**/__snapshots__/**'  ':(exclude)dist/**'        ':(exclude)build/**'
  ':(exclude)vendor/**'        ':(exclude)node_modules/**'    ':(exclude)*.generated.*'
]
```

### Collect Diff

Collect the diff and file list based on the mode from Step 1, applying EXCLUDE to every git command:

| Mode | Commands |
|------|----------|
| Local workspace | `git diff HEAD -- $EXCLUDE`, `git diff --cached -- $EXCLUDE`, `git ls-files --others --exclude-standard` |
| GitHub PR | `gh` if available and authenticated, else GitHub MCP (see [GitHub PR Mode — Step A](../../templates/github-pr-review-mode.md)); filter the changed-file list to remove any path matching the EXCLUDE patterns before assembling the diff for agents |
| Multi-commit (hashes) | `git show <h1> -- $EXCLUDE; git show <h2> -- $EXCLUDE; ...` — concatenated in order |
| Multi-commit (range) | `git diff <base>..<tip> -- $EXCLUDE` |
| Performance Audit | No diff — full codebase scan (EXCLUDE does not apply) |

Also collect:
- `git diff --stat -- $EXCLUDE` (or equivalent) — used in the report header
- Changed file list (after EXCLUDE applied) — used in complexity assessment and routing
- Count of files excluded by EXCLUDE — stored as `excluded_count` for the report header
- **Multi-commit only:** `git log --oneline <range>` or resolved hash+subject list — used in report header

In all modes: skip deleted files and test files when building the changed file list. Noise files (lockfiles, generated, minified) are already absent because EXCLUDE was applied at the diff command level.

## Step 4.5: Sonar Context Resolution

Run after Step 4 (diff file list is known) and before Step 5 (complexity assessment). Result is stored as `sonar_context`.

**MCP tool**: `search_sonar_issues_in_projects` (from the `sonarqube` MCP server)

```
IF sonar_project_key == 'absent':
    sonar_context = { status: 'skipped', skip_reason: 'no project key found' }
    GOTO Step 5

IF sonarqube MCP tools are unavailable in this session:
    sonar_context = { status: 'skipped', skip_reason: 'MCP not installed' }
    GOTO Step 5

ATTEMPT:
    # For GitHub PR mode, pass pullRequest=<PR key> instead of branch
    issues = search_sonar_issues_in_projects(
        projects=[sonar_project_key],
        branch=<current git branch>,         # omit for PR mode; use pullRequest=<PR key>
        issueStatuses=["OPEN"],
        files=[sonar_project_key + ":" + f for f in diff_file_list]
    )
    security_issues = [i for i in issues where "SECURITY" in i.impactSoftwareQualities]
    quality_issues  = [i for i in issues where "RELIABILITY" or "MAINTAINABILITY" in i.impactSoftwareQualities]
    sonar_context = {
        status: 'active',
        project_key: sonar_project_key,
        branch: <current branch>,
        issues_by_agent: {
            security_reviewer:     security_issues (sorted by severity desc, cap 30),
            code_quality_reviewer: quality_issues  (sorted by severity desc, cap 30)
        },
        summary: { total: N, security: N, quality: N }
    }

ON server unreachable / connection error:
    sonar_context = { status: 'skipped', skip_reason: 'server unreachable' }
ON MCP tool returns empty for this branch:
    sonar_context = { status: 'skipped', skip_reason: 'no data for branch <branch> — run sonar-scanner first' }
ON timeout:
    sonar_context = { status: 'skipped', skip_reason: 'query timeout' }
```

In every skipped state: proceed identically to pre-integration behavior. No agent receives a `## Sonar Findings` block.

## Step 5: Review Complexity Assessment

Using post-exclusion metrics from Step 4 (file count and diff lines after EXCLUDE applied), produce a **Review Plan** and print a **complexity banner** to the user before any review work begins.

### Axis 1 — Size Tier → Execution Mode

Evaluate **top-down, first match wins**:

| Tier | Condition (post-exclusion) | Execution mode |
|------|---------------------------|----------------|
| **Small** | ≤5 files **OR** <200 diff lines | **Inline** — orchestrator reviews active dimensions directly, 0 agents |
| **Medium** | ≤15 files **AND** <800 diff lines | **Parallel** — 1 subagent per active dimension dispatched together (N× diff) |
| **Large** | ≤25 files **AND** <1,500 diff lines | **Parallel** — 1 subagent per active dimension dispatched together (N× diff) |
| **Complex** | >25 files **OR** ≥1,500 diff lines | **Parallel + completeness handling** — same as Large, plus caveat and thoroughness directive |

**Multi-commit mode:** apply against combined diff totals across all commits.

### Axis 2 — Content Type → Active Dimensions

Inspect the changed file list (after EXCLUDE) to determine content type. "ALL changed files" means 100% of the non-deleted, non-excluded list matches the pattern. A single source code file → `general`. Evaluation uses file names only — no file content is read.

| Content type | Detection | Active dimensions |
|-------------|-----------|------------------|
| `general` (default) | Any source file present (`*.ts`, `*.js`, `*.py`, `*.go`, `*.rb`, `*.java`, `*.php`, `*.cs`, `*.rs`, `*.kt`, `*.swift`, `*.c`, `*.cpp`, `*.h`, etc.) | All 5 + `requirements-tracer` (conditional) |
| `docs-only` | 100% match: `*.md`, `*.txt`, `*.rst`, `*.mdx`, `docs/`, `README*`, `CHANGELOG*`, `*.adoc` | `code-quality-reviewer` + `requirements-tracer` (conditional) |
| `config-infra-only` | 100% match: `*.yml`, `*.yaml`, `*.json`, `*.toml`, `Dockerfile*`, `*.tf`, `*.tfvars`, `.github/`, `*.env`, `*.ini`, `*.cfg`, `.eslintrc*`, `.prettier*` | `security-reviewer`, `code-quality-reviewer`, `regression-reviewer` + `requirements-tracer` (conditional) |
| `frontend-assets-only` | 100% match: `*.css`, `*.scss`, `*.less`, `*.svg`, `*.png`, `*.jpg`, `*.gif`, `*.ico`, `*.woff*`, `*.ttf` | `code-quality-reviewer`, `security-reviewer` + `requirements-tracer` (conditional) |
| `mixed` | Multiple non-source types, no source files | Fall through to `general` |

Edge cases:
- Empty changed list (rename-only): `general`, Small (0 files / 0 lines) → inline.
- Mixed source + docs: `general` — the source file triggers full 5-dimension scope.
- `requirements-tracer` is omitted regardless of type when `requirements` is absent (no spec/JIRA found in Step 2).

### Review Plan

The assessment emits an explicit plan consumed by Step 6:

```
Review Plan:
  Size tier:         Small | Medium | Large | Complex
  Content type:      general | docs-only | config-infra-only | frontend-assets-only
  Execution mode:    inline | parallel
  Active dimensions: [<dimension list>]
  Agents dispatched: 0 (inline) | N (parallel)
  Complex handling:  none | caveat + thoroughness directive
  Excluded files:    N
```

### Complexity Banner

Immediately after the assessment, print this one-line banner to the user **before any dispatch or inline review begins**. This is required in every mode and every tier, including Small.

```
🔍 Code review — Complexity: **<Tier>** (<N> files, <M> lines[· <X> excluded]) · Type: <content_type> · <execution description>
```

Examples:
```
🔍 Code review — Complexity: **Complex** (32 files, 1,840 lines · 3 excluded) · Type: general · Parallel — 5 agents (⚠️ completeness caveat)
🔍 Code review — Complexity: **Medium** (9 files, 420 lines) · Type: general · Parallel — 5 agents
🔍 Code review — Complexity: **Small** (2 files, 60 lines) · Type: docs-only · Inline review (Code Quality only)
```

### Silent Operation

After the complexity banner, the skill produces **no further output** until the final consolidated report. Specifically prohibited between the banner and the report:
- Progress narration ("dispatching agents", "now reviewing…", "agent X returned")
- Partial or per-agent findings printed as they arrive
- Any intermediate analytical commentary

## Step 6: Dispatch

Execute the Review Plan from Step 5. The execution mode determines how active dimensions run; the active dimension set (from content type) determines which agents/dimensions are in scope.

**Every agent dispatched below must be pinned to the most recent Sonnet model** (see [Subagent Model](#subagent-model-hard-requirement) in Guardrails) — set this explicitly on every dispatch, independent of the session's own model.

### Execution Modes

#### Small — Inline (0 agents)

Apply the reviewer stance directly in the orchestrator across all active dimensions. No subagents. Proceed to Step 8 (Consolidation) when done.

#### Medium / Large — Parallel (one agent per active dimension)

Fire all active dimension agents in a **single parallel message. Never sequentially.** Each receives its own `## Before You Begin` block (targeted to its dimension) plus the full codebase-doc set.

#### Complex — Parallel + Completeness Handling

Same as Large. Additionally:
- Each dispatched agent receives the **thoroughness directive** (below) in its prompt.
- The report header (Step 8) carries the completeness caveat.

**Thoroughness directive** (Complex tier only — added to each agent's prompt):
> This is a Complex review (large change set). Review every file in the diff thoroughly. Do not skip or skim any file. Focus on your assigned dimension across all changed files.

### Agent Prompt Template

Every agent (in all modes except Small inline) receives a prompt structured as:

```
## Before You Begin

Read the following files before starting the review. Skip any file marked absent.

Checklists (load only if present per availability map):
- [list of this agent's assigned checklist files — see Checklist Matrix below]

Codebase docs (load each if present, from docs/codebase/):
- docs/codebase/STACK.md
- docs/codebase/ARCHITECTURE.md
- docs/codebase/CONVENTIONS.md
- docs/codebase/STRUCTURE.md
- docs/codebase/INTEGRATIONS.md
- docs/codebase/CONCERNS.md

## Role
<agent name and dimension>

## Diff
<full diff from Step 4>

## Sonar Findings
<inject this block ONLY when sonar_context.status == 'active' AND this agent has entries in sonar_context.issues_by_agent>
<omit this entire section — do not inject an empty block — when no issues are mapped to this agent>

SonarQube detected the following issues on branch `<branch>` in files within this diff.
Use as additional signal — they do not replace your analysis.

| Type | Severity | Rule | File | Line | Message |
|------|----------|------|------|------|---------|
<one row per issue from sonar_context.issues_by_agent[this_agent], sorted severity desc, max 30>

## Return format
Status: Complete | Blocked | Partial
Dimension: <agent name or "all dimensions">
Findings: [{severity, title, file, line, explanation, recommendation}]
Issues: <any blockers encountered>
```

The orchestrator **does not inline** any checklist or codebase-doc content — the `## Before You Begin` block is a Read instruction for the agent, not pre-loaded content.

### Checklist Matrix (agent → checklists to self-load)

| Agent | Checklists to load (if present) |
|-------|--------------------------------|
| `architecture-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` |
| `code-quality-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` |
| `performance-reviewer` | `performance-checklist.md`, `<stack>-*-performance-review.md` |
| `regression-reviewer` | `review-checklist.md`, `clean-code-checklist.md`, `best-practices-code-review.md`, `observability-code-review.md`, `<stack>-*-code-review.md` |
| `security-reviewer` | None — relies on `security-best-practices` skill + built-in security knowledge |
| `requirements-tracer` | None — uses requirements/spec file only; no codebase docs |

Codebase docs: all reviewing agents except `requirements-tracer` self-load the full set: `STACK`, `ARCHITECTURE`, `CONVENTIONS`, `STRUCTURE`, `INTEGRATIONS`, `CONCERNS`. `TESTING.md` is excluded (belongs to `tests-code-review`). All loads filtered to files present in the availability map.

### Agent Roster

| Agent | Dimension | Degrades without |
|-------|-----------|-----------------|
| `architecture-reviewer` | Layer violations, coupling, pattern misuse | `architecture` |
| `code-quality-reviewer` | Naming, complexity, SOLID, DRY, KISS, clean code; inline docs, API docs, obsolete/misleading comments | `conventions` |
| `performance-reviewer` | N+1, allocations, blocking calls, missing indexes | — |
| `regression-reviewer` | Unrelated deletions, phantom imports, AI hallucination artifacts, weakened assertions | — |
| `security-reviewer` | Auth, injection, secrets, data exposure | — |
| `requirements-tracer` | Does the change satisfy the stated spec/task | **Skip entirely** if `requirements` absent — omit from at-a-glance table |

### Reviewer Stance (injected into every agent)

You are the villain. Find every flaw, violation, and risk — not encourage.

- Be relentless. Code is guilty until proven innocent.
- Every principle violated is worth flagging — no "minor" issues.
- Flag issues even if possibly intentional — surface them regardless.
- State problems directly: file, line number, consequence.
- Never sign off on violations just because they are small.
- Only report a finding when confidence is ≥ 80%. If uncertain whether a pattern is a violation, skip it — do not guess.

### Performance Audit mode exception

In Performance Audit mode: `architecture-reviewer` and `performance-reviewer` scan the full codebase. All other agents scope to changed files only. `requirements-tracer` is skipped. Complexity assessment (Step 5) is skipped — Performance Audit always uses parallel dispatch.

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

## Step 7: Await + Fallback

Wait for all dispatched agents to return. For each agent, resolve its outcome:

| Outcome | Action |
|---------|--------|
| Returned normally | Parse structured result |
| Failed or timed out | Mark dimension as `⚠️ not executed — <reason>` |
| Degraded (missing required context) | Mark dimension as `⚠️ degraded — <missing item>` |
| `requirements-tracer` skipped (no spec/JIRA) | Omit row from at-a-glance table entirely |

Continue to Step 8 regardless of individual agent outcomes. A failed agent never blocks the report.

## Step 8: Consolidation and Present Findings

The **only user-facing outputs** in this skill, in this order, are: (1) the skill-invocation announcement, (2) the complexity banner (from Step 5), and (3) this consolidated report. Nothing is emitted between the banner and this report.

### Report header (always first)

```
# <TASK-ID or branch> — Code Review
Scope: <N files reviewed[, M excluded as generated/lockfiles]>
Branch: <branch>
Commits: <hash — subject>, <hash — subject>, ...   ← multi-commit mode only
Diff: <N files changed, +X insertions, -Y deletions>
Run: <date>
Mode: local | GitHub PR #N | multi-commit | performance audit
Sonar: <status line — see variants below>
[Tier: <tier> | Type: <content_type>]              ← omit when tier=Large/Complex AND type=general; show when type ≠ general OR tier ∈ {Large, Complex}
[⚠️ Complex review (N files / M lines) — findings are best-effort and may be non-exhaustive. Consider splitting this PR.]  ← Complex tier only
```

**Sonar status line variants:**

| Condition | Status line |
|-----------|-------------|
| Active with issues | `Sonar: active — N issues (S security, Q quality) · branch <branch>` |
| Active, 0 issues | `Sonar: active — 0 issues · branch <branch>` |
| Skipped — no project key | `Sonar: skipped — no project key found` |
| Skipped — MCP not installed | `Sonar: skipped — MCP not installed` |
| Skipped — server unreachable | `Sonar: skipped — server unreachable` |
| No branch data | `Sonar: no data for branch <branch> — run sonar-scanner first` |
| Skipped — query timeout | `Sonar: skipped — query timeout` |

Include `excluded_count` in the `Scope` line whenever `excluded_count > 0`. Include the `Tier/Type` line whenever the content type is not `general` OR the tier is `Large` or `Complex`. Include the completeness caveat only when the tier is `Complex`.

### At-a-glance table (always second)

One row per **active** dimension only — omit rows for dimensions not in the active set. Do not show "skipped" or "not executed" for inactive dimensions; their absence is intentional.

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Architecture | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Code Quality & Docs | ... | N | N | N | 1-line |
| Performance | ... | N | N | N | 1-line |
| Regression & Hallucination | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Security | ... | N | N | N | 1-line |
| Requirements | ✅ / ⚠️ (only if active spec/JIRA) | — | — | coverage summary |

Show only the rows for active dimensions. For example, a `docs-only` review shows only Code Quality (and Requirements if active).

### Output format

**Flat format** — use when findings are few and span a single dimension:

| # | Severity | Priority | Title | Type | File:Line | Explanation |
|---|----------|----------|-------|------|-----------|-------------|

**Zoned format** — use when findings are many or span multiple dimensions (default for subagent reviews):

Agent dimensions map directly to zones. Zone letter assignment:

| Zone | Letter | Agent |
|------|--------|-------|
| Architecture | A | `architecture-reviewer` |
| Code Quality & Docs | Q | `code-quality-reviewer` |
| Performance | P | `performance-reviewer` |
| Regression & Hallucination | H | `regression-reviewer` |
| Requirements | R | `requirements-tracer` |
| Security | S | `security-reviewer` |

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
2. **No TLC feature folder** → ask the user where to save it (default: the project root).

Match the changed files / TASK-ID to an existing directory under `.specs/features/`. If none exists, use the fallback. Use `code-review_phase2.md` (then `_phase3`, …) for subsequent passes.

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
2. Step 2: Check presence of `docs/codebase/` docs and `references/` checklists; check for active spec or JIRA task ID — build availability map (no content loaded by orchestrator)
3. Step 3: Availability map ready (presence/absence only)
4. Step 4: `git diff HEAD -- $EXCLUDE` + `git diff --cached -- $EXCLUDE` + `git ls-files --others --exclude-standard`; collect `git diff --stat -- $EXCLUDE`; record `excluded_count`
5. Step 5: Complexity assessment — emit Review Plan and complexity banner; route to execution mode (Small → inline, Medium/Large/Complex → parallel)
6. Step 6: Dispatch per Review Plan (one agent per active dimension, fired in parallel); each agent self-loads checklists + codebase docs via `## Before You Begin`
7. Step 7: Await all results; mark any failures/degraded agents
8. Step 8: Report header (with excluded count if any) → at-a-glance table (active dimensions only) → zoned findings; iterative review until P0/P1 resolved

### Example 2: GitHub PR review

User: "review PR #42"

1. Step 1: PR #42 → GitHub PR mode
2. Step 2: Check presence of `docs/codebase/` docs and `references/` checklists; check PR description for JIRA task ID — build availability map
3. Step 3: Availability map ready
4. Step 4: Fetch diff via `gh` (or GitHub MCP if `gh` unavailable); filter changed-file list to remove EXCLUDE-matching paths; record `excluded_count`
5. Step 5: Complexity assessment — emit banner; route to execution mode
6. Step 6: Dispatch per Review Plan execution mode against PR diff only — ignore local workspace; agents self-load context via `## Before You Begin`
7. Step 7: Await results
8. Step 8: Consolidated report with at-a-glance table (active dimensions only)
9. Step 9: User selects findings to post → create pending review comments via `gh` (or GitHub MCP); user submits manually on GitHub

### Example 3: Performance audit

User: "do a performance audit of the orders module"

1. Step 1: Trigger phrase matches → Performance Audit mode
2. Step 2: Check presence of `docs/codebase/` docs and `references/` checklists — build availability map
3. Step 3: Availability map ready
4. Step 4: No diff — full codebase scan (EXCLUDE does not apply)
5. Step 5: Complexity assessment skipped — Performance Audit always uses parallel dispatch
6. Step 6: Dispatch `architecture-reviewer` and `performance-reviewer` against full codebase; `regression-reviewer`, `security-reviewer`, `code-quality-reviewer` scope to changed files only; `requirements-tracer` skipped; each agent self-loads via `## Before You Begin`
7. Step 7: Await results
8. Step 8: Produce Performance Audit Report in the format above

### Example 4: Multi-commit review

User: "review commits abc123 def456 ghi789"

1. Step 1: Commit hashes detected → multi-commit mode
2. Step 2: Check presence of `docs/codebase/` docs and `references/` checklists; check commit messages for JIRA task IDs — build availability map
3. Step 3: Availability map ready
4. Step 4: `git show abc123 -- $EXCLUDE; git show def456 -- $EXCLUDE; git show ghi789 -- $EXCLUDE` — concatenated into one combined diff; collect commit list (hash + subject) for report header; record `excluded_count`
5. Step 5: Complexity assessment applied against combined diff totals; emit banner; route to execution mode
6. Step 6: Dispatch per Review Plan execution mode against the combined diff; agents self-load context via `## Before You Begin`
7. Step 7: Await results
8. Step 8: Single consolidated report — header lists all 3 commits and excluded count; at-a-glance table (active dimensions only) + findings as normal
