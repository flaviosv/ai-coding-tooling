# Project Details

## Overview

`ai-coding-tooling` is a shared configuration and skills repository for Claude Code. It provides a single source of truth for agent instructions and reusable skills, distributed to Claude Code via symlinks.

## Goals

- Maintain one set of agent instructions usable across all supported AI tools
- Share reusable skills from a single location without duplication
- Make bootstrapping a new machine or project fast and consistent
- Keep global skills and agent configuration in sync across tools

## Project Structure

```
ai-coding-tooling/
├── AGENTS.md            # Project-level agent instructions (CLAUDE.md -> AGENTS.md, via `fsvskills setup`)
├── AGENTS.global.md     # Global agent instructions (symlinked to ~/.claude/CLAUDE.md, etc.)
├── package.json         # Exposes the `fsvskills` command (bin/skills.mjs), no dependencies
├── bin/
│   └── skills.mjs       # `fsvskills` — single-file Node CLI managing all skill operations
├── config/              # Source of truth for the skill manager
│   ├── agents.json      # Per-agent config (paths, npx id, native skills)
│   └── skills.json      # Skill → source/scope/description registry
├── docs/                # Human-readable project documentation
├── personal/            # Local-only personal skills (gitignored, installed by `fsvskills setup`)
├── extended/            # Project-local overrides for globally-installed (vendor) skills
│   ├── coding-guidelines/
│   │   ├── SKILL.md     # Loaded alongside parent skill; adds stack-specific coding style rules
│   │   └── reference/   # Tech-specific style guides loaded at runtime
│   ├── docs-writer/
│   │   └── SKILL.md     # Adds token-efficiency output rules for all generated .md content
│   └── skill-architect/
│       └── SKILL.md     # Adds guardrail design guidance and the extended/ pattern documentation
├── .claude -> .agents   # Untracked symlink created by `fsvskills setup`; exposes .agents skills to Claude Code
├── .agents/skills/      # Project-local skills (exposed to Claude via .claude -> .agents)
│   ├── kb-from-folder/
│   ├── kb-from-raindrop/
│   └── skill-architect/
└── skills/              # Skills owned by this project (installed globally via `fsvskills setup`)
    ├── architecture-evaluate/
    ├── code/
    ├── code-review/
    ├── tech-debt-report/
    ├── tech-reference-add/
    ├── tests/
    └── tests-code-review/
```

## Skill Management

Skills are managed by the **`fsvskills`** command (`bin/skills.mjs`), a single-file Node CLI with no dependencies. It replaces the former `agent-setup`/`skill-manager` skills and the `Makefile`. `config/skills.json` is the authoritative source map; `config/agents.json` holds per-agent config. Sources: `local` (this repo, symlinked), `tech-leads-club` and `matt-pocock` (installed via `npx`), and `native` (built into the agent).

`docs/AGENT-SKILLS.md` is regenerated automatically when `add`/`override` change the registry.

| Command | Purpose |
|---------|---------|
| `fsvskills add claude-code <skill> [--source <s>]` | Install one skill (registers it if new) |
| `fsvskills delete claude-code <skill>` | Remove one skill (uninstall + deregister; keeps `extended/`) |
| `fsvskills destroy claude-code` | Undo `setup`: remove global config, uninstall skills, drop project-local links |
| `fsvskills list claude-code` | Show each skill's source and install state |
| `fsvskills override claude-code <skill>` | Scaffold `extended/<skill>/` and apply the overlay |
| `fsvskills setup claude-code` | Bootstrap: global config + all skills + overrides + personal, plus project-local `.claude → .agents` and `CLAUDE.md → AGENTS.md` |
| `fsvskills statusline [--force]` | Install the Claude Code status line script |
| `fsvskills update claude-code [skills...]` | Update vendor (Tech Leads Club / Matt Pocock) skills |

## Skills Owned by This Project

**Project-local skills** (`.agents/skills/`, exposed to Claude Code via the `.claude → .agents` symlink that `fsvskills setup` creates): `kb-from-folder`, `kb-from-raindrop`, `skill-architect`.

**Globally installed skills** (`skills/`, installed via `fsvskills setup`):

| Skill | Description |
|-------|-------------|
| `architecture-evaluate` | Creates, updates, and incrementally syncs project context docs. Full mode writes the three context files (PROJECT_DETAILS, ARCHITECTURE, PIPELINE); Incremental mode syncs inline API docs, root context files, and `docs/codebase/` files from the git workspace and detects new packages; Package mode generates a scoped `CLAUDE.md` |
| `code` | Alias for `coding-guidelines` — applies behavioral and tech-specific coding guidelines. Delegator to the TLC skill |
| `code-review` | Performs comprehensive code reviews on local workspace changes or GitHub PRs. Covers architecture, performance, code quality, API design, and security. Outputs a flat table for small reviews; switches automatically to a zoned format (at-a-glance summary + per-zone findings with zone-prefix IDs) for large or multi-area reviews. Also runs standalone Performance Audits (P0–P3 findings report) |
| `tech-debt-report` | Maintains a permanent numbered tech-debt ledger in `docs/TECH_DEBTS.md` (on-demand documentation, not auto-loaded); per-debt solution plans go in `docs/tech-debts/TD-XX.md` when planning a fix |
| `tech-reference-add` | Adds technology-specific reference files across all skills and extends qualifying global skills |
| `tests` | Writes and maintains tests covering unit tests, integration tests, and code coverage analysis |
| `tests-code-review` | Reviews test code quality, coverage patterns, and maintainability. Supports local workspace and GitHub PR review modes |

## External Dependencies

- Node.js (≥18, oldest maintained LTS; tested on Node 26) — runs the `fsvskills` script (`bin/skills.mjs`)
- `npx` — installs vendor skills (`npx @tech-leads-club/agent-skills`, `npx skills@latest add mattpocock/skills`)
- Unix-like shell (macOS / Linux)

> The `fsvskills` command is repo-local for now (`npm link` from the clone). Making it available on any computer is deferred — see [TASKS.md](TASKS.md).

## Supported AI Tool

Claude Code is the only supported tool. Project config is authored in `AGENTS.md` (linked to `CLAUDE.md`) and project-local skills live in `.agents/skills/` (linked to `.claude/skills/`); `fsvskills setup` creates both links and installs global skills into `~/.claude/skills/`.