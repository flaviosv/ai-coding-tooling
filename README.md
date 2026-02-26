# ai-coding-tooling

Shared agent configuration and skills for AI coding tools (Claude Code, Cursor, Windsurf, Gemini CLI, etc.).

## Installation

### Prerequisites

- Unix-like shell (macOS/Linux)
- `make` installed

### 1. Clone the repository

```bash
git clone <repo-url>
cd ai-coding-tooling
```

### 2. Create the symlinks

```bash
make link
```

Existing files or symlinks are skipped — nothing is overwritten.

### 3. Set up global agent configuration

Open this project in Claude Code and run:

```
/global-agent-setup
```

This will symlink `AGENTS.global.md` to the agent's global config file and install all global skills.

### 4. Install extended skill files

After the global skills are installed (step 3), link the extended skill files into the installed skill directories:

```bash
make link-extended
```

### 5. Remove symlinks

```bash
make unlink
```

Only removes symlinks — real files are never deleted.

## Skills

Skills are reusable agent instructions that extend AI coding tools with specialized workflows. They are grouped below by source.

### Source: This Project (`ai-coding-tooling`)

Maintained here and installed globally via `make link` / `/global-agent-setup`. These are the only skills you should modify:

| Skill | Description |
|---|---|
| **global-agent-setup** | Sets up global agent configuration by symlinking `AGENTS.global.md` and installing all global skills. |
| **evaluate-architecture** ⭐ | Creates or updates the three mandatory project context files (`PROJECT_DETAILS.md`, `CODING_STYLE.md`, `ARCHITECTURE.md`) inside `.agents/`. Run this when onboarding a new project or when context files are missing. |
| **add-tech-reference** ⭐ | Adds technology-specific reference files across all skills and extends qualifying global skills. Run this when adding a new framework or language to a project's stack. |
| **documentation** | Updates all project documentation by inspecting the git workspace for modified files. Updates inline API docs and related `.md` files. |
| **code-review** | Performs comprehensive code reviews covering architecture, performance, code quality, API design, and security. |
| **performance-review** | Identifies performance bottlenecks, memory issues, and optimization opportunities. |
| **tests** | Writes and maintains tests — unit, integration, TDD, and coverage analysis. |
| **tests-code-review** | Reviews test code quality, coverage patterns, and maintainability. |
| **skill-global-installation** | Guides installation of a new skill into the global Claude Code skills directory. |

> ⭐ **Highlighted skills:**
>
> - **`evaluate-architecture`** — The recommended first step for any new or onboarded project. It generates the three context files that all agents read at the start of every session, ensuring consistent project understanding.
> - **`add-tech-reference`** — The recommended way to extend the tooling for a new technology. It propagates tech-specific reference files into all relevant skills (code review, tests, performance, etc.) in one step.

### Source: [Tech Leads Club](https://techlead.club)

Installed globally by `/global-agent-setup`. Treated as read-only — do not edit these directly:

| Skill | Description |
|---|---|
| **skill-architect** | Expert guide for designing and building high-quality skills through structured conversation. |
| **subagent-creator** | Guide for creating AI subagents with isolated context for complex multi-step workflows. |
| **technical-design-doc-creator** | Creates comprehensive Technical Design Documents (TDD) following industry standards. |
| **the-fool** | Challenges ideas and proposals — plays devil's advocate, runs pre-mortems, and stress-tests assumptions. |
| **web-design-guidelines** | Reviews UI code for accessibility, design, and best-practices compliance. |
| **coding-guidelines** | Behavioral guidelines to reduce common LLM coding mistakes. Applied when writing or reviewing code. |
| **docs-writer** | Writing, reviewing, and editing documentation and `.md` files. |
| **learning-opportunities** | Facilitates deliberate skill development through interactive exercises after architectural work. |
| **best-practices** | Applies modern web development best practices for security, compatibility, and code quality. |
| **security-best-practices** | Language and framework specific security reviews (Python, JavaScript/TypeScript, Go). |
