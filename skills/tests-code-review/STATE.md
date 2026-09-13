# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at Step 6's Medium/Large-tier dispatches — explicit completion condition (every checklist item in `## Before You Begin` checked, findings written), a return shape restricted to findings only, and delegation depth: none.
- **Reason**: Part of a repo-wide retrofit, following a `session-evaluate` audit that found `complete-review`'s own dispatch (which delegates to this skill) running with no completion condition at all. Applied here preventively, in the same pass, since this skill has the identical dispatch shape as `code-review` (dimension agents returning findings).
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Delete the "Key Reminders" footer (`C127`–`C131`) entirely rather than compress it.
- **Reason**: 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` row #35) flagged the footer as pure software-engineering truisms with zero repo-specific content — dual-judge REDUNDANT and cheaply rediscoverable. Nothing in it added skill-specific guidance beyond what the Reviewer Stance section already establishes.
- **Trade-off**: None identified — no repo-specific content was lost.
- **Date**: 2026-09-13
- **Status**: active
