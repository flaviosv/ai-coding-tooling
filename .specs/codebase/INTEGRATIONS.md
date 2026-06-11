# External Integrations

**Analyzed:** 2026-06-11

## Skill Package Registries

### Matt Pocock

**Type:** Third-party skill registry
**Purpose:** Source of vendor skills (`deep-research`, `keybindings-help`, and others).
**Protocol:** npx
**Install:** `npx skills@latest add mattpocock/skills --agent claude-code --skill <name> --yes [--global]`
**Update:** `npx skills update <name> --yes [-g]`
**Auth:** none (public npm package)
**Data flow:** outbound only (install/update)
**Location:** `bin/skills.mjs` → `installSkill` / `updateSkill` functions

### Tech Leads Club

**Type:** Third-party skill registry
**Purpose:** Source of vendor skills (`codenavi`, `docs-writer`, `tlc-spec-driven`, and others).
**Protocol:** npx
**Install:** `npx @tech-leads-club/agent-skills install --skill <name> --agent claude-code [--global]`
**Update:** same npx call (idempotent reinstall)
**Auth:** none (public npm package)
**Data flow:** outbound only (install/update)
**Location:** `bin/skills.mjs` → `installSkill` / `updateSkill` functions

## npm

**Purpose:** `npm link` exposes the `fsvskills` binary globally from the cloned repo.
**Protocol:** local npm link (not published to the npm registry)
**Auth:** none

## Background Jobs

None. No scheduled tasks, crons, or queues.

## Webhooks

None.
