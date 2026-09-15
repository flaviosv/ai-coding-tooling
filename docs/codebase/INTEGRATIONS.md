# External Integrations

**Analyzed:** 2026-09-14

External integrations are limited to skill-package registries reached through `npx`. No application-level service integrations exist.

## Integrations

**Tech Leads Club:**

- Type: third-party skill registry
- Purpose: source of vendor skills (`codenavi`, `docs-writer`, `harness-eval`, `mermaid-studio`, `skill-architect`, `tlc-spec-driven`, and others)
- Protocol: `npx` (public npm package, no auth)
- Data flow: outbound only (install/update)
- Location: `scripts/bin/fs-harness.mjs` → `installSkill` / `updateSkill`
- Install: `npx @tech-leads-club/agent-skills install --skill <name> --agent claude-code [--global]`
- Update: `npx @tech-leads-club/agent-skills update --skill <name>` — a distinct subcommand from install (not idempotent reinstall); for a global-scope skill it runs from the home directory rather than the repo, so the vendor CLI's own cwd-based agent-config detection never materializes a project-local copy from this repo's own local config.

**Matt Pocock:**

- Type: third-party skill registry
- Purpose: source of vendor skills (`grill-me`, `grilling`, and others)
- Protocol: `npx` (public npm package, no auth)
- Data flow: outbound only (install/update)
- Location: `scripts/bin/fs-harness.mjs` → `installSkill` / `updateSkill`
- Install: `npx skills@latest add mattpocock/skills --agent claude-code --skill <name> --yes [--global]`
- Update: `npx skills update <name> --yes [-g]` — see `docs/codebase/CONCERNS.md` for a known limitation where this reports success without effect for global-scope skills.

**npm:**

- Purpose: `npm link` exposes the `fs-harness` binary globally from the cloned repo
- Protocol: local `npm link` (not published to the npm registry)
- Auth: none

## API Integrations

None — no HTTP/REST/GraphQL clients.

## Webhooks

None.

## Background Jobs

None. No scheduled tasks, crons, or queues.
