# Agent Skills

> The **Project Skill Overrides** below are hand-maintained — edit them directly. Everything
> from the marker down (**Global Skills Registry**) is auto-generated from `config/skills.json`
> by `fsvskills` on `add`/`override`; do not hand-edit it.

## Project Skill Overrides

### skill-architect

if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern; also enforces token-efficiency rules for generated skill and reference files via `templates/token-efficiency-rules.md`.

### tlc-spec-driven

When **tlc-spec-driven** runs an **incremental documentation sync** ("update docs" / "document my changes") in this project — in addition to its standard root-file review (brownfield-mapping B5) — update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.

<!-- fsvskills:generated — do not edit below this line; regenerated from config/skills.json -->

## Global Skills Registry

### Built in this project

- **code-review** (`skills/code-review/SKILL.md`): Comprehensive code reviews covering architecture, performance, code quality, API design, and security. Reviews local changes, a GitHub PR, or a range of commits (multi-commit mode); also runs standalone performance audits.
- **tech-debt-report** (`skills/tech-debt-report/SKILL.md`): Maintains a permanent numbered tech-debt ledger in docs/TECH_DEBTS.md (a documentation ledger, intentionally NOT auto-loaded into context); per-debt solution plans are written to docs/tech-debts/TD-XX.md when planning a fix. Rows are never deleted.
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Adds technology-specific reference files across all skills and extends qualifying global skills. Use when adding a new framework or language to a project's stack.
- **tests** (`skills/tests/SKILL.md`): Writes and maintains tests — unit, integration, and coverage analysis. Technology agnostic.
- **tests-code-review** (`skills/tests-code-review/SKILL.md`): Reviews test code quality, coverage patterns, and maintainability. Supports local workspace, GitHub PR, and multi-commit review modes.

### Local-only (project)

- **kb-from-folder** (`.agents/skills/kb-from-folder/SKILL.md`): Reads files or folders (local paths or GitHub repositories via SSH), extracts intelligence, and produces a comprehensive Markdown knowledge note saved to the Obsidian vault. Project-local; exposed to Claude via the .claude -> .agents symlink, not installed globally.
- **kb-from-raindrop** (`.agents/skills/kb-from-raindrop/SKILL.md`): Converts a Raindrop.io bookmark collection into a consolidated knowledge base in the Obsidian vault, clustering bookmarks by topic. Project-local; exposed to Claude via the .claude -> .agents symlink, not installed globally.
### Tech Leads Club

- **codenavi**: Pathfinder for navigating unknown codebases. Investigates with precision, implements surgically, and never assumes. Use for bug fixes, features, refactors, or flow investigation in unfamiliar territory.
- **confluence-assistant**: Expert in Confluence operations using Atlassian MCP. Use when the user says "search Confluence", "create a Confluence page", "update a page", "find documentation in Confluence", "list spaces", or "add a comment to a page". Do NOT use for Jira issues, general web search, or local file creation.
- **docs-writer**: Writing, reviewing, and editing documentation and .md files.
- **jira-assistant**: Manage Jira issues via Atlassian MCP — search, create, update, transition status, and handle sprint tasks. Auto-detects workspace configuration. Use when user says "create a Jira ticket", "update my sprint", "check Jira status", "transition this issue", "search Jira", or "move ticket to done". Do NOT use for Confluence pages (use confluence-assistant).
- **learning-opportunities**: Facilitates deliberate skill development during AI-assisted coding by offering interactive learning exercises after architectural work.
- **mermaid-studio**: Expert Mermaid diagram creation, validation, and rendering with dual-engine output (SVG/PNG/ASCII). Supports all 20+ diagram types including C4 architecture, AWS architecture-beta with service icons, flowcharts, sequence, ERD, state, class, mindmap, timeline, git graph, sankey, and more. Features code-to-diagram analysis, batch rendering, 15+ themes, and syntax validation. Use when users ask to create diagrams, visualize architecture, render mermaid files, generate ASCII diagrams, document system flows, model databases, draw AWS infrastructure, analyze code structure, or anything involving "mermaid", "diagram", "flowchart", "architecture diagram", "sequence diagram", "ERD", "C4", "ASCII diagram". Do NOT use for non-Mermaid image generation, data plotting with chart libraries, or general documentation writing.
- **security-best-practices**: Language and framework specific security reviews (Python, JavaScript/TypeScript, Go).
- **skill-architect**: Expert guide for designing and building high-quality skills from scratch through structured conversation. Use whenever someone wants to create a new skill, build a skill, design a skill, or asks for help making Agents do something consistently. Also use when someone says "turn this into a skill", "I want to automate this workflow", "how do I teach my Agent to do X", or mentions creating SKILL.md files. Covers standalone skills and MCP-enhanced workflows.
- **subagent-creator**: Guide for creating AI subagents with isolated context for complex multi-step workflows.
- **technical-design-doc-creator**: Creates comprehensive Technical Design Documents (TDD) following industry standards.
- **tlc-spec-driven**: Project and feature planning with 4 adaptive phases - Specify, Design, Tasks, Execute. Auto-sizes depth by complexity. Creates atomic tasks with verification criteria, atomic git commits, requirement traceability, and persistent memory across sessions. Stack-agnostic. Use when (1) Starting new projects (initialize vision, goals, roadmap), (2) Working with existing codebases (map stack, architecture, conventions), (3) Planning features (requirements, design, task breakdown), (4) Implementing with verification and atomic commits, (5) Quick ad-hoc tasks (bug fixes, config changes), (6) Tracking decisions/blockers/deferred ideas across sessions, (7) Pausing/resuming work. Triggers on "initialize project", "map codebase", "specify feature", "discuss feature", "design", "tasks", "implement", "validate", "verify work", "UAT", "quick fix", "quick task", "pause work", "resume work". Do NOT use for architecture decomposition analysis (use architecture skills) or technical design docs (use create-technical-design-doc).
- **web-design-guidelines**: Reviews UI code for accessibility, design, and best-practices compliance.

### Matt Pocock

_No Matt Pocock skills installed yet. Add one with:_ `fsvskills add claude-code <skill> --source matt-pocock`

### Native (built-in)

- **keybindings-help**: Customize Claude Code keyboard shortcuts. Built into Claude Code — no installation needed.

## Overridden (extended)

These skills carry a project-specific overlay in `extended/<name>/` (applied as `SKILL.extended.md` and optional `references/`):

- **docs-writer** — overlays the Tech Leads Club skill.
- **skill-architect** — overlays the Tech Leads Club skill.
- **tlc-spec-driven** — overlays the Tech Leads Club skill.
