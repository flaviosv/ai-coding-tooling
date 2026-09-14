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
- **Status**: superseded by AD-003

### AD-003
- **Decision**: `references/coding-principles.md` Code Comments restates the comment rule inline (comments only for genuinely complex or non-obvious logic, or when explicitly requested; never to narrate a variable, a config value, or a single line) instead of pointing at the global `CLAUDE.md` Coding Style rule, and still overrides the parent skill's comment guidance.
- **Reason**: User decision (harness-evaluation #18 scope): a skill must not defer its instructions to a file outside its directory, mentions included. The substance matches the global rule, so AD-002's disagreement problem does not return.
- **Trade-off**: The rule now lives in two places (this file and `CLAUDE.global.md`, kept by user choice) and can drift; a change to one must be mirrored in the other.
- **Date**: 2026-09-14
- **Status**: active
