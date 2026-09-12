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

## Concepts

- **Source** — where a skill comes from: `local` (this repo's `skills/`) or `tech-leads-club` /
  `matt-pocock` (vendor, via `npx`).
- **Scope** — global (`~/.claude/skills/`) by default; project-local (`.claude/skills/`) for
  `local-only` skills or `add --local`.
- **Registry** — `config/skills.json`, the source of truth for install state. Don't hand-edit it;
  `docs/AGENT-SKILLS.md` is regenerated from it on `add` / `delete` / `override`.
- **Overlay** — `extended/<skill>/` augments a vendor skill without forking it (installed as
  `SKILL.extended.md` + `references.extended/` beside the vendor skill).

## Commands

| Command | Purpose |
| ------- | ------- |
| `add <skill> [--source <s>] [--local]` | Install one skill; registers it in `skills.json` if new |
| `delete <skill>` | Uninstall + deregister a skill (keeps `extended/<skill>/`) |
| `destroy` | Undo `setup` — remove config, uninstall skills |
| `help` | Show usage |
| `hooks` | Sync `config/hooks.json` into `settings.json` (run automatically by `setup`) |
| `list` | Show each skill's source and install state |
| `override <skill>` | Scaffold `extended/<skill>/` and apply the overlay |
| `setup` | Bootstrap: global config + all skills + overrides |
| `statusline [--force]` | Install the Claude Code status line script |
| `update <skills\|--all>` | Update vendor skills (Tech Leads Club / Matt Pocock) |

## Flags

| Flag | Applies to | Effect |
| ---- | ---------- | ------ |
| `--all` | `update` | Update every vendor skill |
| `--dry-run` | all | Print the actions, change nothing |
| `--force` | `statusline` | Overwrite the existing status line script |
| `--local` | `add` | Install into `.claude/skills/` instead of the global skills dir |
| `--source <s>` | `add` | Set the source for a new skill: `local` · `tech-leads-club` · `matt-pocock` |

## Notes & gotchas

- `setup` links `templates/` next to the global skills dir so a `SKILL.md`'s
  `../../templates/<name>.md` references resolve after installation — without it those
  references silently read as missing files. Don't remove that link by hand.
- Only `local` skills (`skills/`, `.claude/skills/`) may be edited in this repo; vendor skills
  are read-only — customize via `override` instead.
- Re-run `override <skill>` after `update <skill>` to re-attach the overlay to the new version.
- Editing hooks: change `config/hooks.json` first, then run `fs-harness hooks` — never hand-edit
  `hooks` in the global `settings.json` directly.
- Editing the status line: change `scripts/bin/misc/statusline.sh` first, then
  `fs-harness statusline --force` — never edit the global copy directly.
