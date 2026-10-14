# Architecture

## Overview / Pattern

`ai-coding-tooling` is a **distribution system**, not a runtime application — no server, no build step, no scheduled work. A single repository holds all agent instructions and skills; `fs-harness` links global content (skills, the global agent-instructions file) into the locations Claude Code expects via symlinks, while project-local content (the project's root agent-instructions file, `.claude/skills/`) is tracked directly in the repo and needs no linking. The main executable logic is `scripts/bin/fs-harness.mjs`, backed by two smaller standalone consistency-check scripts, a few Claude Code hook scripts, a status line script, and deterministic helper scripts that individual skills bundle.

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
| Hooks and status line | Event-driven session behavior registered in settings from the manifest | `scripts/hooks/`, `scripts/bin/misc/statusline.sh`, `config/hooks.json` |
| Overrides | Additive extensions to vendor skills | `extended/<skill>/SKILL.md`, `extended/<skill>/references/` |
| Registry | Authoritative skill + hook configuration | `config/skills.json`, `config/hooks.json` |
| Skill scripts | Deterministic steps a skill delegates away from model judgment (PR host detection, GitHub/Azure DevOps reads and writes, review page, `pending.md` validation, session metrics, context scan, k3d stale-image listing) | `skills/<name>/scripts/` |
| Skills (local) | Skill definitions owned by this repo | `skills/`, `.claude/skills/` |
| Skills (vendor) | Third-party skills, read-only | the global skills directory (installed via npx) |

## Dependency Rules

- `scripts/bin/fs-harness.mjs` reads `config/` and `extended/`; it never reads skill content beyond YAML frontmatter (description extraction).
- `skills/` and `.claude/skills/` are agent-facing `.md` content; a skill may also bundle its own scripts under `skills/<name>/scripts/` (Python standard library, bash, or Node built-ins), which nothing outside that skill imports and the CLI never runs.
- A skill keeps everything it links inside its own directory (`references/`, `scripts/`); there is no shared skill-template folder. The repo-root `references/` directory is linked only by the global agent-instructions file.
- `extended/<skill>/` files must augment, never replace, the parent skill.

## Communication Patterns

- Local: filesystem operations (symlinks, copies) via Node.js built-ins.
- Vendor skills: subprocess calls via `execFileSync('npx', args)` — never shell strings (injection-safe).
- The CLI makes no network calls of its own. The one runtime network client is a skill script: `skills/code-review/scripts/ado_review.py` calls Azure DevOps REST over HTTPS (see `docs/codebase/INTEGRATIONS.md`).
- Hooks receive Claude Code events as JSON on stdin; `speak-pending-input.sh` coordinates its alerts across concurrent sessions through a machine-wide marker file and detached background processes.
- No IPC, no queues, no HTTP server.

## State Management

Stateless. All persistent state lives in `config/skills.json` (skill registry) and `config/hooks.json` (hook manifest). Claude Code's own global paths are hardcoded constants in `scripts/bin/fs-harness.mjs`. No sessions, no cache, no database. The one runtime state outside the registry is the spoken-alert hook's marker file in the system temp directory and its compiled microphone helper in the user cache directory — both disposable.

## Error Handling Strategy

- `UserError` (custom `Error` subclass) for expected user mistakes: caught at the CLI entry point (`main()`), printed with `fail()`, exits with code 1.
- Unexpected errors are re-thrown (not caught), producing a stack trace.
- `runNpx` catches subprocess failures, calls `fail()`, and returns `false` — the caller decides whether to abort or continue.
- `cmdDoctor` never throws on an individual failed check — it tallies failures across cross-reference validation, symlink checks, per-skill install checks, and hook-install checks, then exits non-zero only at the end if any were found.

## Observability

No structured logging, no tracing, no metrics. Output is ANSI-colored terminal text via helper functions (`ok`, `info`, `warn`, `fail`, `skip`). Dry-run mode logs intent without executing. The status line (`scripts/bin/misc/statusline.sh`) surfaces session telemetry from Claude Code's status payload: context-window use, prompt-cache hit ratio, session time, and either cost and monthly spend (token mode, when an API key is set) or 5-hour and weekly rate-limit use (subscription mode).

## Notable Patterns

- **Registry-driven CLI:** every command reads `skills.json` (and `hooks.json` for the `hooks` command) as the sole source of truth for registry data — no filesystem scanning to determine install state. Claude Code's own global paths are compile-time constants, not registry-driven.
- **Command-pattern CLI:** each sub-command maps to a named function (`cmdSetup`, `cmdAdd`, `cmdDelete`, `cmdDoctor`, etc.); no class-based dispatch.
- **Dry-run support:** a global `DRY` flag is checked before every filesystem operation; any command can be safely previewed.
- **Safe symlink operations:** `linkSafe` never clobbers existing files; `relinkOverlay` only re-links if the target is already a symlink.
- **Collision-aware overlays:** `extended/<skill>/references/` installs alongside the parent's own `references/`, renamed to avoid collision when the parent already ships one.
- **Deterministic consistency checks:** `fs-harness doctor` composes symlink/install/hook checks with `check-references.mjs` (shared-reference and skill-internal link resolution, aware of each file's *installed* location, not just its repo location) rather than relying on manual review. `check-no-stale-refs.mjs` is a separate, standalone guard — run by hand or from a git hook — against a removed concept's name silently regaining a reference (`STATE.md` decision logs are exempt, since a past entry legitimately names something since removed).
- **Spoken session alerts:** a hook speaks once when a session is blocked on the user (permission prompt, elicitation form, `AskUserQuestion`, plan approval) with one reminder 15 minutes later, and once when a session goes idle; a single machine-wide marker keeps concurrent sessions from stacking alerts. While any app records from a microphone (a Swift helper built on first use), speech plays at reduced volume instead.
- **Per-repo credential scoping:** a SessionStart/CwdChanged hook resolves the right `gh` account for a repo and exports it as `GH_TOKEN`, so every `gh` call in a session — including one made by a dispatched subagent — is scoped without a login being threaded through prompts or flags.
- **Scripted determinism in skills:** where a prose rule governing a mechanical step failed to hold across real runs, the step moves into a script bundled with the skill (verifying GitHub and Azure DevOps writes by re-fetching state, validating `pending.md`, rendering the review checkpoint page); the skill's `.md` keeps the judgment. Python skill scripts ship `unittest` suites.
- **Per-skill decision log:** every skill in `skills/` or `extended/` keeps its own `STATE.md` — an append-only log of `AD-NNN` decision entries. Format and write triggers are in `docs/skill-adr.md`. This is a manual convention — `fs-harness` does not create, update, or track it, though `check-no-stale-refs.mjs` treats every `STATE.md` as an exempt historical record.

**Project-local skills currently unused:** `.claude/skills/` is tracked directly in the repo but holds no skill content at present. Any future project-local skill can be added there without further setup.
