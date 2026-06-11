# Project Structure

**Root:** `ai-coding-tooling/`

## Directory Tree

```
ai-coding-tooling/
├── .agents/skills/          # Project-local skills (exposed via .claude → .agents symlink)
│   ├── kb-from-folder/
│   ├── kb-from-raindrop/
│   └── skill-architect/
├── .specs/                  # Spec-driven planning (tlc-spec-driven convention)
│   ├── codebase/            # Brownfield codebase context docs (this set)
│   └── project/
│       └── PROJECT.md
├── bin/
│   └── skills.mjs           # fsvskills CLI — all install/update/override/link logic (751 lines)
├── config/
│   ├── agents.json          # Per-agent config (paths, npxId, native skills)
│   ├── skills.json          # Skill registry (18 skills: source, scope, description)
│   └── statusline-command.sh
├── docs/
│   ├── AGENT-SKILLS.md      # Auto-generated skills registry (fsvskills regenerates on add/override)
│   ├── codebase/            # Legacy context docs (migrating to .specs/codebase/)
│   │   ├── ARCHITECTURE.md
│   │   └── PROJECT_DETAILS.md
│   └── plans/               # Legacy planning docs (.specs/ is the current convention)
├── extended/                # Additive overrides for vendor skills
│   ├── docs-writer/SKILL.md
│   ├── skill-architect/SKILL.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       └── references/brownfield-mapping.md
├── skills/                  # Project-owned skills (installed globally via fsvskills setup)
│   ├── architecture-evaluate/  # De-registered; source kept as archive
│   ├── code-review/
│   ├── tech-debt-report/
│   ├── tech-reference-add/
│   ├── tests/
│   └── tests-code-review/
├── templates/               # Reusable authoring patterns for skill files
│   ├── extension-frontmatter.md
│   ├── github-pr-review-mode.md
│   ├── reference-file-naming-convention.md
│   ├── reference-loading-constraint.md
│   ├── token-efficiency-rules.md
│   ├── unsupported-tech-stack-alert.md
│   └── version-stratification-guide.md
├── AGENTS.global.md         # Global agent config (symlinked → ~/.claude/CLAUDE.md)
├── AGENTS.md                # Project-level agent instructions (symlinked → .claude/CLAUDE.md)
├── CLAUDE.md                # Project constraints for Claude Code
├── package.json
└── README.md
```

## Module Organization

### CLI (`bin/`)
**Purpose:** All executable logic — install, update, override, link, delete, list, statusline.
**Key files:** `skills.mjs` (single file, 751 lines, zero runtime dependencies)

### Registry (`config/`)
**Purpose:** Authoritative source of truth for agent and skill configuration.
**Key files:** `skills.json` (18 skills), `agents.json` (1 agent: claude-code), `statusline-command.sh`

### Local Skills (`skills/`)
**Purpose:** Skills owned and maintained by this repo; installed globally via `fsvskills setup`.
**Key files:** one `SKILL.md` per skill; some have `references/` subdirs with tech-specific files

### Project-Local Skills (`.agents/skills/`)
**Purpose:** Skills exposed only to Claude Code within this project (via `.claude → .agents` symlink).
**Key files:** `kb-from-folder/`, `kb-from-raindrop/`, `skill-architect/`

### Overrides (`extended/`)
**Purpose:** Additive overlays for vendor skills — augment without forking the vendor source.
**Key files:** `<skill>/SKILL.md` → installed as `SKILL.extended.md`; `<skill>/references/` → `references.extended/`

### Templates (`templates/`)
**Purpose:** Reusable `.md` patterns referenced by skill authoring and CLI scaffold logic.
**Key files:** 7 files covering naming, loading constraints, formatting, frontmatter, and version stratification

## Where Things Live

| Need | Location |
| ---- | -------- |
| Add a new local skill | `skills/<name>/SKILL.md` → `fsvskills add claude-code <name> --source local` |
| Add tech-specific reference | `skills/<name>/references/<tech>-<name>.md` |
| Override a vendor skill | `extended/<name>/SKILL.md` → `fsvskills override claude-code <name>` |
| Project vision | `.specs/project/PROJECT.md` |
| Codebase context docs | `.specs/codebase/` (this set) |
| Feature specs / quick tasks | `.specs/features/` and `.specs/quick/` |
