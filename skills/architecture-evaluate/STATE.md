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

### AD-003
- **Decision**: Replace the `templates/subagent-models.md` and `templates/subagent-dispatch-contract.md` links (Shared Guardrails Sonnet-pin and Model Pinning dispatch contract) with references to the new `subagent-dispatch` skill.
- **Reason**: Both templates were consolidated into one self-triggering skill (see `skills/subagent-dispatch/STATE.md` AD-001) rather than two linked files.
- **Trade-off**: Same dependency as `code-review`'s AD-007 — these sentences now assume `subagent-dispatch` stays installed.
- **Date**: 2026-09-13
- **Status**: active

### AD-004
- **Decision**: Full mode's Step 13 report says agents load the context files when the project's session-start context list references them, instead of claiming they load "via the directive in CLAUDE.global.md".
- **Reason**: User decision (harness-evaluation #18 scope): naming a file outside the skill as the source of a behavior is a dependency. `CLAUDE.global.md` is this harness repo's file name and does not exist in the projects this skill maps, so the claim was false there; registration is already handled by Additional Context Files & Registration.
- **Trade-off**: The report no longer names where the loading directive lives.
- **Date**: 2026-09-14
- **Status**: active
