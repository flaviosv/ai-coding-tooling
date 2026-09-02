# Testing Infrastructure

**Analyzed:** 2026-09-01

## Test Frameworks

None. No test framework is installed or configured, and no test files exist in the codebase.

## Test Organization

The only implementation code (`bin/skills.mjs`, 779 lines) is untested. `.md` skill and reference files are reviewed manually; there is no automated validation.

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| ---------- | ------------------ | ---------------- | ----------- |
| `bin/skills.mjs` CLI commands | unit / integration | — (none exist) | — |
| `config/` JSON registry | schema validation | — (none exist) | — |
| `skills/`, `extended/` `.md` content | none — reviewed manually | n/a | n/a |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Syntax check | Before merging `bin/skills.mjs` changes | `node --check bin/skills.mjs` |
| Manual smoke test | After any CLI change | `fsvskills list claude-code` + a `--dry-run` of the affected command |

## Notes

No test runner, no coverage tooling, no CI gate. Changes to `bin/skills.mjs` are validated manually by running CLI commands with `--dry-run`. See `CONCERNS.md` for the risk assessment and a suggested fix approach.
