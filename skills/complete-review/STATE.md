# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) for Single PR Mode's review subagent and Batch Mode's per-PR subagents — explicit completion condition (PR's pending review posted, or findings returned when `human_review` withholds it), bounded return shape (already documented, now pointed at rather than restated), delegation depth (may invoke `code-review`/`tests-code-review` via `Skill`, no nesting beyond their own Step 6).
- **Reason**: A `session-evaluate` run against a real APLYR-19 build-feature session measured this skill's Single PR Mode dispatch at 156 turns / 23.0M tokens — the longest-running agent in the whole session — with no completion condition in its prompt beyond "review PR #N." Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents.
- **Trade-off**: None identified — this only adds structure to a prompt that was already being written by hand.
- **Date**: 2026-09-02
- **Status**: active
