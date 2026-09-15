# Code Conventions

## Naming Conventions

| Element | Pattern | Examples |
| ------- | ------- | -------- |
| Branch names | kebab-case with context prefix | `sdd-migration-tlc-spec-driven` |
| CLI flags | kebab-case | `--dry-run`, `--all`, `--force`, `--local` |
| Constants | UPPER_SNAKE_CASE | `SCRIPT_DIR`, `ROOT`, `SKILL_NAME_RE` |
| Files (JS) | kebab-case | `fs-harness.mjs` |
| Files (config) | kebab-case | `skills.json`, `hooks.json` |
| Functions | camelCase | `cmdSetup`, `installSkill`, `applyOverlay` |
| Skills (dirs) | kebab-case | `code-review`, `disk-evaluate`, `architecture-evaluate` |
| Variables | camelCase | `dryRun`, `installScope`, `extDir` |

## Code Organization

**Function declarations over arrow functions** for all named top-level functions:

```js
function cmdSetup() { ... }      // preferred
const cmdSetup = () => { ... }   // not used
```

**Import ordering:** Node built-ins first, grouped, no blank lines between them:

```js
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
```

**File structure within `scripts/bin/fs-harness.mjs`:** constants → utility/logging helpers → filesystem helpers → command functions → doc generation → CLI entry point. The two `scripts/bin/misc/` consistency-check scripts follow the same shape at smaller scale: header comment stating intent → constants → check logic → report/exit.

## Error Handling

Throw `UserError` for expected user mistakes; let unexpected errors propagate naturally (no swallowing). `runNpx` returns a boolean on subprocess failure — callers check the return value rather than catching exceptions. `cmdDoctor` tallies per-check failures instead of throwing, so one failed check never hides the rest.

## Documentation Pattern

- `.md` files are the primary deliverable — clarity and correctness matter over code heuristics.
- `scripts/bin/fs-harness.mjs` and the `scripts/bin/misc/` scripts use sparse inline comments at section/intent boundaries only; no multi-line docstrings.
- Every skill's own `SKILL.md` uses YAML frontmatter (`name`, `description`, `metadata.version`); an overlay in `extended/<skill>/SKILL.md` adds `extends`, `metadata.parent_skill`, and `metadata.source`.
- Tech-specific reference files follow `<technology>-<skill-name>.md`, unless a skill declares scoped variants in its own `SKILL.md` — `code-review` suffixes every checklist with its scope: `<topic>.code.md` / `<topic>.tests.md`, stack-specific `<tech>.code.md`, `<tech>-performance.code.md`, `<tech>.tests.md`, while its orchestration references carry no suffix.
- `skills/<name>/reference.md` (no technology prefix, at the skill root) is a workflow/orchestration reference — distinct from tech-specific checklists under `references/<tech>-<skill>.md`.
- Every skill in `skills/` or `extended/` keeps a `STATE.md` — an append-only per-skill decision log (`## Decisions` section, sequential `AD-NNN` entries with Decision/Reason/Trade-off/Date/Status fields; a superseded entry gets `status: superseded by AD-NNN` rather than being deleted). Full format and write triggers are in `docs/skill-adr.md`. Check a skill's `STATE.md` before modifying it, and append an entry after a change driven by a real decision — not for trivial/cosmetic edits. `scripts/bin/misc/check-no-stale-refs.mjs` treats every `STATE.md` as an exempt historical record.
- A skill never names the project's root or global agent-instructions file as the source of a rule or a dependency — state the rule inline instead. `docs/codebase/`'s own generated files follow the same naming guardrail (see `docs/codebase/STRUCTURE.md`).
- Markdown tables and enumerated bullet lists are sorted alphabetically by primary column, per the maintainer's own standing convention — not restated here to avoid drift.
