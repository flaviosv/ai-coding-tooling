# Project

See [docs/PROJECT_DETAILS.md](docs/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `This project (ai-coding-tooling)`** — i.e., files under `skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external registries (e.g. Tech Leads Club). Those are treated as read-only dependencies.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skill Overrides

## documentation

When the **documentation** skill is invoked in this project, in addition to its standard workflow,
update `README.md` with whatever is relevant: new skills added, new tech references, structural
changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep
the README accurate as a first-stop reference for anyone using or contributing to this project.

# Available Skills

- **global-agent-setup** (`skills/global-agent-setup/SKILL.md`): Sets up global agent configuration by symlinking `AGENTS.global.md` to the agent's global config file and installing all global skills from the Tech Leads Club registry. Use when the user says "setup global agent", "install global skills", "run global-agent-setup", "initialize agent global config", or "setup my agent globally". Source: This project (`ai-coding-tooling`).
- **add-tech-reference** (`skills/add-tech-reference/SKILL.md`): Add technology-specific reference files across all skills in this project and extend any qualifying global skills. Use when the user says "add support for <technology>", "add a new technology reference", "add <tech> to the stack", or "onboard <framework>". Source: This project (`ai-coding-tooling`).
