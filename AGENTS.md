# Project

See [docs/PROJECT_DETAILS.md](docs/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `This project (ai-coding-tooling)`** — i.e., files under `skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external registries (e.g. Tech Leads Club). Those are treated as read-only dependencies.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skill Overrides

## documentation-upsert

When the **documentation-upsert** skill is invoked in this project, in addition to its standard workflow,
update `README.md` with whatever is relevant: new skills added, new tech references, structural
changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep
the README accurate as a first-stop reference for anyone using or contributing to this project.

# Available Skills

- **architecture-evaluate** (`skills/architecture-evaluate/SKILL.md`): Creates or updates the three mandatory project context files (PROJECT_DETAILS.md, ARCHITECTURE.md, PIPELINE.md) in docs/. Also supports package mode for individual packages/modules, generating a scoped CLAUDE.md. Use when the user says "evaluate architecture", "update architecture docs", "refresh project context", "onboard project", "create project docs", "evaluate package", or "package architecture". Source: This project (`ai-coding-tooling`).
- **documentation-upsert** (`skills/documentation-upsert/SKILL.md`): Updates all project documentation by inspecting the git workspace for modified files. Detects new packages and triggers scoped architecture evaluation. Updates inline API docs, root context files, and base docs/ files. Uses docs-writer for all .md edits. Use when the user says "update docs", "generate docs", "document my changes", or "sync documentation". Source: This project (`ai-coding-tooling`).
- **global-agent-setup** (`skills/global-agent-setup/SKILL.md`): Sets up global agent configuration by symlinking `AGENTS.global.md` to the agent's global config file and installing all global skills from the Tech Leads Club registry. Use when the user says "setup global agent", "install global skills", "run global-agent-setup", "initialize agent global config", or "setup my agent globally". Source: This project (`ai-coding-tooling`).
- **report-tech-debt** (`skills/report-tech-debt/SKILL.md`): Create, update, and resolve technical debt reports. Generates individual debt documentation in `docs/tech-debts/` and maintains an anti-pattern index in `docs/TECH_DEBTS.md`. Use when the user says "report tech debt", "document tech debt", "add tech debt", "update tech debt", "resolve tech debt", or "mark tech debt as resolved". Source: This project (`ai-coding-tooling`).
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Add technology-specific reference files across all skills in this project and extend any qualifying global skills. Use when the user says "add support for <technology>", "add a new technology reference", "add <tech> to the stack", or "onboard <framework>". Source: This project (`ai-coding-tooling`).
- **update-external-skill** (`skills/update-external-skill/SKILL.md`): Update externally installed skills by reinstalling them from their vendor registry and re-applying any extended skill symlinks. Use when the user says "update external skills", "update all skills", "update skill X", "reinstall skill", "upgrade skills", "refresh skills", or "check for skill updates". Source: This project (`ai-coding-tooling`).
