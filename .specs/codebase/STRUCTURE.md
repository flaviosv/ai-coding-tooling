# Project Structure

**Root:** `/Users/flaviostudart/Projects/Personal/ai/ai-coding-tooling`

## Directory Tree

```
ai-coding-tooling/
├── .agents/                    # Untracked symlink target; exposes project-local skills to Claude
│   └── skills/
│       ├── kb-from-folder/
│       ├── kb-from-raindrop/
│       └── skill-architect/
├── .claude/                    # Symlink → .agents (created by fsvskills setup)
├── .specs/
│   ├── codebase/               # Codebase context docs (this set)
│   └── project/
│       └── PROJECT.md
├── assets/
│   └── images/                 # Static images (statusline screenshot)
├── bin/
│   └── skills.mjs              # fsvskills CLI — all operations (750 LOC)
├── config/
│   ├── agents.json             # Per-agent config (paths, npxId, native skills)
│   ├── skills.json             # Skill → source/scope/description registry
│   └── statusline-command.sh   # Injected into ~/.claude/statusline-command.sh
├── docs/
│   ├── AGENT-SKILLS.md         # Auto-generated skills registry (do not edit manually)
│   └── codebase/               # Legacy context docs — superseded by .specs/codebase/
├── extended/                   # Vendor skill overlays (augment without forking)
│   ├── docs-writer/
│   │   └── SKILL.md
│   ├── skill-architect/
│   │   └── SKILL.md
│   └── tlc-spec-driven/
│       ├── SKILL.md
│       └── references/
│           ├── brownfield-mapping.md
│           ├── coding-principles.md
│           └── coding-guidelines/
│               ├── best-practices-coding-guidelines.md
│               ├── observability-coding-guidelines.md
│               └── php-coding-guidelines.md
├── skills/                     # Globally installed local skills
│   ├── architecture-evaluate/  # Orphaned — deregistered from skills.json
│   ├── code-review/
│   │   └── references/
│   ├── tech-debt-report/
│   ├── tech-reference-add/
│   ├── tests/
│   │   └── references/
│   └── tests-code-review/
│       └── references/
├── templates/                  # Shared templates for skill/reference authoring
├── AGENTS.global.md            # Global agent instructions → ~/.claude/CLAUDE.md
├── AGENTS.md                   # Project agent instructions (CLAUDE.md symlinks here)
├── CLAUDE.md                   # Symlink → AGENTS.md (created by fsvskills setup)
├── LICENSE.md
├── package.json
└── README.md
```

## Where Things Live

**Skill registry:** `config/skills.json` — add/remove entries here via `fsvskills add/delete`

**Agent config:** `config/agents.json` — Claude Code paths, npxId, native skill list

**CLI logic:** `bin/skills.mjs` — all commands live here; no other implementation files

**Generated docs:** `docs/AGENT-SKILLS.md` — auto-regenerated; never edit manually

**Vendor overrides:** `extended/<skill-name>/` — SKILL.md → SKILL.extended.md; references/ → references.extended/

**Project-local skills:** `.agents/skills/<name>/` — exposed to Claude via `.claude → .agents` symlink; not in `skills.json`
