# Project

See [docs/PROJECT_DETAILS.md](docs/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `This project (ai-coding-tooling)`** — i.e., files under `skills/` or `.agents/skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external registries (e.g. Tech Leads Club). Those are treated as read-only dependencies.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skills

See [docs/AGENT-SKILLS.md](docs/AGENT-SKILLS.md) for the global skills registry and project-specific skill overrides.
