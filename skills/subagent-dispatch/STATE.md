# STATE

## Decisions

### AD-001
- **Decision**: Consolidate `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` into one new skill, `subagent-dispatch`, instead of keeping them as two linked templates or merging them into a single template file.
- **Reason**: The two files were candidates for merging into one template, but the dispatch-contract content (the four-field prompt shape: completion condition, observability prefix/scale estimate, return shape, delegation depth) is generic — it applies to any `Agent`-tool dispatch in any project, the same shape as vendor skills like `subagent-creator`/`workflow-authoring` that self-trigger when the agent recognizes the moment, without needing an explicit inline link at every call site. A skill self-triggers on that recognition the same way `workflow-authoring` does; a template only gets read when a caller remembers to link it. Evaluated `subagent-creator` (installed globally, TLC-sourced) first to rule out redundancy: it covers a different lifecycle stage entirely (authoring a new persistent subagent's persona/frontmatter) and doesn't overlap with either file's content — confirmed no substitute exists.
- **Trade-off**: The model-tier matrix (`references/model-matrix.md`) is repo-specific bookkeeping with a closed, known caller list — it doesn't itself need self-triggering, since every consuming skill already states its dispatch site by name. It rides along inside this skill as an L3 reference (loaded only once a named pipeline site is identified) rather than living in the skill's own generically-triggered body, so the trigger surface stays generic while the project-specific table stays out of the way until it's actually relevant. This adds one skill to the project's always-listed skill roster, a small recurring cost `templates/*.md` didn't carry.
- **Date**: 2026-09-13
- **Status**: active

### AD-002
- **Decision**: Fold `templates/agent-wait-protocol.md`'s full content into this skill's own SKILL.md body (a new "Waiting on a Dispatched Subagent" section), delete the template, and migrate its real callers to this skill instead.
- **Reason**: Explicitly re-evaluated on request rather than assumed. Real fan-in and content shape turned out to match AD-001's two files almost exactly: the same caller set (`build-feature`, `code-review`, `complete-review`, `fix-review` + `references/github-delivery.md`, `tests-code-review`, `session-evaluate`, plus `extended/skill-architect`'s own guidance), fully generic content applicable to any `Agent` dispatch, and — checked directly this time — zero real external consumers on this machine despite `templates/` being symlinked machine-wide (the same "technically reachable, never actually used elsewhere" profile as the two files merged in AD-001, not the confirmed-external-usage profile that keeps `test-execution-scope.md` standalone). Placed in the SKILL.md body (Level 2), not an L3 reference like `model-matrix.md`, because it's generic rather than repo-specific — it applies the moment any dispatch is being planned, not only at a named pipeline site.
- **Trade-off**: None identified — content is a straight move, not a summary; every real caller was migrated in the same change so no dangling link was left behind.
- **Date**: 2026-09-13
- **Status**: active

### AD-003
- **Decision**: Model matrix rows for `complete-review` (Single PR Mode subagent, Batch Mode per-PR subagents) and `tests-code-review` (Step 6 dimension subagents) become `code-review` rows (publishing worker, Batch Mode per-PR subagents, Step 6 dimension subagents across every scope), all still `sonnet`; the description and named-site list drop the two removed skills.
- **Reason**: Both skills were merged into `code-review` (see `skills/code-review/STATE.md` AD-009); every dispatch site kept its tier, only its owning skill changed.
- **Trade-off**: None identified — no tier changed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-006

### AD-004
- **Decision**: Model-matrix rows follow the `fix-review` → `code-review` merge: `build-feature`'s Step 11 and Step 12 wrapper rows are removed (Step 11 now invokes `code-review` from the orchestrator), its Step 13/15 rows renumber to 12/14, `fix-review`'s two rows and `code-review`'s publishing-worker row become `code-review`'s Stage 1 review worker, Stage 3 fix worker, and Batch Mode workers, all `sonnet`. The named-site list and two historical examples no longer name `fix-review`.
- **Reason**: `fix-review` no longer exists as a skill (`skills/code-review/STATE.md` AD-010) and `build-feature` dropped its wrappers (`skills/build-feature/STATE.md` AD-014); every surviving dispatch site kept its tier.
- **Trade-off**: None identified — no tier changed.
- **Date**: 2026-09-13
- **Status**: superseded by AD-006

### AD-005
- **Decision**: Model-matrix rows follow `build-feature`'s removal of its Step 3 architecture-evaluate gate: the Step 3 `haiku` row is removed, the remaining rows renumber (6a→5a, 6b→5b, 7→6, 9→8, 12→11, 14→13), the Step 11 row drops "(Incremental)" since `architecture-evaluate` now picks its own mode, and the orchestrator note and pipeline invariant cite grilling as Step 3 and `code-review` as Step 10.
- **Reason**: `build-feature` deleted the gate and renumbered its steps (`skills/build-feature/STATE.md` AD-023); every surviving dispatch site kept its tier.
- **Trade-off**: None identified — no tier changed.
- **Date**: 2026-09-14
- **Status**: superseded by AD-006

### AD-006
- **Decision**: Make this a lifecycle-only skill that names no other skill: delete `references/model-matrix.md` and every pointer to it, drop the named-pipeline-site list, the `subagent-creator` boundary naming, and skill-specific examples, and replace the matrix with a generic rule — set `model` explicitly on every dispatch with a literal alias, and each dispatching skill states its own tier at its dispatch site (harness-eval Skills #148, #151, #158).
- **Reason**: The matrix only listed other skills' dispatch sites, so it drifted from its callers — a `tlc-spec-driven` site with no row, a `session-evaluate` row that skill claimed not to have, an `architecture-evaluate` row and skill each deferring to the other. A tier lives with the step that dispatches, where a retier actually lands.
- **Trade-off**: No single cross-skill view of every site's tier, and no shared place for the "change pipeline tiers together" invariant; each dispatching skill must now state its tier itself. Callers that still point at the matrix are left for their own skills' changes. Supersedes AD-003, AD-004 and AD-005, and AD-001's trade-off about the matrix riding along as an L3 reference (AD-001's consolidation into one skill stands).
- **Date**: 2026-09-14
- **Status**: active

### AD-007
- **Decision**: Remove the "no reasoning-effort parameter" hard fact and its prompt-steering advice from the body and the frontmatter entirely, with no replacement effort guidance (harness-eval Skills #152).
- **Reason**: Effort can't be set on a dispatch, and the old wording overclaimed that a prompt instruction was the only lever; a fact that leads to no action doesn't belong in the calling convention.
- **Trade-off**: Dispatchers get no guidance on effort at all.
- **Date**: 2026-09-14
- **Status**: active

### AD-008
- **Decision**: Add hard facts for the concurrent-subagent cap (default 20, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`; depth via `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; on the limit error launch the rest once running agents report, never drop work) and for `subagent_type` (never `agentType`; `general-purpose` for skill work; never `fork`, which inherits the parent's context and model and ignores `model`); track completion by task id with at least one notification per agent, skipping repeats; cut incident arithmetic to one-sentence rules in "Why This Matters"; drop Guardrails lines that repeated the hard facts (harness-eval Skills #146, #147, #154, #156, #157).
- **Reason**: The cap's error says not to retry and callers fan out in one message; `fork` silently defeats an explicit `model`; the runtime can notify more than once per task id; the incident narrative and repeated guardrails changed no decision but cost tokens on every load.
- **Trade-off**: The concrete incident evidence behind the wait rules is no longer in the skill itself.
- **Date**: 2026-09-14
- **Status**: active

### AD-009
- **Decision**: Simplify the wait protocol: delete the "Waiting on a Clock, Not an Agent" section, and replace the stall ceiling, `TaskOutput` status check and `TaskStop` rule with one rule — a subagent reports back when it finishes; if one runs unusually long, tell the user in one line and keep waiting, and never stop or re-dispatch it without the user's go-ahead (harness-eval Skills #150, #153, #155; #149 is resolved by this rather than by a conditional `TaskOutput` fallback).
- **Reason**: Background commands and tools already notify on exit, so a clock-wait recipe is unnecessary (and its `&&` example conflicted with worktree isolation); the stall ceiling had no defensible number for long work, and `TaskOutput` isn't reliably available, so any agent-side stop decision rested on a check that may not exist.
- **Trade-off**: An agent that is genuinely stuck is never stopped without a human; the user carries that call.
- **Date**: 2026-09-14
- **Status**: active
