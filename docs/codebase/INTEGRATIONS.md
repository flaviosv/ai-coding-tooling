# External Integrations

**Analyzed:** 2026-06-26

External integrations are limited to skill-package registries reached through `npx`. No application-level service integrations exist.

## Integrations

**Tech Leads Club:**

- Type: third-party skill registry
- Purpose: source of vendor skills (`codenavi`, `docs-writer`, `tlc-spec-driven` (v3), and others)
- Protocol: `npx` (public npm package, no auth)
- Data flow: outbound only (install/update)
- Location: `bin/skills.mjs` → `installSkill` / `updateSkill`
- Install: `npx @tech-leads-club/agent-skills install --skill <name> --agent claude-code [--global]`
- Update: same call (idempotent reinstall)

**Matt Pocock:**

- Type: third-party skill registry
- Purpose: source of vendor skills (`deep-research`, `keybindings-help`, and others)
- Protocol: `npx` (public npm package, no auth)
- Data flow: outbound only (install/update)
- Location: `bin/skills.mjs` → `installSkill` / `updateSkill`
- Install: `npx skills@latest add mattpocock/skills --agent claude-code --skill <name> --yes [--global]`
- Update: `npx skills update <name> --yes [-g]`

**npm:**

- Purpose: `npm link` exposes the `fsvskills` binary globally from the cloned repo
- Protocol: local `npm link` (not published to the npm registry)
- Auth: none

## API Integrations

None — no HTTP/REST/GraphQL clients.

## Webhooks

None.

## Background Jobs

None. No scheduled tasks, crons, or queues.
