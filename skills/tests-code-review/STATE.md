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

### AD-003
- **Decision**: Replace the `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` links (Subagent Model guardrail and Step 6 execution) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files, mirroring `code-review`'s identical change (AD-007).
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-008
- **Decision**: Replace the `templates/agent-wait-protocol.md` link (Step 6 wait instruction) with a reference to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch` (see `skills/subagent-dispatch/STATE.md` AD-002) alongside the content already consolidated there (AD-007), mirroring `code-review`'s identical change (AD-008).
- **Trade-off**: Same dependency as AD-007 — this sentence now assumes `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active
