# Codebase Concerns

**Analysis Date:** 2026-09-01

## Tech Debt

**No tests for the only implementation file:**

- Issue: `bin/skills.mjs` has grown from 750 to 779 lines since the last scan, still entirely untested — zero test files in the repo.
- Files: `bin/skills.mjs`
- Why: project began as `.md`-only tooling; the CLI grew without a test harness.
- Impact: regressions in CLI commands (setup, destroy, override, symlink logic) go undetected until manual testing catches them; broken commands can reach `main`.
- Fix approach: add Node's built-in `node:test` runner with integration tests over temp directories (create a scratch dir, run commands, assert symlink state). No extra dependencies needed.

**Orphaned skill-shaped file outside the skill registry:**

- Issue: `karpathy.skill.md` sits at the repo root with `SKILL.md`-style frontmatter (`name: karpathy-guidelines`) but is not under `skills/`, not registered in `config/skills.json`, and not referenced anywhere else in the repo (verified via repo-wide grep) — so it is currently unintegrated and not actually loaded as a skill by `fsvskills`.
- Files: `karpathy.skill.md`
- Why: unclear — likely added ad hoc, never wired into the registry, or intentionally left as reference-only content.
- Impact: dead weight if unintentional; confusing to a future maintainer who assumes anything with `SKILL.md`-style frontmatter is live.
- Fix approach: either move it to `skills/karpathy-guidelines/SKILL.md` and register it via `fsvskills add claude-code karpathy-guidelines --source local`, or, if intentionally reference-only, state that explicitly in the file itself.

**Project-local skills mechanism unused:**

- Issue: `.agents/skills/` (surfaced via the `.claude → .agents` symlink) previously held two skills (`kb-from-folder`, `kb-from-raindrop`); it now holds only `.skill-lock.json` and `scheduled_tasks.lock`, no skill content.
- Files: `.agents/skills/`
- Impact: none currently — the mechanism is architecturally intact and ready to use — but worth confirming whether this is intentional deprecation or a pending re-add, since an unexplained empty directory invites confusion.
- Fix approach: none required; a one-line note in `PROJECT.md` (already added) is enough until the intent is clarified.

**Per-skill `STATE.md` convention has no tooling support:**

- Issue: the new per-skill decision-log convention (`docs/SKILL-STATE.md`; `AGENTS.md` "Skill Decision Log" section) requires an agent to read a skill's `STATE.md` before modifying it and append an `AD-NNN` entry after each real decision — entirely manual; `fsvskills` does not create, update, validate, or check for `STATE.md` files.
- Files: `docs/SKILL-STATE.md`, `AGENTS.md` (Skill Decision Log section)
- Why: added as a lightweight, tooling-free convention — deliberate, avoids CLI complexity for a documentation practice.
- Impact: two-sided. **Compliance risk** — nothing enforces the read-before-modify/append-after-decision steps, so it can silently lapse across skills or sessions (already happened once: `skills/session-evaluate/STATE.md` had to be backfilled after an agent session missed the convention entirely, since it landed mid-session after that session's context was already loaded). **Token-consumption risk** — as more skills adopt `STATE.md`, the cumulative cost of reading a skill's `STATE.md` before every edit adds a small but recurring per-edit overhead across the project; currently only `session-evaluate` has one, so the effect is negligible today but worth watching as adoption grows.
- Fix approach: not urgent at current scale (one skill has a `STATE.md`). If adoption grows, consider a lightweight `fsvskills` check (e.g., `fsvskills list` flags a skill with recent content changes but no matching `STATE.md` entry) rather than relying purely on agent discipline.

**`fsvskills` requires `npm link` — not portable without cloning:**

- Issue: `package.json` is not published to npm; there is no standalone install path.
- Files: `package.json`
- Impact: setting up a new machine requires cloning this repo and running `npm link`.
- Fix approach: publish to npm (planned, deferred — see `docs/codebase/PROJECT.md` scope).

## Performance Bottlenecks

**`session-evaluate` subagents pinned to Opus:**

- Problem: `skills/session-evaluate/SKILL.md`'s Step 6 dispatched subagents (the Medium-tier single covering agent, and the Large-tier per-active-dimension agents) run on `model: opus` (changed 2026-09-01 from `sonnet`) — see `skills/session-evaluate/STATE.md` AD-006 for the decision record.
- Files: `skills/session-evaluate/SKILL.md`
- Cause: the classification work (matching digest signals to a finding catalog, judging Structural vs Incidental, attributing fix targets) was judged reasoning-dense enough to warrant the stronger model.
- Measurement: not yet measured in dollars — Opus costs materially more per token than Sonnet, and a Large-tier run can dispatch several dimension agents in parallel (one per active dimension A–F, up to 6), so a large/complex session evaluation now costs meaningfully more in tokens than before the change.
- Improvement path: this is a deliberate quality-over-cost trade-off, not a defect — worth monitoring as evaluation frequency grows. If cost becomes a concern, consider reverting specific dimensions to `sonnet` while keeping `opus` only where it most benefits reasoning, or add a lighter-weight tier boundary.

## Missing Critical Features

**No CI/CD pipeline:**

- Problem: no `.github/` or any CI config — no automated gate on `bin/skills.mjs` changes.
- Current workaround: manual `node --check bin/skills.mjs` + `--dry-run` smoke tests.
- Blocks: catching broken CLI commands before they reach `main`.
- Rough effort: small — a GitHub Actions workflow running `node --check` plus a basic `fsvskills list` smoke test.

## Other Tech Debt

- **No `package-lock.json`:** reproducibility relies on `npm link` from the working tree; no lockfile governs `npx` calls to vendor skills, so version drift is possible.
- **Synchronous `npx` calls:** `execFileSync` blocks for each vendor skill install; no parallel install path (acceptable at the current scale of 10 vendor skills).
- **Full doc regeneration:** `generateDocs` always rewrites `docs/AGENT-SKILLS.md` in full; no incremental update (acceptable at the current scale of 20 skills).
