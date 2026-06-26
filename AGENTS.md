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
