# Codebase Concerns

**Analysis Date:** 2026-09-14

## Tech Debt

**No tests for the only substantial implementation file:**

- Issue: `scripts/bin/fs-harness.mjs` is now 814 lines, still entirely untested — zero unit-test files in the repo. The two `scripts/bin/misc/` consistency scripts (`check-references.mjs`, `check-no-stale-refs.mjs`) are themselves untested, though they exist precisely to catch the class of drift this concern is about (broken cross-references, stale mentions).
- Files: `scripts/bin/fs-harness.mjs`, `scripts/bin/misc/check-references.mjs`, `scripts/bin/misc/check-no-stale-refs.mjs`
- Why: project began as `.md`-only tooling; the CLI grew without a test harness.
- Impact: regressions in CLI commands (setup, destroy, override, symlink logic) go undetected until manual testing catches them; broken commands can reach `main`. Partially mitigated for cross-reference drift specifically by `fs-harness doctor`, which did not exist when this concern was first raised.
- Fix approach: add Node's built-in `node:test` runner with integration tests over temp directories (create a scratch dir, run commands, assert symlink state). No extra dependencies needed.

**Orphaned skill-shaped file outside the skill registry:**

- Issue: `karpathy.skill.md` sits at the repo root with `SKILL.md`-style frontmatter (`name: karpathy-guidelines`) but is not under `skills/`, not registered in `config/skills.json`, and not referenced anywhere else in the repo (verified via repo-wide grep) — so it is currently unintegrated and not actually loaded as a skill by `fs-harness`.
- Files: `karpathy.skill.md`
- Why: unclear — likely added ad hoc, never wired into the registry, or intentionally left as reference-only content.
- Impact: dead weight if unintentional; confusing to a future maintainer who assumes anything with `SKILL.md`-style frontmatter is live.
- Fix approach: either move it to `skills/karpathy-guidelines/SKILL.md` and register it via `fs-harness add karpathy-guidelines --source local`, or, if intentionally reference-only, state that explicitly in the file itself.

**Project-local skills mechanism unused:**

- Issue: `.claude/skills/` holds no skill content — `.claude/` (tracked directly in the repo) contains only tracked skill-install metadata.
- Files: `.claude/`
- Impact: none currently — the mechanism is architecturally intact and ready to use — but worth confirming whether this is intentional deprecation or a pending re-add, since an unexplained empty directory invites confusion.
- Fix approach: none required until the intent is clarified.

**Per-skill `STATE.md` convention has partial tooling support:**

- Issue: the per-skill decision-log convention (`docs/skill-adr.md`) requires an agent to read a skill's `STATE.md` before modifying it and append an `AD-NNN` entry after each real decision. Adoption has grown to 10 `STATE.md` files across `skills/` and `extended/` (up from one at the last analysis), but nothing mechanically checks that the read-before-modify/append-after-decision steps actually happened — `check-references.mjs` and `check-no-stale-refs.mjs` exempt `STATE.md` from their checks rather than validating its own compliance.
- Files: `docs/skill-adr.md`
- Why: added as a lightweight, tooling-free convention — deliberate, avoids CLI complexity for a documentation practice.
- Impact: **Compliance risk** — nothing enforces the convention, so it can silently lapse across skills or sessions (already happened once: `skills/session-evaluate/STATE.md` had to be backfilled after an agent session missed the convention entirely). **Token-consumption risk** — the cumulative cost of reading a skill's `STATE.md` before every edit now applies across 10 skills instead of 1, a real recurring per-edit overhead rather than a negligible one.
- Fix approach: at current scale (10 of 20 skills), consider a lightweight `fs-harness doctor` check that flags a skill with recent content changes but no matching `STATE.md` entry, rather than relying purely on agent discipline.

**`fs-harness` requires `npm link` — not portable without cloning:**

- Issue: `package.json` is not published to npm; there is no standalone install path.
- Files: `package.json`
- Impact: setting up a new machine requires cloning this repo and running `npm link`.
- Fix approach: publish to npm (planned, deferred — see `docs/codebase/PROJECT.md` scope).

## Known Bugs

**`fs-harness update` silently no-ops for global-scope Matt Pocock skills:**

- Symptoms: `fs-harness update --all` (or a Matt Pocock skill by name) reports `updated <name> (Matt Pocock)` even though the skill's content did not change.
- Trigger: any global-scope skill sourced from `matt-pocock`.
- Files: `scripts/bin/fs-harness.mjs` → `updateSkill` (`matt-pocock` case)
- Root cause: the underlying vendor `update` subcommand tracks installs for updating via its own lock file, but global-scope installs are never written to that lock file — so the update call finds no match, silently no-ops, and still exits 0.
- Workaround: force a fresh fetch directly (bypassing the "already installed → skip" check) with the vendor CLI's own add command in global scope.

## Performance Bottlenecks

**`session-evaluate` subagents pinned to a stronger model:**

- Problem: `skills/session-evaluate/SKILL.md`'s Step 6 dispatched subagents (the Medium-tier single covering agent, and the Large-tier per-active-dimension agents) run on a hard-pinned stronger model rather than inheriting the calling session's — see `skills/session-evaluate/STATE.md` AD-006 for the decision record.
- Files: `skills/session-evaluate/SKILL.md`
- Cause: the classification work (matching digest signals to a finding catalog, judging Structural vs Incidental, attributing fix targets) was judged reasoning-dense enough to warrant the stronger model.
- Measurement: not yet measured in dollars — the pinned model costs materially more per token, and a Large-tier run can dispatch several dimension agents in parallel (one per active dimension, up to 6), so a large/complex session evaluation costs meaningfully more in tokens than a same-tier run would.
- Improvement path: this is a deliberate quality-over-cost trade-off, not a defect — worth monitoring as evaluation frequency grows. If cost becomes a concern, consider reverting specific dimensions to the lighter model while keeping the stronger one only where it most benefits reasoning, or add a lighter-weight tier boundary.

## Missing Critical Features

**No CI/CD pipeline:**

- Problem: no CI configuration of any kind found in the repo — no automated gate on `scripts/bin/fs-harness.mjs` changes.
- Current workaround: manual `node --check scripts/bin/fs-harness.mjs`, `fs-harness doctor`, and `--dry-run` smoke tests.
- Blocks: catching broken CLI commands or cross-reference drift before they reach `main`.
- Rough effort: small — a workflow running `node --check`, `fs-harness doctor`, and a basic `fs-harness list` smoke test.

## Other Tech Debt

- **No `package-lock.json`:** reproducibility relies on `npm link` from the working tree; no lockfile governs `npx` calls to vendor skills, so version drift is possible.
- **Synchronous `npx` calls:** `execFileSync` blocks for each vendor skill install; no parallel install path (acceptable at the current scale of 12 vendor skills — 10 Tech Leads Club, 2 Matt Pocock).
