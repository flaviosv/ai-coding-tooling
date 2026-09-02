# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at Step 6's Medium/Large-tier dispatches — explicit completion condition (every checklist item in `## Before You Begin` checked, findings written), a return shape restricted to findings only, and delegation depth: none.
- **Reason**: Part of a repo-wide retrofit, following a `session-evaluate` audit that found `complete-review`'s own dispatch (which delegates to this skill) running with no completion condition at all. Applied here preventively, in the same pass, since this skill has the identical dispatch shape as `code-review` (dimension agents returning findings).
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active
