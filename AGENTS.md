# Project

See [`docs/codebase/PROJECT.md`](docs/codebase/PROJECT.md) for the project concept and goals, and the rest of [`docs/codebase/`](docs/codebase/) (ARCHITECTURE, STACK, STRUCTURE, CONVENTIONS, INTEGRATIONS, TESTING, CONCERNS) for the full agent context set.

## Project Nature

This is **not an implementation-heavy codebase**. The vast majority of the project consists of `.md` files: skill definitions (`SKILL.md`), reference documents, configuration (`config/*.json`), and documentation. Treat it accordingly:

- Do not apply typical software engineering heuristics (refactoring for abstraction, test coverage, DRY patterns) to `.md` files — clarity and correctness of content is what matters.
- The **only implementation code** lives in `bin/` (`bin/skills.mjs`). Only modify it when the scope of actions it performs actually changes — not for style, cleanup, or speculative improvements.
- When in doubt about a change, ask: "Is this a content edit to a `.md` file, or a behavioral change to `bin/`?" Each requires a very different standard of care.

# Constraints

## Status Line Changes

When modifying the status line script, always apply changes in this order:

1. Edit `config/statusline-command.sh` (the project's source of truth).
2. Copy the updated file to `~/.claude/statusline-command.sh` to apply it globally.

Never edit the global file directly — changes must originate in `config/statusline-command.sh`.

## Skill Modification Rules

- **Only modify skills whose source is `local`** — i.e., files under `skills/` or `.agents/skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external vendors (Tech Leads Club, Matt Pocock). Those are treated as read-only dependencies; override them via `extended/<skill>/` instead.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skills

Skills are managed by the **`fsvskills`** script (`bin/skills.mjs`). Its source of truth is structured JSON in `config/` (`agents.json`, `skills.json`); `docs/AGENT-SKILLS.md` is regenerated from `skills.json` automatically whenever `fsvskills add`/`delete`/`override` change the registry.

- **Running `fsvskills` yourself:** the full command reference is [docs/CLI.md](docs/CLI.md) — every command, flag, and workflow. **Read it before invoking the CLI**, then run the command directly (preview any mutating command with `--dry-run` first). The quick reminders below are a summary; `docs/CLI.md` is authoritative.
- See [docs/AGENT-SKILLS.md](docs/AGENT-SKILLS.md) for the generated skills registry and project-specific skill overrides.
- Add a skill: `fsvskills add claude-code <skill> --source <local|tech-leads-club|matt-pocock>`.
- Delete a skill: `fsvskills delete claude-code <skill>` (uninstalls + deregisters; keeps `extended/<skill>/`).
- Override a vendor skill: `fsvskills override claude-code <skill>` (scaffolds `extended/<skill>/`).

## Known Limitation: `fsvskills update` for Matt Pocock Skills

`fsvskills update claude-code --all` (or targeting a `matt-pocock` skill by name) reports `updated <name> (Matt Pocock)` even when nothing actually changed. The underlying `skills` npx CLI only tracks installs for `update` via a `skills-lock.json` file, but **global-scope installs are never written to that lock file** — so `skills update <name> -g` can never find them, and silently no-ops ("No installed skills found matching") while still exiting 0.

- **Workaround:** force a fresh fetch directly, bypassing `fsvskills`'s own "already installed → skip" check: `npx skills add mattpocock/skills --skill <name> --agent claude-code --global --yes`.
- **Symptom to watch for:** if a Matt Pocock skill needs an update, don't trust `fsvskills update`'s success message alone for that source — verify content changed, or just run the workaround directly.
- `to-prd` was confirmed **removed/renamed upstream** in `mattpocock/skills` as of 2026-07-17, reconfirmed 2026-08-05 — it no longer appears in the repo's skill list, so the workaround above will fail for it (`No matching skills found for: to-prd`). It is still registered in `config/skills.json`/installed locally (left untouched). As of 2026-08-05 the upstream list has no direct equivalent; `to-spec` is the closest match by description if a replacement is wanted — verify its behavior before swapping in.
