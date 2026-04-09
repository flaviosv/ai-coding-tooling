# Project

See [docs/PROJECT_DETAILS.md](docs/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `This project (ai-coding-tooling)`** — i.e., files under `skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external registries (e.g. Tech Leads Club). Those are treated as read-only dependencies.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skill Overrides

## documentation-upsert

When the **documentation-upsert** skill is invoked in this project, in addition to its standard workflow, update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.
