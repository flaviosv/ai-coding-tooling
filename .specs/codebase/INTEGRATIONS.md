# External Integrations

## Vendor Skill Providers

### Tech Leads Club

- **Package:** `@tech-leads-club/agent-skills`
- **Purpose:** Installs curated AI coding skills (tlc-spec-driven, docs-writer, codenavi, mermaid-studio, etc.)
- **Protocol:** `npx` → `execFileSync(['npx', '@tech-leads-club/agent-skills', 'install', skill, npxId])`
- **Install location:** `~/.claude/skills/<name>/`
- **Auth:** None — public npm package

### Matt Pocock

- **Package:** `skills@latest`
- **Purpose:** Installs Matt Pocock's AI coding skills
- **Protocol:** `npx` → `execFileSync(['npx', 'skills@latest', 'add', 'mattpocock/skills'])`
- **Install location:** `~/.claude/skills/<name>/`
- **Auth:** None — public npm package

## Background Jobs

None. No scheduled tasks, no queues, no daemons.

## Webhooks

None.

## APIs

None consumed at runtime. All vendor skill installation is CLI-driven and user-initiated.
