# Tech Stack

**Analyzed:** 2026-06-11

## Core

- Language: JavaScript (ESM, `.mjs`)
- Runtime: Node.js ≥ 18 (tested on Node 26)
- Package manager: npm (local clone via `npm link`)
- Zero runtime dependencies — `bin/skills.mjs` uses only Node built-ins

## Key Libraries

| Library | Version | Purpose | Modern Usage |
|---------|---------|---------|--------------|
| node:fs | built-in | Symlink creation, file checks | `fs.symlinkSync`, `fs.lstatSync` |
| node:path | built-in | Path manipulation | `path.join`, `path.dirname` |
| node:child_process | built-in | Vendor skill installs | `execFileSync` with arg arrays |
| node:os | built-in | Home directory expansion | `os.homedir()` |

## Commands

| Task | Command |
|------|---------|
| Bootstrap machine | `fsvskills setup claude-code` |
| Tear down | `fsvskills destroy claude-code` |
| Add skill | `fsvskills add claude-code <skill> --source <local\|tech-leads-club\|matt-pocock>` |
| Delete skill | `fsvskills delete claude-code <skill>` |
| List skills | `fsvskills list claude-code` |
| Override vendor skill | `fsvskills override claude-code <skill>` |
| Update vendor skills | `fsvskills update claude-code [skills...]` |
| Install statusline | `fsvskills statusline [--force]` |
| Link for local dev | `npm link` (from repo root) |

## External Services

| Category | Service | Protocol |
|----------|---------|---------|
| Vendor skills | Tech Leads Club (`@tech-leads-club/agent-skills`) | npx |
| Vendor skills | Matt Pocock (`skills@latest`) | npx |

## Testing

No test framework — testing is explicitly out of scope for this project.

## Development Tools

- Node.js ≥ 18 (no bundler, no transpiler)
- `npx` — vendor skill installation

## Environment Configuration

No environment variables required. All paths resolve from the repo root or `~/.claude/`.
