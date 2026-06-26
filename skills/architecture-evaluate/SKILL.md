---
name: architecture-evaluate
description: >
  Creates, updates, and incrementally syncs the project context documentation that agents load at
  session start. Three modes. Full mode deep-scans the codebase (brownfield mapping) and writes nine
  context files to docs/codebase/ — PROJECT.md (overview, vision, goals), STACK.md, STRUCTURE.md,
  ARCHITECTURE.md, CONVENTIONS.md, INTEGRATIONS.md, TESTING.md, CONCERNS.md, and PIPELINE.md.
  Incremental mode inspects the git workspace and syncs only what changed — inline API docs in source
  files, root context files (README.md, CLAUDE.md, AGENTS.md), and the context files in docs/codebase/ —
  and detects new packages. Package mode generates a scoped CLAUDE.md for an individual package/module.
  Use when the user says "evaluate architecture", "map codebase", "analyze existing code", "document
  current architecture", "update architecture docs", "refresh project context", "onboard project",
  "create project docs", "update project docs", "update docs", "document my changes", "sync
  documentation", "document recent changes", "evaluate package", or "package architecture".
metadata:
  version: "4.0.0"
  triggers:
    # Full mode — bootstrap / full refresh of the nine context files
    - "evaluate architecture"
    - "map codebase"
    - "analyze existing code"
    - "document current architecture"
    - "initial architecture"
    - "update architecture docs"
    - "refresh project context"
    - "setup project docs"
    - "run architecture-evaluate"
    - "update project docs"
    - "create project docs"
    - "onboard project"
    # Incremental mode — git-diff-driven sync of changed docs, inline API docs, root files
    - "update docs"
    - "generate docs"
    - "document my changes"
    - "sync documentation"
    - "document recent changes"
    - "keep docs in sync"
    - "api documentation"
    # Package mode — scoped CLAUDE.md for one package
    - "evaluate package"
    - "evaluate architecture for package"
    - "package architecture"
---

# Architecture Evaluate

Keep a project's agent-facing context documentation accurate through three modes, selected by the user's intent below. Full mode performs **brownfield codebase mapping** — a systematic scan that produces nine context files in `docs/codebase/`.

## The Nine Context Files

Full mode generates these in `docs/codebase/`. Every file is conditional and budget-bound; include only sections with codebase evidence. Total combined budget ≈ 30,000 tokens — load on-demand per task, not all at once.

| File | Purpose | Budget |
|------|---------|--------|
| `PROJECT.md` | Overview, vision, goals, target users, scope — what the project is and who it's for | ~1,500 |
| `STACK.md` | Tech stack, key libraries, commands, environment config, local dev setup | ~2,000 |
| `STRUCTURE.md` | Directory layout, module organization, monorepo package map | ~2,000 |
| `ARCHITECTURE.md` | Layers, data flow, patterns, system-level concerns (state, auth, observability) | ~4,000 |
| `CONVENTIONS.md` | Naming, code style, error handling, documentation pattern | ~3,000 |
| `INTEGRATIONS.md` | External services, APIs, webhooks, background jobs | ~5,000 |
| `TESTING.md` | Test frameworks, coverage matrix, parallelism, gate-check commands | ~4,000 |
| `CONCERNS.md` | Tech debt, bugs, security, performance, fragile areas, risks — evidence-backed | ~5,000 |
| `PIPELINE.md` | CI/CD, deployment, environment promotion, release management | ~3,000 |

## Mode Selection

Pick the mode from the user's intent:

| Mode | Choose when the request is… | Examples |
|------|------------------------------|----------|
| **Full** (default) | Bootstrap or full refresh of project context — map the codebase, no specific change in mind | "evaluate architecture", "map codebase", "analyze existing code", "onboard project", "create project docs", "refresh project context", "update project docs" |
| **Incremental** | Sync docs to recent code changes in the workspace | "update docs", "document my changes", "sync documentation", "document recent changes", "generate docs", "keep docs in sync", "api documentation" |
| **Package** | Document one specific package/module, or invoked internally by Incremental mode for a confirmed new package | "evaluate package", "package architecture", "evaluate architecture for `packages/auth`" |

When ambiguous, default to **Full** mode. **If Incremental mode runs but the context files are absent from `docs/codebase/`:** if they exist elsewhere in the project, suggest migrating them to `docs/codebase/` first (see Detecting & Migrating Misplaced Context Files); if they exist nowhere, suggest running Full mode first — there is no baseline to sync against.

## Shared Guardrails

These apply to every mode.

- **Default document location is `docs/codebase/`.** Every context file this skill writes lives in `docs/codebase/`. Create the directory if it does not exist. (Package mode is the exception: it writes a `CLAUDE.md` inside the target package directory, not under `docs/codebase/`.)
- **Reading existing context for input** — when this skill loads a context file to inform its own work (not to write it), read it from `docs/codebase/<file>`.
- **The folder is the source of truth.** Treat the actual contents of `docs/codebase/` as authoritative. Sweep the real directory and preserve every `.md` present, including files added by hand beyond the canonical nine. Never regenerate or sync only the fixed list while ignoring what's on disk.
- **Out of scope — owned by `tlc-spec-driven`.** Never create or modify `.specs/STATE.md` (the decisions/handoff memory), feature specs under `.specs/features/`, or `docs/TECH_DEBTS.md` (the `tech-debt-report` ledger). This skill documents the codebase; those are other skills' artifacts. `CONCERNS.md` is the living risk snapshot and is separate from the `TD-XX` ledger — when a concern is already a tracked `TD-XX`, reference it rather than restating it.
- **No code samples** unless strictly necessary. Use prose, tables, bullets. Code blocks only for directory trees, ASCII or Mermaid diagrams, and exact runnable commands. No method signatures, SQL queries, or implementation examples.
- **CI/CD belongs in `PIPELINE.md` only.** Other files may reference it but must not contain pipeline specifics.
- **Diagrams** — author data flows, layer relationships, component interactions, and pipeline stages as **Mermaid** diagrams when the `mermaid-studio` skill is available — delegate creation through it. Fall back to simple box-and-arrow **ASCII** diagrams when `mermaid-studio` is not available. Converting existing ASCII diagrams to Mermaid is always permitted when `mermaid-studio` is present.
- **Factual only** — document what exists in the codebase. Never invent or speculate. Omit any section with no evidence.
- **Never write secret values** into any document. Reference secrets by name and describe only how they are managed (provider, injection mechanism) — everywhere, not just `PIPELINE.md`.
- **Conditional sections** — every section in every output file is conditional. Only include it if the codebase provides evidence for it; omit empty sections entirely.
- **Respect per-file budgets** (see The Nine Context Files). Summarize aggressively — table rows over paragraphs, bullets over tables, omission over filler. Cap any single file at 500 lines.
- **Delegate every `.md` write to the `docs-writer` skill** — regardless of mode. This keeps formatting, style, and link integrity consistent. No exceptions.
- **Follow [Token Efficiency Rules](../../templates/token-efficiency-rules.md)** when generating any `.md` content.

### Holistic Updates (Full and Incremental modes)

Whenever this skill updates the `docs/codebase/` context set — in Full or Incremental mode, at **any** point — it must not touch only the single file it set out to write. **Open every file present in `docs/codebase/`, evaluate each one's purpose against the change at hand, and update any whose content is affected.** A change to the codebase rarely lands in exactly one document; treat the `docs/codebase/` set as one interconnected context that must stay mutually consistent. This applies even when the trigger names a specific file (e.g. "update ARCHITECTURE") — still review the siblings. **Package mode is exempt:** it writes only the target package's `CLAUDE.md` and does not sweep `docs/codebase/`.

### Additional Context Files & Registration

The `docs/codebase/` set is **open-ended**. Beyond the canonical nine, a project may keep other context documents there. Treat **every** `.md` in `docs/codebase/` as part of the context set for Holistic Updates — discover them, don't assume only the canonical nine exist. For each `.md` not in the canonical set (e.g. a hand-added `SECURITY.md`, or nested docs under `docs/codebase/adr/`), do not silently overwrite or drop it. Investigate it against the current code; if impacted or stale, flag it and offer to refresh it rather than rewriting silently.

When a context file in `docs/codebase/` is **not** referenced by the project's session-start context list — the context-files table in the global `AGENTS.global.md` or the project root `CLAUDE.md`/`AGENTS.md` — **suggest adding a pointer to it** as a new table row (file path + a one-line "when to read it"), matching the existing rows, so agents auto-load it. Confirm before editing the root file.

### Detecting & Migrating Misplaced Context Files

The canonical location is `docs/codebase/`. The nine context files are `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `PIPELINE.md`, `PROJECT.md`, `STACK.md`, `STRUCTURE.md`, `TESTING.md` (plus any extra context docs the project keeps in the set).

**Before generating or syncing (Full and Incremental modes), scan the whole project for any of these files living outside `docs/codebase/`:**

```bash
ls docs/codebase/*.md 2>/dev/null      # canonical (correct) location
# anywhere else in the project
find . -type f \( -name ARCHITECTURE.md -o -name CONCERNS.md -o -name CONVENTIONS.md \
  -o -name INTEGRATIONS.md -o -name PIPELINE.md -o -name PROJECT.md -o -name STACK.md \
  -o -name STRUCTURE.md -o -name TESTING.md \) \
  -not -path './docs/codebase/*' -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null
```

**If any context file is found outside `docs/codebase/`:** do **not** move or overwrite it silently. Present what was found and where (e.g. "`STACK.md`, `ARCHITECTURE.md` in `docs/`; `PROJECT.md` in `docs/architecture/`"), **suggest migrating the set to `docs/codebase/`**, and **wait for the user's confirmation** before relocating anything.

**Found files are valuable input — use them, don't discard them.** Any misplaced file that is (or becomes) a context doc is read as **source material for the corresponding `docs/codebase/` file being created or refreshed**: carry its still-accurate content forward and merge it per the Update Merge Strategy rather than regenerating from scratch. This applies whether the user opts to physically move the file or to leave it in place and regenerate — either way its content seeds the new doc.

Once the user confirms a migration:
- Move/merge the files into `docs/codebase/` (never blind-overwrite a same-named file already there — merge per the Update Merge Strategy).
- Update references to the old paths (consumers, root `CLAUDE.md`/`AGENTS.md`, `AGENTS.global.md`).
- Treat it as a structural change → suggest a Full-mode re-evaluation (see Re-evaluate on Structural Change).

Use judgment on the project-wide `find`: a same-named file inside a package or an unrelated docs tree may not be a context doc — flag ambiguous hits and ask rather than assuming.

### Re-evaluate on Structural Change

If the documentation file structure changes — files migrated into `docs/codebase/`, a context file added or removed — or the codebase's own structure shifts significantly (a new architectural layer, moved/renamed top-level directories, a new package) — **suggest re-evaluating all context files together via Full mode.** Structural changes ripple across every document, so the set should be regenerated as a consistent whole rather than patched file by file.

### Update Merge Strategy

When updating existing files:

- Read the existing file first. Work section by section.
- Update sections where codebase evidence changed (new dependencies, renamed dirs, etc.).
- Preserve sections the user manually added that are not part of the standard template — those represent intentional customization.
- Never delete a section just because you cannot find evidence for it in this pass — the user may have added it from knowledge outside the codebase.
- If a section's content is now inaccurate, replace the content but keep the heading.

### Code Change Guardrails (Incremental mode)

- Inline API documentation changes are applied directly to source files.
- Do not refactor, restructure, or modify code — only change comments and doc annotations.
- Do not add documentation to symbols that did not change, unless they are undocumented public exports in a modified file.

### `docs/` Traversal Guardrail (Incremental mode)

- Context files live in `docs/codebase/` — check files directly there (e.g. `docs/codebase/ARCHITECTURE.md`).
- **Never descend into other `docs/` subfolders** (`docs/tasks/`, `docs/specs/`, `docs/tech-debts/`, `docs/decisions/`, etc.). Those are owned by other skills or workflows and are out of scope.

# Mode A — Full

Creates or updates the nine project context files in `docs/codebase/` from a full codebase scan (brownfield mapping).

**High-level approach:** explore the directory structure systematically → identify the stack from dependency manifests → extract patterns from representative code samples → document observed conventions and architecture → catalog external integrations → surface evidence-backed concerns.

**Analysis depth:** sample representative files — focus on consistency and patterns, not exhaustive coverage. Extract actual examples, not assumptions. 10–15 files for small/medium projects; 25–30 for monorepos, one representative module per layer. Prioritize breadth over depth.

## Step 1: Confirm File Location

Default: `docs/codebase/` at project root. Create it if it doesn't exist. If the user specifies a different location, use that instead.

Run the misplaced-file scan (see **Detecting & Migrating Misplaced Context Files**) — check the canonical location and the wider project:

```bash
ls docs/codebase/*.md 2>/dev/null      # canonical (correct) location
find . -type f \( -name ARCHITECTURE.md -o -name CONCERNS.md -o -name CONVENTIONS.md \
  -o -name INTEGRATIONS.md -o -name PIPELINE.md -o -name PROJECT.md -o -name STACK.md \
  -o -name STRUCTURE.md -o -name TESTING.md \) \
  -not -path './docs/codebase/*' -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null
```

If any exist in `docs/codebase/`, inform the user they will be **updated**, not replaced — existing content is preserved and refined per the Update Merge Strategy. If any are found **outside** `docs/codebase/`, **suggest migrating them to `docs/codebase/` and wait for confirmation before proceeding** — never relocate silently. Whether moved or left in place, **read those files as source material** to seed the corresponding new docs (see Detecting & Migrating Misplaced Context Files).

## Step 2: Bootstrap Analysis (Claude Code only)

Run `/init` for an initial codebase perspective. Use output **only as supporting context** — **do not save the generated CLAUDE.md**. If `/init` writes one, discard or revert it. Skip if `/init` is unavailable (other AI tools, non-interactive mode) — the manual exploration in Step 3 is sufficient.

## Step 3: Explore the Codebase

Use Glob and Read to gather context, adapting searches to the actual language, framework, and tooling. If the `codenavi` skill is available, prefer it for discovery and navigation.

| Area | What to look for |
|------|-----------------|
| **Project purpose** | `README.md`, root docs, package metadata `description` fields — for PROJECT.md overview/vision |
| **Dependency manifests** | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `Gemfile`, `requirements.txt` — extract exact pinned versions for key libraries |
| **Infrastructure** | `Dockerfile`, `docker-compose.yml`, `Makefile`, `justfile` |
| **Local dev tooling** | Seed scripts, mock servers, dev-only config, fixture data, local service stubs |
| **Environment** | `.env.example`, `.env.sample`, `README.md` for env docs |
| **Monorepo config** | `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json` |
| **Project structure** | Top-level directory tree (one level deep), main source and test directories |
| **Entry points** | Main files, bootstrap, application config |
| **Code conventions** | 5–10 representative source files — naming, imports, error handling, comment style |
| **External integrations** | API client dirs, SDK configs, webhook handlers/endpoints, service wrappers, gateway adapters, ERP connectors, payment provider modules |
| **Architecture layers** | API routes, services, data access, background jobs |
| **Database** | Schema/migration dirs, ORM config, connection pool config, read replica setup |
| **Observability** | Logging config, tracing setup (OpenTelemetry, Datadog APM), metrics, structured logging conventions |
| **State management** | Session config, cache config, state store setup (Redis, Memcached, in-memory) |
| **Feature flag system** | Provider config (LaunchDarkly, Unleash, env-based, DB-based) |
| **Tests** | 5–10 test files — frameworks, location/naming patterns, layers covered, run commands |
| **API specs** | OpenAPI, GraphQL schemas, protobuf definitions |
| **Concerns signals** | TODO/FIXME/HACK comments, duplicated logic, missing error handling, N+1 queries, untested critical paths, outdated/deprecated deps, client-side-only auth |
| **CI/CD** | `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml`, `azure-pipelines.yml`, `.buildkite/` |
| **Deployment** | `deploy/`, `k8s/`, `helm/`, `terraform/`, `cdk/`, `pulumi/`, `serverless.yml`, `fly.toml`, `vercel.json`, `netlify.toml` |
| **Release management** | `.releaserc`, `release.config.js`, `.changeset/` |
| **Data pipelines** | `dags/`, `pipelines/`, Airflow, dbt, Spark configs |
| **Monitoring** | Datadog monitors, PagerDuty integrations, alerting configs tied to deploys |

Write the nine files in Steps 4–12. **Delegate every `.md` write to `docs-writer`.** Each step gives the file's purpose, what to extract, a template skeleton, and instructions. Include only sections with evidence.

## Step 4: Write PROJECT.md

**Purpose:** What the project is and who it's for — the human-facing context a codebase scan alone cannot infer.
**Extract from:** `README.md`, root docs, package metadata `description`, any product/vision docs.

```markdown
# Project

## Overview

[1–2 sentences: what the project does and who it's for]

## Vision & Goals

[The problem it solves and its primary goals — only as documented]

## Target Users

[Roles or personas who use it]

## Scope

**In scope:** [core capabilities the project owns]
**Out of scope:** [explicitly excluded areas, if documented]

## Status

[Current maturity/phase if evident — e.g. pre-release, production, maintenance]
```

**Instructions:**

- Derive overview and purpose from the README and docs. **Never invent product strategy or vision.**
- Where vision, goals, or scope are not documented anywhere, include what is evident and explicitly flag the gap for the user to fill — do not fabricate.
- This is the only file whose content is not fully derivable from code; keep it factual and short.

## Step 5: Write STACK.md

**Purpose:** Technology stack, key libraries, and how to run the project.
**Extract from:** dependency manifests, build configuration, runtime configuration, `.env.example`.

```markdown
# Tech Stack

## Core

- Language: [name + version]
- Framework: [name + version]
- Runtime: [name + version]
- Package manager: [manager]
- Minimum versions: [runtime/language constraints, e.g. Node >= 18, Python >= 3.11]

## Key Libraries

| Library | Version | Purpose | Modern Usage |
| ------- | ------- | ------- | ------------ |
| [name]  | [pinned]| [role]  | [idiomatic modern API for that version] |

## Frontend (if applicable)

- UI Framework: [name + version]
- Styling: [approach + tools]
- State Management: [library/pattern]
- Form Handling: [library if present]

## Backend (if applicable)

- API Style: [REST/GraphQL/gRPC + framework]
- Database: [ORM/query builder + database system]
- Authentication: [library/approach]

## Testing

- Unit / Integration / E2E: [frameworks] (detail lives in TESTING.md)

## External Services

- [Category]: [Service name] (detail lives in INTEGRATIONS.md)

## Commands

| Task | Command |
| ---- | ------- |
| [setup/build/test/lint/deploy/migrate/seed] | [command] |

## Local Development Setup

[Services to run (docker compose profile, local DB), seed/fixture data, how to mock/stub external services, ports and URLs]

## Environment Configuration

| Variable   | Description |
| ---------- | ----------- |
| [VAR_NAME] | [purpose]   |

## Development Tools

- [Tool category]: [Tool name]
```

**Instructions:**

- **Core:** capture **minimum** runtime/language version constraints — agents must respect these to avoid unsupported features.
- **Key Libraries:** extract the exact pinned version from the manifest; for each, use Context7 (`mcp__context7__*`) or web search to identify the idiomatic modern API for that version (e.g. "React Query v5 → `useQuery`", "SQLAlchemy 2.x → `select()`"). Flag significantly outdated pins.
- **Commands:** test/gate commands here also feed TESTING.md's Gate Check Commands.
- **Environment Configuration:** variable **names only, never values.**

## Step 6: Write STRUCTURE.md

**Purpose:** Directory layout and where things live.
**Extract from:** the actual directory tree, monorepo config.

```markdown
# Project Structure

**Root:** [project root path]

## Directory Tree

[Visual tree, max 3 levels deep, with brief annotations]

## Module Organization

### [Module/Area Name]

- **Purpose:** [what this area handles]
- **Location:** [where files live]
- **Key files:** [important files]

## Where Things Live

**[Capability/Feature]:**

- UI/Interface: [location]
- Business Logic: [location]
- Data Access: [location]
- Configuration: [location]

## Special Directories

**[Directory name]:** [purpose + key files]

## Monorepo Package Map (if monorepo)

| Package | Path | Responsibility |
| ------- | ---- | -------------- |
| [name]  | [path] | [role]       |
```

**Instructions:**

- Limit tree depth to maintain readability; annotate purpose, don't dump every file.
- Map capabilities to physical locations so agents know where to add new code.
- Include the Monorepo Package Map only if the project is actually a monorepo.

## Step 7: Write ARCHITECTURE.md

**Purpose:** How the system is structured — "how is it organized", not "how does X work internally". No method signatures, SQL, or code snippets. Testing strategy lives in TESTING.md, background jobs in INTEGRATIONS.md, CI/CD in PIPELINE.md.
**Extract from:** directory organization, repeated patterns across files, entry points, config.

```markdown
# Architecture

## Overview / Pattern

[2–3 sentences: what the system does + primary architectural style: monolith / microservices / event-driven]

## High-Level Structure

[Mermaid diagram (via mermaid-studio) or ASCII diagram if mermaid-studio is unavailable]

## Layers

| Layer | Responsibility | Key Files or Dirs |
| ----- | -------------- | ----------------- |
| [layer] | [role]       | [paths]           |

## Dependency Rules

[Who can import whom, who can't — e.g. "services never import controllers"]

## Request / Data Flow

[Mermaid diagram (via mermaid-studio) or numbered list / ASCII diagram if mermaid-studio is unavailable]

## Communication Patterns

[How services/modules communicate: REST, events, queues, gRPC]

## Key Components

| Component | Role |
| --------- | ---- |
| [name]    | [role] |

## Data Model

[Key entities and relationships — conceptual map, not full schema]

## Database Access Patterns

[Access pattern (repository, active record, query builder, raw), connection pooling, read replicas, migrations framework]

## State Management

[Stateless (JWT) / server sessions / distributed cache / event sourcing; where state lives, how it's shared across instances]

## Error Handling Strategy

[System-level: where errors are caught, where they propagate, error format. Code-level conventions go in CONVENTIONS.md]

## Auth Strategy

[Middleware, guards, where the logic lives. The auth library name stays in STACK.md]

## Observability

[Logging framework/conventions (structured, levels), tracing (OpenTelemetry/APM), metrics, correlation IDs; how agents should instrument new code]

## API Versioning

[URL path /v1/ / headers / query / none; deprecation policy; version coexistence]

## Feature Flag System

[Provider, runtime evaluation, where definitions live, how agents gate new features]

## Notable Patterns

[Repository pattern, service wrappers, decorators, etc.]
```

**Instructions:**

- Identify patterns from actual code, not assumptions; reference concrete examples by path.
- Keep **infrastructure** dependencies (DBs, caches, queues) here; route **business integrations** (ERPs, payment, CRM, third-party APIs) to INTEGRATIONS.md.

## Step 8: Write CONVENTIONS.md

**Purpose:** Code style and naming, extracted from representative files. Document observed conventions, not ideal ones.
**Extract from:** 5–10 representative source files; identify consistent patterns and note variations.

```markdown
# Code Conventions

## Naming Conventions

- **Files:** [pattern] — examples: [actual names]
- **Functions/Methods:** [pattern] — examples
- **Variables:** [pattern] — examples
- **Constants:** [pattern] — examples
- **Database tables:** [pattern]
- **Routes:** [pattern]
- **Branches:** [pattern]

## Code Organization

- **Import/Dependency Declaration:** [observed ordering]
- **File Structure:** [organization within files]

## Type Safety / Documentation

[Type system or documentation approach in use]

## Error Handling

[Code-level pattern — how errors are raised/wrapped in code. System-level propagation goes in ARCHITECTURE.md]

## Comments / Documentation

[When and how comments are used]

## Documentation Pattern

[How docs are organized: Swagger/OpenAPI, JSDoc/PHPDoc, guides]
```

**Instructions:**

- Extract patterns from real samples; include concrete examples from the codebase.
- Note exceptions or variations where found — don't present an idealized version.

## Step 9: Write INTEGRATIONS.md

**Purpose:** External service integrations.
**Extract from:** API client dirs, SDK configs, webhook handlers, service wrappers, job definitions, config.

```markdown
# External Integrations

## Integrations

**[Service name]:**

- Type: [ERP / payment / CRM / email-SMS / auth / cloud / third-party API]
- Purpose: [what it provides]
- Data flow: [inbound / outbound / both]
- Protocol: [REST / SOAP / webhooks / SDK]
- Location: [where the integration lives in code]
- Authentication: [auth method]

## API Integrations

### [API Name]

- Purpose: [what it provides]
- Location: [where the client lives]
- Authentication: [method]
- Key endpoints: [major endpoints used]

## Webhooks

### [Webhook Source]

- Purpose: [events handled]
- Location: [handler location]
- Direction: [consumed / exposed]
- Events: [event types]

## Background Jobs

| Job | Frequency | Purpose |
| --- | --------- | ------- |
| [job] | [frequency] | [role] |

**Queue system:** [system if used] — **Location:** [where definitions live]
```

**Instructions:**

- Document authentication approaches and data-flow direction for each integration.
- **Background Jobs** is the single source of truth for jobs/crons — ARCHITECTURE.md may reference but not duplicate it.

## Step 10: Write TESTING.md

**Purpose:** Testing infrastructure and patterns.
**Extract from:** test dependencies, 5–10 test files, `package.json`/`Makefile`/CI config for run commands.

```markdown
# Testing Infrastructure

## Test Frameworks

- **Unit/Integration:** [framework + version]
- **E2E:** [framework + version]
- **Coverage:** [tool if used]

## Test Organization

- **Location:** [where tests live]
- **Naming:** [test file naming pattern]
- **Structure:** [how tests are organized]

## Testing Patterns

- **Unit:** [approach, location]
- **Integration:** [approach, location — e.g. "Jest + Supertest, no DB mocking"]
- **E2E:** [approach, location if present]

## Test Execution

- **Commands:** [how to run tests]
- **Configuration:** [test config approach]

## Coverage Targets

- **Current:** [if measurable] — **Goals:** [if documented] — **Enforcement:** [if automated]

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| ---------- | ------------------ | ---------------- | ----------- |
| [layer]    | [unit/integration/e2e/none] | [glob or path] | [command] |

## Parallelism Assessment

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --------- | -------------- | --------------- | -------- |
| [type]    | [Yes/No]       | [description]   | [file/pattern that proves it] |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | [unit test command] |
| Full  | After tasks with e2e/integration tests | [unit + e2e commands] |
| Build | After phase completion | [build + lint + unit + e2e] |
```

**Instructions:**

- **Test Coverage Matrix:** sample 5–10 test files to infer which layers are tested and how; mark untested layers "none" and note them in CONCERNS.md.
- **Parallelism Assessment:** NOT-safe signals — shared DB connection (same URL from config), table-level cleanup in `beforeEach`/`afterAll` (`.del()`, `DELETE FROM`, `TRUNCATE`), shared mock state reset on globals. Safe signals — per-test DB creation (Testcontainers, dynamic schema, in-memory SQLite), data namespacing by unique test ID, no shared mutable state between files, all deps mocked (`jest.fn()`, `vi.fn()`).
- **Gate Check Commands:** extract from real project commands — do not invent commands.

## Step 11: Write CONCERNS.md

**Purpose:** Actionable, evidence-backed warnings — "what to watch out for when making changes." Living documentation, not a complaint list.
**Extract from:** TODO/FIXME/HACK comments, duplicated logic, missing error handling, dependency manifests, performance and security patterns observed during the scan.

Each entry needs **what** the problem is, **where** it lives (file paths in backticks), **why** it matters (impact, with measurements where possible), and **how** to fix it. Omit any category with no findings.

```markdown
# Codebase Concerns

**Analysis Date:** [YYYY-MM-DD]

## Tech Debt

**[Area/Component]:**
- Issue: [the shortcut/workaround]
- Files: [`paths`]
- Why: [why it was done this way]
- Impact: [what breaks or degrades]
- Fix approach: [how to properly address it]

## Known Bugs

**[Bug]:** Symptoms / Trigger (repro) / Files / Workaround / Root cause (if known)

## Security Considerations

**[Area]:** Risk / Files / Current mitigation / Recommendations

## Performance Bottlenecks

**[Operation]:** Problem / Files / Measurement ("500ms p95") / Cause / Improvement path

## Fragile Areas

**[Component]:** Files / Why fragile / Common failures / Safe-modification notes / Test coverage

## Scaling Limits

**[Resource/System]:** Current capacity (numbers) / Limit / Symptoms at limit / Scaling path

## Dependencies at Risk

**[Package/Service]:** Risk (deprecated/unmaintained/breaking) / Impact / Migration plan

## Missing Critical Features

**[Gap]:** Problem / Current workaround / Blocks / Rough effort

## Test Coverage Gaps

**[Untested area]:** What's not tested / Risk / Priority / Difficulty to test
```

**Instructions:**

- **Always include file paths** — concerns without locations are not actionable.
- Be specific with measurements ("500ms p95", not "slow"); include reproduction steps for bugs; suggest fix approaches, not just problems. Prioritize by risk/impact.
- **Exclude:** opinions without evidence, complaints without solutions, future feature ideas, normal TODOs, decisions that work fine, minor style issues.
- **Tone:** professional, solution-oriented, factual. Coexists with `docs/TECH_DEBTS.md` — reference a tracked `TD-XX` rather than restating it.

## Step 12: Write PIPELINE.md

**Purpose:** How code gets from commit to production. **If no CI/CD or pipeline configuration exists, skip this file entirely** and note its absence in the Step 13 report.
**Extract from:** CI config, deploy/infra dirs, release config, data-pipeline dirs.

```markdown
# CI/CD Pipeline

## Overview

[CI/CD platform + pipeline philosophy — trunk-based / GitFlow / monorepo-aware, 1–2 sentences]

## CI/CD Platform

| Platform | Config Location | Runner Type |
| -------- | --------------- | ----------- |
| [name]   | [path]          | [hosted/self-hosted] |

## Pipeline Stages

[Mermaid flowchart (via mermaid-studio) or ASCII flow diagram if mermaid-studio is unavailable]

| Stage | Purpose | Trigger |
| ----- | ------- | ------- |
| [stage] | [what it does] | [when it runs] |

## Trigger Rules

| Event | Pipeline | Conditions |
| ----- | -------- | ---------- |
| [push/PR/tag/schedule/manual] | [pipeline] | [branch/path filters] |

## Environment Matrix

[Mermaid diagram (via mermaid-studio) or ASCII promotion flow if mermaid-studio is unavailable — e.g. dev → staging → prod]

| Environment | Purpose | Promotion Method |
| ----------- | ------- | ---------------- |
| [env]       | [use]   | [auto/manual/approval] |

## Quality Gates

[Required checks, coverage thresholds, approvals before merge/deploy]

## Build Artifacts

| Artifact | Format | Storage |
| -------- | ------ | ------- |
| [name]   | [type] | [registry/bucket] |

## Deployment Strategy

[Strategy (blue/green, rolling, canary), tooling, rollback procedure]

## Secrets Management

[How secrets are injected — vault / CI env vars / sealed secrets. Names and mechanisms only, never values]

## Infrastructure as Code

| Tool | Scope |
| ---- | ----- |
| [tool] | [what it provisions] |

## Monitoring & Alerting

[Deploy notifications, failure alerts, post-deploy health checks]

## Data Pipelines

| Pipeline | Type | Schedule | Purpose |
| -------- | ---- | -------- | ------- |
| [name]   | [ETL/streaming/batch] | [cron] | [purpose] |

## Release Management

[Versioning scheme (semver/calver/commit-based), changelog generation, how tags are cut, release-notes process]

## Notable Patterns

[Matrix builds, reusable workflow templates, etc.]
```

**Instructions:**

- Focus on "how code gets from commit to production" — not internal application implementation.
- No secrets/tokens/values — only describe how secrets are managed.
- Include only sections with evidence; omit those with no findings.

## Step 13: Report

```
✓ docs/codebase/PROJECT.md       — [created | updated]
✓ docs/codebase/STACK.md         — [created | updated]
✓ docs/codebase/STRUCTURE.md     — [created | updated]
✓ docs/codebase/ARCHITECTURE.md  — [created | updated]
✓ docs/codebase/CONVENTIONS.md   — [created | updated]
✓ docs/codebase/INTEGRATIONS.md  — [created | updated]
✓ docs/codebase/TESTING.md       — [created | updated]
✓ docs/codebase/CONCERNS.md      — [created | updated]
✓ docs/codebase/PIPELINE.md      — [created | updated | skipped (no pipeline config found)]

These files are automatically loaded by agents at the start of each session
via the directive in AGENTS.global.md.
```

If any file could not be written, report the error and reason.

# Mode B — Incremental

Brings documentation in sync with the **current state of the workspace** — inline API docs, root context files, and the context files in `docs/codebase/`. Updates only what changed in the git diff, and detects new packages to scaffold (handing off to Package mode internally). Use for "update docs", "document my changes", "sync documentation", and similar.

Per the **Holistic Updates** guardrail, an "update" is never scoped to one file: after determining what changed, open **every** file in `docs/codebase/` and update each whose purpose is touched by the change.

## Step 1: Identify Modified Files

```bash
git diff --name-only HEAD                 # staged + unstaged vs HEAD
git ls-files --others --exclude-standard   # untracked new files
```

Group into **source files** (may carry inline API docs) and **documentation files**. If nothing changed, inform the user and stop.

## Step 2: Detect New Packages

```bash
git diff HEAD --name-only --diff-filter=A
git ls-files --others --exclude-standard
```

Extract unique parent directories from new files; a directory is "newly created" if ALL its files are new. What counts as a "package" depends on the stack — use project context:

1. **Read project context first** — load `docs/codebase/STACK.md` and `ARCHITECTURE.md` to learn the module conventions.
2. **Compare against sibling packages** at the same level.
3. **Stack-aware reasoning** — Go: dir of `.go` files under a `go.mod`; Django: app dir with `models.py`/`views.py`; Magento 2: dir with `registration.php` + `etc/module.xml`; Node monorepo: dir under `packages/`/`apps/` with its own `package.json`; PSR-4 namespaces. Reason from actual structure, not a fixed checklist.
4. **When uncertain, ask:** "I found new directories: `<list>`. Are any new packages that should get their own `CLAUDE.md`?"

If no new packages are detected (or the user confirms none), skip to Step 4.

## Step 3: Scaffold New Package Context

**Always confirm before scaffolding** — detection has false positives. For each candidate, ask "I detected what looks like a new package: `<path>`. Generate a `CLAUDE.md` for it?" If yes, **switch to Package mode internally** for that path (writes the package's `CLAUDE.md` via `docs-writer`). If multiple candidates, present them all at once. A confirmed new package is a **structural change** → afterward, suggest a Full-mode re-evaluation.

## Step 4: Update Inline API Documentation

For each modified source file: read it, check public/exported symbols (functions, classes, methods, types, constants) for missing or outdated docs, and update inline docs directly. Only touch symbols that changed or are undocumented public exports; preserve each file's existing doc style; do **not** refactor or modify code — only comments/annotations.

## Step 5: Review Root Context Files

Check if present and impacted: `README.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, other root `.md`. Read each, decide whether any section is affected, mark impacted/not. If `CLAUDE.md`/`GEMINI.md` are symlinks to `AGENTS.md`, update only `AGENTS.md`.

## Step 6: Holistic Sweep of `docs/codebase/`

```bash
find docs/codebase/ -name '*.md' -type f 2>/dev/null
```

Read **every** file — the whole tree, not just the top level, so nested and manually-added docs are covered — compare against the change, mark impacted ones. Files beyond the canonical nine are handled per **Additional Context Files** above: investigate them as input, flag/offer before refreshing rather than silently rewriting. Do **not** modify `docs/TECH_DEBTS.md`, `.specs/STATE.md`, `.specs/features/*`, or other out-of-scope areas (see the `docs/` Traversal Guardrail).

## Step 7: Apply Updates via docs-writer

For each impacted `.md` (plus any new-package `CLAUDE.md` from Step 3):

> **Delegate to `docs-writer`** with the target file path, a concise description of what changed in the codebase, and the specific sections to add/remove/revise.

## Step 8: Verify and Report

Confirm: modified source files have updated inline docs; new packages have a `CLAUDE.md`; root files reviewed; every `docs/codebase/` file opened and impacted ones updated; all `.md` writes delegated to docs-writer. Then report:

```
Documentation sync complete:

New packages scaffolded (Package mode):
  ✓ <path>/CLAUDE.md — created

Inline docs updated:
  ✓ <file> — <what was updated>

Context docs updated (via docs-writer):
  ✓ docs/codebase/<file> — <what was updated>

No changes needed:
  – docs/codebase/<file> — <reason>
```

Flag anything that could not be updated and explain what information is needed.

## Incremental Mode Examples

### Example 1: Standard documentation update

User: "update docs"

1. `git diff --name-only HEAD` → `src/api/auth.go`, `src/api/auth_test.go`, `docs/codebase/ARCHITECTURE.md`
2. No new directories → skip package detection
3. Update inline docs in `src/api/auth.go` (new exported `ValidateToken` undocumented)
4. Root files: `README.md`, `CLAUDE.md` — not impacted
5. Holistic sweep: `ARCHITECTURE.md` impacted; `TESTING.md` impacted (new test file); others opened and evaluated, not impacted
6. Delegate impacted files to docs-writer
7. Report: 1 source file, 2 context docs updated

### Example 2: New package detected — user confirms

User: "document my changes"

1. `git diff HEAD --name-only --diff-filter=A` → new files under `app/code/Vendor/Shipping/`
2. Project is Magento 2 (from `STACK.md`). New dir has `registration.php` + `etc/module.xml` → matches module pattern
3. Ask to scaffold → user confirms → Package mode internally → `Shipping/CLAUDE.md` via docs-writer
4. Update inline docs; holistic sweep (`ARCHITECTURE.md`, `STRUCTURE.md` impacted)
5. New package = structural change → suggest Full-mode re-evaluation
6. Report

### Example 3: New directory — user declines

User: "sync documentation"

1. New files under `internal/notifications/` (Go monolith)
2. Ask: "Should `internal/notifications/` get its own CLAUDE.md?"
3. User: "no, it's just a helper" → skip scaffolding
4. Continue with inline docs, root files, and the holistic sweep

# Mode C — Package

Triggered with a specific package/module path (e.g. "evaluate architecture for `packages/auth`"), or **internally by Incremental mode** when a new package is confirmed. Produces a **single `CLAUDE.md`** inside the package directory — not the `docs/codebase/` set — scoped to the package but deeper than project level.

## Scope Constraints

- Analyze ONLY files within the given package directory.
- Go deeper than project-level: internal structure, public API surface, dependency graph, integration boundaries.
- Do NOT create the `docs/codebase/` set — package mode produces only the package's `CLAUDE.md`.
- Same quality bar (factual, scannable, no code snippets unless strictly necessary, Mermaid diagrams preferred via `mermaid-studio` when available, ASCII diagrams as fallback).

## PM Step 1: Validate Package Path

Confirm the path exists and looks like a package for this stack. Load `docs/codebase/STACK.md` and `ARCHITECTURE.md` for module conventions. Reason from actual structure. If not a meaningful package boundary, inform the caller and stop.

## PM Step 2: Explore the Package

Read manifest/entry-point metadata; list the dir tree (2–3 levels); read entry points, main sources, key modules (cap 15–20 files); identify the public API surface and internal patterns. **The package dir is the source of truth:** glob it for manually-added docs (`find <package-path> -name '*.md' -type f` — READMEs, NOTES, ADRs, an existing `CLAUDE.md`) and investigate them as input. Preserve hand-authored docs — fold their content into the merge, never overwrite or delete.

## PM Step 3: Analyze Integration Points

How the package relates to the parent project; which other packages import it (`grep` for imports of this path); what it imports from the project; the boundary interfaces with consumers.

## PM Step 4: Write `<package-path>/CLAUDE.md`

> **Delegate to `docs-writer`** for the write.

Up to 500 lines; the depth the package warrants (a small utility may need 50; a complex domain module 400+). Same Update Merge Strategy. Sections (conditional):

| Section | Content |
|---------|---------|
| **Purpose** | What this package does and why it exists within the larger project |
| **Architecture** | Internal structure, layers, patterns. Mermaid diagram (via mermaid-studio) or ASCII if unavailable, when multi-layered |
| **Key Components** | Component / Role table |
| **Public API** | Exported interfaces, functions, types, contracts — the package boundary |
| **Internal Design** | Non-obvious implementation details: algorithms, state, concurrency, caching |
| **Data Model** | Key entities/structures internal to the package; relationships if applicable |
| **Dependencies (Internal)** | Other project packages this depends on and why |
| **Dependencies (External)** | Third-party libraries and their purpose here |
| **Integration Points** | How it connects to the rest of the project, imports, events produced/consumed |
| **Error Handling** | How errors are produced, propagated, expected handling by callers |
| **Constraints** | Invariants, performance, thread safety, ordering guarantees |
| **Conventions** | Naming, file organization, deviations from project-wide conventions |
| **Testing Strategy** | How tested: unit, integration, fixtures, mocks; key scenarios |

## PM Step 5: Report

```
Package architecture evaluated:
  ✓ <package-path>/CLAUDE.md — [created | updated]
    Sections: [list]
    Lines: [count]
```

If the package could not be fully evaluated, report what was generated and flag gaps. A newly scaffolded package is a structural change — suggest a Full-mode re-evaluation of `docs/codebase/`.

## Keeping Docs Up to Date

Re-run this skill when:

- Major new dependencies are added → **Full mode**
- The project structure significantly changes → **Full mode** (re-evaluate the set as a whole)
- A new architectural layer or pattern is introduced → **Full mode**
- CI/CD, deployment, or environment configuration changes → **Full mode**
- You've made code changes and want docs to reflect them → **Incremental mode**
- A new package/module is added → **Package mode** (directly, or via Incremental detection), then suggest a Full-mode re-evaluation
- Onboarding a new developer or agent → **Full mode**

These files should reflect the **current state of the codebase**, not aspirational design.
