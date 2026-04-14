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
/agent-setup
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

### Project-Local Skills (`.agents/skills/`)

These skills live in `.agents/skills/` and are auto-loaded when the project is opened in Claude Code. No installation step required.

| Skill | Description |
|---|---|
| **agent-setup** | Sets up global agent configuration by symlinking `AGENTS.global.md` and installing all global skills. Multi-agent — supports Claude Code, Gemini CLI, and others via agent reference files. |
| **generate-knowledge-base** | Reads files or folders, extracts intelligence, and produces a comprehensive Markdown knowledge note saved to the Obsidian vault. |
| **raindrop-kb-convert** | Converts a Raindrop.io bookmark collection into a consolidated knowledge base in the Obsidian vault. Clusters bookmarks by topic and generates deduplicated `.md` files per cluster. |
| **skill-architect** | Expert guide for designing and building high-quality skills through structured conversation. Source: Tech Leads Club. Installed locally. |
| **skill-manager** | Installs or updates skills in an agent's global skills directory. Handles fresh installation (Tech Leads Club via npx or local project via symlink) and updates externally installed skills by reinstalling from their vendor registry and re-applying extended skill symlinks. Prompts for install vs update if intent is ambiguous. |

### Source: This Project (`ai-coding-tooling`)

Maintained here and installed globally via `make link` / `/agent-setup`. These are the only skills you should modify:

| Skill | Description |
|---|---|
| **architecture-evaluate** ⭐ | Creates or updates the three mandatory project context files (`PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`) inside `docs/`. Also supports package mode for evaluating individual packages/modules, generating a scoped `CLAUDE.md` inside the package directory. Run this when onboarding a new project or when context files are missing. |
| **code** | Apply coding guidelines when writing code. Thin delegator to `coding-guidelines` (TLC). Pairs with `code-review` for the `/code` + `/code-review` naming pattern. |
| **code-review** | Performs comprehensive code reviews covering architecture, performance, code quality, API design, and security. Reviews local workspace changes by default, or a GitHub PR when a PR number is provided. Also performs standalone Performance Audits (full-codebase P0–P3 findings report) when triggered by performance audit phrases. |
| **documentation-upsert** | Updates all project documentation by inspecting the git workspace for modified files. Detects new packages and triggers scoped architecture evaluation. Updates inline API docs, root context files, and base `docs/` files. |
| **tech-debt-report** | Documents tech debts in `docs/tech-debts/` and maintains an anti-pattern index in `docs/TECH_DEBTS.md` so agents avoid replicating bad patterns. |
| **tech-reference-add** ⭐ | Adds technology-specific reference files across all skills and extends qualifying global skills. Run this when adding a new framework or language to a project's stack. |
| **tests** | Writes and maintains tests — unit, integration, and coverage analysis. |
| **tests-code-review** | Reviews test code quality, coverage patterns, and maintainability. Supports local workspace and GitHub PR review modes. |

> ⭐ **Highlighted skills:**
>
> - **`architecture-evaluate`** — The recommended first step for any new or onboarded project. It generates the context files in `docs/` that agents load progressively based on task relevance.
> - **`tech-reference-add`** — The recommended way to extend the tooling for a new technology. It propagates tech-specific reference files into all relevant skills (code review, coding guidelines, tests, etc.) in one step.
> - **`tech-debt-report`** — Documents known anti-patterns so agents avoid replicating them. The `docs/TECH_DEBTS.md` index is loaded automatically when writing or reviewing code.

### Skill Aliases

Aliases are thin delegators that provide shorter slash commands for existing skills. The original skill remains unchanged and fully functional.

| Alias | Original Skill | Description |
|---|---|---|
| **code** | `coding-guidelines` | Short command for `/coding-guidelines`. Pairs with `/code-review`. |

### Personal Skills (`personal/`)

You can add private, local-only skills that are never committed to git. Create a `personal/` directory at the project root and add skill subdirectories inside it — each must contain a `SKILL.md` file following the same structure as `skills/`.

```
personal/
  my-private-skill/
    SKILL.md
```

`/agent-setup` and `make link` both auto-discover and install everything in `personal/` via symlink. Personal skills installed via `make link` are removed with `make unlink`. These skills are labeled `Personal (local-only)` in the `/agent-setup` install summary and are never listed in `AGENTS.md`.

The `personal/` directory is gitignored — nothing inside it is tracked or committed.

## Recommended MCP Servers

| MCP Server | Purpose | Used by |
|---|---|---|
| **[Context7](https://context7.com)** | Fetches up-to-date documentation and code examples for any library. Provides authoritative raw material when generating technology-specific reference files. | `tech-reference-add` (Step 7) |

Context7 is optional but strongly recommended. When available, `tech-reference-add` queries it for official documentation to ground reference files in current best practices rather than relying solely on LLM training data. If unavailable, the skill falls back to the agent's own knowledge.

### Source: [Tech Leads Club](https://techlead.club)

Installed globally by `/agent-setup`. Treated as read-only — do not edit these directly:

| Skill | Description |
|---|---|
| **coding-guidelines** | Behavioral guidelines to reduce common LLM coding mistakes. Applied when writing or reviewing code. |
| **docs-writer** | Writing, reviewing, and editing documentation and `.md` files. |
| **security-best-practices** | Language and framework specific security reviews (Python, JavaScript/TypeScript, Go). |
| **subagent-creator** | Guide for creating AI subagents with isolated context for complex multi-step workflows. |
| **technical-design-doc-creator** | Creates comprehensive Technical Design Documents (TDD) following industry standards. |
| **web-design-guidelines** | Reviews UI code for accessibility, design, and best-practices compliance. |
