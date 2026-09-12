# STATE

## Decisions

### AD-001
- **Decision**: Adopt the shared [Subagent Dispatch Contract](../../templates/subagent-dispatch-contract.md) at this skill's one dispatch site (the off-Sonnet subagent launch) — completion condition tied to the selected mode's context files existing on disk, return shape restricted to file paths plus a short summary, delegation depth: none.
- **Reason**: Part of a repo-wide retrofit applied to every skill in `skills/` that dispatches subagents, following a `session-evaluate` audit of a real `build-feature` run.
- **Trade-off**: None identified.
- **Date**: 2026-09-02
- **Status**: active

### AD-002
- **Decision**: Compressed the three fully-narrated Incremental Mode worked-example traces (Go `auth.go` update, Magento `Shipping` package-mode, Go `internal/notifications` decline) into one merged compact example; removed all three `docs/TECH_DEBTS.md` cross-references (Shared Guardrails out-of-scope bullet, Step 11 Tone instruction, Step 6 Holistic Sweep do-not-modify list) since the file is not in use; deleted two duplicate/generic Step 12 instruction lines — the secrets/tokens restatement (near-duplicate of the fuller "never write secret values" statement in Shared Guardrails) and the content-free "only include sections with evidence" platitude.
- **Reason**: Applying three approved fixes (rows #1–#3, `skills/architecture-evaluate`) from this repo's 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md`) — both Track B judges scored the example traces and the two Step 12 lines REDUNDANT, and `docs/TECH_DEBTS.md` no longer exists/is in use in this repo.
- **Trade-off**: The merged example demonstrates only the new-package-confirmed path directly; the decline branch is now a one-line parenthetical instead of its own full walkthrough.
- **Date**: 2026-09-12
- **Status**: active
