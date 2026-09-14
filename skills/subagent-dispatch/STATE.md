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
- **Status**: active

### AD-004
- **Decision**: Model-matrix rows follow the `fix-review` → `code-review` merge: `build-feature`'s Step 11 and Step 12 wrapper rows are removed (Step 11 now invokes `code-review` from the orchestrator), its Step 13/15 rows renumber to 12/14, `fix-review`'s two rows and `code-review`'s publishing-worker row become `code-review`'s Stage 1 review worker, Stage 3 fix worker, and Batch Mode workers, all `sonnet`. The named-site list and two historical examples no longer name `fix-review`.
- **Reason**: `fix-review` no longer exists as a skill (`skills/code-review/STATE.md` AD-010) and `build-feature` dropped its wrappers (`skills/build-feature/STATE.md` AD-014); every surviving dispatch site kept its tier.
- **Trade-off**: None identified — no tier changed.
- **Date**: 2026-09-13
- **Status**: active

### AD-005
- **Decision**: Model-matrix rows follow `build-feature`'s removal of its Step 3 architecture-evaluate gate: the Step 3 `haiku` row is removed, the remaining rows renumber (6a→5a, 6b→5b, 7→6, 9→8, 12→11, 14→13), the Step 11 row drops "(Incremental)" since `architecture-evaluate` now picks its own mode, and the orchestrator note and pipeline invariant cite grilling as Step 3 and `code-review` as Step 10.
- **Reason**: `build-feature` deleted the gate and renumbered its steps (`skills/build-feature/STATE.md` AD-023); every surviving dispatch site kept its tier.
- **Trade-off**: None identified — no tier changed.
- **Date**: 2026-09-14
- **Status**: active
