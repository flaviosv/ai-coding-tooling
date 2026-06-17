# Code Review Token Efficiency — Tasks

**Spec:** [spec.md](spec.md) — Feature ID: CR-TOKEN
**Target files:** `skills/code-review/SKILL.md` (primary), `skills/code-review/references/review-checklist.md` (one edit)
**Status:** Complete

---

## Testing note

These are **markdown skill files**, not implementation code. Per the project CLAUDE.md ("do not apply test-coverage heuristics to `.md` files"), there is no test suite and no `TESTING.md` coverage matrix in scope. Verification for every task is **grep / structural inspection** of the edited file — captured in each task's `Verify` block. `Tests: none` is therefore correct for all tasks (it reflects the coverage matrix's "none" for documentation, not test deferral).

**Tools (all tasks):** `Edit`, `Read`, `Grep`/`Bash` (grep verification). No MCPs. No skills.

---

## Execution Plan

All `SKILL.md` edits touch one file → they run **sequentially, top-down by document position** (Step 2 → Step 4 → Step 5 → Step 6 → Step 8 → Examples). `T1` edits a different file (`review-checklist.md`) and is the only parallel-safe task.

```
T1 [P] ── (review-checklist.md, independent)

T2 ──→ T3 ──→ T4 ──→ T5 ──→ T6 ──→ T7        (all SKILL.md, sequential)
```

- **Phase 1:** T1 (parallel-safe) + T2 can start together (different files).
- **Phase 2:** T3 → T4 → T5 → T6 → T7 in order (same file, each builds on prior sections).

---

## Task Breakdown

### T1: Strip `## Performance` section from `review-checklist.md` [P]

**What:** Remove the entire `## Performance` section from the baseline review checklist (its 7 items are fully covered by `performance-checklist.md`; performance-reviewer becomes the sole owner).
**Where:** `skills/code-review/references/review-checklist.md`
**Depends on:** None
**Reuses:** `performance-checklist.md` (already contains every item — no content migration needed)
**Requirement:** CR-TOKEN-11

**Tools:** Edit, Grep

**Done when:**
- [x] The `## Performance` heading and all its bullet items are removed from `review-checklist.md`.
- [x] No other section is touched.

**Verify:**
```
grep -c "^## Performance" skills/code-review/references/review-checklist.md   # → 0
grep -c "^## " skills/code-review/references/review-checklist.md              # → one fewer than before
```

**Tests:** none **Gate:** inspection
**Commit:** `refactor(code-review): remove Performance section from review-checklist (owned by performance-checklist)`

---

### T2: Step 2 + Step 3 — availability-map-only context; purge `tech_debts`

**What:** Reduce Context Collection to recording **presence/absence only** (no checklist or codebase-doc content loaded by the orchestrator); collapse Step 3 bundle-assembly to availability-map only; remove the `tech_debts` key and `docs/TECH_DEBTS.md` from Step 2 and the availability map.
**Where:** `skills/code-review/SKILL.md` — Step 2 (Context Collection), Step 3 (Context Availability Map + Bundle Assembly)
**Depends on:** None (functionally); same file as T3–T7 so ordered first
**Reuses:** Existing Step 2/3 structure and availability-map concept
**Requirement:** CR-TOKEN-12, CR-TOKEN-14 (Step 2 + availability-map portion)

**Tools:** Edit, Grep

**Done when:**
- [x] Step 2 no longer instructs loading file **content** from `references/` or `.specs/codebase/` — only records present/absent into the availability map.
- [x] The "Review checklists" loading table is removed/converted to presence-only (no content load).
- [x] `docs/TECH_DEBTS.md` row and `tech_debts` key removed from Step 2 and the Step 3 availability-map structure.
- [x] Step 3 describes producing the availability map only — no inlined "context bundle" content assembly.

**Verify:**
```
grep -ni "tech_debt" skills/code-review/SKILL.md            # → only matches inside Step 6 roster (removed in T5) or none here
# Manual: Step 2/3 contain no instruction to read file *content* from references/ or .specs/codebase/
```

**Tests:** none **Gate:** inspection
**Commit:** `refactor(code-review): orchestrator holds availability map only; drop tech_debts`

---

### T3: Step 4 — noise file exclusion at diff collection

**What:** Add the pathspec exclusion list as a single named constant and apply it to every git-based diff command; filter excluded paths in GitHub PR mode; capture the excluded-file count for the report header.
**Where:** `skills/code-review/SKILL.md` — Step 4 (Diff Collection)
**Depends on:** T2
**Reuses:** Existing Step 4 per-mode command table; existing "What NOT to Review" intent
**Requirement:** CR-TOKEN-01, CR-TOKEN-02, CR-TOKEN-03 (capture)

**Tools:** Edit, Grep

**Done when:**
- [x] A single named `EXCLUDE` pathspec constant is defined (lockfiles, `*.min.*`, `*.map`, `__snapshots__`, `dist/`, `build/`, `vendor/`, `node_modules/`, `*.generated.*`, per spec list).
- [x] `git diff`/`git show` commands for local + multi-commit modes apply the exclusion constant.
- [x] GitHub PR mode filters excluded paths from the changed-file list before assembling the diff.
- [x] Step 4 records the count of excluded files for later use in the report header.
- [x] The exclusion list is referenced (not duplicated) across modes.

**Verify:**
```
grep -ni "exclude" skills/code-review/SKILL.md   # → exclusion constant present, referenced by modes
# Manual: each mode's diff command references the single EXCLUDE constant
```

**Tests:** none **Gate:** inspection
**Commit:** `feat(code-review): exclude lockfiles/generated/minified from diff at collection`

---

### T4: Step 5 — Review Complexity Assessment & Routing (+ banner)

**What:** Replace the current "Step 5: Quick Mode Check" with the Complexity Assessment step: 4-tier size logic (Small/Medium/Large/Complex → inline/single-agent/parallel/parallel+caveat, top-down first-match on post-exclusion metrics), content-type detection (general/docs-only/config-infra-only/frontend-assets-only), the axis-combination rules, the emitted Review Plan, and the user-visible complexity banner.
**Where:** `skills/code-review/SKILL.md` — Step 5
**Depends on:** T3 (post-exclusion metrics feed the size tier)
**Reuses:** Existing quick-mode threshold (`≤5 files OR <200 lines` → Small/inline); existing mode-detection table
**Requirement:** CR-TOKEN-04, CR-TOKEN-05, CR-TOKEN-06, CR-TOKEN-10

**Tools:** Edit, Grep

**Done when:**
- [x] Size-tier table present with the 4 tiers, exact thresholds, and "top-down, first match wins" rule.
- [x] Content-type detection table present (the 4 types + `mixed` → general fallthrough).
- [x] Axis-combination subsection present (execution mode × active dimensions).
- [x] Review Plan block defined (tier, content type, execution mode, active dimensions, agents-dispatched count, Complex flag, excluded count).
- [x] Complexity banner specified to print before any dispatch/inline review, all modes/tiers, with the exact fields.
- [x] Old "Quick Mode Check" framing replaced (Small tier subsumes it).

**Verify:**
```
grep -ni "Small\|Medium\|Large\|Complex" skills/code-review/SKILL.md | head   # tiers present in Step 5
grep -ni "Review Plan\|Complexity:" skills/code-review/SKILL.md                # plan + banner present
```

**Tests:** none **Gate:** inspection
**Commit:** `feat(code-review): complexity assessment routing (4 tiers) + banner`

---

### T5: Step 6 — dispatch rework (modes, self-loading, roster, return format)

**What:** Rework dispatch to execute per the size tier's mode — inline (Small, orchestrator), single agent covering all active dimensions (Medium, union-loads checklists + full codebase docs), one agent per active dimension (Large), parallel + thoroughness directive (Complex). Add `## Before You Begin` blocks (targeted checklists per the checklist matrix + the FULL codebase-doc set for every reviewing agent except requirements-tracer; TESTING.md excluded). Update the Agent Roster Required/Optional columns to reflect self-loading and remove `tech_debts`. Strip `Files reviewed`/coverage roll-call from the return format (findings only).
**Where:** `skills/code-review/SKILL.md` — Step 6 (Parallel Subagent Dispatch), incl. prompt template, Agent Roster, return format
**Depends on:** T2 (availability map), T4 (tiers/execution modes)
**Reuses:** Existing Step 6 agent roster, reviewer-stance injection, prompt-template structure
**Requirement:** CR-TOKEN-07, CR-TOKEN-08 (thoroughness directive), CR-TOKEN-13, CR-TOKEN-14 (roster columns), CR-TOKEN-15 (return-format strip)

**Tools:** Edit, Grep

**Done when:**
- [x] Dispatch describes all 4 execution modes and which agents run per content type.
- [x] Medium single-agent path: ONE subagent, all active dimensions, union of targeted checklists + full codebase docs.
- [x] `## Before You Begin` block added to the prompt template: targeted checklist(s) per dimension + full codebase-doc set (STACK/ARCHITECTURE/CONVENTIONS/STRUCTURE/INTEGRATIONS/CONCERNS, not TESTING.md), filtered to present files.
- [x] `security-reviewer` has no checklist load (relies on `security-best-practices` skill) but loads full codebase docs; `requirements-tracer` loads neither.
- [x] `performance-reviewer` checklist load is only `performance-checklist.md` (+ stack perf) + full codebase docs.
- [x] Agent Roster Required/Optional columns updated; `tech_debts` removed from roster.
- [x] Return format no longer contains `Files reviewed`/coverage roll-call — findings only.
- [x] Complex thoroughness directive added (self-contained; NO reference to a "second-pass").

**Verify:**
```
grep -ni "Before You Begin" skills/code-review/SKILL.md     # block present in template
grep -ni "Files reviewed\|tech_debt" skills/code-review/SKILL.md   # → 0
grep -ni "second pass\|second-pass" skills/code-review/SKILL.md    # → 0
```

**Tests:** none **Gate:** inspection
**Commit:** `feat(code-review): execution-mode dispatch + agent self-loading + lean returns`

---

### T6: Step 8 — consolidation, header notes, silent operation

**What:** Update consolidation: omit inactive-dimension rows from the at-a-glance table; add the `Tier: … | Type: …` header note when not a plain general review; show the excluded-file count in the report header; add the Complex completeness caveat to the header; add the Silent-operation rule (only skill invocation → banner → final report; no intermediate output).
**Where:** `skills/code-review/SKILL.md` — Step 8 (Consolidation and Present Findings), report header + at-a-glance table
**Depends on:** T5
**Reuses:** Existing report-header + at-a-glance + zoned-format structure (unchanged shape)
**Requirement:** CR-TOKEN-03 (display), CR-TOKEN-08 (caveat in header), CR-TOKEN-09, CR-TOKEN-15 (silent operation)

**Tools:** Edit, Grep

**Done when:**
- [x] At-a-glance table omits rows for inactive dimensions (no "skipped" phantom rows).
- [x] Header includes the excluded-file count (e.g. `N files changed (M excluded as generated/lockfiles)`).
- [x] Header carries the Complex completeness caveat when tier = Complex.
- [x] `Tier: … | Type: …` note added to header when content type ≠ general OR tier ∈ {Large, Complex}.
- [x] Silent-operation rule stated: exactly three user-facing outputs (skill invocation, complexity banner, final report); no progress/partial output.

**Verify:**
```
grep -ni "excluded\|completeness\|Tier:\|silent" skills/code-review/SKILL.md | head
# Manual: at-a-glance instructions say to omit inactive dimensions
```

**Tests:** none **Gate:** inspection
**Commit:** `feat(code-review): consolidation header notes + silent operation`

---

### T7: Examples, Guardrails & metadata version

**What:** Update the Examples section to reflect the new flow (complexity assessment, execution modes, banner, silent operation); update the "What NOT to Review" / Guardrails wording to reference the Step 4 noise exclusion; bump the skill `metadata.version`. Final internal-consistency pass (counts, step numbers, no stale 5-agent-always language).
**Where:** `skills/code-review/SKILL.md` — Guardrails, Examples, frontmatter `metadata.version`
**Depends on:** T2, T3, T4, T5, T6
**Reuses:** Existing four examples (local / GitHub PR / performance audit / multi-commit)
**Requirement:** Consistency for CR-TOKEN-01..15 (no new requirement; closes the loop)

**Tools:** Edit, Grep

**Done when:**
- [x] Each example reflects: complexity assessment + banner, the correct execution mode, silent operation.
- [x] "What NOT to Review" / Guardrails references the noise-exclusion constant (no contradiction with Step 4).
- [x] `metadata.version` bumped (2.3.0 → 2.4.0).
- [x] No stale "always dispatch 5 agents" / "Quick Mode Check" language remains.

**Verify:**
```
grep -ni "version:" skills/code-review/SKILL.md            # → 2.4.0
grep -ni "Quick Mode Check\|all 5 agents in parallel" skills/code-review/SKILL.md  # → no stale unconditional phrasing
```

**Tests:** none **Gate:** inspection
**Commit:** `docs(code-review): update examples, guardrails, version for token-efficiency rework`

---

## Validation — Pre-Approval Checks

### Check 1 — Task Granularity

| Task | Scope | Status |
|------|-------|--------|
| T1 | 1 section removed in 1 file | ✅ Granular |
| T2 | Steps 2–3 (context collection) — one cohesive concern | ✅ Granular |
| T3 | Step 4 (diff collection) — one concern | ✅ Granular |
| T4 | Step 5 (complexity assessment) — one cohesive new step | ✅ Granular |
| T5 | Step 6 (dispatch) — one cohesive step (largest, but single concern: dispatch+loading) | ✅ Granular |
| T6 | Step 8 (consolidation) — one concern | ✅ Granular |
| T7 | Examples + guardrails + version — consistency closeout | ✅ Granular |

### Check 2 — Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram shows | Status |
|------|-------------------|---------------|--------|
| T1 | None | `[P]`, no arrows in | ✅ Match |
| T2 | None | start of chain | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T2, T4 | T4 → T5 (T2 upstream in chain) | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T2–T6 | T6 → T7 (all upstream in chain) | ✅ Match |

### Check 3 — Test Co-location

N/A — all tasks edit markdown skill files. The project's coverage matrix treats `.md` as "none" (clarity/correctness of content, not test coverage). Verification is grep/inspection per task, included in each `Verify` block. No `Tests: none` here is a deferral.

---

## Requirement Coverage

| Requirement | Task(s) |
|-------------|---------|
| CR-TOKEN-01 | T3 |
| CR-TOKEN-02 | T3 |
| CR-TOKEN-03 | T3 (capture), T6 (display) |
| CR-TOKEN-04 | T4 |
| CR-TOKEN-05 | T4 |
| CR-TOKEN-06 | T4 |
| CR-TOKEN-07 | T5 |
| CR-TOKEN-08 | T5 (thoroughness directive), T6 (caveat in header) |
| CR-TOKEN-09 | T6 |
| CR-TOKEN-10 | T4 |
| CR-TOKEN-11 | T1 |
| CR-TOKEN-12 | T2 |
| CR-TOKEN-13 | T5 |
| CR-TOKEN-14 | T2 (Step 2 + availability map), T5 (roster columns) |
| CR-TOKEN-15 | T5 (return-format strip), T6 (silent operation) |

All 15 requirements covered.
