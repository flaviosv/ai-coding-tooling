# ai-coding-tooling

**Vision:** A single-repository source of truth for Claude Code agent instructions and reusable skills, distributed to any machine or project via symlinks — no duplication, no drift.
**For:** Developers (primarily Flavio Studart) using Claude Code across multiple projects and machines.
**Solves:** Agent configuration and skills scattered across machines; inconsistent behavior; slow bootstrapping of new environments.

## Goals

- One set of agent instructions usable across all projects and machines, kept in sync automatically.
- Reusable skills installable from a single location without duplication.
- Bootstrapping a new machine or project reduced to one command (`fsvskills setup claude-code`).
- Vendor skills (Tech Leads Club, Matt Pocock) overridable without forking, via the `extended/` overlay system.

## Tech Stack

**Core:**

- Language: JavaScript (Node.js ≥ 18, tested on Node 26)
- Runtime: Node.js + `npx` (zero runtime dependencies)
- Shell: Unix-like (macOS / Linux)

**Key dependencies:**

- `fsvskills` CLI (`bin/skills.mjs`) — single-file, dependency-free Node CLI; manages all install/update/override/link operations
- `npx` — vendor skill installation (`@tech-leads-club/agent-skills`, `skills@latest`)

## Scope

**Current capabilities:**

- Global agent config symlinked from `AGENTS.global.md` to `~/.claude/CLAUDE.md`
- Local skills (`skills/`) symlinked globally; project-local skills (`.agents/skills/`) via `.claude → .agents`
- Vendor skill integration (Tech Leads Club, Matt Pocock via `npx`)
- `extended/` overlay system for customizing vendor skills without forking
- `fsvskills` CLI: `setup`, `destroy`, `add`, `delete`, `update`, `override`, `list`, `statusline`
- `config/skills.json` + `config/agents.json` as authoritative registry

**Explicitly out of scope:**

- Supporting AI tools other than Claude Code
- Publishing `fsvskills` to npm (currently requires `npm link` from the repo clone)
- Runtime application logic — this repo has no server, no build step, no tests

## Constraints

- Technical: Node ≥ 18 required; no runtime dependencies allowed in `bin/skills.mjs`
- Platform: Unix-like OS only (macOS / Linux)
- Skill modification: vendor skills (`tech-leads-club`, `matt-pocock`) are read-only; override via `extended/` only
