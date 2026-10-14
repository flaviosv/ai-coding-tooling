# Project

## Overview

`ai-coding-tooling` is a single-repository source of truth for Claude Code agent instructions and reusable skills, distributed to any machine or project via symlinks — no duplication, no drift. It is primarily for **Flavio Studart**, using Claude Code across multiple projects and machines.

## Vision & Goals

**Vision:** one repository holds all agent configuration and skills; every machine and project links back to it, so there is a single place to edit and everything stays in sync.

- One set of agent instructions usable across all projects and machines, kept in sync automatically.
- Reusable skills installable from a single location without duplication.
- Bootstrapping a new machine or project reduced to one command (`fs-harness setup`).
- Vendor skills (Tech Leads Club, Matt Pocock) overridable without forking, via the `extended/` overlay system.

## Target Users

Developers (primarily the maintainer) running Claude Code across several machines/projects who want consistent agent behavior and one-command environment bootstrapping. Single-maintainer project.

## Scope

**In scope:**

- Global agent config, tracked at the repo root and symlinked into Claude Code's global config location.
- 9 local skills (`skills/`) symlinked globally: `architecture-evaluate`, `build-feature`, `code-review`, `disk-evaluate`, `increment-flow`, `not-your-babysitter`, `session-evaluate`, `subagent-dispatch`, `tech-reference-add`.
- Project-local skills (`.claude/skills/`), tracked directly in the repo — mechanism supported but currently unused (`.claude/` holds only tracked skill-install metadata, no skill content).
- Vendor skill integration (Tech Leads Club, Matt Pocock) via `npx`.
- `extended/` overlay system for customizing vendor skills without forking: `mermaid-studio`, `skill-architect`, `tlc-spec-driven`.
- `fs-harness` CLI: `setup`, `destroy`, `add`, `delete`, `update`, `override`, `unoverride`, `list`, `doctor`, `statusline`, `hooks`.
- `config/skills.json` as the authoritative skill registry (`config/hooks.json` for hook definitions).
- Claude Code hooks (`scripts/hooks/`, defined in `config/hooks.json`): per-repo credential scoping and spoken alerts when a session needs input or goes idle.
- A status line script (`scripts/bin/misc/statusline.sh`) with token-based and subscription display modes.
- A shared, repo-root `references/` directory linked only from the global agent-instructions file.
- Consistency checks (`scripts/bin/misc/`) that validate cross-references between skills, overlays, and the shared `references/` directory, and guard against a removed concept regaining a stale mention.

**Out of scope:**

- Supporting AI tools other than Claude Code.
- Publishing `fs-harness` to npm (currently requires `npm link` from the repo clone).
- Runtime application logic — no server and no build step. Automated tests exist only for the Python scripts that skills bundle, not for the CLI.

## Status

Actively used personal tooling, single maintainer. No release/versioning process; consumed directly from the working tree via symlinks.
