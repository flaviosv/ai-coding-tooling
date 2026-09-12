# Testing Infrastructure

**Analyzed:** 2026-09-01

## Test Frameworks

None. No test framework is installed or configured, and no test files exist in the codebase.

## Test Organization

The only implementation code (`bin/fs-harness.mjs`, 779 lines) is untested. `.md` skill and reference files are reviewed manually; there is no automated validation.

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| ---------- | ------------------ | ---------------- | ----------- |
| `bin/fs-harness.mjs` CLI commands | unit / integration | — (none exist) | — |
| `config/` JSON registry | schema validation | — (none exist) | — |
| `skills/`, `extended/` `.md` content | none — reviewed manually | n/a | n/a |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Syntax check | Before merging `bin/fs-harness.mjs` changes | `node --check bin/fs-harness.mjs` |
| Manual smoke test | After any CLI change | `fs-harness list claude-code` + a `--dry-run` of the affected command |

## Notes

No test runner, no coverage tooling, no CI gate. Changes to `bin/fs-harness.mjs` are validated manually by running CLI commands with `--dry-run`. See `CONCERNS.md` for the risk assessment and a suggested fix approach.
