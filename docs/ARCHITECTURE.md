# Architecture

`ai-coding-tooling` is a configuration distribution system, not a runtime application. Its architecture is based on a symlink model: a single repository holds all agent instructions and skills, which are linked into the expected locations for each supported AI tool. There is no build step and no server. The only operational tool is the dependency-free `fsvskills` script (`bin/skills.mjs`), which performs all install/update/override/link operations; vendor skills are fetched via `npx`.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Agent instructions** | Markdown files (`AGENTS.md`, `AGENTS.global.md`) that tell an AI agent how to behave in a project or globally |
| **Skills** | Self-contained `SKILL.md` files that an agent loads on demand to perform a specific workflow |
| **Project context** | `docs/` files (`PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`) loaded progressively based on task relevance. `docs/TECH_DEBTS.md` is a separate on-demand documentation ledger — intentionally not auto-loaded |
| **Symlinks** | The mechanism for distributing one set of files to all supported tools without duplication |

## Distribution Model

```
Repository (single source of truth)
  ├── Global (~/.claude/, via fsvskills setup)
  │     ├── AGENTS.global.md  ─────────► ~/.claude/CLAUDE.md
  │     ├── skills/<name>/  ───────────► ~/.claude/skills/<name>/  (symlink)
  │     ├── tech-leads-club / matt-pocock ─► ~/.claude/skills/<name>/  (npx)
  │     └── extended/<skill>/
  │           ├── SKILL.md  ──────────► ~/.claude/skills/<skill>/SKILL.extended.md
  │           └── reference/  ────────► ~/.claude/skills/<skill>/reference/ (or reference.extended)
  └── Project-local (this repo, via fsvskills setup)
        ├── .agents/  ◄─────────────── .claude  (symlink: project-local skills)
        └── AGENTS.md  ◄────────────── CLAUDE.md (symlink: project instructions)
```

`fsvskills setup claude-code` creates both the global links (config, skills, overrides, personal) and the project-local ones (`.claude → .agents`, `CLAUDE.md → AGENTS.md`). `fsvskills destroy claude-code` reverses everything. Both go through `bin/skills.mjs`.

## Skill Sources

`config/skills.json` records each skill's source. There is no filesystem marker detection — the registry is authoritative.

| Source | Location | Install method |
|--------|----------|---------------|
| `local` (project-local) | `.agents/skills/<name>/` | Exposed to Claude Code in this repo via the `.claude → .agents` symlink that `fsvskills setup` creates |
| `local` (global) | `skills/<name>/` | Symlinked via `fsvskills setup` / `fsvskills add` |
| `tech-leads-club` | `~/.claude/skills/<name>/` | `npx @tech-leads-club/agent-skills install` |
| `matt-pocock` | `~/.claude/skills/<name>/` | `npx skills@latest add mattpocock/skills` |

## Extended Skills

The `extended/` directory holds project-local additions to globally-installed skills. Each subdirectory name matches an installed skill. It may contain:

- `SKILL.md` — loaded alongside the parent skill as `SKILL.extended.md`; adds stack-specific rules (e.g. language-specific coding style guides)
- `reference/` — reference files (checklists, style guides) loaded by the skill at runtime based on the detected tech stack

`fsvskills setup` (and `fsvskills override`) symlink these into the correct installed skill directories — collision-aware: if the vendor shipped a `references/` dir, the overlay is named `reference.extended`.

## Key Workflows

### Bootstrapping a new machine
```
git clone → npm link → fsvskills setup claude-code → fsvskills statusline
```

### Adding a new project-local skill
```
Create .agents/skills/<name>/SKILL.md
  → Visible to Claude Code via the .claude -> .agents symlink (created by fsvskills setup); no registration or global install needed
```

### Adding a new globally installed skill
```
Create skills/<name>/SKILL.md
  → fsvskills add claude-code <name> --source local   (registers it + regenerates the doc)
```

### Adding a personal skill
```
Create personal/<name>/SKILL.md  (directory is gitignored)
  → fsvskills setup symlinks it into ~/.claude/skills/
  → Appears in agent skill list; never committed or listed in skills.json
```

### Installing a vendor skill (Tech Leads Club or Matt Pocock)
```
fsvskills add claude-code <name> --source tech-leads-club   (or --source matt-pocock)
  → npx install → registered in skills.json → AGENT-SKILLS.md regenerated
```

### Extending (overriding) a globally-installed skill
```
fsvskills override claude-code <skill-name>
  → Scaffolds extended/<skill-name>/SKILL.md and symlinks the overlay into ~/.claude/skills/<skill-name>/
```

### Evaluating a new package
```
New package detected by architecture-evaluate Incremental mode (or user runs architecture-evaluate in package mode)
  → Analyze package manifest, structure, public API, and dependencies
  → Generate <package-path>/CLAUDE.md with scoped context for agents
```

## Design Principles

- **Tool-agnostic** — instructions and skills work across all supported AI assistants
- **Single source of truth** — one repo, one set of files, no duplication
- **Non-destructive** — symlink operations never overwrite real files; guardrails refuse rather than clobber
- **Deterministic management** — a dependency-free Node script (not LLM prose) performs install/update/override; vendor commands run via argument arrays, never shell strings
- **No runtime** — markdown + one Node CLI; no servers, no build step