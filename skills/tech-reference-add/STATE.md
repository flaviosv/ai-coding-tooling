# STATE

## Decisions

### AD-001
- **Decision**: Removed three generic instruction lines from `SKILL.md`: "Parse from the user's message:" (Step 1 intro), "Ask clarifying questions before proceeding if any of the above is unclear." (Step 1 closing), and "For each confirmed target file:" (Step 6 intro, deleted outright rather than merged — the per-file iteration is already implied by Step 5's confirmed target-file list).
- **Reason**: All three were generic agent-instruction-parsing/iteration scaffolding that any agent already does by default, flagged as `REDUNDANT-GENERAL` by both judges in the 2026-09-12 harness-eval run (`docs/HARNESS-EVALUATION.md` rows #30-#32, all **Ship** verdicts).
- **Trade-off**: None — pure deletion of non-skill-specific framing; surrounding instructions (the Step 1 bullet list and Step 6 file-creation rule) still read correctly without them.
- **Date**: 2026-09-13
- **Status**: active

### AD-002
- **Decision**: Step 3 now records any reference-file naming a skill declares in its own `SKILL.md`, and Step 5 proposes targets in that form — `code-review` uses `<tech>.code.md`, `<tech>-performance.code.md`, `<tech>.tests.md` instead of `<tech>-<skill-name>.md`. Examples updated to the merged `code-review` skill.
- **Reason**: `code-review` (after absorbing `tests-code-review`, see its AD-009) suffixes every checklist with its scope; without reading the skill's declaration this skill would create `django-code-review.md`, a file `code-review` never loads.
- **Trade-off**: Relies on a skill stating its naming in `SKILL.md`; a skill that deviates silently would still get the default pattern.
- **Date**: 2026-09-13
- **Status**: active
