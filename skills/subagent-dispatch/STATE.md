# STATE

## Decisions

### AD-001
- **Decision**: Consolidate `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` into one new skill, `subagent-dispatch`, instead of keeping them as two linked templates or merging them into a single template file.
- **Reason**: The two files were candidates for merging into one template, but the dispatch-contract content (the four-field prompt shape: completion condition, observability prefix/scale estimate, return shape, delegation depth) is generic — it applies to any `Agent`-tool dispatch in any project, the same shape as vendor skills like `subagent-creator`/`workflow-authoring` that self-trigger when the agent recognizes the moment, without needing an explicit inline link at every call site. A skill self-triggers on that recognition the same way `workflow-authoring` does; a template only gets read when a caller remembers to link it. Evaluated `subagent-creator` (installed globally, TLC-sourced) first to rule out redundancy: it covers a different lifecycle stage entirely (authoring a new persistent subagent's persona/frontmatter) and doesn't overlap with either file's content — confirmed no substitute exists.
- **Trade-off**: The model-tier matrix (`references/model-matrix.md`) is repo-specific bookkeeping with a closed, known caller list — it doesn't itself need self-triggering, since every consuming skill already states its dispatch site by name. It rides along inside this skill as an L3 reference (loaded only once a named pipeline site is identified) rather than living in the skill's own generically-triggered body, so the trigger surface stays generic while the project-specific table stays out of the way until it's actually relevant. This adds one skill to the project's always-listed skill roster, a small recurring cost `templates/*.md` didn't carry.
- **Date**: 2026-09-13
- **Status**: active
