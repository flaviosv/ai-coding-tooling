# Tech Stack

**Analyzed:** 2026-06-11

## Core

- Language: JavaScript (ES modules, `"type": "module"`)
- Runtime: Node.js ≥ 18 (tested on Node 26)
- Minimum versions: Node ≥ 18 (oldest maintained LTS)
- Package manager: npm (`npm link` for local install)

## Key Libraries

| Library | Version | Purpose | Modern Usage |
| ------- | ------- | ------- | ------------ |
| `node:child_process` | built-in | Execute npx commands for vendor skill installation | `execFileSync('npx', args)` — never a shell string |
| `node:fs` | built-in | Symlinks, file reads/writes, directory checks | `fs.symlinkSync`, `fs.unlinkSync`, `fs.readFileSync`, `fs.mkdirSync` |
| `node:os` | built-in | Home directory resolution | `os.homedir()` |
| `node:path` | built-in | Path construction and resolution | `path.join`, `path.dirname`, `path.resolve` |
| `node:url` | built-in | Derive script root from ESM context | `fileURLToPath(import.meta.url)` |

## Commands

| Task | Command |
| ---- | ------- |
| Bootstrap agent setup | `fsvskills setup claude-code` |
| Install one skill | `fsvskills add claude-code <skill> [--source <s>]` |
| Install status line | `fsvskills statusline [--force]` |
| List skills + state | `fsvskills list claude-code` |
| Preview without changes | append `--dry-run` to any command |
| Remove one skill | `fsvskills delete claude-code <skill>` |
| Scaffold override | `fsvskills override claude-code <skill>` |
| Undo setup | `fsvskills destroy claude-code` |
| Update vendor skills | `fsvskills update claude-code [skills|--all]` |

## Local Development Setup

Clone the repo; run `npm link` to expose `fsvskills` globally. No build step, no external services, no seed data. Alternative without `npm link`: `node bin/skills.mjs <command>` from the repo root.

> **nvm note:** `npm link` installs under the active Node's global prefix. Run `npm link` on the Node version you intend to use; confirm with `node --version` before `setup`.

## Environment Configuration

No environment variables. All paths are resolved from the repo root (`import.meta.url`) and `config/agents.json`.
