# Testing Infrastructure

## Test Frameworks

None. Testing is explicitly out of scope for this project (`PROJECT.md`: "Runtime application logic — this repo has no server, no build step, no tests").

## Manual Verification

Changes to `bin/skills.mjs` are verified manually:

| Check | Command |
|-------|---------|
| CLI help loads | `node bin/skills.mjs --help` (or `fsvskills` after `npm link`) |
| Skill list resolves | `fsvskills list claude-code` |
| Setup/destroy round-trip | `fsvskills setup claude-code && fsvskills destroy claude-code` |

## Test Coverage Matrix

| Code Layer | Required Test Type | Notes |
|------------|--------------------|-------|
| `bin/skills.mjs` | None (currently) | See CONCERNS.md — no automated coverage |
| `config/*.json` | None | Validated by schema-awareness in CLI at runtime |
| `.md` files | None | Content correctness verified by human review |

## Gate Check Commands

No automated gate. Merges rely on manual smoke-test of `fsvskills` commands.
