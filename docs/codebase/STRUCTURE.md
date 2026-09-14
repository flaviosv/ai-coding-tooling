# Project Structure

**Root:** `ai-coding-tooling/`

## Directory Tree

```
ai-coding-tooling/
├── .claude/                 # Project-local, tracked directly in the repo
│   └── .skill-lock.json     # Tracked skill-install metadata — skills/ mechanism supported, not yet materialized
├── .specs/                  # tlc-spec-driven (v3) artifacts
│   ├── STATE.md             # tlc memory: Decisions (AD-NNN) + Handoff (created on first decision)
│   ├── LESSONS.md           # self-improving lessons layer (human-readable)
│   ├── lessons.json         # self-improving lessons layer (structured)
│   ├── tools/
│   │   └── review-token-usage.py
│   └── features/            # 8 past feature specs for this repo's own skills (spec/design/tasks/validation)
├── assets/                  # static assets referenced by skills/docs
├── config/
│   ├── hooks.json           # Hook manifest (flat array, merged into settings.json by `hooks`)
│   └── skills.json          # Skill registry (20 skills: name, source, scope)
├── docs/
│   ├── cli.md                # fs-harness command reference
│   ├── skill-adr.md        # Per-skill STATE.md decision-log format spec
│   ├── uninstall_sonar.md    # Historical removal guide for a since-uninstalled SonarQube integration
│   └── codebase/            # Agent context docs (THIS set — canonical location)
├── extended/                # Additive overrides for vendor skills
│   ├── mermaid-studio/scripts/
│   ├── skill-architect/SKILL.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       └── references/
│           ├── coding-principles.md
│           └── coding-guidelines/
├── scripts/
│   ├── bin/
│   │   ├── fs-harness.mjs       # fs-harness CLI — all install/update/override/link logic (674 lines)
│   │   └── misc/
│   │       └── statusline.sh    # deployment source for the `statusline` command
│   ├── hooks/
│   │   ├── require-direnv-credential.sh
│   │   └── resolve-gh-account.sh
│   └── skills/
│       └── sonar-mcp-wrapper.sh # Docker DNS fix for k3d-hosted SonarQube MCP server
├── skills/                  # Project-owned skills (installed globally via fs-harness setup)
│   ├── architecture-evaluate/   # codebase-doc owner (Full / Incremental / Package modes)
│   ├── build-feature/
│   ├── code-review/             # review → optional checkpoint → fix (see its WORKFLOW.md)
│   ├── not-your-babysitter/
│   ├── qa-steps/
│   ├── session-evaluate/
│   └── tech-reference-add/
├── CLAUDE.global.md         # Global agent config (symlinked → ~/.claude/CLAUDE.md)
├── CLAUDE.md                # Project constraints for Claude Code — tracked directly in the repo
├── karpathy.skill.md        # SKILL.md-shaped file at repo root — NOT under skills/, not registered in config/skills.json (see CONCERNS.md)
├── LICENSE.md
├── package.json             # name: fs-harness, type: module, bin: fs-harness, no deps
└── README.md
```

## Module Organization

### CLI (`scripts/`)
**Purpose:** All executable logic — install, update, override, link, delete, list, statusline — plus the standalone hook and MCP-wrapper scripts it wires up.
**Key files:** `scripts/bin/fs-harness.mjs` (single file, 674 lines, zero runtime dependencies). Manages Claude Code only — its paths are hardcoded constants, not registry-driven. `scripts/bin/misc/statusline.sh` is the deployment source for the `statusline` command, copied to `~/.claude/statusline-command.sh`. `scripts/hooks/require-direnv-credential.sh` is the SessionStart/UserPromptSubmit hook registered via `config/hooks.json`. `scripts/hooks/resolve-gh-account.sh` is the SessionStart/CwdChanged hook, registered the same way, that scopes a GitHub repo's `gh` calls to its owning account via `GH_TOKEN` in `CLAUDE_ENV_FILE` when more than one `gh` account is logged in. `scripts/skills/sonar-mcp-wrapper.sh` is a standalone Docker DNS fix for the SonarQube MCP server, deployed manually per `docs/uninstall_sonar.md`.

### Registry (`config/`)
**Purpose:** Authoritative source of truth for skill and hook configuration.
**Key files:** `skills.json` (20 skills: 10 local, 8 tech-leads-club, 2 matt-pocock), `hooks.json` (flat array of hook entries).

### Local Skills (`skills/`)
**Purpose:** Skills owned and maintained by this repo; installed globally via `fs-harness setup`.
**Key files:** one `SKILL.md` per skill; some have `references/` subdirs with tech-specific files.

### Project-Local Skills (`.claude/skills/`)
**Purpose:** Skills exposed only to Claude Code within this project. `.claude/` is tracked directly in the repo — no setup step needed to see it.
**Key files:** currently none — `.claude/` holds only `.skill-lock.json` (tracked skill-install metadata), no `skills/` subdirectory yet. The mechanism is intact and supported but unused at present.

### Overrides (`extended/`)
**Purpose:** Additive overlays for vendor skills — augment without forking the vendor source.
**Key files:** `<skill>/SKILL.md` → installed as `SKILL.extended.md`; `<skill>/references/` → `references.extended/`.

## Where Things Live

| Need | Location |
| ---- | -------- |
| Add a new local skill | `skills/<name>/SKILL.md` → `fs-harness add <name> --source local` |
| Add a tech-specific reference | `skills/<name>/references/<tech>-<name>.md` (`code-review`: `<tech>.code.md`, `<tech>-performance.code.md`, `<tech>.tests.md`) |
| Add a skill workflow reference | `skills/<name>/reference.md` |
| Codebase context docs | `docs/codebase/` (this set) |
| Feature specs / tlc memory | `.specs/features/`, `.specs/STATE.md` (owned by tlc-spec-driven) |
| Override a vendor skill | `extended/<name>/SKILL.md` → `fs-harness override <name>` |
| Project vision | `docs/codebase/PROJECT.md` |
