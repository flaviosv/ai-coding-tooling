# External Integrations

**Analyzed:** 2026-10-14

The CLI's external integrations are skill-package registries reached through `npx`. Beyond that, skills bundle scripts that call PR hosts and local tooling when a skill runs; there are no application-level service integrations.

## Integrations

**Azure DevOps Services:**

- Type: PR host (REST api-version 7.1, `dev.azure.com` only; on-prem Azure DevOps Server is rejected)
- Purpose: `code-review` reads PR metadata, changed files and comment threads, lists candidate PRs for a batch sweep, posts one thread per finding, and replies to or sets the status of existing threads
- Data flow: both (reads and writes), every count confirmed by re-fetching Azure DevOps state
- Protocol: HTTPS REST via `urllib`
- Location: `skills/code-review/scripts/ado_review.py`; remote detection in `skills/code-review/scripts/detect_remote.py`; private findings page rendered by `skills/code-review/scripts/review_page.py` from `skills/code-review/assets/review-page.template.html`
- Authentication: Entra token from `az account get-access-token` after `az login`, else a PAT in `AZURE_DEVOPS_EXT_PAT`; tokens are never printed
- Constraint: Azure DevOps has no pending review, so a thread is public on creation; the script never votes, touches work items, or deletes

**GitHub:**

- Type: PR host
- Purpose: `code-review` posts a pending review, submits it as a comment review, and replies to and resolves threads
- Data flow: both, every count confirmed by re-fetching GitHub state
- Protocol: the `gh` CLI, invoked with argument arrays
- Location: `skills/code-review/scripts/github_review.py`; per-repo account scoping by `scripts/hooks/resolve-gh-account.sh`
- Authentication: the active `gh` login, or `GH_TOKEN` as exported by that hook

**Local session tooling:**

- Type: macOS system utilities and local cluster tooling
- Purpose: `scripts/hooks/speak-pending-input.sh` speaks alerts with `say` and plays them quietly through `afplay` while `scripts/hooks/mic-in-use.swift` (Core Audio) reports a microphone in use; `skills/disk-evaluate/scripts/k3d_stale_images.sh` reads k3d node images through `docker`, `kubectl` and `jq`, plus an optional local registry HTTP check
- Data flow: local only; the k3d script is read-only

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

**Tech Leads Club:**

- Type: third-party skill registry
- Purpose: source of vendor skills (`codenavi`, `docs-writer`, `harness-eval`, `mermaid-studio`, `skill-architect`, `tlc-spec-driven`, and others)
- Protocol: `npx` (public npm package, no auth)
- Data flow: outbound only (install/update)
- Location: `scripts/bin/fs-harness.mjs` → `installSkill` / `updateSkill`
- Install: `npx @tech-leads-club/agent-skills install --skill <name> --agent claude-code [--global]`
- Update: `npx @tech-leads-club/agent-skills update --skill <name>` — a distinct subcommand from install (not idempotent reinstall); for a global-scope skill it runs from the home directory rather than the repo, so the vendor CLI's own cwd-based agent-config detection never materializes a project-local copy from this repo's own local config.

## API Integrations

The CLI has no HTTP/REST/GraphQL clients. The only REST client in the repo is `skills/code-review/scripts/ado_review.py` (Azure DevOps, above); GitHub is reached through the `gh` CLI.

## Webhooks

None.

## Background Jobs

None scheduled. No crons or queues. The one detached background work is `speak-pending-input.sh`: it starts a delayed reminder (900 seconds) per armed alert and, on first use, a background `swiftc` build of the microphone helper.
