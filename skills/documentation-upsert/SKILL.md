---
name: documentation-upsert
description: >
  Updates all project documentation by inspecting the git workspace for modified files. Detects new packages and triggers scoped architecture evaluation via evaluate-architecture package mode. Updates inline API documentation, root context files (CLAUDE.md, README.md, AGENTS.md), and base docs/ files. Uses the docs-writer skill for all .md file edits. Technology agnostic. Use when the user says "update docs", "generate docs", "api documentation", "document my changes", "sync documentation", or "document recent changes". Do NOT use for creating documentation from scratch — use evaluate-architecture for that.
metadata:
  version: "4.0.0"
  triggers:
    - "update docs"
    - "generate docs"
    - "api documentation"
    - "document my changes"
    - "sync documentation"
    - "document recent changes"
    - "keep docs in sync"
---

# Documentation Upsert

Brings all project documentation in sync with the current state of the codebase — inline API docs, root context files, and project docs. Detects new packages and scaffolds their context automatically.

## Core Rule

> **Any time this skill writes or edits a `.md` file — regardless of context — it must delegate to the `docs-writer` skill.** This ensures consistent formatting, style, and link integrity across all documentation.

## Guardrails

### Scope

- Only update documentation for what actually changed in the git diff.
- New package detection applies only to directories that appear as newly created in the git diff.
- Do not create documentation from scratch for the entire project — that is evaluate-architecture's job.

### Delegation

- All `.md` file edits must go through the **docs-writer** skill — no exceptions.
- New package scaffolding is delegated to **evaluate-architecture** in package mode.

### docs/ Traversal

- Only check files directly in `docs/` (e.g. `docs/ARCHITECTURE.md`, `docs/PROJECT_DETAILS.md`).
- **Never descend into `docs/` subfolders** (`docs/tasks/`, `docs/specs/`, `docs/tech-debts/`, etc.). Those are owned by other skills or workflows and are out of scope.

### Code Changes

- Inline API documentation changes are applied directly to source files.
- Do not refactor, restructure, or modify code — only change comments and doc annotations.
- Do not add documentation to symbols that did not change, unless they are undocumented public exports in a modified file.

## Step 1: Identify Modified Files

Inspect the git workspace to find what has changed:

```bash
# Staged + unstaged changes against HEAD
git diff --name-only HEAD

# Untracked new files
git ls-files --others --exclude-standard
```

Group results into:
- **Source files** — code files that may contain inline API documentation
- **Documentation files** — `.md` and other prose files

If no files are modified, inform the user and stop.

## Step 2: Detect New Packages

Check if any newly created directories in the git diff represent a **new package** — a logical module boundary within the existing project.

### How to detect newly created directories

```bash
# Get all new files (not previously tracked)
git diff HEAD --name-only --diff-filter=A
git ls-files --others --exclude-standard
```

Extract unique parent directories from new files. A directory is "newly created" if ALL files in it are new (no previously tracked files exist in that path).

### How to determine if a new directory is a package

What constitutes a "package" depends entirely on the project's tech stack and conventions. There is no universal checklist — use project context to decide.

1. **Read project context first.** Load `docs/PROJECT_DETAILS.md` and `docs/ARCHITECTURE.md` if available. Understand how this project is structured, what its module boundaries look like, and what patterns existing packages follow.
2. **Compare against existing patterns.** Look at sibling directories at the same level. If the project has `packages/auth/`, `packages/billing/`, and the diff introduces `packages/notifications/` with a similar structure — that's a new package.
3. **Stack-aware reasoning.** Apply what you know about the project's ecosystem:
   - Go: a new directory with `.go` files under an existing `go.mod` is a new package.
   - Django: a new directory under the project's apps directory with `models.py` or `views.py` is likely a new app — `apps.py` is not required.
   - Adobe Commerce / Magento 2: a new directory with `registration.php` and `etc/module.xml` is a new module.
   - Node monorepo: a new directory under `packages/` or `apps/` with its own `package.json` is a new package.
   - PHP: a new directory following the project's PSR-4 namespace structure may be a new module.
   - The above are examples, not an exhaustive list. Reason from the project's actual structure.
4. **When uncertain, ask the user.** If you detect new directories but cannot confidently determine whether they are packages, ask:
   > "I found new directories: `<list>`. Are any of these new packages that should get their own `CLAUDE.md`?"

If no new packages are detected (or the user confirms none), skip to Step 4.

## Step 3: Scaffold New Package Context

**Always ask for user confirmation before invoking evaluate-architecture.** Package detection can produce false positives — the user must confirm before any scaffolding happens.

For each candidate new package:

1. Present findings and ask for confirmation:
   > "I detected what looks like a new package: `<path>`. Should I run evaluate-architecture to generate a `CLAUDE.md` for it?"
2. If the user confirms, invoke evaluate-architecture in **package mode** with the package path:
   > **Invoking skill:** `evaluate-architecture` (package mode for `<path>`)
3. Wait for the package `CLAUDE.md` to be generated before continuing.
4. If the user declines, skip and continue to Step 4.

If multiple candidates are detected, present them all at once so the user can confirm or decline each one in a single response.

## Step 4: Update Inline API Documentation

For each modified source file:

1. **Read the file** to understand what changed.
2. **Check public/exported symbols** (functions, classes, methods, types, constants) for missing or outdated documentation:
   - Are all public symbols documented?
   - Do parameter and return descriptions match the current implementation?
   - Are stale references to removed or renamed symbols present in comments?
3. **Update inline documentation** directly in the source file.

**Principles:**
- Only update docs for symbols that actually changed or are undocumented.
- Preserve the existing documentation style and comment syntax used in each file.
- Keep descriptions factual and concise; do not speculate about intent.

## Step 5: Review Root Context Files

Check root-level context files for potential updates based on the code changes.

Explicitly check these files if they exist:
- `README.md` — project overview, usage instructions, feature lists
- `CLAUDE.md` — agent instructions, skill overrides, available skills list
- `AGENTS.md` — if separate from CLAUDE.md (check if symlink or independent file)
- `GEMINI.md` — if separate from AGENTS.md
- Any other root-level `.md` files that serve as agent or project context

For each file:
1. Read the file to understand its scope and purpose.
2. Determine if any section's content is affected by the code changes.
3. Mark as impacted or not impacted.

**Note:** If CLAUDE.md and GEMINI.md are symlinks to AGENTS.md, only update AGENTS.md — the symlinks propagate automatically.

## Step 6: Cross-Reference Base docs/ Files

List only files directly in `docs/` (no subdirectories):

```bash
find docs/ -maxdepth 1 -name '*.md' -type f 2>/dev/null
```

Typical files: `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`, `TECH_DEBTS.md`, `CODING_STYLE.md`, `TESTS.md`.

For each file:
1. Read the file to understand its scope.
2. Compare against the code changes from Step 1.
3. Mark as impacted if changes fall within its scope.

## Step 7: Update All Impacted .md Files via docs-writer

For each impacted `.md` file identified in Steps 5 and 6:

> **Delegate to `docs-writer`**: invoke the docs-writer skill with the target file path and a summary of what changed. docs-writer handles style, formatting, link verification, and consistency.

Provide docs-writer with:
- The file to update
- A concise description of what changed in the codebase
- Any specific sections that need to be added, removed, or revised

## Step 8: Verify and Report

After all updates, check that:

- [ ] All modified source files with public symbols have updated inline documentation
- [ ] New packages have a `CLAUDE.md` generated via evaluate-architecture package mode
- [ ] Root-level context files are still accurate
- [ ] Every impacted `docs/` base file has been updated
- [ ] All `.md` edits were delegated to docs-writer

Then report:

```
Documentation upsert complete:

New packages scaffolded (via evaluate-architecture):
  ✓ <path>/CLAUDE.md — created

Inline docs updated:
  ✓ <file> — <what was updated>

Project docs updated (via docs-writer):
  ✓ <file> — <what was updated>

No changes needed:
  – <file> — <reason>
```

If any file could not be updated (e.g. ambiguous change, insufficient context), flag it and explain what information is needed.

## Examples

### Example 1: Standard documentation update

User: "update docs"

1. `git diff --name-only HEAD` → `src/api/auth.go`, `src/api/auth_test.go`, `docs/ARCHITECTURE.md`
2. No new directories detected → skip package detection
3. Update inline docs in `src/api/auth.go` (new exported function `ValidateToken` undocumented)
4. Root files: `README.md` — not impacted. `CLAUDE.md` — not impacted.
5. Base docs/: `docs/ARCHITECTURE.md` already in the diff — mark impacted. `docs/PROJECT_DETAILS.md` — not impacted.
6. Delegate `docs/ARCHITECTURE.md` update to docs-writer
7. Report: 1 source file updated, 1 doc file updated

### Example 2: New package detected — user confirms

User: "document my changes"

1. `git diff HEAD --name-only --diff-filter=A` → new files under `app/code/Vendor/Shipping/`
2. Project is Magento 2 (from PROJECT_DETAILS.md). New directory has `registration.php` + `etc/module.xml` → matches existing module pattern in `app/code/Vendor/`
3. Ask: "I detected what looks like a new Magento module: `app/code/Vendor/Shipping/`. Should I run evaluate-architecture to generate a CLAUDE.md for it?"
4. User: "yes" → invoke evaluate-architecture package mode → generates `app/code/Vendor/Shipping/CLAUDE.md`
5. Update inline docs in modified source files
6. Base docs/: `docs/ARCHITECTURE.md` — impacted (new module in the system)
7. Delegate `docs/ARCHITECTURE.md` update to docs-writer
8. Report: 1 package scaffolded, inline docs updated, 1 doc file updated

### Example 3: New directory — user declines

User: "sync documentation"

1. `git diff HEAD --name-only --diff-filter=A` → new files under `internal/notifications/`
2. Project is a Go monolith. `internal/notifications/` is newly created with `.go` files.
3. Ask: "I found a new directory `internal/notifications/` with Go files. Should it get its own CLAUDE.md?"
4. User: "no, it's just a helper package" → skip scaffolding
5. Continue with inline docs, root files, base docs/ as usual
