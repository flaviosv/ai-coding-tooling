# Project Structure

**Root:** `ai-coding-tooling/`

## Directory Tree

```
ai-coding-tooling/
├── .claude/                 # Project-local, tracked directly (no longer a symlink)
│   └── .skill-lock.json     # Tracked skill-install metadata — skills/ mechanism supported, not yet materialized
├── .specs/                  # tlc-spec-driven (v3) artifacts
│   ├── STATE.md             # tlc memory: Decisions (AD-NNN) + Handoff (created on first decision)
│   ├── LESSONS.md           # self-improving lessons layer (human-readable)
│   ├── lessons.json         # self-improving lessons layer (structured)
│   ├── tools/
│   │   └── review-token-usage.py
│   └── features/            # 8 past feature specs for this repo's own skills (spec/design/tasks/validation)
├── assets/                  # static assets referenced by skills/docs
├── bin/
│   └── fs-harness.mjs           # fs-harness CLI — all install/update/override/link logic (779 lines)
├── config/
│   ├── agents.json          # Per-agent config (paths, npxId, native skills)
│   ├── skills.json          # Skill registry (20 skills: source, scope, description)
│   └── statusline-command.sh
├── docs/
│   ├── AGENT-SKILLS.md      # Auto-generated skills registry (fs-harness regenerates on add/delete/override)
│   ├── CLI.md                # fs-harness command reference
│   ├── SKILL-STATE.md        # Per-skill STATE.md decision-log format spec
│   ├── UNINSTALL_SONAR.md    # Historical removal guide for a since-uninstalled SonarQube integration
│   └── codebase/            # Agent context docs (THIS set — canonical location)
├── extended/                # Additive overrides for vendor skills
│   ├── docs-writer/SKILL.md
│   ├── mermaid-studio/scripts/
│   ├── skill-architect/SKILL.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       └── references/
│           ├── coding-principles.md
│           └── coding-guidelines/
├── skills/                  # Project-owned skills (installed globally via fs-harness setup)
│   ├── architecture-evaluate/   # codebase-doc owner (Full / Incremental / Package modes)
│   ├── build-feature/
│   ├── code-review/
│   ├── complete-review/
│   ├── fix-review/
│   ├── not-your-babysitter/
│   ├── qa-steps/
│   ├── session-evaluate/
│   ├── tech-reference-add/
│   └── tests-code-review/
├── templates/               # Reusable authoring patterns for skill files (12 files)
├── CLAUDE.global.md         # Global agent config (symlinked → ~/.claude/CLAUDE.md)
├── CLAUDE.md                # Project constraints for Claude Code — tracked directly (no longer a symlink)
├── karpathy.skill.md        # SKILL.md-shaped file at repo root — NOT under skills/, not registered in config/skills.json (see CONCERNS.md)
├── LICENSE.md
├── package.json             # name: fs-harness, type: module, bin: fs-harness, no deps
└── README.md
```

## Module Organization

### CLI (`bin/`)
**Purpose:** All executable logic — install, update, override, link, delete, list, statusline.
**Key files:** `fs-harness.mjs` (single file, 813 lines, zero runtime dependencies).

### Registry (`config/`)
**Purpose:** Authoritative source of truth for agent and skill configuration.
**Key files:** `skills.json` (20 skills: 10 local, 8 tech-leads-club, 2 matt-pocock), `agents.json` (1 agent: claude-code), `statusline-command.sh`.

### Local Skills (`skills/`)
**Purpose:** Skills owned and maintained by this repo; installed globally via `fs-harness setup`.
**Key files:** one `SKILL.md` per skill; some have `references/` subdirs with tech-specific files.

### Project-Local Skills (`.claude/skills/`)
**Purpose:** Skills exposed only to Claude Code within this project. `.claude/` is tracked directly in the repo (no longer a symlink to `.agents/`) — no setup step needed to see it.
**Key files:** currently none — `.claude/` holds only `.skill-lock.json` (tracked skill-install metadata), no `skills/` subdirectory yet. The mechanism is intact and supported but unused at present.

### Overrides (`extended/`)
**Purpose:** Additive overlays for vendor skills — augment without forking the vendor source.
**Key files:** `<skill>/SKILL.md` → installed as `SKILL.extended.md`; `<skill>/references/` → `references.extended/`.

### Templates (`templates/`)
**Purpose:** Reusable `.md` patterns referenced by skill authoring and CLI scaffold logic.
**Key files:** 12 files covering naming, loading constraints, formatting, frontmatter, version stratification, and shared runtime protocols (agent waiting, subagent models, test execution scope).

## Where Things Live

| Need | Location |
| ---- | -------- |
| Add a new local skill | `skills/<name>/SKILL.md` → `fs-harness add claude-code <name> --source local` |
| Add a tech-specific reference | `skills/<name>/references/<tech>-<name>.md` |
| Add a skill workflow reference | `skills/<name>/reference.md` |
| Codebase context docs | `docs/codebase/` (this set) |
| Feature specs / tlc memory | `.specs/features/`, `.specs/STATE.md` (owned by tlc-spec-driven) |
| Override a vendor skill | `extended/<name>/SKILL.md` → `fs-harness override claude-code <name>` |
| Project vision | `docs/codebase/PROJECT.md` |
