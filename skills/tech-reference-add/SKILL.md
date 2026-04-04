---
name: tech-reference-add
description: >
  Add technology-specific reference files across all skills in this project and extend any global
  skills that qualify. Use when the user says "add support for <technology>", "add a new technology
  reference", "add <tech> to the stack", or "onboard <framework>". Do NOT use for general skill
  creation or project setup.
metadata:
  version: "2.2.0"
  triggers:
    - "add support for"
    - "add a new technology reference"
    - "add <tech> to the stack"
    - "onboard <framework>"
---

# Add Tech Reference

Generate technology-specific reference files for any skill that uses per-technology content, across project skills, extended skills, and global skills. Fully agnostic — works with any skill that has a `references/` or `reference/` directory containing tech-specific files.

## Guardrails

### Scope
- Do NOT write to any location outside `skills/`, `extended/`, or `~/.claude/skills/`.
- Do NOT modify `SKILL.md` files inside `skills/` or `extended/` other than creating new extension files under `extended/`.
- Do NOT run `make link-extended` without explicit user confirmation.
- Do NOT pull in patterns from a parent language when adding a framework-specific reference. If the user requests Laravel, generate content strictly for Laravel — not PHP in general. Stay within the requested technology's own official documentation and idioms only. Do not infer or borrow conventions from the underlying language unless the framework's own documentation explicitly mandates them.
- Do NOT include sensitive information in any reference file — no API keys, credentials, tokens, passwords, private endpoints, connection strings, or internal configuration values. If a secret must be referenced, use a placeholder name only (e.g. `$API_KEY`, `$DATABASE_URL`), never its value. If sensitive information is encountered during research (e.g. in example output from Context7), strip it before writing.

### External Skill Routing

For any skill sourced from an external registry (Tech Leads Club, or any source other than `This project (ai-coding-tooling)`): **never write reference files directly to `~/.claude/skills/<skill-name>/`**. Always route through the `extended/` pattern:

- If `extended/<skill-name>/` already exists → write the reference file to `extended/<skill-name>/reference/` directly. No global files are touched.
- If `extended/<skill-name>/` does not yet exist → trigger Step 8 to create the extension infrastructure first, then write the reference file to `extended/<skill-name>/reference/`.

This is an absolute rule. It applies even when the user confirms the "Before modifying global skills" prompt below. External skills must only ever be extended, never modified in-place.

### Before modifying global skills (`~/.claude/skills/`)

After Step 3, if any selected skill lives in `~/.claude/skills/`, pause before proceeding to Step 6 and show the user:

> "The following globally installed skills will be modified. This affects **all your projects**. Confirm to proceed, or say 'no' to cancel:"
> [list the global skills by name]

If the user says no or does not explicitly confirm, **stop immediately**. Do not proceed with any global skill changes — not even for project-local skills in the same run. The entire run is cancelled.

### Before running `make link-extended`

Before executing `make link-extended`, show the user:

> "About to run: `make link-extended` — this will symlink `extended/<skill-name>/` into `~/.claude/skills/`, making it active for all sessions. Confirm?"

If the user does not explicitly confirm, skip the command and instruct them to run it manually. Note the skipped step in the Step 10 report.

### On collision: `extended/<skill-name>/SKILL.md` already exists

Before creating a new extension `SKILL.md` in Step 8a, check whether `extended/<skill-name>/SKILL.md` already exists. If it does:

1. Read the existing file.
2. Show a diff-style comparison: what the new file would add or change vs. what exists.
3. Ask the user: **overwrite / skip / merge**. Do not write anything until the user chooses.

### On collision: `AGENTS.global.md` annotation already exists

Before appending the `— **Extended**:` annotation in Step 8c, check if that annotation is already present for the target skill. If it is, skip silently and note "annotation already present — skipped" in the Step 10 report.

### Output validation before saving

After generating each reference file in Step 7 (create or re-evaluate mode), verify all of the following before saving:

- A header line is present (e.g. `# <Technology> Reference — <SkillName>`).
- At least one fenced code block exists.
- Version stratification is applied if the technology has meaningful version differences across supported releases.
- No placeholder text remains (e.g. `[TODO]`, `[INSERT HERE]`, `TBD`, `...`).
- No sensitive information is present (credentials, keys, tokens, passwords, private endpoints, connection strings).
- Content is strictly specific to the requested technology — no borrowed patterns from parent languages or sibling frameworks unless explicitly sourced from the technology's own official documentation.

If any check fails, show the specific issue to the user and ask whether to fix and retry or skip this file. Do not save a file that fails validation without explicit user approval.

## File Naming Convention

Load and apply [Reference File Naming Convention](../../templates/reference-file-naming-convention.md).

## Step 1: Resolve the Technology Name and Supported Versions

Parse the technology name from the user's request. Derive:

- **Display name** — e.g. `Ruby on Rails`, `FastAPI`, `Go Gin`
- **File prefix** — kebab-case slug used in filenames, e.g. `ruby-on-rails`, `fastapi`, `go-gin`
- **Language** — the underlying language if the tech is a framework, e.g. `ruby`, `python`, `go`

Determine the **currently supported version range** using Context7 MCP (preferred) or your own knowledge as fallback:

1. Call `mcp__context7__resolve-library-id` with the technology name, then `mcp__context7__query-docs` querying for "supported versions", "release schedule", or "end of life" to get authoritative version support data from the official docs.
2. Identify which versions are currently receiving **active support or security updates** from their official maintainers.
3. The **base version** is the oldest version still receiving any official support (active or security-only). Do not include end-of-life versions.
4. The **latest version** is the most recent stable release.
5. Example: for PHP today, PHP 8.1 still receives security updates and PHP 8.4 is the latest stable → base is 8.1, latest is 8.4.

If the user's input is ambiguous (e.g. "Rails" could mean Ruby on Rails), confirm before proceeding.

## Step 2: Discover All Skills with Reference Directories

Scan all three locations for skill directories that contain a `references/` or `reference/` folder:

1. `skills/` — project skills (uses `references/` plural)
2. `extended/` — extended skills (uses `reference/` singular)
3. `~/.claude/skills/` — global skills (check for both conventions)

For each skill directory found with a reference folder:

1. List all files in the reference folder.
2. Classify each file as **tech-specific** (name contains a language or framework slug, e.g. `golang-code-review.md`, `django-tests.md`) or **generic** (e.g. `checklist.md`, `patterns.md`, `testing-patterns.md`).
3. If the folder contains at least one tech-specific file, mark the skill as **reference-enabled**. Skills with only generic files do not qualify.
4. For each reference-enabled skill: read one existing tech-specific reference file to understand the expected depth, section structure, and code example style. Also read the skill's `SKILL.md` to understand its purpose.
5. Record: skill name, full path, location type (project/extended/global), naming pattern in use, purpose inferred from skill name + sample file read.
6. Determine the skill's **source classification** by checking `AGENTS.global.md`:
   - **Internal** — discovered in `skills/`; source is `This project (ai-coding-tooling)`. Write target: `skills/<name>/references/`.
   - **External (already extended)** — discovered in `extended/`; an external skill that already has extension infrastructure. Write target: `extended/<name>/reference/`.
   - **External (unextended)** — discovered only in `~/.claude/skills/` with an external source (Tech Leads Club, etc.) and no corresponding `extended/<name>/` directory. Write target: `extended/<name>/reference/` — but Step 8 must run first to create the extension infrastructure.

## Step 3: Present Discovered Skills and Ask Which to Target

Present the complete list of reference-enabled skills found across all locations. Use the source classification from Step 2 to populate the Write Target column:

| Skill | Location | Source | Write Target | Sample Reference |
|-------|----------|--------|--------------|-----------------|
| code-review | skills/ | Internal | `skills/code-review/references/` | `golang-code-review.md` |
| coding-guidelines | extended/ | External (already extended) | `extended/coding-guidelines/reference/` | `php-coding-guidelines.md` |
| tests | ~/.claude/skills/ | External (unextended) | `extended/tests/reference/` (Step 8 first) | `django-tests.md` |
| ... | ... | ... | ... | ... |

The Write Target column is fixed by source classification — do not ask the user to choose where to write. Ask only: **"Which of these skills should receive a `<technology>` reference? List them by name or say 'all'."**

Only proceed with the skills the user selects. If the user says "all", include all reference-enabled skills.

**Additional qualification for global skills** — include an **External (unextended)** skill (discovered in `~/.claude/skills/`) in the list only if ALL of the following are true:

1. It has a `references/` or `reference/` subdirectory with at least two tech-specific files.
2. It does NOT already have a corresponding `extended/<name>/` directory (unextended — if it does, it was already discovered as `extended/` with source "External (already extended)").
3. It is listed in `AGENTS.global.md` with source `Tech Leads Club` or an external registry — skills sourced from `This project (ai-coding-tooling)` are in `skills/` and already handled.

## Step 4: Check for Existing Coverage and Confirm Intent

For each skill selected in Step 3, check whether a reference file already exists for the requested technology — including partial matches (e.g. a `python-*.md` file when adding `fastapi`, or a `go-*.md` when adding `go-gin`).

For each match found:

1. Read the existing file in full.
2. Classify coverage as **adequate** (covers this tech specifically and thoroughly), **partial** (related but missing key areas for the new tech), or **none**.

For skills with **adequate** or **partial** coverage, pause and ask the user:

> **"A reference for `<technology>` already exists in `<skill>` (`<filename>`). What do you want to do?"**
> - **a) Re-evaluate** — Regenerate from scratch using current best practices and documentation
> - **b) Improve** — I'll review the existing file and suggest targeted improvements
> - **c) Skip** — Leave it unchanged

For **improve** mode: after reading the existing file, generate a diff-style suggestion listing specific additions, removals, and edits with rationale. Do not regenerate the full file unless the user explicitly asks after seeing the suggestions.

For skills with **no** coverage: proceed with creation.

## Step 5: Present the Action Plan and Confirm

Before writing any files, present a concise summary table. The Write Target is determined by source classification from Step 2 — do not ask the user to choose it:

| Skill | Source | Action | Write Target |
|-------|--------|--------|--------------|
| code-review | Internal | Create | `skills/code-review/references/<prefix>-code-review.md` |
| tests | Internal | Improve existing | `skills/tests/references/<prefix>-tests.md` (targeted edits) |
| coding-guidelines | External (already extended) | Re-evaluate | `extended/coding-guidelines/reference/<prefix>-coding-guidelines.md` |
| \<external-skill\> | External (unextended) | New extension + create | `extended/<skill>/reference/<prefix>-*.md` (Step 8 first) |

Ask the user to confirm before proceeding.

## Step 6: Gather Technology Documentation via Context7 (if available)

Before generating any reference files, use Context7 MCP (if available) to gather authoritative, up-to-date documentation. This grounds reference files in official docs rather than relying solely on training data.

**6a. Resolve the library ID**

Call `mcp__context7__resolve-library-id` with the technology name. Pick the result with the highest relevance — prefer official documentation sources (e.g. `/websites/php_net_manual` over community forks) and high source reputation.

**6b. Query for applicable content domains**

For each skill in the action plan, determine which content domains from the **Reference Content Standard** apply based on the skill's purpose and the sample file read in Step 2. Craft one targeted Context7 query per applicable domain group. Run at most 3 calls total to respect rate guidance.

**6c. Filter and curate the results**

- **Discard deprecated patterns** — e.g. `mysql_*` functions in PHP, `var` in modern JS.
- **Discard insecure examples** — e.g. MD5 for passwords, string concatenation for SQL.
- **Extract the useful signal** — idiomatic syntax, modern feature usage, official recommendations. Ignore boilerplate and trivial examples.
- **Note version requirements** — if a feature requires a specific version, capture that for use in versioned sections.

The curated snippets become source material for Step 7. They supplement — not replace — your own knowledge of the technology.

## Step 7: Generate Reference Files

For each skill in the action plan (create or re-evaluate mode):

Generate the tech-specific reference file using the **Reference Content Standard** below, combined with curated Context7 material from Step 6.

**Generation rules:**

- Match the section headings style of the sample file read in Step 2 exactly.
- Include concrete code examples specific to the technology — not generic pseudo-code. Prefer examples sourced from official documentation (via Context7) over invented ones, adapted to the reference file's style.
- **Determine content domains by reading the skill's own `SKILL.md`** (already loaded in Step 2). Do not infer purpose from the skill's folder name. Instead: (1) read the skill's `SKILL.md` description to understand what workflow it supports and what output it produces; (2) check what domains the existing sample reference files already cover; (3) select applicable domains from the **Content Domains** table below — only those that are relevant to this specific skill's workflow AND have official or widely-adopted community standards for the target technology. Each skill will produce a different domain selection: a skill that reviews code for correctness will need different domains than one that writes tests or enforces coding style.
- **Do not invent standards or conventions.** If a domain has no official documentation, style guide, or well-established community consensus for this technology, skip it entirely. Do not fill gaps with speculation.
- Apply version stratification as defined in the Reference Content Standard.
- Write at the same depth level as the sample. Do not over-engineer or under-deliver.
- Save to the path identified in the action plan.

For **improve** mode: apply only the targeted changes proposed in Step 4. Do not regenerate the full file.

## Reference Content Standard

This section defines the structure and content domains that all tech-specific reference files generated by this skill must follow.

### Version Stratification

Load and apply [Version Stratification Guide](../../templates/version-stratification-guide.md).

### Token Efficiency

When generating reference file content, follow [Token Efficiency Rules](../../templates/token-efficiency-rules.md).

### Content Domains

Use this table as the authoritative menu of what to include in a reference file. For each skill, include only the domains that are (a) relevant to the skill's purpose and (b) have official documentation, an official style guide, or a widely-adopted community standard for the target technology.

**Do not include a domain if no official or market-adopted standard exists for it in this technology.** Skip it without substituting invented conventions.

| Domain | What to cover |
|--------|---------------|
| **API design conventions** | REST, gRPC, GraphQL, or RPC conventions recommended by the framework or ecosystem (e.g. JSON:API, OpenAPI, Protobuf). Only include if the technology has explicit API design guidance. |
| **Anti-patterns and bad practices** | Patterns that are officially discouraged, widely recognized as harmful, or legacy approaches that persist in the wild but should no longer be used. Include: deprecated APIs still commonly seen in older codebases, patterns that were once standard but are now superseded, well-known market anti-patterns documented in official migration guides or community resources (e.g. PHP.net migration notes, Go Proverbs, PEP deprecation notices). Do NOT invent anti-patterns — only include ones with documented evidence of being harmful or obsolete. Where relevant, note which version deprecated or replaced a pattern. |
| **Architecture best practices** | Recommended structural patterns: layers, modules, separation of concerns, dependency direction — from framework docs or official architecture guides |
| **Coding best practices** | Language idioms, naming conventions, formatting and style rules — sourced from official style guides (e.g. PSR for PHP, PEP 8 for Python, `gofmt`/Effective Go for Go) |
| **Code organization patterns** | File layout, module/package structure, directory conventions — from official project templates, scaffolding tools, or framework documentation |
| **Concurrency and async patterns** | Official concurrency model: goroutines, async/await, fibers, actors, event loops — from language specification or official framework docs |
| **Configuration management** | Official config loading patterns, environment variable conventions, secrets management — from framework docs or 12-factor app guidance |
| **Dependency management** | Official package manager, versioning conventions (semver, lock files), private registry setup |
| **Error handling** | Official error and exception handling conventions (e.g. checked vs unchecked in Java, `error` return in Go, typed exceptions in PHP, `Result` in Rust) |
| **Logging** | Official or framework-provided logging interfaces and conventions — not homebrew wrappers. Only include if the technology or its ecosystem defines a standard logging interface. |
| **Performance best practices** | Profiling tools, known bottlenecks, caching strategies, memory management — from official performance guides or widely-adopted community benchmarks |
| **Security best practices** | Injection prevention, authentication, authorization, input validation, secrets handling, cryptography — from official security advisories, framework security docs, or OWASP guidance specific to this technology |
| **Testing architecture patterns** | Platform-idiomatic structural patterns for organizing and writing tests. Examples: table-driven tests in Go (`t.Run` subtests over a slice of cases), `pytest.mark.parametrize` in Python, `@ParameterizedTest` in JUnit, spec-style `describe`/`it` blocks in RSpec or Jasmine, BDD-style Given/When/Then, property-based testing (QuickCheck, Hypothesis, `testing/quick`). Also covers: test helper and fixture patterns idiomatic to the technology, sub-test naming conventions, when to use each structural pattern. Include only patterns with official documentation or strong community consensus — do not invent structural conventions. |
| **Testing best practices** | Official or community-standard testing approach, test organization, assertion style, coverage conventions. Always include code examples using the standard test framework for this technology. |

## Step 8: Generate Extension Infrastructure for Global Skills

For each qualifying global skill recorded in Step 3:

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

The body should instruct the agent to detect the project's tech stack from `docs/PROJECT_DETAILS.md` and load all matching files from both the parent skill's reference directory and this extension's `reference/` directory, following the naming convention observed in Step 2.

**8b. Create the reference directory and first tech file**

Create `extended/<skill-name>/reference/<prefix>-<purpose>.md` using the same content generation rules as Step 7.

**8c. Update AGENTS.global.md**

Find the existing entry for this skill in `AGENTS.global.md`. Append the extended annotation to the end of its description line, matching the exact format used for `coding-guidelines`:

```
— **Extended**: if `skills/<skill-name>/SKILL.extended.md` exists, load it alongside the parent skill; also load any matching files from `skills/<skill-name>/reference/` for the project's tech stack.
```

Do not create a new entry — update the existing one in place.

## Step 9: Run make link-extended (only if new extension directories were created)

Only run this command if Step 8 created a **new** `extended/<skill-name>/` directory that did not previously exist:

```bash
make link-extended
```

This symlinks the new directory into `~/.claude/skills/`. The Makefile handles all directories under `extended/` generically — no Makefile changes are needed.

If Step 8 only added reference files inside an already-existing `extended/<skill-name>/reference/` directory, skip this step — the directory is already symlinked and the new files are immediately accessible through it.

## Step 10: Report

Output a summary of everything created:

```
## tech-reference-add: <Technology> added

### New reference files
- skills/<skill-name>/references/<prefix>-<skill-name>.md
- extended/<skill-name>/reference/<prefix>-<skill-name>.md

### Improved reference files
- skills/<skill-name>/references/<prefix>-<skill-name>.md (targeted improvements applied)

### New extensions
- extended/<skill-name>/ (SKILL.md + reference/<prefix>-*.md)
  AGENTS.global.md updated ✓
  make link-extended run ✓

### Skipped
- <skill>: no tech-specific reference pattern detected
- <skill>: user skipped
- <skill>: reference already adequate, no changes needed
```

If `make link-extended` fails, report the error and instruct the user to run it manually.
