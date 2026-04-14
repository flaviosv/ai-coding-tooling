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
├── personal/            # Local-only personal skills (gitignored, auto-installed by make link)
├── extended/            # Project-local extensions for globally-installed skills
│   ├── coding-guidelines/
│   │   ├── SKILL.md     # Loaded alongside parent skill; adds stack-specific coding style rules
│   │   └── reference/   # Tech-specific style guides loaded at runtime
│   ├── docs-writer/
│   │   └── SKILL.md     # Adds token-efficiency output rules for all generated .md content
│   └── skill-architect/
│       └── SKILL.md     # Adds guardrail design guidance and the extended/ pattern documentation
├── .agents/skills/      # Project-local skills (auto-loaded when project is opened)
│   ├── agent-setup/     # Bootstraps global agent config and installs all global skills
│   └── skill-manager/   # Installs or updates skills in an agent's skills directory
└── skills/              # Skills owned by this project (installed globally via make link / agent-setup)
    ├── architecture-evaluate/
    ├── code/
    ├── code-review/
    ├── documentation-upsert/
    ├── tech-debt-report/
    ├── tech-reference-add/
    ├── tests/
    └── tests-code-review/
```

## Skills Owned by This Project

**Project-local skills** (`.agents/skills/`, auto-loaded when the project is opened):

| Skill | Description |
|-------|-------------|
| `agent-setup` | Bootstraps global agent config and installs all global skills for any supported agent |
| `skill-manager` | Installs or updates skills in an agent's global skills directory. Prompts for intent if ambiguous |

**Globally installed skills** (`skills/`, installed via `make link` / `/agent-setup`):

| Skill | Description |
|-------|-------------|
| `architecture-evaluate` | Creates/updates the three project context files (PROJECT_DETAILS, ARCHITECTURE, PIPELINE) |
| `code` | Alias for `coding-guidelines` — applies behavioral and tech-specific coding guidelines. Delegator to the TLC skill |
| `code-review` | Performs comprehensive code reviews on local workspace changes or GitHub PRs. Covers architecture, performance, code quality, API design, and security. Includes standalone Performance Audit mode (full-codebase P0–P3 findings report) |
| `documentation-upsert` | Syncs inline API docs and project `.md` files with the current git workspace state. Detects new packages and scaffolds context via architecture-evaluate package mode |
| `tech-debt-report` | Documents tech debts and maintains an anti-pattern index in `docs/TECH_DEBTS.md` |
| `tech-reference-add` | Adds technology-specific reference files across all skills and extends qualifying global skills |
| `tests` | Writes and maintains tests covering unit tests, integration tests, and code coverage analysis |
| `tests-code-review` | Reviews test code quality, coverage patterns, and maintainability. Supports local workspace and GitHub PR review modes |

## External Dependencies

- `make` — symlink automation
- `npx` / Node.js — required for installing Tech Leads Club skills via `npx @tech-leads-club/agent-skills`
- Unix-like shell (macOS / Linux)

## Supported AI Tools

| Tool | Config File | Skills Directory |
|------|-------------|-----------------|
| Claude Code | `CLAUDE.md` | `.claude/skills/` |
| Cursor | — | `.cursor/skills/` |
| Gemini CLI | `GEMINI.md` | `.gemini/skills/` |
| Generic agents | `AGENTS.md` | `.agents/skills/`, `.agent/skills/` |
| Windsurf | — | `.windsurf/skills/` |