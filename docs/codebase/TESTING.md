# Testing Infrastructure

**Analyzed:** 2026-10-14

## Test Frameworks

- **Python skill scripts:** standard-library `unittest`, no third-party runner or coverage tool. Suites exist for `code-review` (`test_ado_review.py`, `test_detect_remote.py`, `test_github_review.py`, `test_review_page.py`; 103 tests) and `session-evaluate` (`test_session_metrics.py`; 4 tests).
- **Everything else:** no test framework is installed or configured. The CLI, hooks, status line and other skill scripts have no tests; correctness is checked by deterministic, standalone consistency scripts (see Gate Check Commands).

## Test Organization

Skill-bundled Python tests live in `skills/<skill>/scripts/tests/` as `test_<module>.py`; each test file puts its parent `scripts/` directory on `sys.path` and imports the module under test. The CLI (`scripts/bin/fs-harness.mjs`, 814 lines) has no unit tests. `.md` skill and reference files are reviewed manually, backed by two structural checks: `scripts/bin/misc/check-references.mjs` (cross-reference and link resolution) and `scripts/bin/misc/check-no-stale-refs.mjs` (stale-mention guard). `extended/skill-architect/scripts/validate_skill.py` performs a similar structural check, but scoped to `skill-architect`'s own generation flow (run against one newly authored or edited skill folder, not the whole repo).

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| ---------- | ------------------ | ---------------- | ----------- |
| `config/` JSON registry | schema validation | — (none exist) | — |
| `scripts/hooks/*`, `scripts/bin/misc/statusline.sh` | none | — | — |
| `scripts/bin/fs-harness.mjs` CLI commands | unit / integration | — (none exist) | — |
| `scripts/bin/misc/*.mjs` | deterministic script (not unit-tested itself) | — | `node scripts/bin/misc/<script>.mjs [args]` |
| `skills/*/scripts/*.py` (`code-review`, `session-evaluate`) | unit | `skills/<skill>/scripts/tests/test_*.py` | `python3 -m unittest discover -s skills/<skill>/scripts/tests` |
| `skills/`, `extended/` `.md` content | structural check | `extended/skill-architect/scripts/validate_skill.py <skill-folder>` | see above |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Syntax check | Before merging `scripts/bin/fs-harness.mjs` changes | `node --check scripts/bin/fs-harness.mjs` |
| Cross-reference check | After adding/removing/renaming a skill, overlay, or shared reference file | `fs-harness doctor` (or directly: `node scripts/bin/misc/check-references.mjs`) |
| Stale-reference check | After removing a concept/feature that may have left a stale mention | `node scripts/bin/misc/check-no-stale-refs.mjs [pattern]` |
| Skill script unit tests | After changing a Python script under `skills/<skill>/scripts/` that has a `tests/` folder | `python3 -m unittest discover -s skills/<skill>/scripts/tests` |
| Manual smoke test | After any CLI change | `fs-harness list` + a `--dry-run` of the affected command |

## Notes

No third-party test runner, no coverage tooling, no CI gate. `fs-harness doctor` and the two `scripts/bin/misc/` scripts are the closest thing to an automated check the repo has — deterministic and structural (references resolve, symlinks and installs are intact, a removed string hasn't crept back in), not behavioral. Changes to `scripts/bin/fs-harness.mjs` itself are still validated manually by running CLI commands with `--dry-run`. See `CONCERNS.md` for the risk assessment and a suggested fix approach.
