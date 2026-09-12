# Tech Stack

**Analyzed:** 2026-09-01

## Core

- Language: JavaScript (ES modules, `"type": "module"`)
- Runtime: Node.js ≥ 18 (tested on Node 26)
- Minimum versions: Node ≥ 18 (oldest maintained LTS)
- Package manager: npm (`npm link` for local install); zero runtime dependencies

## Key Libraries

The only implementation file (`bin/fs-harness.mjs`, 779 lines) uses Node built-ins exclusively — no third-party packages.

| Library | Version | Purpose | Modern Usage |
| ------- | ------- | ------- | ------------ |
| `node:child_process` | built-in | Execute `npx` for vendor skill install/update | `execFileSync('npx', args)` — never a shell string |
| `node:fs` | built-in | Symlinks, reads/writes, directory checks | `fs.symlinkSync`, `fs.unlinkSync`, `fs.readFileSync`, `fs.mkdirSync` |
| `node:os` | built-in | Home directory resolution | `os.homedir()` |
| `node:path` | built-in | Path construction and resolution | `path.join`, `path.dirname`, `path.resolve` |
| `node:url` | built-in | Derive script root from ESM context | `fileURLToPath(import.meta.url)` |

## Commands

| Task | Command |
| ---- | ------- |
| Bootstrap agent setup | `fs-harness setup claude-code` |
| Install one skill | `fs-harness add claude-code <skill> [--source <s>] [--local]` |
| Install status line | `fs-harness statusline [--force]` |
| List skills + state | `fs-harness list claude-code` |
| Preview without changes | append `--dry-run` to any command |
| Remove one skill | `fs-harness delete claude-code <skill>` |
| Scaffold / apply override | `fs-harness override claude-code <skill>` |
| Undo setup | `fs-harness destroy claude-code` |
| Update vendor skills | `fs-harness update claude-code [skills|--all]` |

## Local Development Setup

Clone the repo; run `npm link` to expose `fs-harness` globally. No build step, no external services, no seed data. Alternative without `npm link`: `node bin/fs-harness.mjs <command>` from the repo root.

> **nvm note:** `npm link` installs under the active Node's global prefix. Run `npm link` on the Node version you intend to use; confirm with `node --version` before `setup`.

## Environment Configuration

No environment variables. All paths are resolved from the repo root (`import.meta.url`) and `config/agents.json`.

## Development Tools

No linter/formatter/test runner configured. Syntax is checked ad hoc with `node --check bin/fs-harness.mjs`; behavior is verified with `--dry-run`.
