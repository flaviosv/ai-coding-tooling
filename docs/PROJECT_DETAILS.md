# Project Details

## Overview

`ai-coding-tooling` is a shared configuration and skills repository for AI coding assistants. It provides a single source of truth for agent instructions and reusable skills, distributed to any supported tool (Claude Code, Cursor, Windsurf, Gemini CLI, etc.) via symlinks.

## Goals

- Maintain one set of agent instructions usable across all supported AI tools
- Share reusable skills from a single location without duplication
- Make bootstrapping a new machine or project fast and consistent
- Keep global skills and agent configuration in sync across tools

## Project Structure

```
ai-coding-tooling/
├── AGENTS.md            # Project-level agent instructions (symlinked to CLAUDE.md, GEMINI.md)
├── AGENTS.global.md     # Global agent instructions (symlinked to ~/.claude/CLAUDE.md, etc.)
├── Makefile             # Automates symlink creation and removal
├── docs/                # Human-readable project documentation
├── skills/              # Skills owned by this project
│   ├── code-review/
│   ├── documentation/
│   ├── evaluate-architecture/
│   ├── global-agent-setup/
│   ├── performance-review/
│   ├── skill-global-installation/
│   ├── tests/
│   └── tests-code-review/
└── skills_copied/       # Skills imported from external sources (reference only)
```

## Skills Owned by This Project

| Skill | Description |
|-------|-------------|
| `global-agent-setup` | Bootstraps global agent config and installs all global skills |
| `skill-global-installation` | Installs a skill globally and updates the Global Skills list in `~/.claude/CLAUDE.md` |
| `evaluate-architecture` | Creates/updates the three project context files (PROJECT_DETAILS, CODING_STYLE, ARCHITECTURE) |
| `documentation` | Syncs inline API docs and project `.md` files with the current git workspace state |
| `code-review` | Performs comprehensive code reviews covering architecture, performance, code quality, API design, and security |
| `performance-review` | Identifies performance bottlenecks, memory issues, and optimization opportunities |
| `tests` | Writes and maintains tests covering unit tests, integration tests, TDD practices, and code coverage analysis |
| `tests-code-review` | Reviews test code quality, coverage patterns, and maintainability |

## External Dependencies

- `make` — symlink automation
- `npx` / Node.js — required for installing Tech Leads Club skills via `npx @tech-leads-club/agent-skills`
- Unix-like shell (macOS / Linux)

## Supported AI Tools

| Tool | Config File | Skills Directory |
|------|-------------|-----------------|
| Claude Code | `CLAUDE.md` | `.claude/skills/` |
| Gemini CLI | `GEMINI.md` | `.gemini/skills/` |
| Cursor | — | `.cursor/skills/` |
| Windsurf | — | `.windsurf/skills/` |
| Generic agents | `AGENTS.md` | `.agents/skills/`, `.agent/skills/` |
