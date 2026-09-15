---
name: architecture-evaluate
description: >
  Creates, updates, and incrementally syncs the project context documentation that agents load at
  session start. Three modes. Full mode deep-scans the codebase (brownfield mapping) and writes the
  context files to docs/codebase/ — PROJECT.md (overview, vision, goals), STACK.md, STRUCTURE.md,
  ARCHITECTURE.md, CONVENTIONS.md, INTEGRATIONS.md, TESTING.md, and CONCERNS.md, plus PIPELINE.md when
  the project has CI/CD or pipeline config. Incremental mode inspects the git workspace or a
  caller-supplied commit range and syncs only what changed — inline API docs in source files, root
  context files, and the context files in docs/codebase/ — and detects new packages. Package mode
  generates a scoped CLAUDE.md for an individual package/module.
  Use when the user says "evaluate architecture", "map codebase", "analyze existing code", "document
  current architecture", "initial architecture", "update architecture docs", "refresh project
  context", "setup project docs", "run architecture-evaluate", "onboard project", "create project
  docs", "update project docs", "update docs", "generate docs", "document my changes", "sync
  documentation", "document recent changes", "keep docs in sync", "api documentation", "evaluate
  package", "evaluate architecture for package", or "package architecture".
metadata:
  version: "5.0.1"
---

# Architecture Evaluate

Keep a project's agent-facing context documentation accurate through three modes, selected by the user's intent below. Full mode performs **brownfield codebase mapping** — a systematic scan that produces the context files in `docs/codebase/`.

## The Context Files

The canonical set lives in `docs/codebase/`. Full mode always writes eight of these files and writes `PIPELINE.md` only when the project has CI/CD or pipeline config (see Mode A — Full). Every section within a file is conditional and budget-bound; include only sections with codebase evidence. Total combined budget ≈ 30,000 tokens — load on-demand per task, not all at once.

| File | Purpose | Budget |
|------|---------|--------|
| `ARCHITECTURE.md` | Layers, data flow, patterns, system-level concerns (state, auth, observability) | ~4,000 |
| `CONCERNS.md` | Tech debt, bugs, security, performance, fragile areas, risks — evidence-backed | ~5,000 |
| `CONVENTIONS.md` | Naming, code style, error handling, documentation pattern | ~3,000 |
| `INTEGRATIONS.md` | External services, APIs, webhooks, background jobs | ~5,000 |
| `PIPELINE.md` | CI/CD, deployment, environment promotion, release management | ~3,000 |
| `PROJECT.md` | Overview, vision, goals, target users, scope — what the project is and who it's for | ~1,500 |
| `STACK.md` | Tech stack, key libraries, commands, environment config, local dev setup | ~2,000 |
| `STRUCTURE.md` | Directory layout, module organization, monorepo package map | ~2,000 |
| `TESTING.md` | Test frameworks, coverage matrix, parallelism, gate-check commands | ~4,000 |

## Context Scan

`scripts/context_scan.py` (Python 3, standard library only) gathers the facts that mode selection, the baseline check, misplaced-file detection, and change detection depend on. Run it from the project root and act on its JSON rather than re-deriving these facts with ad hoc `ls`, `find`, or `git diff` commands:

```bash
python3 <skill-dir>/scripts/context_scan.py                # changes from the working tree
python3 <skill-dir>/scripts/context_scan.py --base <ref>   # changes from <ref>...HEAD
```

| Key | Meaning |
|-----|---------|
| `baseline` | Which canonical files exist in `docs/codebase/` (`present` / `missing`), whether any baseline exists (`exists`), and every other `.md` in the folder, nested ones included (`extra`) |
| `changes` | Changed (`changed`) and newly added (`added`) files — from the working tree including untracked files, or from `<base>...HEAD` with `--base`; `error` when git could not answer |
| `deliverables` | Full mode's expected files: the eight always-required ones, plus `docs/codebase/PIPELINE.md` when `pipeline.exists` is true |
| `misplaced` | Canonical file names found anywhere outside `docs/codebase/`, including `docs/` subfolders and `.specs/codebase/` (`.git`, `node_modules`, vendor and build directories excluded) |
| `pipeline` | Whether CI/CD or pipeline config exists (`exists`) and the config paths found (`paths`) |

## Mode Selection

Pick the mode from the user's intent:

| Mode | Choose when the request is… | Examples |
|------|------------------------------|----------|
| **Full** (default) | Bootstrap or full refresh of project context — map the codebase, no specific change in mind | "evaluate architecture", "map codebase", "analyze existing code", "onboard project", "create project docs", "refresh project context", "update project docs" |
| **Incremental** | Sync docs to recent code changes in the workspace or a caller-supplied commit range | "update docs", "document my changes", "sync documentation", "document recent changes", "generate docs", "keep docs in sync", "api documentation" |
| **Package** | Document one specific package/module, or invoked internally by Incremental mode for a confirmed new package | "evaluate package", "package architecture", "evaluate architecture for `packages/auth`" |

When the intent is ambiguous, run the context scan and decide from its facts: pick **Incremental** if `changes.changed` is non-empty and `baseline.exists` is true; otherwise pick **Full**. If it is still unclear, ask the user which mode to run.

## Shared Guardrails

These apply to every mode.

- **This skill runs on Sonnet, in every mode** — doc generation is a long, read-heavy, write-heavy job whose tier shouldn't depend on which model the user happened to be in when they asked for it. See Model Pinning below for how that's enforced when the session is on something else.
- **Default document location is `docs/codebase/`.** Every context file this skill writes lives in `docs/codebase/`. Create the directory if it does not exist. (Package mode is the exception: it writes a `CLAUDE.md` inside the target package directory, not under `docs/codebase/`.)
- **Reading existing context for input** — when this skill loads a context file to inform its own work (not to write it), read it from `docs/codebase/<file>`.
- **The folder is the source of truth.** Treat the actual contents of `docs/codebase/` as authoritative. Sweep the real directory and preserve every `.md` present, including files added by hand beyond the canonical nine. Never regenerate or sync only the fixed list while ignoring what's on disk.
- **Out of scope.** Never create or modify `.specs/STATE.md` (the decisions/handoff memory) or feature specs under `.specs/features/`. This skill documents the codebase; those are another workflow's artifacts. `CONCERNS.md` is the living risk snapshot.
- **No code samples** unless strictly necessary. Use prose, tables, bullets. Code blocks only for directory trees, ASCII or Mermaid diagrams, and exact runnable commands. No method signatures, SQL queries, or implementation examples.
- **CI/CD belongs in `PIPELINE.md` only.** Other files may reference it but must not contain pipeline specifics.
- **Diagrams** — author data flows, layer relationships, component interactions, and pipeline stages as **Mermaid** diagrams. Converting existing ASCII diagrams to Mermaid is always permitted.
- **Factual only** — document what exists in the codebase. Never invent or speculate. Omit any section with no evidence.
- **Never write secret values** into any document. Reference secrets by name and describe only how they are managed (provider, injection mechanism) — everywhere, not just `PIPELINE.md`.
- **Conditional sections** — every section in every output file is conditional. Only include it if the codebase provides evidence for it; omit empty sections entirely.
- **Respect per-file budgets** (see The Context Files). Summarize aggressively — table rows over paragraphs, bullets over tables, omission over filler. Cap any single file at 500 lines.

### Model Pinning

Check the session's own model before doing any scanning work.

- **Already on Sonnet** (including when a caller already dispatched this skill into a Sonnet subagent) → run inline, exactly as documented below. Never dispatch a subagent from within an already-Sonnet run; that nests one isolation layer inside another for nothing.
- **On any other model** → run the pre-flight below, then dispatch one `Agent` (`subagent_type: general-purpose`, `model: sonnet`) to carry out the selected mode in its own context, passing the mode, the caller-supplied base ref if any, and the pre-flight answers.
  - **Completion condition:** Full — every path in the context scan's `deliverables` exists on disk, with `PIPELINE.md` reported as skipped when it is not a deliverable; Incremental — every impacted file from Steps 4–6 is updated; Package — the package's `CLAUDE.md` exists.
  - **Return shape:** `status` (`ok` / `blocked` / `question`), the file paths written (never their content), and `questions` — one item per user decision the subagent could not make.

**Pre-flight, required before any such dispatch.** A dispatched subagent cannot wait for the user, so split this skill's user decisions by when they can be made:

1. **Before dispatch — the misplaced-file migration.** Run the context scan yourself. If `misplaced` is non-empty, ask the migration question (see Detecting & Migrating Misplaced Context Files) and pass the answer as an explicit instruction ("migrate these paths" / "leave them in place, read them as source material"). Never dispatch with it unresolved — a subagent that silently picks a migration is worse than a slower run.
2. **After the subagent returns — decisions that depend on what it found.** Pointer registration (see Additional Context Files & Registration), new-package scaffolding (Incremental Steps 2–3), and refreshes of extra docs beyond the canonical set come back as `questions` items; the subagent skips those actions instead of guessing. Ask the user, then apply the approved actions or re-dispatch with the answers.

### Holistic Updates (Full and Incremental modes)

Whenever this skill updates the `docs/codebase/` context set — in Full or Incremental mode, at **any** point — it must not touch only the single file it set out to write. **Open every file present in `docs/codebase/`, evaluate each one's purpose against the change at hand, and update any whose content is affected.** A change to the codebase rarely lands in exactly one document; treat the `docs/codebase/` set as one interconnected context that must stay mutually consistent. This applies even when the trigger names a specific file (e.g. "update ARCHITECTURE") — still review the siblings. **Package mode is exempt:** it writes only the target package's `CLAUDE.md` and does not sweep `docs/codebase/`.

### Additional Context Files & Registration

The `docs/codebase/` set is **open-ended**. Beyond the canonical nine, a project may keep other context documents there. Treat **every** `.md` in `docs/codebase/` as part of the context set for Holistic Updates — the context scan lists the non-canonical ones as `baseline.extra`; don't assume only the canonical nine exist. For each such file (e.g. a hand-added `SECURITY.md`, or nested docs under `docs/codebase/adr/`), do not silently overwrite or drop it. Investigate it against the current code; if impacted or stale, flag it and offer to refresh it rather than rewriting silently.

When a context file in `docs/codebase/` is **not** referenced by the project's session-start context list, **suggest adding a pointer to it** as a new row (file path + a one-line "when to read it"), matching the existing rows, so agents auto-load it. Identify which of the project's root context files holds that list from what actually exists. Confirm before editing it.

### Detecting & Migrating Misplaced Context Files

The canonical location is `docs/codebase/`. The nine canonical file names are `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `PIPELINE.md`, `PROJECT.md`, `STACK.md`, `STRUCTURE.md`, `TESTING.md`.

**Before generating or syncing (Full Step 1, Incremental Step 0), check the context scan's `misplaced` list** — every canonical file name found outside `docs/codebase/`.

**If it is non-empty:** do **not** move or overwrite anything silently. Present what was found and where (e.g. "`STACK.md`, `ARCHITECTURE.md` in `docs/`; `PROJECT.md` in `docs/architecture/`"), **suggest migrating the set to `docs/codebase/`**, and **wait for the user's confirmation** before relocating anything.

**Found files are valuable input — use them, don't discard them.** Any misplaced file that is (or becomes) a context doc is read as **source material for the corresponding `docs/codebase/` file being created or refreshed**: carry its still-accurate content forward and merge it per the Update Merge Strategy rather than regenerating from scratch. This applies whether the user opts to physically move the file or to leave it in place and regenerate — either way its content seeds the new doc.

Once the user confirms a migration:
- Move/merge the files into `docs/codebase/` (never blind-overwrite a same-named file already there — merge per the Update Merge Strategy).
- Find the files that reference the old paths (consumers, root context files) and update those references.
- Treat it as a structural change → suggest a Full-mode re-evaluation (see Re-evaluate on Structural Change).

Use judgment on the scan's hits: a same-named file inside a package or an unrelated docs tree may not be a context doc — flag ambiguous hits and ask rather than assuming.

### Re-evaluate on Structural Change

If the documentation file structure changes — files migrated into `docs/codebase/`, a context file added or removed — or the codebase's own structure shifts significantly (a new architectural layer, moved/renamed top-level directories, a new package) — **suggest re-evaluating all context files together via Full mode.** Structural changes ripple across every document, so the set should be regenerated as a consistent whole rather than patched file by file.

### Update Merge Strategy

When updating existing files:

- Work section by section.
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
- **Never browse other `docs/` subfolders** (`docs/tasks/`, `docs/specs/`, `docs/tech-debts/`, `docs/decisions/`, etc.). Those belong to other workflows and are out of scope.
- The context scan is the one sanctioned way to locate canonical context files anywhere else in the project, `docs/` subfolders included. Read only the paths it returns in `misplaced`.

# Mode A — Full

Creates or updates the project context files in `docs/codebase/` from a full codebase scan (brownfield mapping).

**Deliverables:** the eight always-required files — `ARCHITECTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `PROJECT.md`, `STACK.md`, `STRUCTURE.md`, `TESTING.md` — plus `PIPELINE.md` only when CI/CD or pipeline config exists; otherwise `PIPELINE.md` is reported as skipped. The context scan's `deliverables` list is this set for the project at hand; Full mode is complete when every path in it exists on disk.

**High-level approach:** explore the directory structure systematically → identify the stack from dependency manifests → extract patterns from representative code samples → document observed conventions and architecture → catalog external integrations → surface evidence-backed concerns.

**Analysis depth:** sample representative files — focus on consistency and patterns, not exhaustive coverage. Extract actual examples, not assumptions. Prioritize breadth over depth.

## Step 1: Confirm File Location

Default: `docs/codebase/` at project root. Create it if it doesn't exist. If the user specifies a different location, use that instead.

Run the context scan (see Context Scan) without `--base`.

- **`baseline.present` is non-empty** → inform the user those files will be **updated**, not replaced — existing content is preserved and refined per the Update Merge Strategy.
- **`misplaced` is non-empty** → **suggest migrating them to `docs/codebase/` and wait for confirmation before proceeding** — never relocate silently. Whether moved or left in place, **read those files as source material** to seed the corresponding new docs (see Detecting & Migrating Misplaced Context Files).
- **`deliverables`** is the list Steps 3–11 must produce; `pipeline.exists` decides whether Step 11 writes `PIPELINE.md`.

## Step 2: Explore the Codebase

Use Glob and Read to gather context, adapting searches to the actual language, framework, and tooling.

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

Write the deliverables in Steps 3–11. Each step gives the file's purpose, what to extract, a template skeleton, and instructions. Include only sections with evidence.

## Step 3: Write PROJECT.md

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

## Step 4: Write STACK.md

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

## Step 5: Write STRUCTURE.md

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

## Step 6: Write ARCHITECTURE.md

**Purpose:** How the system is structured — "how is it organized", not "how does X work internally". No method signatures, SQL, or code snippets. Testing strategy lives in TESTING.md, background jobs in INTEGRATIONS.md, CI/CD in PIPELINE.md.
**Extract from:** directory organization, repeated patterns across files, entry points, config.

```markdown
# Architecture

## Overview / Pattern

[2–3 sentences: what the system does + primary architectural style: monolith / microservices / event-driven]

## High-Level Structure

[Mermaid diagram]

## Layers

| Layer | Responsibility | Key Files or Dirs |
| ----- | -------------- | ----------------- |
| [layer] | [role]       | [paths]           |

## Dependency Rules

[Who can import whom, who can't — e.g. "services never import controllers"]

## Request / Data Flow

[Mermaid diagram or numbered list]

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

## Step 7: Write CONVENTIONS.md

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

## Step 8: Write INTEGRATIONS.md

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

## Step 9: Write TESTING.md

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

## Step 10: Write CONCERNS.md

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

## Step 11: Write PIPELINE.md

**Purpose:** How code gets from commit to production. **If the context scan's `pipeline.exists` is false, skip this file entirely** — it is not a deliverable — and report it as skipped in Step 12.
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

[Mermaid flowchart]

| Stage | Purpose | Trigger |
| ----- | ------- | ------- |
| [stage] | [what it does] | [when it runs] |

## Trigger Rules

| Event | Pipeline | Conditions |
| ----- | -------- | ---------- |
| [push/PR/tag/schedule/manual] | [pipeline] | [branch/path filters] |

## Environment Matrix

[Mermaid promotion diagram — e.g. dev → staging → prod]

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

## Step 12: Report

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

Agents load these files on demand, as each task needs them.
```

If any file could not be written, report the error and reason.

# Mode B — Incremental

Brings documentation in sync with the **current state of the workspace**, or with a caller-supplied commit range — inline API docs, root context files, and the context files in `docs/codebase/`. Updates only what changed, and detects new packages to scaffold (handing off to Package mode internally). Use for "update docs", "document my changes", "sync documentation", and similar.

**Scope input:** if the caller supplies a base ref (the commit range `<base>...HEAD`, e.g. everything pushed to a branch since it left its target), pass it to the context scan as `--base <ref>`; otherwise the scan reads the working tree. Committed-and-pushed work shows up only through a base ref.

Per the **Holistic Updates** guardrail, an "update" is never scoped to one file: after determining what changed, open **every** file in `docs/codebase/` and update each whose purpose is touched by the change.

## Step 0: Baseline & Misplaced-File Check

Run the context scan (see Context Scan), with `--base <ref>` when one was supplied.

1. **`baseline.exists` is false** → stop; there is no baseline to sync against. If `misplaced` lists context files, suggest migrating them to `docs/codebase/` first (see Detecting & Migrating Misplaced Context Files); otherwise suggest running Full mode first.
2. **`misplaced` is non-empty** → handle it per Detecting & Migrating Misplaced Context Files before continuing.

## Step 1: Identify Modified Files

Use the scan's `changes.changed`. If `changes.error` is set, report it and stop. Group the files into **source files** (may carry inline API docs) and **documentation files**. If nothing changed, inform the user and stop.

## Step 2: Detect New Packages

Take the scan's `changes.added` and extract their unique parent directories; a directory is "newly created" if ALL its files are new. What counts as a "package" depends on the stack — use project context:

1. **Read project context first** — load `docs/codebase/STACK.md` and `ARCHITECTURE.md` to learn the module conventions.
2. **Compare against sibling packages** at the same level.
3. **Stack-aware reasoning** — Go: dir of `.go` files under a `go.mod`; Django: app dir with `models.py`/`views.py`; Magento 2: dir with `registration.php` + `etc/module.xml`; Node monorepo: dir under `packages/`/`apps/` with its own `package.json`; PSR-4 namespaces. Reason from actual structure, not a fixed checklist.
4. **When uncertain, ask:** "I found new directories: `<list>`. Are any new packages that should get their own `CLAUDE.md`?"

If no new packages are detected (or the user confirms none), skip to Step 4.

## Step 3: Scaffold New Package Context

**Always confirm before scaffolding** — detection has false positives. For each candidate, ask "I detected what looks like a new package: `<path>`. Generate a `CLAUDE.md` for it?" If yes, **switch to Package mode internally** for that path (writes the package's `CLAUDE.md`). If multiple candidates, present them all at once. A confirmed new package is a **structural change** → afterward, suggest a Full-mode re-evaluation.

## Step 4: Update Inline API Documentation

For each modified source file: read it, check public/exported symbols (functions, classes, methods, types, constants) for missing or outdated docs, and update inline docs directly. Only touch symbols that changed or are undocumented public exports; preserve each file's existing doc style; do **not** refactor or modify code — only comments/annotations.

## Step 5: Review Root Context Files

Identify which root context files the project actually has (its README and any agent instruction files at the root). Read each, decide whether any section is affected by the change, and mark it impacted or not. If one root file is a symlink to another, update only the target.

## Step 6: Holistic Sweep of `docs/codebase/`

Read **every** file in `docs/codebase/` — the scan's `baseline.present` plus `baseline.extra`, which covers nested and manually-added docs — compare each against the change, and mark impacted ones. Files beyond the canonical nine are handled per **Additional Context Files** above: investigate them as input, flag/offer before refreshing rather than silently rewriting. Do **not** modify `.specs/STATE.md`, `.specs/features/*`, or other out-of-scope areas (see Shared Guardrails and the `docs/` Traversal Guardrail).

## Step 7: Apply Updates

For each impacted `.md` (plus any new-package `CLAUDE.md` from Step 3), add, remove, or revise the specific sections the change affects, per the Update Merge Strategy.

## Step 8: Verify and Report

Confirm: modified source files have updated inline docs; new packages have a `CLAUDE.md`; root context files reviewed; every `docs/codebase/` file opened and impacted ones updated. Then report:

```
Documentation sync complete:

New packages scaffolded (Package mode):
  ✓ <path>/CLAUDE.md — created

Inline docs updated:
  ✓ <file> — <what was updated>

Context docs updated:
  ✓ docs/codebase/<file> — <what was updated>

No changes needed:
  – docs/codebase/<file> — <reason>
```

Flag anything that could not be updated and explain what information is needed.

## Incremental Mode Example

User: "update docs"

0. Context scan → `baseline.exists` true, `misplaced` empty
1. `changes.changed` → `src/api/auth.go`, `src/api/auth_test.go`, plus new files under `app/code/Vendor/Shipping/` (also listed in `changes.added`)
2. New directory has `registration.php` + `etc/module.xml` → matches this stack's (Magento 2, from `STACK.md`) module pattern → ask to scaffold → user confirms → Package mode internally writes `Shipping/CLAUDE.md` (a decline here would just skip scaffolding and continue at Step 4)
3. Update inline docs in `src/api/auth.go` (new exported `ValidateToken` undocumented)
4. Root context files: `README.md` — not impacted
5. Holistic sweep: `ARCHITECTURE.md` and `STRUCTURE.md` impacted (new package); `TESTING.md` impacted (new test file); others opened and evaluated, not impacted
6. Apply the section updates to the three impacted files
7. New package = structural change → suggest Full-mode re-evaluation
8. Report: 1 source file, 1 new package `CLAUDE.md`, 3 context docs updated

# Mode C — Package

Triggered with a specific package/module path (e.g. "evaluate architecture for `packages/auth`"), or **internally by Incremental mode** when a new package is confirmed. Produces a **single `CLAUDE.md`** inside the package directory — not the `docs/codebase/` set — scoped to the package but deeper than project level.

## Scope Constraints

- Analyze ONLY files within the given package directory.
- Go deeper than project-level: internal structure, public API surface, dependency graph, integration boundaries.
- Do NOT create the `docs/codebase/` set — package mode produces only the package's `CLAUDE.md`.
- Same quality bar (factual, scannable, no code snippets unless strictly necessary, Mermaid diagrams).

## PM Step 1: Validate Package Path

Confirm the path exists and looks like a package for this stack. Load `docs/codebase/STACK.md` and `ARCHITECTURE.md` for module conventions. Reason from actual structure. If not a meaningful package boundary, inform the caller and stop.

## PM Step 2: Explore the Package

Read manifest/entry-point metadata; list the dir tree (2–3 levels); read entry points, main sources, key modules (cap 15–20 files); identify the public API surface and internal patterns. **The package dir is the source of truth:** glob it for manually-added docs (`find <package-path> -name '*.md' -type f` — READMEs, NOTES, ADRs, an existing `CLAUDE.md`) and investigate them as input. Preserve hand-authored docs — fold their content into the merge, never overwrite or delete.

## PM Step 3: Analyze Integration Points

How the package relates to the parent project; which other packages import it (`grep` for imports of this path); what it imports from the project; the boundary interfaces with consumers.

## PM Step 4: Write `<package-path>/CLAUDE.md`

Up to 500 lines; the depth the package warrants (a small utility may need 50; a complex domain module 400+). Same Update Merge Strategy. Sections (conditional):

| Section | Content |
|---------|---------|
| **Purpose** | What this package does and why it exists within the larger project |
| **Architecture** | Internal structure, layers, patterns. Mermaid diagram when multi-layered |
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

- No `docs/codebase/` baseline exists → **Full mode**
- Major new dependencies are added → **Full mode**
- The project structure significantly changes → **Full mode** (re-evaluate the set as a whole)
- A new architectural layer or pattern is introduced → **Full mode**
- CI/CD, deployment, or environment configuration changes → **Full mode**
- You've made code changes and want docs to reflect them → **Incremental mode**
- A new package/module is added → **Package mode** (directly, or via Incremental detection), then suggest a Full-mode re-evaluation
- Onboarding a new developer or agent → **Full mode**

These files should reflect the **current state of the codebase**, not aspirational design.
