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
