# Architecture

## Overview / Pattern

`ai-coding-tooling` is a **distribution system**, not a runtime application — no server, no build step, no scheduled work. A single repository holds all agent instructions and skills; `fs-harness` links global content (skills, the global agent-instructions file) into the locations Claude Code expects via symlinks, while project-local content (the project's root agent-instructions file, `.claude/skills/`) is tracked directly in the repo and needs no linking. The only substantial executable logic is `scripts/bin/fs-harness.mjs`, backed by two smaller standalone consistency-check scripts.

## High-Level Structure

```
Repository (single source of truth)
  ├── Global (linked into Claude Code's global config, via fs-harness setup)
  │     ├── global agent-instructions file  ──► Claude Code's global agent-instructions location   (symlink)
  │     ├── skills/<name>/  ─────────────────► the global skills directory, <name>/                (symlink)
  │     ├── extended/<skill>/SKILL.md ───────► an extension file alongside the installed skill
  │     └── extended/<skill>/references/ ────► an overlay references directory alongside it
  └── Project-local (this repo, tracked directly — no setup step)
        ├── project's root agent-instructions file  (real file)
        └── .claude/skills/                          (real dir)
```

## Layers

| Layer | Responsibility | Key Files or Dirs |
| ----- | -------------- | ----------------- |
| Agent config | Global + project-level agent instructions | repo root (see naming note in `docs/codebase/STRUCTURE.md`) |
| CLI | Parse commands, orchestrate all operations | `scripts/bin/fs-harness.mjs` |
| Consistency checks | Validate cross-references and catch stale mentions | `scripts/bin/misc/check-references.mjs`, `scripts/bin/misc/check-no-stale-refs.mjs` |
| Overrides | Additive extensions to vendor skills | `extended/<skill>/SKILL.md`, `extended/<skill>/references/` |
| Registry | Authoritative skill + hook configuration | `config/skills.json`, `config/hooks.json` |
| Skills (local) | Skill definitions owned by this repo | `skills/`, `.claude/skills/` |
| Skills (vendor) | Third-party skills, read-only | the global skills directory (installed via npx) |

## Dependency Rules

- `scripts/bin/fs-harness.mjs` reads `config/` and `extended/`; it never reads skill content beyond YAML frontmatter (description extraction).
- `skills/` and `.claude/skills/` contain agent-facing `.md` content only — no imports, no JavaScript.
- A skill keeps everything it links inside its own directory (`references/`, `scripts/`); there is no shared skill-template folder. The repo-root `references/` directory is linked only by the global agent-instructions file.
- `extended/<skill>/` files must augment, never replace, the parent skill.

## Communication Patterns

- Local: filesystem operations (symlinks, copies) via Node.js built-ins.
- Vendor skills: subprocess calls via `execFileSync('npx', args)` — never shell strings (injection-safe).
- No IPC, no network calls, no queues, no HTTP.

## State Management

Stateless. All persistent state lives in `config/skills.json` (skill registry) and `config/hooks.json` (hook manifest). Claude Code's own global paths are hardcoded constants in `scripts/bin/fs-harness.mjs`. No sessions, no cache, no database.

## Error Handling Strategy

- `UserError` (custom `Error` subclass) for expected user mistakes: caught at the CLI entry point (`main()`), printed with `fail()`, exits with code 1.
- Unexpected errors are re-thrown (not caught), producing a stack trace.
- `runNpx` catches subprocess failures, calls `fail()`, and returns `false` — the caller decides whether to abort or continue.
- `cmdDoctor` never throws on an individual failed check — it tallies failures across cross-reference validation, symlink checks, per-skill install checks, and hook-install checks, then exits non-zero only at the end if any were found.

## Observability

No structured logging, no tracing, no metrics. Output is ANSI-colored terminal text via helper functions (`ok`, `info`, `warn`, `fail`, `skip`). Dry-run mode logs intent without executing.

## Notable Patterns

- **Registry-driven CLI:** every command reads `skills.json` (and `hooks.json` for the `hooks` command) as the sole source of truth for registry data — no filesystem scanning to determine install state. Claude Code's own global paths are compile-time constants, not registry-driven.
- **Command-pattern CLI:** each sub-command maps to a named function (`cmdSetup`, `cmdAdd`, `cmdDelete`, `cmdDoctor`, etc.); no class-based dispatch.
- **Dry-run support:** a global `DRY` flag is checked before every filesystem operation; any command can be safely previewed.
- **Safe symlink operations:** `linkSafe` never clobbers existing files; `relinkOverlay` only re-links if the target is already a symlink.
- **Collision-aware overlays:** `extended/<skill>/references/` installs alongside the parent's own `references/`, renamed to avoid collision when the parent already ships one.
- **Deterministic consistency checks:** `fs-harness doctor` composes symlink/install/hook checks with `check-references.mjs` (shared-reference and skill-internal link resolution, aware of each file's *installed* location, not just its repo location) rather than relying on manual review. `check-no-stale-refs.mjs` is a separate, standalone guard — run by hand or from a git hook — against a removed concept's name silently regaining a reference (`STATE.md` decision logs are exempt, since a past entry legitimately names something since removed).
- **Per-repo credential scoping:** a SessionStart/CwdChanged hook resolves the right `gh` account for a repo and exports it as `GH_TOKEN`, so every `gh` call in a session — including one made by a dispatched subagent — is scoped without a login being threaded through prompts or flags.
- **Per-skill decision log:** every skill in `skills/` or `extended/` keeps its own `STATE.md` — an append-only log of `AD-NNN` decision entries. Format and write triggers are in `docs/skill-adr.md`. This is a manual convention — `fs-harness` does not create, update, or track it, though `check-no-stale-refs.mjs` treats every `STATE.md` as an exempt historical record.

**Project-local skills currently unused:** `.claude/skills/` is tracked directly in the repo but holds no skill content at present. Any future project-local skill can be added there without further setup.
