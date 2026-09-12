# fs-harness — CLI Reference

`fs-harness` (`bin/fs-harness.mjs`) is the skill manager for this repo. It links agent config, installs/updates/removes skills, applies vendor overrides, and keeps `config/skills.json` + `docs/AGENT-SKILLS.md` in sync. Single-file Node CLI, zero runtime dependencies.

> **For agents:** this file is the executable reference. When a task needs to install, remove, override, update, or list skills (or bootstrap the agent setup), read this file, then run the matching command yourself. **Always preview with `--dry-run` first** for any mutating command, show the planned actions, and prefer the smallest command that does the job. `config/skills.json` and `config/agents.json` are the source of truth — do not hand-edit install state; let the CLI manage it.

## Invocation

```bash
fs-harness <command> [args] [--dry-run]        # after `npm link`
node bin/fs-harness.mjs <command> [args]          # without npm link, from repo root
fs-harness help                                # show usage
```

The agent id is the first positional arg for most commands and is currently **`claude-code`** (defined in `config/agents.json`).

## Concepts

- **Agent** — a target tool (`claude-code`); carries its config path, global `skillsDir`, and `npxId`.
- **Source** — where a skill comes from: `local` (this repo's `skills/`) or `tech-leads-club` / `matt-pocock` (vendor, via `npx`).
- **Scope / install location** — global (`~/.claude/skills/`) by default; **project-local** (`.claude/skills/`) for `local-only` skills or when `--local` is passed to `add`.
- **Registry** — `config/skills.json` (skills) + `config/agents.json` (agents). `docs/AGENT-SKILLS.md` is regenerated from the registry on `add` / `delete` / `override`.
- **Overlay** — `extended/<skill>/` augments a vendor skill without forking; installed as `SKILL.extended.md` + `references.extended/` beside the vendor skill.

## Global flags

| Flag | Applies to | Effect |
| ---- | ---------- | ------ |
| `--all` | `update` | Update every vendor skill |
| `--dry-run` | all | Print the actions, change nothing |
| `--force` | `statusline` | Overwrite the existing status line script |
| `--local` | `add` | Install into `.claude/skills/` (project-local) instead of the global skills dir |
| `--source <s>` | `add` | Set the source when registering a new skill: `local` · `tech-leads-club` · `matt-pocock` |

## Commands

| Command | Purpose |
| ------- | ------- |
| `add <agent> <skill> [--source <s>] [--local]` | Install one skill; registers it in `skills.json` if new |
| `delete <agent> <skill>` | Uninstall + deregister a skill (keeps `extended/<skill>/`) |
| `destroy <agent>` | Undo `setup` — remove config, uninstall skills |
| `help` | Show usage |
| `hooks <agent>` | Sync `config/hooks.json` into the agent's `settings.json` (run automatically by `setup`) |
| `list <agent>` | Show each skill's source and install state |
| `override <agent> <skill>` | Scaffold `extended/<skill>/` and apply the overlay |
| `setup <agent>` | Bootstrap: global config + all skills + overrides |
| `statusline [--force]` | Install the Claude Code status line script |
| `update <agent> <skills|--all>` | Update vendor skills (Tech Leads Club / Matt Pocock) |

### `setup <agent>`

Bootstraps everything for the agent: symlinks `CLAUDE.global.md` → the agent config, symlinks `templates/` → the agent config dir, installs every registered skill, applies all `extended/` overrides, and syncs `config/hooks.json` into the agent's `settings.json` (see `hooks <agent>` below). Idempotent and safe — never clobbers existing real files. (Project-local content — `CLAUDE.md`, `.claude/skills/` — is tracked directly in the repo; `setup` doesn't need to create it.)

The `templates/` link is what makes `[Name](../../templates/<name>.md)` references inside a `SKILL.md` resolve once the skill is installed. Installed skills are symlinks into this repo, so a path-resolving tool that normalizes `../../` *lexically* (before following the symlink) lands on `<skillsDir>/../templates` rather than the repo — without this link, every such reference reads as a missing file, silently, and the agent falls back to guessing or to a filesystem-wide search. Re-run `setup` after cloning onto a new machine, and don't remove the link by hand.

```bash
fs-harness setup claude-code --dry-run     # preview a machine bootstrap
fs-harness setup claude-code
```

### `add <agent> <skill> [--source <s>] [--local]`

Installs one skill and registers it if it is new to `skills.json`. For `local` skills it symlinks `skills/<skill>` (or `.claude/skills/<skill>` with `--local`); for vendor skills it runs the matching `npx` installer.

```bash
fs-harness add claude-code architecture-evaluate --source local       # global install
fs-harness add claude-code my-skill --source local --local            # project-local (.claude/skills/)
fs-harness add claude-code jira-assistant --source tech-leads-club
```

### `delete <agent> <skill>`

Uninstalls the skill and removes it from the registry. **Keeps** any `extended/<skill>/` overlay so a later reinstall re-applies it.

```bash
fs-harness delete claude-code some-skill
```

### `update <agent> <skills|--all>`

Runs each vendor's `update` subcommand for the named skills (comma- or space-separated) or all vendor skills with `--all`. Local skills have nothing to update. Tech Leads Club updates run from the home directory (the vendor `update` has no `--global` flag and auto-detects agents from cwd) so global skills are never duplicated into this repo's `.claude/`.

```bash
fs-harness update claude-code tlc-spec-driven
fs-harness update claude-code --all
```

### `override <agent> <skill>`

Scaffolds `extended/<skill>/` (if absent) and applies the overlay symlinks (`SKILL.extended.md`, `references.extended/`) against the installed vendor skill. **Re-run this after updating a vendor skill** to re-attach the overlay to the new version.

```bash
fs-harness override claude-code tlc-spec-driven
```

### `hooks <agent>`

Merges `config/hooks.json` (the source of truth for what's installed — same role as `config/skills.json`) into the agent's `settings.json` `hooks` object. Additive only: existing entries for an event (e.g. other tools' hooks) are never touched or removed, and it's idempotent — matches on the hook script's absolute path already present for an event, so re-running is a no-op. Run automatically by `setup`; use standalone to re-sync without a full `setup` re-run.

```bash
fs-harness hooks claude-code --dry-run
fs-harness hooks claude-code
```

### `list <agent>` · `destroy <agent>` · `statusline [--force]`

```bash
fs-harness list claude-code            # source + install state per skill, then the shared-templates link state
fs-harness destroy claude-code         # tear down a setup
fs-harness statusline --force          # (re)install the status line script
```

## Common workflows

- **Bootstrap a new machine:** `fs-harness setup claude-code` (preview with `--dry-run` first).
- **Add a repo-owned skill:** create `skills/<name>/SKILL.md`, then `fs-harness add claude-code <name> --source local`.
- **Adopt a vendor skill:** `fs-harness add claude-code <name> --source tech-leads-club`.
- **Customize a vendor skill:** `fs-harness override claude-code <name>`, edit `extended/<name>/`.
- **Upgrade a vendor skill + keep your overlay:** `fs-harness update claude-code <name>` → `fs-harness override claude-code <name>`.
- **Remove a skill but keep your overlay:** `fs-harness delete claude-code <name>`.

## Notes & safety

- Editing the status line: change `config/statusline-command.sh` first, then `fs-harness statusline --force` (never edit the global copy directly).
- Editing hooks: change `config/hooks.json` (and/or the script it points to) first, then `fs-harness hooks claude-code` — never hand-edit `hooks` in the global `settings.json` directly.
- Mutating commands support `--dry-run` — use it to preview before applying.
- `add` / `delete` / `override` regenerate `docs/AGENT-SKILLS.md` from `skills.json` (content above its marker is preserved).
- Only `local` skills (`skills/`, `.claude/skills/`) may be edited in this repo; vendor skills are read-only — customize via `extended/`.
