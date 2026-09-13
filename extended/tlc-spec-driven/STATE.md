# STATE

## Decisions

### AD-001
- **Decision**: Replace the `templates/subagent-models.md` link in the Phase Models section with a reference to the new `subagent-dispatch` skill's model matrix (`references/model-matrix.md`).
- **Reason**: `templates/subagent-models.md` was consolidated, together with `templates/subagent-dispatch-contract.md`, into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked template files.
- **Trade-off**: This overlay's Phase Models sentence now assumes `subagent-dispatch` stays installed; removing that skill without updating this file would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: active
