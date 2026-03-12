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

### 5. Install the status line script

Run this separately (not included in `make link`) to install the Claude Code status line script to `~/.claude/statusline-command.sh`. It displays the active model, effort level, current directory, git branch, context remaining, and token usage:

```
[Claude Sonnet 4.6 - **High**] 📁 my-project git:(main) | 82% | 4321 tokens
```

The script is copied from `config/statusline-command.sh`. If the destination already exists it is skipped:

```bash
make install-statusline          # skip if file already exists
make install-statusline FORCE=1  # overwrite with the version from this repo
```

To customize the status line without losing your changes on the next `FORCE=1` run, edit `~/.claude/statusline-command.sh` directly — omit the `FORCE=1` flag and it will never be overwritten.

### 6. Remove symlinks

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
| **evaluate-architecture** ⭐ | Creates or updates the two mandatory project context files (`PROJECT_DETAILS.md`, `ARCHITECTURE.md`) inside `.agents/`. Run this when onboarding a new project or when context files are missing. |
| **add-tech-reference** ⭐ | Adds technology-specific reference files across all skills and extends qualifying global skills. Run this when adding a new framework or language to a project's stack. |
| **documentation** | Updates all project documentation by inspecting the git workspace for modified files. Updates inline API docs and related `.md` files. |
| **code-review** | Performs comprehensive code reviews covering architecture, performance, code quality, API design, and security. |
| **performance-review** | Identifies performance bottlenecks, memory issues, and optimization opportunities. |
| **tests** | Writes and maintains tests — unit, integration, TDD, and coverage analysis. |
| **tests-code-review** | Reviews test code quality, coverage patterns, and maintainability. |
| **skill-global-installation** | Guides installation of a new skill into the global Claude Code skills directory. |

> ⭐ **Highlighted skills:**
>
> - **`evaluate-architecture`** — The recommended first step for any new or onboarded project. It generates the two context files that all agents read at the start of every session, ensuring consistent project understanding.
> - **`add-tech-reference`** — The recommended way to extend the tooling for a new technology. It propagates tech-specific reference files into all relevant skills (code review, tests, performance, etc.) in one step.

### Personal Skills (`personal/`)

You can add private, local-only skills that are never committed to git. Create a `personal/` directory at the project root and add skill subdirectories inside it — each must contain a `SKILL.md` file following the same structure as `skills/`.

```
personal/
  my-private-skill/
    SKILL.md
```

`/global-agent-setup` and `make link` both auto-discover and install everything in `personal/` via symlink. Personal skills installed via `make link` are removed with `make unlink`. These skills are labeled `Personal (local-only)` in the `/global-agent-setup` install summary and are never listed in `AGENTS.global.md`.

The `personal/` directory is gitignored — nothing inside it is tracked or committed.

## Recommended MCP Servers

| MCP Server | Purpose | Used by |
|---|---|---|
| **[Context7](https://context7.com)** | Fetches up-to-date documentation and code examples for any library. Provides authoritative raw material when generating technology-specific reference files. | `add-tech-reference` (Step 7) |

Context7 is optional but strongly recommended. When available, `add-tech-reference` queries it for official documentation to ground reference files in current best practices rather than relying solely on LLM training data. If unavailable, the skill falls back to the agent's own knowledge.

### Source: [Tech Leads Club](https://techlead.club)

Installed globally by `/global-agent-setup`. Treated as read-only — do not edit these directly:

| Skill | Description |
|---|---|
| **skill-architect** | Expert guide for designing and building high-quality skills through structured conversation. Extended by `extended/skill-architect/SKILL.md`: adds guardrail design guidance into the workflow and documents the `extended/` pattern for modifying global skills. |
| **subagent-creator** | Guide for creating AI subagents with isolated context for complex multi-step workflows. |
| **technical-design-doc-creator** | Creates comprehensive Technical Design Documents (TDD) following industry standards. |
| **the-fool** | Challenges ideas and proposals — plays devil's advocate, runs pre-mortems, and stress-tests assumptions. |
| **web-design-guidelines** | Reviews UI code for accessibility, design, and best-practices compliance. |
| **coding-guidelines** | Behavioral guidelines to reduce common LLM coding mistakes. Applied when writing or reviewing code. |
| **docs-writer** | Writing, reviewing, and editing documentation and `.md` files. |
| **learning-opportunities** | Facilitates deliberate skill development through interactive exercises after architectural work. |
| **best-practices** | Applies modern web development best practices for security, compatibility, and code quality. |
| **security-best-practices** | Language and framework specific security reviews (Python, JavaScript/TypeScript, Go). |
