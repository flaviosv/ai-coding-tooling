# Architecture

## Overview

`ai-coding-tooling` is a configuration distribution system, not a runtime application. Its architecture is based on a symlink model: a single repository holds all agent instructions and skills, which are linked into the expected locations for each supported AI tool. There is no build step, no server, and no runtime dependencies beyond `make`.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Agent instructions** | Markdown files (`AGENTS.md`, `AGENTS.global.md`) that tell an AI agent how to behave in a project or globally |
| **Skills** | Self-contained `SKILL.md` files that an agent loads on demand to perform a specific workflow |
| **Symlinks** | The mechanism for distributing one set of files to all supported tools without duplication |

## Distribution Model

```
Repository (single source of truth)
  ├── AGENTS.md  ──────────────────────► CLAUDE.md, GEMINI.md (project root)
  ├── AGENTS.global.md  ───────────────► ~/.claude/CLAUDE.md (global, via global-agent-setup)
  └── skills/  ────────────────────────► .claude/skills/, .cursor/skills/, .gemini/skills/, etc.
```

`make link` creates all project-level symlinks. `/global-agent-setup` handles the global ones.

## Skill Sources

Skills come from two sources:

| Source | Location | Install method |
|--------|----------|---------------|
| This project | `skills/<name>/` | Symlinked via `make link` or `skill-global-installation` |
| Tech Leads Club | `~/.claude/skills/<name>/` | Installed via `npx @tech-leads-club/agent-skills` |

Skills in `skills_copied/` are reference copies only — not installed or symlinked.

## Key Workflows

### Bootstrapping a new machine
```
git clone → make link → /global-agent-setup (in Claude Code)
```

### Adding a new skill
```
Create skills/<name>/SKILL.md
  → Register in AGENTS.md and/or AGENTS.global.md
  → Run /skill-global-installation if it should be globally available
```

### Installing a Tech Leads Club skill
```
/skill-global-installation → npx @tech-leads-club/agent-skills install → CLAUDE.md updated
```

## Design Principles

- **Tool-agnostic** — instructions and skills work across all supported AI assistants
- **Single source of truth** — one repo, one set of files, no duplication
- **Non-destructive** — symlink operations never overwrite real files
- **No runtime** — pure shell and markdown; no servers, no build tools beyond `make`
