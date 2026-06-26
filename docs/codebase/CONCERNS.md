# Codebase Concerns

**Analysis Date:** 2026-06-26

## Tech Debt

**No tests for the only implementation file:**

- Issue: `bin/skills.mjs` (750 lines) is entirely untested — zero test files in the repo.
- Files: `bin/skills.mjs`
- Why: project began as `.md`-only tooling; the CLI grew without a test harness.
- Impact: regressions in CLI commands (setup, destroy, override, symlink logic) go undetected until manual testing catches them; broken commands can reach `main`.
- Fix approach: add Node's built-in `node:test` runner with integration tests over temp directories (create a scratch dir, run commands, assert symlink state). No extra dependencies needed.

**`fsvskills` requires `npm link` — not portable without cloning:**

- Issue: `package.json` is not published to npm; there is no standalone install path.
- Files: `package.json`
- Impact: setting up a new machine requires cloning this repo and running `npm link`.
- Fix approach: publish to npm (planned, deferred — see `docs/codebase/PROJECT.md` scope).

## Missing Critical Features

**No CI/CD pipeline:**

- Problem: no `.github/` or any CI config — no automated gate on `bin/skills.mjs` changes.
- Current workaround: manual `node --check bin/skills.mjs` + `--dry-run` smoke tests.
- Blocks: catching broken CLI commands before they reach `main`.
- Rough effort: small — a GitHub Actions workflow running `node --check` plus a basic `fsvskills list` smoke test.

## Other Tech Debt

- **No `package-lock.json`:** reproducibility relies on `npm link` from the working tree; no lockfile governs `npx` calls to vendor skills, so version drift is possible.
- **Synchronous `npx` calls:** `execFileSync` blocks for each vendor skill install; no parallel install path (acceptable at the current scale of ~12 vendor skills).
- **Full doc regeneration:** `generateDocs` always rewrites `docs/AGENT-SKILLS.md` in full; no incremental update (acceptable at the current scale of 21 skills).
