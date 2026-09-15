# Testing Infrastructure

**Analyzed:** 2026-09-14

## Test Frameworks

None. No unit-test framework is installed or configured, and no test files exist in the codebase. Correctness is instead checked by deterministic, standalone consistency scripts (see Gate Check Commands).

## Test Organization

The CLI (`scripts/bin/fs-harness.mjs`, 814 lines) has no unit tests. `.md` skill and reference files are reviewed manually, backed by two structural checks: `scripts/bin/misc/check-references.mjs` (cross-reference and link resolution) and `scripts/bin/misc/check-no-stale-refs.mjs` (stale-mention guard). `extended/skill-architect/scripts/validate_skill.py` performs a similar structural check, but scoped to `skill-architect`'s own generation flow (run against one newly authored or edited skill folder, not the whole repo).

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| ---------- | ------------------ | ---------------- | ----------- |
| `config/` JSON registry | schema validation | — (none exist) | — |
| `scripts/bin/fs-harness.mjs` CLI commands | unit / integration | — (none exist) | — |
| `scripts/bin/misc/*.mjs` | deterministic script (not unit-tested itself) | — | `node scripts/bin/misc/<script>.mjs [args]` |
| `skills/`, `extended/` `.md` content | structural check | `extended/skill-architect/scripts/validate_skill.py <skill-folder>` | see above |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Syntax check | Before merging `scripts/bin/fs-harness.mjs` changes | `node --check scripts/bin/fs-harness.mjs` |
| Cross-reference check | After adding/removing/renaming a skill, overlay, or shared reference file | `fs-harness doctor` (or directly: `node scripts/bin/misc/check-references.mjs`) |
| Stale-reference check | After removing a concept/feature that may have left a stale mention | `node scripts/bin/misc/check-no-stale-refs.mjs [pattern]` |
| Manual smoke test | After any CLI change | `fs-harness list` + a `--dry-run` of the affected command |

## Notes

No unit-test runner, no coverage tooling, no CI gate. `fs-harness doctor` and the two `scripts/bin/misc/` scripts are the closest thing to an automated check the repo has — deterministic and structural (references resolve, symlinks and installs are intact, a removed string hasn't crept back in), not behavioral. Changes to `scripts/bin/fs-harness.mjs` itself are still validated manually by running CLI commands with `--dry-run`. See `CONCERNS.md` for the risk assessment and a suggested fix approach.
