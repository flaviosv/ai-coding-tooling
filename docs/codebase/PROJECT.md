# Project

## Overview

`ai-coding-tooling` is a single-repository source of truth for Claude Code agent instructions and reusable skills, distributed to any machine or project via symlinks — no duplication, no drift. It is primarily for **Flavio Studart**, using Claude Code across multiple projects and machines.

## Vision & Goals

**Vision:** one repository holds all agent configuration and skills; every machine and project links back to it, so there is a single place to edit and everything stays in sync.

- One set of agent instructions usable across all projects and machines, kept in sync automatically.
- Reusable skills installable from a single location without duplication.
- Bootstrapping a new machine or project reduced to one command (`fsvskills setup claude-code`).
- Vendor skills (Tech Leads Club, Matt Pocock) overridable without forking, via the `extended/` overlay system.

## Target Users

Developers (primarily the maintainer) running Claude Code across several machines/projects who want consistent agent behavior and one-command environment bootstrapping. Single-maintainer project.

## Scope

**In scope:**

- Global agent config symlinked from `AGENTS.global.md` to `~/.claude/CLAUDE.md`.
- 10 local skills (`skills/`) symlinked globally: `architecture-evaluate`, `build-feature`, `code-review`, `complete-review`, `fix-review`, `not-your-babysitter`, `qa-steps`, `session-evaluate`, `tech-reference-add`, `tests-code-review`.
- Project-local skills (`.agents/skills/`) via `.claude → .agents` — mechanism supported but currently unused (the directory holds only lock files, no skill content).
- Vendor skill integration (Tech Leads Club, Matt Pocock) via `npx`.
- `extended/` overlay system for customizing vendor skills without forking.
- `fsvskills` CLI: `setup`, `destroy`, `add`, `delete`, `update`, `override`, `list`, `statusline`.
- `config/skills.json` + `config/agents.json` as the authoritative registry.

**Out of scope:**

- Supporting AI tools other than Claude Code.
- Publishing `fsvskills` to npm (currently requires `npm link` from the repo clone).
- Runtime application logic — no server, no build step, no automated tests.

## Status

Actively used personal tooling, single maintainer. No release/versioning process; consumed directly from the working tree via symlinks.
