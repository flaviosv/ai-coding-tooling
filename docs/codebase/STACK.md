# Tech Stack

**Analyzed:** 2026-10-14

## Core

- Language: JavaScript (ES modules, `"type": "module"`) for the CLI; Python 3 (standard library only) for the scripts skills bundle; POSIX/bash shell for hooks, the status line and `disk-evaluate`'s k3d script; Swift for one macOS hook helper (`scripts/hooks/mic-in-use.swift`, compiled on first use with `swiftc`, needs macOS 14+)
- Runtime: Node.js ≥ 18 (tested on Node 26)
- Minimum versions: Node ≥ 18 (oldest maintained LTS)
- Package manager: npm (`npm link` for local install); zero runtime dependencies
- System tools used by hooks and the status line: `jq`, macOS `say` / `afplay` (spoken alerts), `swiftc` (optional; without it alerts keep normal volume)

## Key Libraries

The CLI (`scripts/bin/fs-harness.mjs`, 814 lines) and its two consistency-check scripts (`scripts/bin/misc/check-references.mjs`, `scripts/bin/misc/check-no-stale-refs.mjs`) use Node built-ins exclusively — no third-party packages.

| Library | Version | Purpose | Modern Usage |
| ------- | ------- | ------- | ------------ |
| `node:child_process` | built-in | Execute `npx` for vendor skill install/update; `git grep` for stale-reference checks | `execFileSync('npx', args)` — never a shell string |
| `node:fs` | built-in | Symlinks, reads/writes, directory checks | `fs.symlinkSync`, `fs.unlinkSync`, `fs.readFileSync`, `fs.mkdirSync` |
| `node:os` | built-in | Home directory resolution | `os.homedir()` |
| `node:path` | built-in | Path construction and resolution | `path.join`, `path.dirname`, `path.resolve` |
| `node:url` | built-in | Derive script root from ESM context | `fileURLToPath(import.meta.url)` |

## Commands

| Task | Command |
| ---- | ------- |
| Bootstrap setup | `fs-harness setup` |
| Health check (cross-references, symlinks, skill/hook installs) | `fs-harness doctor` |
| Install one skill | `fs-harness add <skill> [--source <s>] [--local]` |
| Install status line | `fs-harness statusline [--force]` |
| List skills + state | `fs-harness list` |
| Preview without changes | append `--dry-run` to any command |
| Remove an override | `fs-harness unoverride <skill>` |
| Remove one skill | `fs-harness delete <skill>` |
| Scaffold / apply override | `fs-harness override <skill>` |
| Sync hook definitions into settings (run automatically by `setup`) | `fs-harness hooks` |
| Test a skill's bundled Python scripts | `python3 -m unittest discover -s skills/<skill>/scripts/tests` |
| Undo setup | `fs-harness destroy` |
| Update vendor skills | `fs-harness update [skills|--all]` |

## Local Development Setup

Clone the repo; run `npm link` to expose `fs-harness` globally. No build step, no external services, no seed data. Alternative without `npm link`: `node scripts/bin/fs-harness.mjs <command>` from the repo root.

> **nvm note:** `npm link` installs under the active Node's global prefix. Run `npm link` on the Node version you intend to use; confirm with `node --version` before `setup`.

## Environment Configuration

No environment variables read by the CLI itself. All paths are resolved from the repo root (`import.meta.url`) plus hardcoded constants for Claude Code's global locations (skills directory, status-line script, settings file, home-relative global agent-instructions path), via `os.homedir()`. A per-repo credential-scoping hook exports `GH_TOKEN` at session start for `gh` calls (see `docs/codebase/ARCHITECTURE.md`'s Notable Patterns). Skill scripts read `AZURE_DEVOPS_EXT_PAT` (`code-review`'s Azure DevOps script, fallback when no `az login` token) and the status line script checks whether `ANTHROPIC_API_KEY` is set to pick token or subscription display mode; the hook scripts read `CLAUDE_CODE_ENTRYPOINT` to stay silent in headless sessions. Names only; values are never recorded.

## Development Tools

No linter/formatter/unit-test runner configured. Syntax is checked ad hoc with `node --check scripts/bin/fs-harness.mjs`. Python skill scripts are tested with the standard-library `unittest` (see `docs/codebase/TESTING.md`). Structural correctness is checked by `fs-harness doctor` (cross-reference resolution, symlink state, skill/hook install status) and by two standalone scripts under `scripts/bin/misc/`: `check-references.mjs` (shared-reference and skill-internal link validation) and `check-no-stale-refs.mjs` (fails if a given string — e.g. a removed concept's name — still appears anywhere in tracked files, `STATE.md` decision logs exempted). Behavior beyond that is verified with `--dry-run`.
