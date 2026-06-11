# Codebase Concerns

**Snapshot:** 2026-06-11

## Tech Debt

### TD-1 — Orphaned `skills/architecture-evaluate/` directory

**Severity:** Low | **Area:** `skills/`

`skills/architecture-evaluate/` exists on disk but is not registered in `config/skills.json`. It is a deregistered skill whose directory was never deleted. Agents scanning `skills/` may be confused by its presence; it bloats the repo.

**Fix:** `git rm -r skills/architecture-evaluate/` and verify `fsvskills list claude-code` shows no reference to it.

### TD-2 — Stale `docs/codebase/` docs

**Severity:** Medium | **Area:** `docs/codebase/`

`docs/codebase/ARCHITECTURE.md` and `docs/codebase/PROJECT_DETAILS.md` reference retired structures: `extended/coding-guidelines/` (deleted), the `architecture-evaluate` and `code` skills (deregistered), and old `docs/codebase/` as the canonical context path. These files now live in `.specs/codebase/` (this set).

**Fix:** Delete `docs/codebase/ARCHITECTURE.md` and `docs/codebase/PROJECT_DETAILS.md` after confirming `.specs/codebase/` is complete. Update any remaining cross-references in `AGENTS.md` / `AGENTS.global.md`.

### TD-3 — No automated test coverage for `bin/skills.mjs`

**Severity:** Medium | **Area:** `bin/`

`bin/skills.mjs` is 750 LOC of CLI logic (symlink creation, overlay detection, vendor npx calls, registry management) with zero automated tests. Regressions in install/unlink logic, collision-detection, or overlay symlinking are only caught manually.

**Fix:** Add integration tests (e.g. using Node's `test` built-in or Vitest) against a tmp directory fixture that mocks the home dir and project root. Prioritize: `cmdSetup`, `cmdDestroy`, `applyOverlay`, `installSkill`.

### TD-4 — `npm link` requirement prevents portable use

**Severity:** Low | **Area:** distribution

`fsvskills` is available only after `npm link` from the local clone. It is not published to npm. A new machine or contributor must clone the repo to a stable path before setup works.

**Fix:** Defer until publishing to npm is in scope (currently out of scope per PROJECT.md). Document the `npm link` step prominently in README.

### TD-5 — No atomic rollback on partial `fsvskills setup`

**Severity:** Low | **Area:** `bin/skills.mjs`

If `fsvskills setup` fails midway (e.g. npx install error), some symlinks may exist while others don't. `fsvskills destroy` is the manual remedy but requires awareness of the failure.

**Fix:** Collect all actions before executing, or add a `--rollback` mode that undoes partial state detected by comparing expected vs actual links.
