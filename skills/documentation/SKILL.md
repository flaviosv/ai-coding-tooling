---
name: documentation
description: >
  Updates all project documentation by inspecting the git workspace for modified files. Updates inline API documentation (comments, annotations) in source files and related project context .md files. Uses the docs-writer skill for all .md file edits. Technology agnostic. Use when the user says "update docs", "generate docs", "api documentation", "document my changes", or "sync documentation".
metadata:
  version: "3.0.0"
  triggers:
    - "update docs"
    - "generate docs"
    - "api documentation"
    - "document my changes"
    - "sync documentation"
    - "document recent changes"
    - "keep docs in sync"
---

# Update Documentation

This skill brings all project documentation in sync with the current state of the codebase.

## Core Rule

> **Any time this skill writes or edits a `.md` file — regardless of context — it must delegate to the `docs-writer` skill.** This ensures consistent formatting, style, and link integrity across all documentation.

## Scope

When invoked, this skill updates one or more of:

1. **Inline API Documentation** — annotations, docstrings, and comments in source files
2. **Agent Context files** —  files in .agents folder

---

## Instructions

### Step 1: Identify modified files

Inspect the git workspace to find what has changed:

```bash
# Staged + unstaged changes against HEAD
git diff --name-only HEAD

# Untracked new files
git ls-files --others --exclude-standard
```

Group results into two buckets:
- **Source files** — code files that may contain inline API documentation
- **Documentation files** — `.md` and other prose files

If no files are modified, inform the user and stop.

---

### Step 2: Update inline API documentation in source files

For each modified source file:

1. **Read the file** to understand what changed.
2. **Check public/exported symbols** (functions, classes, methods, types, constants) for missing or outdated documentation:
   - Are all public symbols documented?
   - Do parameter and return descriptions match the current implementation?
   - Are stale references to removed or renamed symbols present in comments?
3. **Update inline documentation** directly in the source file.

**Principles:**
- Only update docs for symbols that actually changed or are undocumented.
- Do not refactor or restructure code — only change comments and doc annotations.
- Preserve the existing documentation style and comment syntax used in each file.
- Keep descriptions factual and concise; do not speculate about intent.

---

### Step 3: Identify impacted project documentation

Discover which project documentation files exist and determine whether the code changes affect any of them.

**Discovery locations (in order):**

1. **`.agents/` directory** — list all `.md` files present. These are agent context files (e.g. `ARCHITECTURE.md`, `PROJECT_DETAILS.md`, `PIPELINE.md`, `CODING_STYLE.md`, `TESTS.md`, or any other file the project maintains there).
2. **Project root** — check for AI context files: `README.md`, `AGENTS.md`, `CLAUDE.md`, and any other root-level `.md` files that serve as agent or project context.

**For each discovered file:**

1. Read the file to understand its scope and purpose.
2. Compare against the detected code changes.
3. Mark the file as impacted if the changes fall within its scope.

> If the project uses a `docs/` directory symlinked into `.agents/`, edit files at their real source path (e.g. `docs/ARCHITECTURE.md`) rather than through the symlink.

---

### Step 4: Update project documentation via docs-writer

For each impacted `.md` file:

> **Delegate to `docs-writer`**: invoke the docs-writer skill with the target file path and a summary of what changed. docs-writer will handle style, formatting, link verification, and consistency.

Provide docs-writer with:
- The file to update
- A concise description of what changed in the codebase
- Any specific sections that need to be added, removed, or revised

---

### Step 5: Verify and report

After all updates, check that:

- [ ] All modified source files with public symbols have updated inline documentation
- [ ] Every impacted `.agents/` context file has been updated to reflect the changes
- [ ] Root-level AI context files (`README.md`, `AGENTS.md`, `CLAUDE.md`) are still accurate
- [ ] All documentation is consistent with the current implementation

Then report:

```
Documentation update complete:

Inline docs updated:
  ✓ <file> — <what was updated>

Project docs updated (via docs-writer):
  ✓ <file> — <what was updated>

No changes needed:
  – <file> — <reason>
```

If any file could not be updated (e.g. ambiguous change, insufficient context), flag it and explain what information is needed.

---

## Workflow Summary

1. **Identify changes** — review git workspace
2. **Update inline docs** — annotate modified public symbols in source files
3. **Discover context files** — scan `.agents/` and project root for all `.md` context files
4. **Update impacted files** — update every context file whose scope overlaps with the changes
5. **Verify** — confirm all docs are consistent and complete

---

## Notes

- Focus on "what" and "why" rather than "how" in architecture and project docs
- Inline API documentation should be detailed enough for consumers of the API
- Project Details should remain high-level; avoid implementation specifics
- Keep all context files concise — they are loaded by agents at session start
