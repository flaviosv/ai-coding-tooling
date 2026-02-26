---
name: add-tech-reference
description: >
  Add technology-specific reference files across all skills in this project and extend any global
  skills that qualify. Use when the user says "add support for <technology>", "add a new technology
  reference", "add <tech> to the stack", or "onboard <framework>". Do NOT use for general skill
  creation or project setup.
metadata:
  version: "1.0.0"
  triggers:
    - "add support for"
    - "add a new technology reference"
    - "add <tech> to the stack"
    - "onboard <framework>"
---

# Add Tech Reference

Generate technology-specific reference files across all skills that support per-technology content,
and extend any qualifying global skills that are not yet extended.

## File Naming Convention

All tech-specific reference files follow the pattern: **`<technology>-<skill-name>.md`**

- `<technology>` is the kebab-case slug for the language or framework (e.g. `fastapi`, `go-gin`, `ruby-on-rails`)
- `<skill-name>` is the exact name of the skill directory (e.g. `code-review`, `tests`, `coding-guidelines`)
- Examples: `fastapi-code-review.md`, `go-gin-tests.md`, `ruby-on-rails-coding-guidelines.md`

Generic baseline files (non-tech-specific) are exempt from this pattern and keep their existing names (e.g. `review-checklist.md`, `testing-patterns.md`).

## Step 1: Resolve the Technology Name

Parse the technology name from the user's request. Derive:

- **Display name** — e.g. `Ruby on Rails`, `FastAPI`, `Go Gin`
- **File prefix** — kebab-case slug used in filenames, e.g. `ruby-on-rails`, `fastapi`, `go-gin`
- **Language** — the underlying language if the tech is a framework, e.g. `ruby`, `python`, `go`

If the user's input is ambiguous (e.g. "Rails" could mean Ruby on Rails), confirm before proceeding.

## Step 2: Scan Project Skills for Reference Directories

Scan the `skills/` directory of this project. For each subdirectory, check whether it contains a
`references/` folder. If it does:

1. List the existing reference files to understand the naming convention in use (e.g. `<lang>-<skill-name>.md`, `<framework>-<skill-name>.md`).
2. Check whether at least one file follows a language- or framework-specific naming pattern (i.e. not a generic baseline like `review-checklist.md`). If no tech-specific files exist, skip this skill — it does not use per-technology references.
3. If tech-specific files do exist, infer the content type from the existing filenames and the skill name (e.g. `golang-code-review.md` in skill `code-review` → content type is a code review checklist for Go).
4. Read one existing tech-specific reference file to understand the expected depth, section structure, and code example style.
5. Record this skill in the action plan with: path, naming pattern, content type, and sample file path.

## Step 3: Scan Extended Skills for Reference Directories

Scan the `extended/` directory of this project. For each subdirectory, check whether it contains a
`reference/` folder (singular — note the different convention from `skills/`). Apply the same logic
as Step 2: check for tech-specific files, infer the pattern, read a sample, and record the skill.

## Step 4: Scan Global Skills for Unextended Tech-Specific References

Scan `~/.claude/skills/`. For each skill directory:

**Constraint — qualify a global skill for extension only if ALL of the following are true:**

1. It has a `references/` or `reference/` subdirectory.
2. That directory contains at least two files whose names match a language- or framework-specific pattern (e.g. `<lang>-*.md`, `<framework>-*.md`, `<lang>-<framework>-*.md`). Generic files like `checklist.md`, `patterns.md`, `guide.md`, or `style-guide.md` alone do not qualify.
3. It does NOT already have a `SKILL.extended.md` file (meaning it is not yet extended by this project).
4. The skill is listed in `AGENTS.global.md` with source `Tech Leads Club` or an external registry — skills sourced from `This project (ai-coding-tooling)` are already in `skills/` and handled by Step 2.

For each qualifying global skill:

1. Infer the naming pattern and content type from its existing reference files (same as Step 2).
2. Read its `SKILL.md` to understand what the skill does and how it loads reference files.
3. Record it in the action plan with: global path, naming pattern, content type, extension actions needed.

## Step 5: Check for Existing Coverage

Before building the action plan, check every identified skill for an existing reference file that
already covers the requested technology — including partial matches (e.g. a `python-*.md` file when
adding `fastapi`, or a `go-*.md` file when adding `go-gin`).

For each match found:

1. Read the existing file.
2. Assess whether it already covers the new technology adequately, partially, or not at all:
   - **Adequate** — the file already covers this tech specifically and thoroughly. Skip creating a new file for this skill; note it as "already covered" in the action plan.
   - **Partial** — a related file exists (e.g. a language-level guide when adding a framework, or a file covering some areas but missing key ones for the new tech). Flag for **refactor**: extend the existing file rather than creating a new one.
   - **None** — no relevant file exists. Proceed with creation as planned.

For partial matches flagged for refactor, the action is to extend the existing file by adding a
clearly delimited framework-specific section (e.g. `## FastAPI-Specific Patterns`) rather than
duplicating shared content into a new file.

## Step 6: Present the Action Plan and Confirm

Before writing any files, present a concise summary table to the user:

| Skill | Location | Action | File |
|-------|----------|--------|------|
| code-review | skills/ | Create | `references/<prefix>-review-checklist.md` |
| tests | skills/ | Refactor existing | `references/<existing>-tests.md` (add new tech section) |
| coding-guidelines | extended/ | Already covered | — |
| <global-skill> | ~/.claude/skills/ | New extension + create | `extended/<skill>/reference/<prefix>-*.md` |

Ask the user to confirm before proceeding.

## Step 7: Generate Reference Files for Project Skills

For each skill recorded in Steps 2 and 3:

Generate the tech-specific reference file using your knowledge of the technology. Base the content
on the structure and depth of the sample file you read in the discovery phase. Follow these rules:

- Match the section headings style of the sample file exactly.
- Include concrete code examples specific to the technology — not generic pseudo-code.
- Cover the same thematic areas as other tech-specific files in the same skill (e.g. if the skill covers security, cover security for this tech; if it covers testing patterns, cover testing patterns).
- Write at the same depth level as the sample. Do not over-engineer or under-deliver.
- **Ground content in current best and recommended practices**: use official documentation, widely-adopted community conventions, and well-known framework guides as the authoritative source. Prefer patterns that the framework's own authors recommend over outdated or non-idiomatic alternatives. When a practice is version-specific, note the minimum version it requires.
- Save to the path identified in the action plan.

## Step 8: Generate Extension Infrastructure for Global Skills

For each qualifying global skill recorded in Step 4:

**8a. Create the extension SKILL.md**

Create `extended/<skill-name>/SKILL.md`. Model it on `extended/coding-guidelines/SKILL.md`:

```yaml
---
name: <skill-name>-extended
extends: <skill-name>
description: >
  Tech-specific extension for the <skill-name> skill. This file MUST be read together with the
  parent <skill-name> SKILL.md. The parent skill defines the core workflow; this extension adds
  stack-specific content loaded from reference files.
metadata:
  version: "1.0.0"
  parent_skill: <skill-name>
  source: "ai-coding-tooling (extended/)"
---
```

The body should instruct the agent to detect the project's tech stack from `.agents/PROJECT_DETAILS.md`
and load all matching files from both the parent skill's reference directory and this extension's
`reference/` directory, following the naming convention observed in Step 4.

**8b. Create the reference directory and first tech file**

Create `extended/<skill-name>/reference/<prefix>-<purpose>.md` using the same content generation
rules as Step 6.

**8c. Update AGENTS.global.md**

Find the existing entry for this skill in `AGENTS.global.md`. Append the extended annotation to
the end of its description line, matching the exact format used for `coding-guidelines`:

```
— **Extended**: if `skills/<skill-name>/SKILL.extended.md` exists, load it alongside the parent skill; also load any matching files from `skills/<skill-name>/reference/` for the project's tech stack.
```

Do not create a new entry — update the existing one in place.

## Step 9: Run make link-extended

After all files are written, run:

```bash
make link-extended
```

This symlinks the new `extended/<skill-name>/` directories into `~/.claude/skills/` so the agent
can load them. The Makefile already handles all directories under `extended/` generically — no
Makefile changes are needed.

## Step 10: Report

Output a summary of everything created:

```
## add-tech-reference: <Technology> added

### New reference files
- skills/<skill-name>/references/<prefix>-<skill-name>.md
- extended/<skill-name>/reference/<prefix>-<skill-name>.md
- ...

### New extensions
- extended/<skill-name>/ (SKILL.md + reference/<prefix>-*.md)
  AGENTS.global.md updated ✓
  make link-extended run ✓

### Skipped
- <skill>: no tech-specific reference pattern detected
```

If `make link-extended` fails, report the error and instruct the user to run it manually.
