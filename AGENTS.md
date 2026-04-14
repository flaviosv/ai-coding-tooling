# Project

See [docs/PROJECT_DETAILS.md](docs/PROJECT_DETAILS.md) for the full project concept, architecture, and workflows.

# Constraints

## Skill Modification Rules

- **Only modify skills whose source is `This project (ai-coding-tooling)`** — i.e., files under `skills/` or `.agents/skills/` in this repository.
- **Never modify skills installed globally** (e.g. `~/.claude/skills/`) or sourced from external registries (e.g. Tech Leads Club). Those are treated as read-only dependencies.
- If a globally installed skill needs changes, raise it with the user instead of editing it directly.

# Skill Overrides

## documentation-upsert

When the **documentation-upsert** skill is invoked in this project, in addition to its standard workflow, update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.

## skill-architect

if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern; also enforces token-efficiency rules for generated skill and reference files via `templates/token-efficiency-rules.md`.

# Global Skills

- **architecture-evaluate** (`skills/architecture-evaluate/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **best-practices**: Source: Tech Leads Club.
- **chrome-devtools**: Source: Tech Leads Club.
- **code** (`skills/code/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **code-review** (`skills/code-review/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **coding-guidelines**: Source: Tech Leads Club.
- **docs-writer**: Source: Tech Leads Club.
- **documentation-upsert** (`skills/documentation-upsert/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **learning-opportunities**: Source: Tech Leads Club.
- **security-best-practices**: Source: Tech Leads Club.
- **skill-architect**: Source: Tech Leads Club. Install: local.
- **subagent-creator**: Source: Tech Leads Club.
- **tech-debt-report** (`skills/tech-debt-report/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **technical-design-doc-creator**: Source: Tech Leads Club.
- **tests** (`skills/tests/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **tests-code-review** (`skills/tests-code-review/SKILL.md`): Source: This project (`ai-coding-tooling`).
- **the-fool**: Source: Tech Leads Club.
- **web-design-guidelines**: Source: Tech Leads Club.
