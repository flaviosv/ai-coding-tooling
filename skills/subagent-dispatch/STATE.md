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
