# STATE

## Decisions

### AD-001
- **Decision**: Removed `templates/version-stratification-guide.md` and its two touchpoints in this overlay (the Phase 2.4 link, and the Phase 3 "Version sections" compression rule that depended on the concept it defined).
- **Reason**: No reference file in the repo (`skills/*/references/`, `extended/*/references/`) ever exercised the version-stratified structure — the guide was unused template weight, and the leftover "Version sections" compression rule referenced a concept with no definition once the guide was gone.
- **Trade-off**: If a future skill needs multi-version reference docs (e.g. a PHP skill spanning 8.1–8.4 with real per-version differences), the stratification pattern has to be re-authored — it's recoverable from git history (deleted in the same change that added this entry) but not currently in the template set.
- **Date**: 2026-09-13
- **Status**: active

### AD-002
- **Decision**: Removed `templates/reference-file-naming-convention.md` and inlined its content directly into this overlay's Phase 2.4 (naming pattern, kebab-case slug rule, examples, generic-baseline exemption).
- **Reason**: This overlay was the template's only real caller (a bare link) — extracting a two-paragraph rule used by a single reader added an indirection with no reuse benefit.
- **Trade-off**: If a second skill later needs this same naming rule, it will be duplicated rather than shared until re-extracted into `templates/`.
- **Date**: 2026-09-13
- **Status**: active

### AD-003
- **Decision**: Replace the two `templates/agent-wait-protocol.md` links in Extension 4 (the Phase 2.5 dispatch-check instruction and the Phase 3 wait-instruction wording) with references to the `subagent-dispatch` skill.
- **Reason**: `templates/agent-wait-protocol.md` was folded into `subagent-dispatch`'s own SKILL.md body (see `skills/subagent-dispatch/STATE.md` AD-002) rather than remaining a standalone template.
- **Trade-off**: Extension 4's wording now assumes `subagent-dispatch` stays installed; removing that skill without updating this overlay would leave a stale pointer.
- **Date**: 2026-09-13
- **Status**: active

### AD-004
- **Decision**: Phase 2.4's `<technology>-<skill-name>.md` rule gains an exception: a skill whose references split by scope declares `<technology>.<variant>.md` naming in its own `SKILL.md` (e.g. `code-review`'s `fastapi.code.md`, `fastapi.tests.md`), and the declaration wins. Examples no longer name the removed `tests-code-review`.
- **Reason**: `code-review` absorbed `tests-code-review` and `complete-review` and now names checklists by scope suffix; an overlay still mandating `<tech>-<skill-name>.md` would steer new skills and `tech-reference-add` toward files that skill never loads.
- **Trade-off**: Two naming patterns exist repo-wide instead of one; the default still applies to every skill that doesn't declare otherwise.
- **Date**: 2026-09-13
- **Status**: active

### AD-005
- **Decision**: Phase 2.4's "Linking a shared template" guidance is replaced by "Keep links inside the skill": a skill links only files in its own directory, since the repo's `templates/` folder no longer exists.
- **Reason**: Its last file, `reply-review-filter.md`, moved into `code-review` once that skill became its only consumer (`skills/code-review/STATE.md` AD-010), and `fs-harness` no longer creates the `~/.claude/templates` link; guidance to link `../../templates/` would now produce broken links.
- **Trade-off**: Content two skills genuinely share would have to be duplicated or re-extracted into a new shared mechanism; accepted, since every template this repo ever had ended up with a single consumer.
- **Date**: 2026-09-13
- **Status**: active
