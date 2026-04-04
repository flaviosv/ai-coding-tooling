# Architecture

## Overview

`ai-coding-tooling` is a configuration distribution system, not a runtime application. Its architecture is based on a symlink model: a single repository holds all agent instructions and skills, which are linked into the expected locations for each supported AI tool. There is no build step, no server, and no runtime dependencies beyond `make`.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Agent instructions** | Markdown files (`AGENTS.md`, `AGENTS.global.md`) that tell an AI agent how to behave in a project or globally |
| **Skills** | Self-contained `SKILL.md` files that an agent loads on demand to perform a specific workflow |
| **Project context** | `docs/` files (`PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`, `TECH_DEBTS.md`) loaded progressively based on task relevance |
| **Symlinks** | The mechanism for distributing one set of files to all supported tools without duplication |

## Distribution Model

```
Repository (single source of truth)
  ├── AGENTS.md  ──────────────────────► CLAUDE.md, GEMINI.md (project root)
  ├── AGENTS.global.md  ───────────────► ~/.claude/CLAUDE.md (global, via agent-setup)
  ├── skills/  ────────────────────────► .claude/skills/, .cursor/skills/, .gemini/skills/, etc.
  └── extended/<skill>/
        ├── SKILL.md  ───────────────► ~/.claude/skills/<skill>/SKILL.extended.md
        └── reference/  ─────────────► ~/.claude/skills/<skill>/reference/
```

`make link` creates all project-level symlinks (including extended skill files). `/agent-setup` handles the global ones.

## Skill Sources

Skills come from two sources:

| Source | Location | Install method |
|--------|----------|---------------|
| This project | `skills/<name>/` | Symlinked via `make link` or `skill-installation` |
| Tech Leads Club | `~/.claude/skills/<name>/` | Installed via `npx @tech-leads-club/agent-skills` |

## Extended Skills

The `extended/` directory holds project-local additions to globally-installed skills. Each subdirectory name matches an installed skill. It may contain:

- `SKILL.md` — loaded alongside the parent skill as `SKILL.extended.md`; adds stack-specific rules (e.g. language-specific coding style guides)
- `reference/` — reference files (checklists, style guides) loaded by the skill at runtime based on the detected tech stack

`make link-extended` symlinks these into the correct installed skill directories. It runs automatically as part of `make link`. `make unlink-extended` removes the symlinks.

## Key Workflows

### Bootstrapping a new machine
```
git clone → make link → /agent-setup (in Claude Code)
```

### Adding a new skill
```
Create skills/<name>/SKILL.md
  → Register in AGENTS.md and/or AGENTS.global.md
  → Run /skill-installation if it should be globally available
```

### Adding a personal skill
```
Create personal/<name>/SKILL.md  (directory is gitignored)
  → make link  (or make link-personal) symlinks it into ~/.claude/skills/
  → Appears in agent skill list; never committed or listed in AGENTS.global.md
```

### Installing a Tech Leads Club skill
```
/skill-installation → npx @tech-leads-club/agent-skills install → CLAUDE.md updated
```

### Creating a skill alias
```
/skill-alias → generates skills/<new-name>/SKILL.md (thin delegator)
  → Registers in AGENTS.md, AGENTS.global.md, README.md
  → Original skill remains unchanged
```

### Extending a globally-installed skill
```
Create extended/<skill-name>/SKILL.md (and/or reference/ files)
  → make link-extended (or make link) symlinks them into ~/.claude/skills/<skill-name>/
```

### Evaluating a new package
```
New package detected by documentation-upsert (or user runs architecture-evaluate in package mode)
  → Analyze package manifest, structure, public API, and dependencies
  → Generate <package-path>/CLAUDE.md with scoped context for agents
```

## Design Principles

- **Tool-agnostic** — instructions and skills work across all supported AI assistants
- **Single source of truth** — one repo, one set of files, no duplication
- **Non-destructive** — symlink operations never overwrite real files
- **No runtime** — pure shell and markdown; no servers, no build tools beyond `make`
