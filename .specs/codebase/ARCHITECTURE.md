# Architecture

**Pattern:** Configuration distribution via symlinks — no runtime server, no build step, no database.

## Overview / Pattern

`ai-coding-tooling` is a **symlink distribution system**. A single repository holds all agent instructions and skills. `fsvskills setup` links them into the expected locations for each supported AI tool (currently Claude Code only). The only executable artifact is `bin/skills.mjs` — a 750-line, dependency-free Node CLI.

## Layers

| Layer | Responsibility | Key Files or Dirs |
|-------|---------------|-------------------|
| Registry | Authoritative source of truth for which skills exist and their metadata | `config/skills.json`, `config/agents.json` |
| CLI | All install, unlink, override, and list operations | `bin/skills.mjs` |
| Global skills | Skills installed into `~/.claude/skills/` for use across all projects | `skills/` |
| Project-local skills | Skills exposed only within this repo via `.claude → .agents` symlink | `.agents/skills/` |
| Vendor overlays | Project-specific augmentations to globally-installed vendor skills | `extended/` |
| Agent instructions | Markdown files that govern agent behavior globally or per-project | `AGENTS.global.md`, `AGENTS.md` |

## Distribution Model

```
Repository (source of truth)
  ├── Global (via fsvskills setup)
  │     ├── AGENTS.global.md ────────────► ~/.claude/CLAUDE.md (copy)
  │     ├── skills/<name>/ ─────────────► ~/.claude/skills/<name>/ (symlink)
  │     └── extended/<skill>/
  │           ├── SKILL.md ────────────► ~/.claude/skills/<skill>/SKILL.extended.md (symlink)
  │           └── references/ ─────────► ~/.claude/skills/<skill>/references.extended/ (symlink)
  └── Project-local (this repo)
        ├── .agents/ ◄─── .claude (symlink)
        └── AGENTS.md ◄── CLAUDE.md (symlink)
```

## Dependency Rules

- `bin/skills.mjs` imports only Node built-ins (`fs`, `path`, `os`, `child_process`, `url`)
- No file in `skills/`, `extended/`, or `templates/` imports another file — each is a standalone document loaded by the agent at runtime
- Vendor skill calls go through `execFileSync` with explicit arg arrays — never shell strings

## Communication Patterns

CLI → filesystem only. No HTTP, no sockets, no queues. Vendor skill installs delegate to `npx` via `execFileSync`.

## Data Model

| File | Role | Schema |
|------|------|--------|
| `config/skills.json` | Skill registry | `{ skills: [{ name, source, scope, description, extended?, installScope? }] }` |
| `config/agents.json` | Agent config | `{ "<agent-id>": { configPath, skillsDir, npxId, projectDir, projectConfig, native[] } }` |

`config/skills.json` is the authoritative source — `fsvskills list` reads it, not the filesystem.

## State Management

Stateless at runtime. The only persistent state is the filesystem: symlinks created by `fsvskills setup` and the JSON config files. No cache, no lock file owned by fsvskills (TLC installer artifacts `.skill-lock.json` are gitignored and not managed by this project).

## Error Handling Strategy

`UserError` (extends `Error`) for expected user-facing failures. `main()` catches `UserError` and prints a clean message with `process.exit(1)`. Unexpected errors propagate as uncaught exceptions (Node default output).

## Skill Sources

| Source | Install location | Install method |
|--------|----------------|----------------|
| `local` (global) | `~/.claude/skills/<name>/` (symlink to `skills/<name>/`) | `fsvskills setup` / `fsvskills add` |
| `local` (project-only) | `.agents/skills/<name>/` (exposed via `.claude → .agents`) | No install step needed |
| `tech-leads-club` | `~/.claude/skills/<name>/` | `npx @tech-leads-club/agent-skills install` |
| `matt-pocock` | `~/.claude/skills/<name>/` | `npx skills@latest add mattpocock/skills` |
| `native` | Built into the agent | Not installed |

## Extended Skills (Overlay System)

`extended/<skill>/` adds to a vendor skill without forking it:

- `SKILL.md` → symlinked as `~/.claude/skills/<skill>/SKILL.extended.md`
- `references/` → symlinked as `~/.claude/skills/<skill>/references.extended/` (collision-aware: only used if vendor already shipped a `references/` dir)

Agents load the base `SKILL.md` then check for and load `SKILL.extended.md` immediately after.

## Notable Patterns

- **Collision-aware symlinking:** `linkSafe` never overwrites an existing target; `relinkOverlay` updates only if the target is already a symlink
- **Arg-array vendor calls:** `runNpx(args, label)` passes commands as `string[]` to `execFileSync`, preventing command injection
- **Registry-first:** skill presence is determined by `config/skills.json`, not filesystem detection
