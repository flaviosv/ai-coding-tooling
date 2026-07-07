# Agent Skills

> The **Project Skill Overrides** below are hand-maintained — edit them directly. Everything
> from the marker down (**Global Skills Registry**) is auto-generated from `config/skills.json`
> by `fsvskills` on `add`/`override`; do not hand-edit it.

## Project Skill Overrides

### architecture-evaluate

When **architecture-evaluate** runs an **incremental documentation sync** ("update docs" / "document my changes") in this project — as part of its standard root-file review — update `README.md` with whatever is relevant: new skills added, new tech references, structural changes to the `skills/` or `extended/` directories, or changes to the global agent setup. Keep the README accurate as a first-stop reference for anyone using or contributing to this project.

### skill-architect

if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern; also enforces token-efficiency rules for generated skill and reference files via `templates/token-efficiency-rules.md`.

<!-- fsvskills:generated — do not edit below this line; regenerated from config/skills.json -->

## Global Skills Registry

### Built in this project

- **architecture-evaluate** (`skills/architecture-evaluate/SKILL.md`): Creates, updates, and incrementally syncs the project context documentation that agents load at session start. Three modes. Full mode deep-scans the codebase (brownfield mapping) and writes nine context files to docs/codebase/ — PROJECT.md (overview, vision, goals), STACK.md, STRUCTURE.md, ARCHITECTURE.md, CONVENTIONS.md, INTEGRATIONS.md, TESTING.md, CONCERNS.md, and PIPELINE.md. Incremental mode inspects the git workspace and syncs only what changed — inline API docs in source files, root context files (README.md, CLAUDE.md, AGENTS.md), and the context files in docs/codebase/ — and detects new packages. Package mode generates a scoped CLAUDE.md for an individual package/module. Use when the user says "evaluate architecture", "map codebase", "analyze existing code", "document current architecture", "update architecture docs", "refresh project context", "onboard project", "create project docs", "update project docs", "update docs", "document my changes", "sync documentation", "document recent changes", "evaluate package", or "package architecture".
- **code-review** (`skills/code-review/SKILL.md`): Comprehensive code reviews covering architecture, performance, code quality, API design, and security. Reviews local changes, a GitHub PR, or a range of commits (multi-commit mode); also runs standalone performance audits.
- **prompt-quality** (`skills/prompt-quality/SKILL.md`): Checks whether a task prompt follows the anatomy-of-a-prompt guidelines (8 layers: Task, Context Files, Reference, Success Brief, Rules, Conversation, Plan, Alignment). Auto-invoked before responding to any new task. Outputs a quality report — confirmed or missing layers — then proceeds without blocking. Never invoke for follow-ups, continuations, or responses to clarifying questions.
- **tech-debt-report** (`skills/tech-debt-report/SKILL.md`): Maintains a permanent numbered tech-debt ledger in docs/TECH_DEBTS.md (a documentation ledger, intentionally NOT auto-loaded into context); per-debt solution plans are written to docs/tech-debts/TD-XX.md when planning a fix. Rows are never deleted.
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Adds technology-specific reference files across all skills and extends qualifying global skills. Use when adding a new framework or language to a project's stack.
- **tests** (`skills/tests/SKILL.md`): Writes and maintains tests — unit, integration, and coverage analysis. Technology agnostic.
- **tests-code-review** (`skills/tests-code-review/SKILL.md`): Reviews test code quality, coverage patterns, and maintainability. Supports local workspace, GitHub PR, and multi-commit review modes.

### Tech Leads Club

- **codenavi**: Your pathfinder for navigating unknown codebases. Investigates with precision, implements surgically, and never assumes — if it doesn't know, it says so. Maintains a .notebook/ knowledge base that grows across sessions, turning every discovery into lasting intelligence. Summons available skills, MCPs, and docs when the mission demands. Use when fixing bugs, implementing features, refactoring, investigating flows, or any development task in unfamiliar territory. Triggers on "fix this", "implement this", "how does this work", "investigate this flow", "help me with this code". Do NOT use for greenfield scaffolding, CI/CD, or infrastructure provisioning.
- **confluence-assistant**: Expert in Confluence operations using Atlassian MCP. Use when the user says "search Confluence", "create a Confluence page", "update a page", "find documentation in Confluence", "list spaces", or "add a comment to a page". Do NOT use for Jira issues, general web search, or local file creation.
- **docs-writer**: Use this skill for writing, reviewing, and editing documentation (`/docs` directory or any .md file).
- **jira-assistant**: Manage Jira issues via Atlassian MCP — search, create, update, transition status, and handle sprint tasks. Auto-detects workspace configuration. Use when user says "create a Jira ticket", "update my sprint", "check Jira status", "transition this issue", "search Jira", or "move ticket to done". Do NOT use for Confluence pages (use confluence-assistant).
- **learning-opportunities**: Facilitates deliberate skill development during AI-assisted coding. Offers interactive learning exercises after architectural work (new files, schema changes, refactors). Use when completing features, making design decisions, or when user asks to understand code better. Triggers on "learning exercise", "help me understand", "teach me", "why does this work", or after creating new files/modules. Do not trigger during urgent debugging, quick fixes, or when user says "just ship it".
- **mermaid-studio**: Expert Mermaid diagram creation, validation, and rendering with dual-engine output (SVG/PNG/ASCII). Supports all 20+ diagram types including C4 architecture, AWS architecture-beta with service icons, flowcharts, sequence, ERD, state, class, mindmap, timeline, git graph, sankey, and more. Features code-to-diagram analysis, batch rendering, 15+ themes, and syntax validation. Use when users ask to create diagrams, visualize architecture, render mermaid files, generate ASCII diagrams, document system flows, model databases, draw AWS infrastructure, analyze code structure, or anything involving "mermaid", "diagram", "flowchart", "architecture diagram", "sequence diagram", "ERD", "C4", "ASCII diagram". Do NOT use for non-Mermaid image generation, data plotting with chart libraries, or general documentation writing.
- **security-best-practices**: Perform language and framework specific security best-practice reviews and suggest improvements. Trigger only when the user explicitly requests security best practices guidance, a security review/report, or secure-by-default coding help. Trigger only for supported languages (python, javascript/typescript, go). Do not trigger for general code review, debugging, or non-security tasks.
- **skill-architect**: Expert guide for designing and building high-quality skills from scratch through structured conversation. Use whenever someone wants to create a new skill, build a skill, design a skill, or asks for help making Agents do something consistently. Also use when someone says "turn this into a skill", "I want to automate this workflow", "how do I teach my Agent to do X", or mentions creating SKILL.md files. Covers standalone skills and MCP-enhanced workflows.
- **subagent-creator**: Guide for creating AI subagents with isolated context for complex multi-step workflows. Use when users want to create a subagent, specialized agent, verifier, debugger, or orchestrator that requires isolated context and deep specialization. Works with any agent that supports subagent delegation. Triggers on "create subagent", "new agent", "specialized assistant", "create verifier".
- **technical-design-doc-creator**: Creates comprehensive Technical Design Documents (TDD) following industry standards with mandatory sections, optional sections, and interactive gathering of missing information.
- **tlc-spec-driven**: Feature planning and implementation with 4 adaptive phases — Specify, Design, Tasks, Execute. Auto-sizes depth by complexity. Creates atomic tasks with verification criteria, atomic git commits, and requirement traceability. Features an independent Verifier (author != verifier, evidence-or-zero), persistent decision log (STATE.md), and test-coverage-matrix-driven tests, plus a self-improving lessons layer that turns verification failures into reusable project-local guidance. Stack-agnostic. Use when (1) Planning features (requirements, design, task breakdown), (2) Implementing with verification and atomic commits, (3) Validating or verifying an implementation against a spec. Triggers on "specify feature", "discuss feature", "design", "tasks", "implement", "validate", "verify work", "UAT", "record decision", "pause work", "resume work". Do NOT use for architecture decomposition analysis (use architecture skills) or technical design docs (use create-technical-design-doc).
- **web-design-guidelines**: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".

### Matt Pocock

- **grill-me**: A relentless interview to sharpen a plan or design.

### Native (built-in)

- **keybindings-help**: Customize Claude Code keyboard shortcuts. Built into Claude Code — no installation needed.

## Overridden (extended)

These skills carry a project-specific overlay in `extended/<name>/` (applied as `SKILL.extended.md` and optional `references/`):

- **docs-writer** — overlays the Tech Leads Club skill.
- **mermaid-studio** — overlays the Tech Leads Club skill.
- **skill-architect** — overlays the Tech Leads Club skill.
- **tlc-spec-driven** — overlays the Tech Leads Club skill.
