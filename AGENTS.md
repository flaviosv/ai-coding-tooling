# Project

See [docs/codebase/PROJECT_DETAILS.md](docs/codebase/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `local`** — i.e., files under `skills/` or `.agents/skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external vendors (Tech Leads Club, Matt Pocock). Those are treated as read-only dependencies; override them via `extended/<skill>/` instead.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skills

Skills are managed by the **`fsvskills`** script (`bin/skills.mjs`). Its source of truth is structured JSON in `config/` (`agents.json`, `skills.json`); `docs/AGENT-SKILLS.md` is regenerated from `skills.json` automatically whenever `fsvskills add`/`delete`/`override` change the registry.

- See [docs/AGENT-SKILLS.md](docs/AGENT-SKILLS.md) for the generated skills registry and project-specific skill overrides.
- Add a skill: `fsvskills add claude-code <skill> --source <local|tech-leads-club|matt-pocock>`.
- Delete a skill: `fsvskills delete claude-code <skill>` (uninstalls + deregisters; keeps `extended/<skill>/`).
- Override a vendor skill: `fsvskills override claude-code <skill>` (scaffolds `extended/<skill>/`).
