# fs-harness — CLI Reference

`fs-harness` (`scripts/bin/fs-harness.mjs`) is the skill manager for this repo: installs, updates,
removes, and overrides skills, and keeps `config/skills.json` in sync. Single-file Node CLI, zero
runtime dependencies.

## Usage

```bash
fs-harness <command> [args] [--dry-run]              # after `npm link`
node scripts/bin/fs-harness.mjs <command> [args]      # without npm link, from repo root
fs-harness help                                       # print this same command list from the CLI itself
```

`fs-harness help` is the CLI's own source of truth for syntax — there is no per-command
`--help` (e.g. `fs-harness add --help` errors out), only the one global listing. Always preview a
mutating command with `--dry-run` first.

## Commands

| Command | Purpose |
| ------- | ------- |
| `add <skill> [--source <s>] [--local]` | Install one skill; registers it in `skills.json` if new |
| `delete <skill>` | Uninstall + deregister a skill (keeps `extended/<skill>/`; remove it with `unoverride`) |
| `destroy` | Undo `setup` — remove config, uninstall skills |
| `doctor` | Health check: cross-references, installed-location link resolution, symlinks, skill installs, `config/hooks.json` hooks installed |
| `help` | Show usage |
| `hooks` | Sync `config/hooks.json` into `settings.json` (run automatically by `setup`) |
| `list` | Show each skill's source and install state |
| `override <skill>` | Scaffold `extended/<skill>/` and apply the overlay |
| `setup` | Bootstrap: global config + all skills + overrides |
| `statusline [--force]` | Install the Claude Code status line script |
| `unoverride <skill>` | Undo `override`: unlink the installed overlay, unmark `extended` in `skills.json`, delete `extended/<skill>/` (vendor skill stays installed) |
| `update <skills\|--all>` | Update vendor skills (Tech Leads Club / Matt Pocock) |

## Flags

| Flag | Applies to | Effect |
| ---- | ---------- | ------ |
| `--all` | `update` | Update every vendor skill |
| `--dry-run` | all | Print the actions, change nothing |
| `--force` | `statusline` | Overwrite the existing status line script |
| `--local` | `add` | Install into `.claude/skills/` instead of the global skills dir |
| `--source <s>` | `add` | Set the source for a new skill: `local` · `tech-leads-club` · `matt-pocock` |

## Gotchas

- Don't hand-edit `config/skills.json` — `add`/`delete`/`override`/`unoverride` keep it in sync automatically.
- A vendor skill is read-only — customize it via `override` instead of editing it directly, and
  re-run `override <skill>` after `update <skill>` to re-attach the overlay to the new version.
- Editing hooks: change `config/hooks.json` first, then run `fs-harness hooks` — never hand-edit
  the installed settings file's `hooks` directly.
- Editing the status line: change `scripts/bin/misc/statusline.sh` first, then
  `fs-harness statusline --force` — never edit the installed copy directly.
