# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at this skill's one dispatch site (the off-Sonnet subagent launch) — completion condition tied to the selected mode's context files existing on disk, return shape restricted to file paths plus a short summary, delegation depth: none.
- **Reason**: Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents, following a `session-evaluate` audit of a real `build-feature` run.
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active
