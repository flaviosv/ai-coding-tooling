# Concerns

**Analyzed:** 2026-06-11

## Critical

### No tests for the only implementation file

**Evidence:** Zero test files in the repo; `bin/skills.mjs` (751 lines) is entirely untested.
**Risk:** Regressions in CLI commands (setup, destroy, override, symlink logic) go undetected until manual testing catches them. Broken commands can reach `main` unnoticed.
**Fix approach:** Add Node's built-in `node:test` runner. Cover core command functions with integration tests using temp directories (create a scratch dir, run commands, assert symlink state). No extra dependencies needed.

## High

### fsvskills requires npm link — not portable without cloning

**Evidence:** README states "repo-local for now"; `package.json` is not published to npm.
**Risk:** Setting up a new machine requires cloning this specific repo and running `npm link`. No standalone install path exists.
**Fix approach:** Publish to npm (planned but deferred; see `.specs/project/PROJECT.md` scope section).

### Legacy `docs/codebase/` not migrated to `.specs/codebase/`

**Evidence:** `docs/codebase/PROJECT_DETAILS.md` and `docs/codebase/ARCHITECTURE.md` still exist alongside the new `.specs/codebase/` convention. Some reader files (skills, templates) still reference `docs/codebase/` paths.
**Risk:** Agents may load stale docs from `docs/codebase/` when `.specs/codebase/` is the authoritative set. Confusion about which files are current.
**Fix approach:** Update all reader paths to use the `.specs/codebase/ → docs/codebase/ → docs/` fallback chain, then remove `docs/codebase/` once all readers are updated.

## Medium

### `skills/architecture-evaluate/` de-registered but still present

**Evidence:** `skills/architecture-evaluate/` exists on disk but is not in `config/skills.json` (de-registered per the SDD migration). It sits alongside active skills in `skills/`.
**Risk:** Confusion for contributors; stale code coexists with active skills.
**Fix approach:** Move to `archive/skills/` or delete after confirming the `tlc-spec-driven` brownfield-mapping overlay covers all three modes (Full, Incremental, Package).

### No CI/CD pipeline

**Evidence:** No `.github/` directory, no CI config of any kind.
**Risk:** No automated gate on `bin/skills.mjs` changes; broken CLI commands can reach `main` undetected.
**Fix approach:** Add a GitHub Actions workflow: `node --check bin/skills.mjs` (syntax) + a basic smoke test (`fsvskills list claude-code`).

## Low

### `docs/plans/` is a legacy planning convention

**Evidence:** `docs/plans/SDD-MIGRATION/plan.md` exists; the current convention (`tlc-spec-driven`) uses `.specs/`.
**Risk:** Low — the plan is complete. Minor confusion for contributors about where plans live.
**Fix approach:** Archive or delete after the migration is closed.

## Tech Debt

- **No package-lock.json:** reproducibility relies on `npm link` from the working tree; no lockfile governs `npx` calls to vendor skills (version drift is possible).
- **Synchronous npx calls:** `execFileSync` blocks for each vendor skill install; no parallel install path (acceptable at current scale of ~15 vendor skills).
- **Full doc regeneration:** `generateDocs` always rewrites `docs/AGENT-SKILLS.md` in full; no incremental update (acceptable at current scale of 18 skills).
