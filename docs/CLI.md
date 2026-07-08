# fsvskills — CLI Reference

`fsvskills` (`bin/skills.mjs`) is the skill manager for this repo. It links agent config, installs/updates/removes skills, applies vendor overrides, and keeps `config/skills.json` + `docs/AGENT-SKILLS.md` in sync. Single-file Node CLI, zero runtime dependencies.

> **For agents:** this file is the executable reference. When a task needs to install, remove, override, update, or list skills (or bootstrap the agent setup), read this file, then run the matching command yourself. **Always preview with `--dry-run` first** for any mutating command, show the planned actions, and prefer the smallest command that does the job. `config/skills.json` and `config/agents.json` are the source of truth — do not hand-edit install state; let the CLI manage it.

## Invocation

```bash
fsvskills <command> [args] [--dry-run]        # after `npm link`
node bin/skills.mjs <command> [args]          # without npm link, from repo root
fsvskills help                                # show usage
```

The agent id is the first positional arg for most commands and is currently **`claude-code`** (defined in `config/agents.json`).

## Concepts

- **Agent** — a target tool (`claude-code`); carries its config path, global `skillsDir`, and `npxId`.
- **Source** — where a skill comes from: `local` (this repo's `skills/`), `tech-leads-club` / `matt-pocock` (vendor, via `npx`), or `native` (built into the agent; not installed).
- **Scope / install location** — global (`~/.claude/skills/`) by default; **project-local** (`.agents/skills/`) for `local-only` skills or when `--local` is passed to `add`.
- **Registry** — `config/skills.json` (skills) + `config/agents.json` (agents). `docs/AGENT-SKILLS.md` is regenerated from the registry on `add` / `delete` / `override`.
- **Overlay** — `extended/<skill>/` augments a vendor skill without forking; installed as `SKILL.extended.md` + `references.extended/` beside the vendor skill.

## Global flags

| Flag | Applies to | Effect |
| ---- | ---------- | ------ |
| `--all` | `update` | Update every vendor skill |
| `--dry-run` | all | Print the actions, change nothing |
| `--force` | `statusline` | Overwrite the existing status line script |
| `--local` | `add` | Install into `.agents/skills/` (project-local) instead of the global skills dir |
| `--source <s>` | `add` | Set the source when registering a new skill: `local` · `tech-leads-club` · `matt-pocock` · `native` |

## Commands

| Command | Purpose |
| ------- | ------- |
| `add <agent> <skill> [--source <s>] [--local]` | Install one skill; registers it in `skills.json` if new |
| `delete <agent> <skill>` | Uninstall + deregister a skill (keeps `extended/<skill>/`) |
| `destroy <agent>` | Undo `setup` — remove config, uninstall skills, drop links |
| `help` | Show usage |
| `list <agent>` | Show each skill's source and install state |
| `override <agent> <skill>` | Scaffold `extended/<skill>/` and apply the overlay |
| `setup <agent>` | Bootstrap: global config + all skills + overrides + project-local links |
| `statusline [--force]` | Install the Claude Code status line script |
| `update <agent> <skills|--all>` | Update vendor skills (Tech Leads Club / Matt Pocock) |

### `setup <agent>`

Bootstraps everything for the agent: symlinks `AGENTS.global.md` → the agent config, installs every registered skill, applies all `extended/` overrides, and creates the project-local links (`.claude → .agents`, `CLAUDE.md → AGENTS.md`). Idempotent and safe — never clobbers existing real files.

```bash
fsvskills setup claude-code --dry-run     # preview a machine bootstrap
fsvskills setup claude-code
```

### `add <agent> <skill> [--source <s>] [--local]`

Installs one skill and registers it if it is new to `skills.json`. For `local` skills it symlinks `skills/<skill>` (or `.agents/skills/<skill>` with `--local`); for vendor skills it runs the matching `npx` installer.

```bash
fsvskills add claude-code architecture-evaluate --source local       # global install
fsvskills add claude-code my-skill --source local --local            # project-local (.agents/skills/)
fsvskills add claude-code codenavi --source tech-leads-club
```

### `delete <agent> <skill>`

Uninstalls the skill and removes it from the registry. **Keeps** any `extended/<skill>/` overlay so a later reinstall re-applies it.

```bash
fsvskills delete claude-code some-skill
```

### `update <agent> <skills|--all>`

Runs each vendor's `update` subcommand for the named skills (comma- or space-separated) or all vendor skills with `--all`. Local and native skills have nothing to update. Tech Leads Club updates run from the home directory (the vendor `update` has no `--global` flag and auto-detects agents from cwd) so global skills are never duplicated into this repo's `.agents/`.

```bash
fsvskills update claude-code tlc-spec-driven
fsvskills update claude-code --all
```

### `override <agent> <skill>`

Scaffolds `extended/<skill>/` (if absent) and applies the overlay symlinks (`SKILL.extended.md`, `references.extended/`) against the installed vendor skill. **Re-run this after updating a vendor skill** to re-attach the overlay to the new version.

```bash
fsvskills override claude-code tlc-spec-driven
```

### `list <agent>` · `destroy <agent>` · `statusline [--force]`

```bash
fsvskills list claude-code            # source + install state per skill
fsvskills destroy claude-code         # tear down a setup
fsvskills statusline --force          # (re)install the status line script
```

## Common workflows

- **Bootstrap a new machine:** `fsvskills setup claude-code` (preview with `--dry-run` first).
- **Add a repo-owned skill:** create `skills/<name>/SKILL.md`, then `fsvskills add claude-code <name> --source local`.
- **Adopt a vendor skill:** `fsvskills add claude-code <name> --source tech-leads-club`.
- **Customize a vendor skill:** `fsvskills override claude-code <name>`, edit `extended/<name>/`.
- **Upgrade a vendor skill + keep your overlay:** `fsvskills update claude-code <name>` → `fsvskills override claude-code <name>`.
- **Remove a skill but keep your overlay:** `fsvskills delete claude-code <name>`.

## Notes & safety

- Editing the status line: change `config/statusline-command.sh` first, then `fsvskills statusline --force` (never edit the global copy directly).
- Mutating commands support `--dry-run` — use it to preview before applying.
- `add` / `delete` / `override` regenerate `docs/AGENT-SKILLS.md` from `skills.json` (content above its marker is preserved).
- Only `local` skills (`skills/`, `.agents/skills/`) may be edited in this repo; vendor skills are read-only — customize via `extended/`.
