# Code Conventions

## Naming Conventions

| Element | Pattern | Examples |
| ------- | ------- | -------- |
| Branch names | kebab-case with context prefix | `sdd-migration-tlc-spec-driven` |
| CLI flags | kebab-case | `--dry-run`, `--all`, `--force` |
| Constants | UPPER_SNAKE_CASE | `SCRIPT_DIR`, `ROOT`, `SKILL_NAME_RE`, `DOC_MARKER` |
| Files (JS) | kebab-case | `skills.mjs` |
| Files (config) | kebab-case | `agents.json`, `skills.json` |
| Functions | camelCase | `cmdSetup`, `installSkill`, `readSkillDescription` |
| Skills (dirs) | kebab-case | `code-review`, `tech-debt-report`, `tlc-spec-driven` |
| Variables | camelCase | `agentId`, `skillsDir`, `dryRun` |

## Code Organization

**Function declarations over arrow functions** for all named top-level functions:

```js
function cmdSetup(agentId) { ... }      // preferred
const cmdSetup = (agentId) => { ... }   // not used
```

**Import ordering:** Node built-ins first, grouped, no blank lines between them:

```js
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
```

**File structure within `bin/skills.mjs`:** constants → utility/logging helpers → filesystem helpers → command functions → doc generation → CLI entry point.

## Error Handling

Throw `UserError` for expected user mistakes; let unexpected errors propagate naturally (no swallowing). `runNpx` returns a boolean on subprocess failure — callers check the return value rather than catching exceptions.

## Documentation Pattern

- `.md` files are the primary deliverable — clarity and correctness matter over code heuristics.
- `bin/skills.mjs` uses sparse inline comments at section boundaries only; no multi-line docstrings.
- `SKILL.md` files use YAML frontmatter (`name`, `description`, `version`, `triggers`).
- `extended/<skill>/SKILL.md` uses frontmatter from `templates/extension-frontmatter.md` (`name`, `extends`, `description`, `metadata.version`, `metadata.parent_skill`, `metadata.source`).
- Reference files follow `templates/reference-file-naming-convention.md`: `<technology>-<skill-name>.md`.
- `skills/<name>/reference.md` (no technology prefix, at skill root) is a workflow or orchestration reference — distinct from tech-specific checklists placed under `references/<tech>-<skill>.md`.
- `docs/AGENT-SKILLS.md` is auto-generated below its marker; hand-written content above the marker is preserved on every regeneration.
