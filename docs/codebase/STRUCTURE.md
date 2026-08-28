# Project Structure

**Root:** `ai-coding-tooling/`

## Directory Tree

```
ai-coding-tooling/
├── .agents/skills/          # Project-local skills (exposed via .claude → .agents symlink)
│   ├── kb-from-folder/
│   └── kb-from-raindrop/
├── .specs/                  # tlc-spec-driven (v3) artifacts
│   ├── STATE.md             # tlc memory: Decisions (AD-NNN) + Handoff (created on first decision)
│   └── features/            # per-feature spec/design/tasks/validation
├── assets/                  # static assets referenced by skills/docs
├── bin/
│   └── skills.mjs           # fsvskills CLI — all install/update/override/link logic (750 lines)
├── config/
│   ├── agents.json          # Per-agent config (paths, npxId, native skills)
│   ├── skills.json          # Skill registry (21 skills: source, scope, description)
│   └── statusline-command.sh
├── docs/
│   ├── AGENT-SKILLS.md      # Auto-generated skills registry (fsvskills regenerates on add/delete/override)
│   └── codebase/            # Agent context docs (THIS set — canonical location)
├── extended/                # Additive overrides for vendor skills
│   ├── docs-writer/SKILL.md
│   ├── skill-architect/SKILL.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       └── references/
│           ├── coding-principles.md
│           └── coding-guidelines/
├── skills/                  # Project-owned skills (installed globally via fsvskills setup)
│   ├── architecture-evaluate/   # codebase-doc owner (Full / Incremental / Package modes)
│   ├── code-review/
│   ├── tech-debt-report/
│   ├── tech-reference-add/
│   ├── tests/
│   └── tests-code-review/
├── templates/               # Reusable authoring patterns for skill files (12 files)
├── AGENTS.global.md         # Global agent config (symlinked → ~/.claude/CLAUDE.md)
├── AGENTS.md                # Project-level agent instructions (symlinked → CLAUDE.md)
├── CLAUDE.md                # Project constraints for Claude Code
├── LICENSE.md
├── package.json             # name: fsvskills, type: module, bin: fsvskills, no deps
└── README.md
```

## Module Organization

### CLI (`bin/`)
**Purpose:** All executable logic — install, update, override, link, delete, list, statusline.
**Key files:** `skills.mjs` (single file, 750 lines, zero runtime dependencies).

### Registry (`config/`)
**Purpose:** Authoritative source of truth for agent and skill configuration.
**Key files:** `skills.json` (21 skills: 8 local, 12 tech-leads-club, 1 native), `agents.json` (1 agent: claude-code), `statusline-command.sh`.

### Local Skills (`skills/`)
**Purpose:** Skills owned and maintained by this repo; installed globally via `fsvskills setup`.
**Key files:** one `SKILL.md` per skill; some have `references/` subdirs with tech-specific files.

### Project-Local Skills (`.agents/skills/`)
**Purpose:** Skills exposed only to Claude Code within this project (via `.claude → .agents` symlink).
**Key files:** `kb-from-folder/`, `kb-from-raindrop/`.

### Overrides (`extended/`)
**Purpose:** Additive overlays for vendor skills — augment without forking the vendor source.
**Key files:** `<skill>/SKILL.md` → installed as `SKILL.extended.md`; `<skill>/references/` → `references.extended/`.

### Templates (`templates/`)
**Purpose:** Reusable `.md` patterns referenced by skill authoring and CLI scaffold logic.
**Key files:** 12 files covering naming, loading constraints, formatting, frontmatter, version stratification, and shared runtime protocols (agent waiting, subagent models, test execution scope).

## Where Things Live

| Need | Location |
| ---- | -------- |
| Add a new local skill | `skills/<name>/SKILL.md` → `fsvskills add claude-code <name> --source local` |
| Add a tech-specific reference | `skills/<name>/references/<tech>-<name>.md` |
| Add a skill workflow reference | `skills/<name>/reference.md` |
| Codebase context docs | `docs/codebase/` (this set) |
| Feature specs / tlc memory | `.specs/features/`, `.specs/STATE.md` (owned by tlc-spec-driven) |
| Override a vendor skill | `extended/<name>/SKILL.md` → `fsvskills override claude-code <name>` |
| Project vision | `docs/codebase/PROJECT.md` |
