# Project Structure

**Root:** `ai-coding-tooling/`

## Directory Tree

```
ai-coding-tooling/
├── .claude/                 # Project-local, tracked directly in the repo
│   └── .skill-lock.json     # Tracked skill-install metadata — skills/ mechanism supported, not yet materialized
├── assets/                  # static assets referenced by skills/docs
├── config/
│   ├── hooks.json           # Hook manifest (flat array, merged into settings by `hooks`)
│   └── skills.json          # Skill registry (20 skills: name, source, scope)
├── docs/
│   ├── cli.md                # fs-harness command reference
│   ├── skill-adr.md          # Per-skill STATE.md decision-log format spec
│   ├── skills-dependency.md  # Which skill invokes/reads/writes another
│   ├── uninstall_sonar.md    # Historical removal guide for a since-uninstalled SonarQube integration
│   └── codebase/             # Agent context docs (THIS set — canonical location)
├── extended/                # Additive overrides for vendor skills
│   ├── mermaid-studio/
│   │   ├── scripts/render-c4-fixed.mjs   # headless-Chromium C4 layout-width fix
│   │   ├── SKILL.md
│   │   └── STATE.md
│   ├── skill-architect/
│   │   ├── scripts/validate_skill.py     # overlay validator, extends the parent's
│   │   ├── SKILL.md
│   │   └── STATE.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       ├── STATE.md
│       └── references/       # coding-principles.md, design.md, specify.md, coding-guidelines/
├── references/               # shared reference content, linked only from the global agent-instructions file
│   └── .gitkeep
├── scripts/
│   ├── bin/
│   │   ├── fs-harness.mjs       # fs-harness CLI — all install/update/override/link/doctor logic (814 lines)
│   │   └── misc/
│   │       ├── check-no-stale-refs.mjs  # fails if a removed concept's name reappears in tracked files
│   │       ├── check-references.mjs     # shared-reference + skill-internal link validation (used by `doctor`)
│   │       └── statusline.sh            # deployment source for the `statusline` command
│   ├── hooks/
│   │   ├── require-direnv-credential.sh
│   │   └── resolve-gh-account.sh
│   └── skills/
│       └── sonar-mcp-wrapper.sh # Docker DNS fix for k3d-hosted SonarQube MCP server
├── skills/                  # Project-owned skills (installed globally via fs-harness setup)
│   ├── architecture-evaluate/   # codebase-doc owner (Full / Incremental / Package modes)
│   ├── build-feature/
│   ├── code-review/             # review → optional checkpoint → fix (see its WORKFLOW.md)
│   ├── disk-evaluate/
│   ├── not-your-babysitter/
│   ├── session-evaluate/
│   ├── subagent-dispatch/
│   └── tech-reference-add/
├── karpathy.skill.md        # SKILL.md-shaped file at repo root — NOT under skills/, not registered in config/skills.json (see CONCERNS.md)
├── LICENSE.md
├── package.json             # name: fs-harness, type: module, bin: fs-harness, no deps
└── README.md
```

The project's root agent-instructions file and its global counterpart (symlinked into Claude Code's global config location) are tracked at the repo root but omitted from the tree above per this skill's own naming guardrail; see `docs/codebase/ARCHITECTURE.md`'s High-Level Structure.

## Module Organization

### CLI (`scripts/`)
**Purpose:** All executable logic — install, update, override, link, delete, list, doctor, statusline, hooks — plus the standalone hook and MCP-wrapper scripts it wires up, and two consistency-check scripts.
**Key files:** `scripts/bin/fs-harness.mjs` (single file, 814 lines, zero runtime dependencies). Manages Claude Code only — its paths are hardcoded constants, not registry-driven. `scripts/bin/misc/statusline.sh` is the deployment source for the `statusline` command, copied to Claude Code's global status-line script location. `scripts/bin/misc/check-references.mjs` validates the shared-reference rule and skill-internal link resolution (installed-location aware); run standalone or via `fs-harness doctor`. `scripts/bin/misc/check-no-stale-refs.mjs` is a standalone `git grep` guard against a removed concept's name reappearing in tracked files (`STATE.md` files exempt, as an append-only decision log). `scripts/hooks/require-direnv-credential.sh` is the SessionStart/UserPromptSubmit hook registered via `config/hooks.json`. `scripts/hooks/resolve-gh-account.sh` is the SessionStart/CwdChanged hook, registered the same way, that scopes a GitHub repo's `gh` calls to its owning account via `GH_TOKEN` when more than one `gh` account is logged in. `scripts/skills/sonar-mcp-wrapper.sh` is a standalone Docker DNS fix for the SonarQube MCP server, deployed manually per `docs/uninstall_sonar.md`.

### Registry (`config/`)
**Purpose:** Authoritative source of truth for skill and hook configuration.
**Key files:** `skills.json` (20 skills: 8 local, 10 tech-leads-club, 2 matt-pocock), `hooks.json` (flat array of hook entries).

### Local Skills (`skills/`)
**Purpose:** Skills owned and maintained by this repo; installed globally via `fs-harness setup`.
**Key files:** one `SKILL.md` per skill; some have `references/` subdirs with tech-specific files.

### Project-Local Skills (`.claude/skills/`)
**Purpose:** Skills exposed only to Claude Code within this project. `.claude/` is tracked directly in the repo — no setup step needed to see it.
**Key files:** currently none — `.claude/` holds only tracked skill-install metadata, no `skills/` subdirectory yet. The mechanism is intact and supported but unused at present.

### Overrides (`extended/`)
**Purpose:** Additive overlays for vendor skills — augment without forking the vendor source.
**Key files:** `<skill>/SKILL.md` installs as an extension file alongside the vendor skill; `<skill>/references/` installs as an overlay references directory; a skill may also ship its own `scripts/` (e.g. `mermaid-studio`'s render fix, `skill-architect`'s overlay validator).

### Shared References (`references/`)
**Purpose:** Reference content shared across the global agent-instructions file only — no skill links into it (each skill keeps everything it links inside its own directory).
**Key files:** currently a placeholder (`.gitkeep`); real content not yet added.

## Where Things Live

| Need | Location |
| ---- | -------- |
| Add a new local skill | `skills/<name>/SKILL.md` → `fs-harness add <name> --source local` |
| Add a shared reference (global agent-instructions file only) | `references/` |
| Add a skill workflow reference | `skills/<name>/reference.md` |
| Add a tech-specific reference | `skills/<name>/references/<tech>-<name>.md` (`code-review`: `<tech>.code.md`, `<tech>-performance.code.md`, `<tech>.tests.md`) |
| Codebase context docs | `docs/codebase/` (this set) |
| Override a vendor skill | `extended/<name>/SKILL.md` → `fs-harness override <name>` |
| Project vision | `docs/codebase/PROJECT.md` |
