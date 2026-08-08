# Design — Code Review Subagent Orchestration (CR-SUBAGENT)

**Status:** Draft  
**Spec:** [spec.md](spec.md)

---

## Overview

The current SKILL.md is a single-agent, 8-step sequential pipeline. This design restructures it into an **orchestrator + 7 parallel subagents** model. The orchestrator owns context collection, dispatch, and consolidation. Subagents own reviewing within their dimension.

The 8 steps become two conceptual layers:

```
ORCHESTRATOR (main agent context)
├── Step 1: Mode detection
├── Step 2: Context collection (all .specs/codebase/ + checklists)
├── Step 3: Context availability check + bundle assembly
├── Step 4: Diff collection
├── Step 5: Quick mode check → fallback to inline if triggered
├── Step 6: Dispatch 7 subagents in parallel  ← boundary
│   ├── architecture-reviewer
│   ├── code-quality-reviewer
│   ├── security-reviewer
│   ├── performance-reviewer
│   ├── docs-comments-reviewer
│   ├── build-test-validator
│   └── requirements-tracer
├── Step 7: Await all results + fallback handling
├── Step 8: Consolidate → flat or zoned output
└── Step 9: Post to GitHub (GitHub PR mode only — unchanged)
```

Steps 1–5 and 7–9 run in the orchestrator. Step 6 is the parallel boundary.

---

## Step 1 — Mode Detection

Parse the user's request before touching any files. Resolve to exactly one mode:

| Priority | Trigger | Mode |
|----------|---------|------|
| 1 | "performance audit", "performance review", "slow code", etc. | Performance Audit |
| 2 | "review commits X Y", "review commits X..Y", "review last N commits" | Multi-commit |
| 3 | PR number present (e.g. "review PR #42") | GitHub PR |
| 4 | Default | Local workspace |

Mode is fixed for the rest of the pipeline — no re-detection later.

---

## Step 2 — Context Collection

Load all of the following in one pass. Each item is either present (loaded) or absent (noted in availability map):

**Codebase docs** (from `.specs/codebase/` — fall back to `docs/codebase/` then `docs/`):

| File | Status field in availability map |
|------|----------------------------------|
| `STACK.md` | `stack` |
| `ARCHITECTURE.md` | `architecture` |
| `CONVENTIONS.md` | `conventions` |
| `TESTING.md` | `testing` |
| `CONCERNS.md` | `concerns` |
| `INTEGRATIONS.md` | `integrations` |
| `STRUCTURE.md` | `structure` |

**Review checklists** (from `references/` — all mandatory baselines always loaded):

| File | Status field |
|------|-------------|
| `references/review-checklist.md` | `checklist_baseline` |
| `references/clean-code-checklist.md` | `checklist_clean_code` |
| `references/best-practices-code-review.md` | `checklist_best_practices` |
| `references/performance-checklist.md` | `checklist_performance` |
| `references/<stack>-*-code-review.md` (if match) | `checklist_tech_specific` |
| `references/<stack>-*-performance-review.md` (if match) | `checklist_tech_perf` |

**Other:**

| Item | Status field |
|------|-------------|
| `docs/TECH_DEBTS.md` | `tech_debts` |
| Active spec or task description | `requirements` |

---

## Step 3 — Context Availability Map + Bundle Assembly

Build a map of what is available. This drives degraded mode warnings (REQ-11).

```
availability = {
  stack: present | absent,
  architecture: present | absent,
  conventions: present | absent,
  testing: present | absent,
  concerns: present | absent,
  integrations: present | absent,
  structure: present | absent,
  checklist_baseline: present | absent,
  checklist_clean_code: present | absent,
  checklist_best_practices: present | absent,
  checklist_performance: present | absent,
  checklist_tech_specific: present | absent,
  checklist_tech_perf: present | absent,
  tech_debts: present | absent,
  requirements: present | absent
}
```

Assemble a **context bundle** per agent (see Agent Roster below). Each bundle is a structured block of text injected into the agent's prompt — only the items from the availability map that are marked `present` and relevant to that agent.

If a bundle is missing a required item, the agent is flagged as `degraded` for that item in the at-a-glance table.

---

## Step 4 — Diff Collection

Collect the diff based on mode:

| Mode | Commands |
|------|----------|
| Local workspace | `git diff HEAD`, `git diff --cached`, `git ls-files --others --exclude-standard` |
| GitHub PR | `gh pr diff <PR#>` (or GitHub MCP if available) |
| Multi-commit (hashes) | `git show <h1>; git show <h2>; ...` — concatenated |
| Multi-commit (range) | `git diff <base>..<tip>` |
| Performance Audit | No diff — full codebase scan |

Also collect:
- `git diff --stat` (or equivalent) → used in report header (REQ-08)
- Changed file list → used to route file slices to agents
- For multi-commit: commit list (hash + subject) → used in report header

---

## Step 5 — Quick Mode Check

**Condition:** changed file count ≤ 2 AND total diff lines < 100  
**Action:** skip subagent dispatch; fall back to the original inline review flow (Steps 5–7 of the legacy pipeline)  
**Note:** In multi-commit mode, apply this check against the combined diff.

---

## Step 6 — Parallel Subagent Dispatch

All 7 agents MUST be fired in a single message. The orchestrator constructs each agent's prompt using the bundle assembled in Step 3 and the diff from Step 4.

### Agent Roster and Context Bundles

Each agent's prompt has four sections:

```
## Role
<agent name and dimension>

## Context
<inlined content from context bundle — only items marked present and relevant>

## Diff
<full diff — all agents receive the full diff; slicing is in the context, not the code>

## Return format
<structured return schema — see REQ-04>
```

**Why full diff per agent, not file slices:** All dimensions (security, performance, architecture) can have findings in any file. Slicing by file would cause agents to miss cross-cutting issues. The "minimal context" in REQ-03 is achieved by scoping the *context docs and checklists* per agent, not the diff.

#### Agent context bundle definitions

| Agent | Required context | Optional context | Degrades without |
|-------|-----------------|------------------|-----------------|
| `architecture-reviewer` | `checklist_baseline` | `architecture`, `structure`, `stack`, `concerns` | `architecture` |
| `code-quality-reviewer` | `checklist_clean_code`, `checklist_best_practices` | `conventions`, `stack`, `concerns`, `tech_debts`, `checklist_tech_specific` | `conventions` |
| `security-reviewer` | `checklist_baseline` (security section) | `integrations`, `stack`, `concerns` | — (runs on diff alone) |
| `performance-reviewer` | `checklist_performance` | `stack`, `integrations`, `concerns`, `checklist_tech_perf` | — (runs on diff alone) |
| `docs-comments-reviewer` | `checklist_baseline` (docs section) | `conventions`, `stack` | — (runs on diff alone) |
| `build-test-validator` | — | `testing` | `testing` (falls back to standard commands) |
| `requirements-tracer` | `requirements` | — | skipped entirely if `requirements` absent (REQ-06) |

---

## Step 7 — Await + Fallback

Wait for all agents to return. For each agent:

- **Returned normally** → parse structured result
- **Failed / timed out** → mark dimension as `⚠️ not executed — <reason>` (REQ-06)
- **Degraded (missing context)** → mark dimension as `⚠️ degraded — <missing item>` (REQ-11)
- **requirements-tracer skipped** → mark as `➖ skipped — no requirements available`

Continue to consolidation regardless of individual agent outcomes.

---

## Step 8 — Consolidation

### At-a-glance table (always first)

One row per agent dimension:

| Dimension | Status | Findings | Critical | High | Summary |
|-----------|--------|----------|----------|------|---------|
| Architecture | ✅ / ⚠️ degraded / ⚠️ not executed | N | N | N | 1-line |
| Code Quality | ... | | | | |
| Security | ... | | | | |
| Performance | ... | | | | |
| Docs & Comments | ... | | | | |
| Build & Tests | ✅ pass / ❌ fail / ⚠️ | — | — | gate result |
| Requirements | ✅ / ➖ skipped | — | — | coverage summary |

### Report header

```
# <TASK-ID or branch> — Code Review
Scope: <files reviewed>
Branch: <branch> | Commits: <hash list + subjects> (multi-commit mode)
Diff: <N files changed, +X -Y lines>
Run: <date>
Modes: <local | GitHub PR #N | multi-commit | performance audit>
```

### Output format selection

Same rules as current SKILL.md:
- **Flat format** → few findings, single area
- **Zoned format** → many findings or multi-zone; agent dimensions map directly to zones

Zone letter assignment: use first letter of agent name (A = Architecture, Q = Quality, S = Security, P = Performance, D = Docs, B = Build, R = Requirements).

### Finding ID scheme

`<ZoneLetter><SequenceNumber>` within each zone — e.g. `A1`, `Q3`, `S2`. Unchanged from current skill.

---

## Step 9 — Post to GitHub (GitHub PR mode only)

Unchanged from current SKILL.md Step 8. No subagent involvement.

---

## What Changes vs What Stays the Same

| Aspect | Current | New |
|--------|---------|-----|
| Step count | 8 steps, all inline | 9 steps; Steps 6 dispatches subagents |
| Context loading | Steps 2–3 (STACK + ARCH only) | Step 2 (all 7 codebase docs + all checklists) |
| Review execution | Sequential, inline | 7 parallel subagents |
| Output formats | Flat / Zoned | Same — agents map to zones |
| Finding IDs | Zone-prefix | Same scheme, zone letters updated |
| GitHub PR posting | Step 8 | Step 9 (renumbered, unchanged) |
| Performance Audit | Inline | architecture + performance agents; others skip |
| Quick mode | Implicit (small diffs just go fast) | Explicit check at Step 5; reverts to inline |
| Multi-commit | Not supported | Step 1 detects; diff aggregated; single report |

---

## Files to Modify

| File | Change |
|------|--------|
| `skills/code-review/SKILL.md` | Full restructure — replace Steps 1–8 with the 9-step orchestrator flow above |

No new files. No changes to `reference.md`, `references/`, or any other skill.
