# Agent Skills

> The **Project Skill Overrides** below are hand-maintained — edit them directly. Everything
> from the marker down (**Global Skills Registry**) is auto-generated from `config/skills.json`
> by `fsvskills` on `add`/`override`; do not hand-edit it.

## Project Skill Overrides

### documentation-upsert

When the **documentation-upsert** skill is invoked in this project, in addition to its standard workflow, update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.

### skill-architect

if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern; also enforces token-efficiency rules for generated skill and reference files via `templates/token-efficiency-rules.md`.

<!-- fsvskills:generated — do not edit below this line; regenerated from config/skills.json -->

## Global Skills Registry

### Built in this project

- **architecture-evaluate** (`skills/architecture-evaluate/SKILL.md`): Creates or updates the mandatory project context files (PROJECT_DETAILS.md, ARCHITECTURE.md, PIPELINE.md) in docs/. Supports package mode for scoped CLAUDE.md generation.
- **code** (`skills/code/SKILL.md`): Applies coding guidelines when writing code. Thin delegator to coding-guidelines; pairs with code-review for the /code + /code-review naming pattern.
- **code-review** (`skills/code-review/SKILL.md`): Comprehensive code reviews covering architecture, performance, code quality, API design, and security. Reviews local changes or a GitHub PR; also runs standalone performance audits.
- **documentation-upsert** (`skills/documentation-upsert/SKILL.md`): Updates all project documentation by inspecting the git workspace for modified files. Detects new packages, updates inline API docs, root context files, and base docs/ files.
- **tech-debt-report** (`skills/tech-debt-report/SKILL.md`): Documents tech debts in docs/tech-debts/ and maintains an anti-pattern index in docs/TECH_DEBTS.md so agents avoid replicating bad patterns.
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Adds technology-specific reference files across all skills and extends qualifying global skills. Use when adding a new framework or language to a project's stack.
- **tests** (`skills/tests/SKILL.md`): Writes and maintains tests — unit, integration, and coverage analysis. Technology agnostic.
- **tests-code-review** (`skills/tests-code-review/SKILL.md`): Reviews test code quality, coverage patterns, and maintainability. Supports local workspace and GitHub PR review modes.

### Local-only (project)

- **generate-knowledge-base** (`.agents/skills/generate-knowledge-base/SKILL.md`): Reads files or folders, extracts intelligence, and produces a comprehensive Markdown knowledge note saved to the Obsidian vault. Project-local; exposed to Claude via the .claude -> .agents symlink, not installed globally.
- **raindrop-kb-convert** (`.agents/skills/raindrop-kb-convert/SKILL.md`): Converts a Raindrop.io bookmark collection into a consolidated knowledge base in the Obsidian vault, clustering bookmarks by topic. Project-local; exposed to Claude via the .claude -> .agents symlink, not installed globally.

### Tech Leads Club

- **codenavi**: Pathfinder for navigating unknown codebases. Investigates with precision, implements surgically, and never assumes. Use for bug fixes, features, refactors, or flow investigation in unfamiliar territory.
- **coding-guidelines**: Behavioral guidelines to reduce common LLM coding mistakes. Applied when writing or reviewing code.
- **docs-writer**: Writing, reviewing, and editing documentation and .md files.
- **learning-opportunities**: Facilitates deliberate skill development during AI-assisted coding by offering interactive learning exercises after architectural work.
- **security-best-practices**: Language and framework specific security reviews (Python, JavaScript/TypeScript, Go).
- **skill-architect**: Expert guide for designing and building high-quality skills through structured conversation. Installed project-locally (not global).
- **subagent-creator**: Guide for creating AI subagents with isolated context for complex multi-step workflows.
- **technical-design-doc-creator**: Creates comprehensive Technical Design Documents (TDD) following industry standards.
- **web-design-guidelines**: Reviews UI code for accessibility, design, and best-practices compliance.

### Matt Pocock

_No Matt Pocock skills installed yet. Add one with:_ `fsvskills add claude-code <skill> --source matt-pocock`

### Native (built-in)

- **keybindings-help**: Customize Claude Code keyboard shortcuts. Built into Claude Code — no installation needed.

## Overridden (extended)

These skills carry a project-specific overlay in `extended/<name>/` (applied as `SKILL.extended.md` and optional `reference/`):

- **coding-guidelines** — overlays the Tech Leads Club skill.
- **docs-writer** — overlays the Tech Leads Club skill.
- **skill-architect** — overlays the Tech Leads Club skill.
