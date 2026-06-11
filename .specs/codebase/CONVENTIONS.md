# Code Conventions

## Naming Conventions

**Files:**
- CLI script: `skills.mjs` (single file, `.mjs` for ESM)
- Config: lowercase with hyphens (`agents.json`, `skills.json`)
- Skill directories: kebab-case (`code-review`, `tech-debt-report`, `tlc-spec-driven`)
- Doc files: `UPPER_SNAKE_CASE.md` (`SKILL.md`, `AGENTS.md`, `ARCHITECTURE.md`)
- Tech-specific reference files: `<technology>-<skill-name>.md` (`php-code-review.md`, `go-tests.md`)

**Functions/Methods:**
- camelCase: `expandHome`, `loadJson`, `validateSkillName`, `cmdSetup`, `installSkill`
- Command handlers prefixed with `cmd`: `cmdSetup`, `cmdAdd`, `cmdDelete`, `cmdList`, `cmdOverride`

**Variables:**
- camelCase: `agentId`, `skillName`, `skillsDir`

**Constants:**
- UPPER_SNAKE_CASE: `ROOT`, `SCRIPT_DIR`, `SKILL_NAME_RE`, `DRY`, `AGENTS_DIR`, `MD_SOURCE`
- Color codes grouped in single `c` object: `c.red`, `c.green`, `c.bold`, etc.

## Code Organization

**Section headers in `bin/skills.mjs`:**
```js
// ---------------------------------------------------------------------------
// Section Name
// ---------------------------------------------------------------------------
```
Groups: Paths & config → Utilities → Filesystem actions → Overlay → Install/uninstall → Commands → Docs generation → Main

**Import order:** Node built-ins only, alphabetical by module name.

## Error Handling

- User-facing errors: `throw new UserError(message)` — caught in `main()`, printed cleanly, exits 1
- Unexpected errors: propagate as uncaught exceptions
- Vendor calls: always use `execFileSync` with an explicit `string[]` arg array — never template strings or shell expansion

## Documentation Pattern

- `config/agents.json` and `config/skills.json` are the authoritative registries — `docs/AGENT-SKILLS.md` is auto-regenerated from them
- Agent-facing `.md` files follow token-efficiency rules: tables over prose, bullets over tables, omit sections with no evidence
- Markdown tables sorted alphabetically by the primary column
- SKILL.md files: YAML frontmatter followed by body sections; no horizontal rules inside the body

## Markdown Table Sorting

All tables and bullet lists that enumerate items must be sorted alphabetically by the primary column or item name.
