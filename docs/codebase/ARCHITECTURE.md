# Architecture

## Overview / Pattern

`ai-coding-tooling` is a **distribution system**, not a runtime application — no server, no build step, no scheduled work. A single repository holds all agent instructions and skills; `fsvskills` links global content (`~/.claude/...`) into the locations Claude Code expects via symlinks, while project-local content (`CLAUDE.md`, `.claude/skills/`) is tracked directly in the repo and needs no linking. The only executable logic is `bin/skills.mjs`.

## High-Level Structure

```
Repository (single source of truth)
  ├── Global (~/.claude/, via fsvskills setup)
  │     ├── AGENTS.global.md  ──────────► ~/.claude/CLAUDE.md                       (symlink)
  │     ├── skills/<name>/  ────────────► ~/.claude/skills/<name>/                  (symlink)
  │     ├── extended/<skill>/SKILL.md ──► ~/.claude/skills/<skill>/SKILL.extended.md
  │     └── extended/<skill>/references/ ► ~/.claude/skills/<skill>/references.extended/
  └── Project-local (this repo, tracked directly — no setup step)
        ├── CLAUDE.md       (real file)
        └── .claude/skills/ (real dir)
```

## Layers

| Layer | Responsibility | Key Files or Dirs |
| ----- | -------------- | ----------------- |
| Agent config | Global + project-level agent instructions | `AGENTS.global.md`, `CLAUDE.md` |
| CLI | Parse commands, orchestrate all operations | `bin/skills.mjs` |
| Overrides | Additive extensions to vendor skills | `extended/<skill>/SKILL.md`, `extended/<skill>/references/` |
| Registry | Authoritative skill + agent configuration | `config/skills.json`, `config/agents.json` |
| Skills (local) | Skill definitions owned by this repo | `skills/`, `.claude/skills/` |
| Skills (vendor) | Third-party skills, read-only | `~/.claude/skills/<name>/` (installed via npx) |
| Templates | Reusable authoring patterns for skills | `templates/` |

## Dependency Rules

- `bin/skills.mjs` reads `config/` and `extended/`; it never reads skill content beyond YAML frontmatter (description extraction).
- `skills/` and `.claude/skills/` contain agent-facing `.md` content only — no imports, no JavaScript.
- `templates/` files are referenced by skills and the CLI scaffold logic; never auto-loaded by agents.
- `extended/<skill>/` files must augment, never replace, the parent skill.

## Communication Patterns

- Local: filesystem operations (symlinks, copies) via Node.js built-ins.
- Vendor skills: subprocess calls via `execFileSync('npx', args)` — never shell strings (injection-safe).
- No IPC, no network calls, no queues, no HTTP.

## State Management

Stateless. All persistent state lives in `config/skills.json` and `config/agents.json`. No sessions, no cache, no database.

## Error Handling Strategy

- `UserError` (custom `Error` subclass) for expected user mistakes: caught at the CLI entry point (`main()`), printed with `fail()`, exits with code 1.
- Unexpected errors are re-thrown (not caught), producing a stack trace.
- `runNpx` catches subprocess failures, calls `fail()`, and returns `false` — the caller decides whether to abort or continue.

## Observability

No structured logging, no tracing, no metrics. Output is ANSI-colored terminal text via helper functions (`ok`, `info`, `warn`, `fail`, `skip`). Dry-run mode logs intent without executing.

## Notable Patterns

- **Registry-driven CLI:** every command reads `skills.json` + `agents.json` as the sole source of truth — no filesystem scanning to determine install state.
- **Command-pattern CLI:** each sub-command maps to a named function (`cmdSetup`, `cmdAdd`, `cmdDelete`, etc.); no class-based dispatch.
- **Dry-run support:** a global `DRY` flag is checked before every filesystem operation; any command can be safely previewed.
- **Safe symlink operations:** `linkSafe` never clobbers existing files; `relinkOverlay` only re-links if the target is already a symlink.
- **Collision-aware overlays:** `extended/<skill>/references/` installs as `references/` (if the parent has none) or `references.extended/` (when the parent already ships `references/`).
- **Per-skill decision log:** every skill in `skills/` or `extended/` keeps its own `STATE.md` — an append-only log of `AD-NNN` decision entries, mirroring `tlc-spec-driven`'s project-level `.specs/STATE.md` Decisions log but scoped per skill instead of per project. Format and write triggers are in `docs/SKILL-STATE.md`; referenced from `CLAUDE.md`'s "Skill Decision Log" section. This is a manual convention — `fsvskills` does not create, update, or track it.

**Project-local skills currently unused:** `.claude/skills/` is tracked directly in the repo (no longer surfaced via a symlink) but holds no skill content at present — `.claude/` contains only `.skill-lock.json`. Any future project-local skill can still be added there without further setup.
