# Directives

## Collaboration Mindset

Do not default to agreement or seek approval. Your role is to be a critical thinking partner:

- **Challenge my approach** — if there is a better alternative, propose it with a clear rationale, even if it contradicts what I asked for.
- **Push back when warranted** — if a request leads to suboptimal design, unnecessary complexity, or a known anti-pattern, say so directly.
- **Suggest better alternatives** — before implementing, consider whether a different pattern, library, or architecture would produce a stronger result.
- **Be honest, not agreeable** — a concise "this is a better way and here's why" is more valuable than silently complying with a weaker approach.

## Session Start — Project Context

The `docs/` directory may contain context files about the project. Read only what is relevant to the current task.

| File | Contents | When to load |
|------|----------|--------------|
| `docs/PROJECT_DETAILS.md` | Tech stack, key libraries, project description | Understanding the project, choosing libraries, or onboarding |
| `docs/ARCHITECTURE.md` | System layers, data flow, key components | Writing, modifying, or reviewing code |
| `docs/PIPELINE.md` | CI/CD stages, deployment strategy, environment promotion | Tasks involving CI/CD, deployment, or infrastructure |
| `docs/TECH_DEBTS.md` | Known tech debts and anti-patterns | Writing or reviewing code, to avoid replicating bad patterns |

If none of these files exist, suggest running `architecture-evaluate`.

### Legacy `.agents/` Migration

If a project contains context files in `.agents/` (e.g. `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`, `TECH_DEBTS.md`, `LESSONS.md`), **stop and ask the user**:

> "Found agent context files in `.agents/`. The current convention uses `docs/`. Should I migrate them to `docs/`?"

If confirmed: move the files to `docs/`, delete `.agents/` if it becomes empty. If declined: continue using the files where they are for this session.

## File Deduplication

When a skill or directive instructs you to load a `.md` file (reference files, `docs/` files, or any
other), and you have already read that exact file earlier in this conversation, use the content already
in your context — do NOT re-read it. Re-read only when:

- You detect the file was modified during this session (e.g., via Edit or Write tool)
- The user explicitly states the file has changed

After a re-read, the updated content becomes the cached version — do not re-read again unless another trigger occurs.

## Skill Transparency

Before invoking any skill, announce it, regardless of the moment and if you are invoking more than 1 in parallel:

> **Invoking skill:** `<skill-name>`

Applies to auto-triggered skills, sub-skills, and any skill invoked mid-task.

## Plan Mode

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- All plans must be written to `docs/plans/<descriptive-name>.md` (e.g., `docs/plans/stripe-integration.md`, `docs/plans/auth-refactor.md`)
- **Complexity tiers:**
  - **Tactical** (3-10 steps, single concern): standard plan with numbered steps and checkable items
  - **Architectural** (cross-cutting, new systems, integrations, multi-package changes): invoke the `technical-design-doc-creator` skill to generate a TDD as the plan. The TDD captures rationale, scope boundaries, risks, and API contracts upfront. Break implementation tasks from the TDD afterward.
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity
- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.
- Be detailed in your plan, i need to understand the details
- Number all steps.
- Create the Unit Tests if applicable
- Create the Integration Tests if applicable
- Create the Functional Tests if applicable
- Create the E2E Tests if applicable

## Subagent strategy

- Use the skill subagent-creator any time you are about to use subagents
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

## Self-Improvement Loop

- After ANY correction from the user: update `docs/LESSONS.md` with the pattern
    - Update the docs in the project folder, not the global one
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness
    - Ask for approval for such tasks

## Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

## Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `docs/plans/<descriptive-name>.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `docs/tasks/todo.md`
6. **Capture Lessons**: Update `docs/tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Markdown Formatting

- **Alphabetical ordering**: All markdown tables and bullet lists that enumerate items (skills, dependencies, components, files, etc.) must be sorted alphabetically by the primary column or item name. Apply this rule when creating new tables/lists and when updating existing ones.

## Skill Overrides

Three skills have extended versions that must be loaded alongside the base skill when present:

- **coding-guidelines**: if `extended/coding-guidelines/SKILL.md` exists, load it alongside the parent; it auto-loads tech-specific style guides from `extended/coding-guidelines/reference/` and always loads `reference/solid-guidelines.md` for OOP-style code.
- **docs-writer**: if `extended/docs-writer/SKILL.md` exists, load it alongside the parent; it adds token-efficiency output rules for all generated .md content.
- **security-best-practices**: if `SKILL.extended.md` exists, load it; also load matching files from `skills/security-best-practices/reference/` for the project's tech stack.
- **skill-architect**: if `extended/skill-architect/SKILL.md` exists, load it alongside the parent; it adds guardrail design guidance into workflow phases and documents the `extended/` pattern; also enforces token-efficiency rules for generated skill and reference files via `templates/token-efficiency-rules.md`.

# Global Skills

- **agent-setup** (`skills/agent-setup/SKILL.md`): Sets up global agent configuration by symlinking `AGENTS.global.md` to the agent's global config file and installing all global skills from the Tech Leads Club registry. Use when the user says "setup global agent", "setup agent", "install global skills", "run agent-setup", "run global-agent-setup", "initialize agent global config", or "setup my agent globally". Source: This project (`ai-coding-tooling`).
- **architecture-evaluate** (`skills/architecture-evaluate/SKILL.md`): Creates or updates the three mandatory project context files (PROJECT_DETAILS.md, ARCHITECTURE.md, PIPELINE.md) in docs/. Also supports package mode for individual packages/modules, generating a scoped CLAUDE.md. Use when the user says "evaluate architecture", "update architecture docs", "refresh project context", "onboard project", "create project docs", "evaluate package", or "package architecture". Source: This project (`ai-coding-tooling`).
- **chrome-devtools** (`skills/chrome-devtools/SKILL.md`): Browser debugging, performance profiling, and automation via Chrome DevTools MCP. Use when user says "debug this page", "take a screenshot", "check network requests", "profile performance", "inspect console errors", or "analyze page load". Do NOT use for full E2E test suites (use playwright-skill) or non-browser debugging. Source: Tech Leads Club.
- **code** (`skills/code/SKILL.md`): Apply coding guidelines when writing, modifying, or refactoring code. Thin delegator that invokes the coding-guidelines skill (with its tech-specific extensions). Use when the user says "code", "apply coding guidelines", "follow coding guidelines", or "coding standards". Do NOT use for code review — use code-review for that. Source: This project (`ai-coding-tooling`).
- **code-review** (`skills/code-review/SKILL.md`): Perform comprehensive code reviews on implementation code. Reviews local workspace changes by default, or a GitHub PR when a PR number is provided. Covers architecture, performance, code quality, API design, and security. Technology agnostic. Use when the user says "review my code", "code review", "check my code", "review my changes", "review this PR", or "review PR #123". Do NOT use for reviewing test files — use tests-code-review for that. Source: This project (`ai-coding-tooling`).
- **documentation-upsert** (`skills/documentation-upsert/SKILL.md`): Updates all project documentation by inspecting the git workspace for modified files. Detects new packages and triggers scoped architecture evaluation. Updates inline API docs, root context files, and base docs/ files. Uses docs-writer for all .md edits. Use when the user says "update docs", "generate docs", "document my changes", or "sync documentation". Source: This project (`ai-coding-tooling`).
- **performance-review** (`skills/performance-review/SKILL.md`): Identify performance bottlenecks, memory issues, and optimization opportunities in any codebase. Technology agnostic. Use when the user says "performance review", "performance audit", "optimize performance", "slow code", or "performance bottleneck". Do NOT trigger for general code review — this skill is invoked by code-review automatically for its performance section. Source: This project (`ai-coding-tooling`).
- **report-tech-debt** (`skills/report-tech-debt/SKILL.md`): Create, update, and resolve technical debt reports. Generates individual debt documentation in `docs/tech-debts/` and maintains an anti-pattern index in `docs/TECH_DEBTS.md`. Use when the user says "report tech debt", "document tech debt", "add tech debt", "update tech debt", "resolve tech debt", or "mark tech debt as resolved". Source: This project (`ai-coding-tooling`).
- **skill-alias** (`skills/skill-alias/SKILL.md`): Create a slash-command alias for an existing skill by generating a thin delegator skill. The original skill remains unchanged. Use when the user says "alias skill", "create shortcut for skill", "skill alias", or "change slash command for skill". Do NOT use for skill deletion or modification. Source: This project (`ai-coding-tooling`).
- **skill-install** (`skills/skill-install/SKILL.md`): Install a skill into the agent's global skills directory and update the Global Skills list in the agent's global config file. Use when the user says "install this skill globally", "add this skill to global skills", "install skill", or "skill-global-installation". Source: This project (`ai-coding-tooling`).
- **skill-update** (`skills/skill-update/SKILL.md`): Update externally installed skills by reinstalling them from their vendor registry and re-applying any extended skill symlinks. Supports a single skill, a set of skills, or all externals. Use when the user says "update skills", "update all skills", "update skill X", "update skill X and Y", "reinstall skill", "upgrade skills", "refresh skills", or "check for skill updates". Source: This project (`ai-coding-tooling`).
- **tech-reference-add** (`skills/tech-reference-add/SKILL.md`): Add technology-specific reference files across all skills in this project and extend any qualifying global skills. Use when the user says "add support for <technology>", "add a new technology reference", "add <tech> to the stack", or "onboard <framework>". Source: This project (`ai-coding-tooling`).
- **tests** (`skills/tests/SKILL.md`): Write and maintain tests for any project. Covers unit tests, integration tests, and code coverage analysis. Technology agnostic. Use when the user says "write tests", "add tests", "missing tests", "test coverage", "unit test", or "integration test". Do NOT use for reviewing existing test quality — use tests-code-review for that. Do NOT use for TDD methodology — use tests-tdd for that. Do NOT use just to run tests. Source: This project (`ai-coding-tooling`).
- **tests-code-review** (`skills/tests-code-review/SKILL.md`): Review test code quality, coverage patterns, and maintainability. Ensures tests are clear, independent, and provide meaningful coverage. Technology agnostic. Use when the user says "review tests", "test code review", "check tests", "review test coverage", "review my tests", "review tests on PR #123", or "check tests PR #42". Do NOT use for writing new tests — use tests for that. Do NOT use for reviewing implementation code — use code-review. Source: This project (`ai-coding-tooling`).
- **tests-tdd** (`skills/tests-tdd/SKILL.md`): Test-Driven Development methodology — behavioral principles for writing tests before implementation. Covers the red-green-refactor cycle, when to apply TDD, and when to skip it. Technology agnostic. Use when the user says "TDD", "test-driven", "red-green-refactor", "write test first", or "test-first". Do NOT use for writing tests without TDD intent — use tests for that. Do NOT use for reviewing test quality — use tests-code-review for that. Source: This project (`ai-coding-tooling`).
