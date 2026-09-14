# STATE

## Decisions

### AD-001
- **Decision**: Replace the `templates/subagent-models.md` link in the Phase Models section with a reference to the new `subagent-dispatch` skill's model matrix (`references/model-matrix.md`).
- **Reason**: `templates/subagent-models.md` was consolidated, together with `templates/subagent-dispatch-contract.md`, into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked template files.
- **Trade-off**: This overlay's Phase Models sentence now assumes `subagent-dispatch` stays installed; removing that skill without updating this file would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: active

### AD-002
- **Decision**: Replace the `Code Comments (always apply)` body in `references/coding-principles.md` with a pointer to the global `CLAUDE.md` Coding Style comment rule, stated as overriding this overlay's previous comment rule and any parent-skill comment guidance.
- **Reason**: The overlay restated the global rule with narrower exceptions (dropped "when explicitly requested", narrowed to "business logic"), so the two disagreed on edge cases inside tlc-spec-driven runs, where the global file is always loaded anyway (harness-eval `docs/harness-evaluation.md` Root Context Files row #14; same precedent as `skills/code-review/STATE.md` FR-AD-009, which shortened its copy to a pointer).
- **Trade-off**: The overlay now depends on the global `CLAUDE.md` being loaded; in an environment without it, tlc-spec-driven runs carry no comment rule.
- **Date**: 2026-09-14
- **Status**: active
