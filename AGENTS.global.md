# Directives

## Coding (Auto-Apply)

Before any code work, invoke `coding-guidelines`. This applies to all implementation work: new features, bug fixes, refactoring, and code changes of any kind.

**Do NOT invoke** `coding-guidelines` for:
- Questions, explanations, or analysis (e.g. "how does X work?", "explain this code")
- Documentation-only tasks (reading/writing markdown, comments)
- Non-code tasks: planning, research, configuration review, Git operations, CLI commands
- Conversational messages or clarifying questions

## Session Start

If these files exist in the project, read them before doing any work:

- `.agents/PROJECT_DETAILS.md` — tech stack, key libraries, project description
- `.agents/CODING_STYLE.md` — naming conventions, patterns, formatting rules
- `.agents/ARCHITECTURE.md` — system layers, data flow, key components

If missing or stale, suggest running `evaluate-architecture`.

## Skill Transparency

Before invoking any skill, announce it:

> **Invoking skill:** `<skill-name>`

Applies to auto-triggered skills, sub-skills, and any skill invoked mid-task.

## Plan Mode

- Extremely concise. Sacrifice grammar.
- Number all steps.
- List unresolved questions at the end.

## Skill Overrides

Three skills have extended versions that must be loaded alongside the base skill when present:

- **coding-guidelines**: if `extended/coding-guidelines/SKILL.md` exists, load it alongside the parent; it auto-loads tech-specific style guides from `extended/coding-guidelines/reference/` and always loads `reference/solid-guidelines.md` for OOP-style code.
- **security-best-practices**: if `SKILL.extended.md` exists, load it; also load matching files from `skills/security-best-practices/reference/` for the project's tech stack.
- **skill-architect**: if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern.
