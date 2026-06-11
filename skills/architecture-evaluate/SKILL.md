---
name: architecture-evaluate
description: >
  Creates, updates, and incrementally syncs the project context documentation that agents load at
  session start. Three modes. Full mode deep-scans the codebase to create or update the three mandatory
  context files (PROJECT_DETAILS.md, ARCHITECTURE.md, PIPELINE.md) in docs/codebase/. Incremental mode
  inspects the git workspace and syncs only what changed — inline API docs in source files, root context
  files (README.md, CLAUDE.md, AGENTS.md), and the context files in docs/codebase/ — and detects new
  packages. Package mode generates a scoped CLAUDE.md for an individual package/module. Use when the user
  says "evaluate architecture", "update architecture docs", "refresh project context", "onboard project",
  "create project docs", "update project docs", "update docs", "document my changes", "sync
  documentation", "document recent changes", "evaluate package", or "package architecture".
metadata:
  version: "3.1.0"
  triggers:
    # Full mode — bootstrap / full refresh of the three context files
    - "evaluate architecture"
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

Keep a project's agent-facing context documentation accurate through three modes, selected by the user's intent below.

## Mode Selection

Pick the mode from the user's intent:

| Mode | Choose when the request is… | Examples |
|------|------------------------------|----------|
| **Full** (default) | Bootstrap or full refresh of project context — no specific change in mind | "evaluate architecture", "onboard project", "create project docs", "refresh project context", "update architecture docs", "update project docs" |
| **Incremental** | Sync docs to recent code changes in the workspace | "update docs", "document my changes", "sync documentation", "document recent changes", "generate docs", "keep docs in sync", "api documentation" |
| **Package** | Document one specific package/module, or invoked internally by Incremental mode for a confirmed new package | "evaluate package", "package architecture", "evaluate architecture for `packages/auth`" |

When ambiguous, default to **Full** mode. **If Incremental mode runs but the three core files are absent from `docs/codebase/`:** if they exist in the legacy `docs/` root, suggest migrating them to `docs/codebase/` first (see Migrating Legacy Context Files); if they exist nowhere, suggest running Full mode first — there is no baseline to sync against.

## Shared Guardrails

These apply to every mode.

- **Default document location is `docs/codebase/`.** Every codebase context file this skill writes — `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`, and any other context documents present there — lives in `docs/codebase/`. Create the directory if it does not exist. (Package mode is the exception: it writes a `CLAUDE.md` inside the target package directory, not under `docs/codebase/`.)
- **Reading existing context for input** — when this skill loads a context file to inform its own work (not to write it), check `docs/codebase/<file>` first, then fall back to the legacy `docs/<file>`. A project mid-migration may still keep them in `docs/`. The skill only ever *writes* to `docs/codebase/`; the fallback applies to reads.
- **500-line budget** per output file — these are agent context files, not exhaustive documentation. Summarize aggressively. Prefer table rows over paragraphs, bullets over tables, omission over filler.
- **No code samples** unless strictly necessary. Use prose, tables, bullets. Code blocks only for directory trees, ASCII diagrams, and exact runnable commands. Do not include code snippets, method signatures, SQL queries, or implementation examples.
- **CI/CD belongs in PIPELINE.md only.** PROJECT_DETAILS.md and ARCHITECTURE.md may reference PIPELINE.md but must not contain pipeline specifics.
- **ASCII diagrams encouraged** for data flows, layer relationships, component interactions, pipeline stages. Keep them simple (box-and-arrow style) and focused on the conceptual level.
- **Factual only** — document what exists in the codebase. Never invent or speculate. Omit any section with no evidence.
- **Never write secret values** into any document. Reference secrets by name and describe only how they are managed (provider, injection mechanism) — this applies everywhere, not just PIPELINE.md.
- **Conditional sections** — every section in every output file is conditional. Only include it if the codebase provides evidence for it.
- **Delegate every `.md` write to the `docs-writer` skill** — regardless of mode or context. This ensures consistent formatting, style, and link integrity across all documentation. No exceptions.
- **Follow [Token Efficiency Rules](../../templates/token-efficiency-rules.md)** when generating any `.md` content.

### Holistic Updates (Full and Incremental modes)

Whenever this skill updates the `docs/codebase/` context set — in Full or Incremental mode, at **any** point — it must not touch only the single file it set out to write. **Open every file present in `docs/codebase/`, evaluate each one's purpose against the change at hand, and update any whose content is affected.** A change to the codebase rarely lands in exactly one document; treat the `docs/codebase/` set as one interconnected context that must stay mutually consistent. This applies even when the trigger names a specific file (e.g. "update PROJECT_DETAILS") — still review the siblings. **Package mode is exempt:** it writes only the target package's `CLAUDE.md` and does not sweep `docs/codebase/` (when reached internally from Incremental mode, the Incremental flow runs the sweep separately).

### Additional Context Files & Registration

The `docs/codebase/` set is **open-ended**. Beyond the three canonical files, a project may keep other context documents there (e.g. `CODING_STYLE.md`, `TESTS.md`, `AGENT-SKILLS.md`). Treat **every** `.md` in `docs/codebase/` as part of the context set for Holistic Updates — discover them, don't assume only the canonical three exist.

When a context file in `docs/codebase/` is **not** referenced by the project's session-start context list — the context-files table in the global `AGENTS.global.md` or the project root `CLAUDE.md`/`AGENTS.md` — **suggest adding a pointer to it in the project root `CLAUDE.md`/`AGENTS.md`** as a new table row (file path + a one-line "when to read it"), matching the existing rows, so agents auto-load it. Confirm before editing the root file.

### Migrating Legacy Context Files

If any context document — the canonical three (`PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`) or another context file such as `CODING_STYLE.md` — is found directly in `docs/` instead of `docs/codebase/`, **suggest moving it to `docs/codebase/`** before proceeding, so the location convention stays consistent. Ask the user to confirm the move — do not relocate files silently. After a confirmed move, update any references to the old path (see Re-evaluate on Structural Change).

### Re-evaluate on Structural Change

If the documentation file structure changes — files are migrated into `docs/codebase/`, a context file is added or removed, or the codebase's own structure shifts significantly (a new architectural layer, moved/renamed top-level directories, a new package) — **suggest re-evaluating all context files together via Full mode.** Structural changes ripple across every document, so the set should be regenerated as a consistent whole rather than patched file by file.

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

- Context files live in `docs/codebase/` — check files directly in `docs/codebase/` (e.g. `docs/codebase/ARCHITECTURE.md`, `docs/codebase/PROJECT_DETAILS.md`).
- **Never descend into other `docs/` subfolders** (`docs/tasks/`, `docs/specs/`, `docs/tech-debts/`, `docs/decisions/`, etc.). Those are owned by other skills or workflows and are out of scope.

# Mode A — Full

Creates or updates the three project context files (`docs/codebase/PROJECT_DETAILS.md`, `docs/codebase/ARCHITECTURE.md`, `docs/codebase/PIPELINE.md`) from a full codebase scan.

## Step 1: Confirm File Location

Default: `docs/codebase/` at project root. Create it if it doesn't exist. If the user specifies a different location, use that instead.

Check for existing files in both the new and legacy locations:

```bash
ls docs/codebase/PROJECT_DETAILS.md docs/codebase/ARCHITECTURE.md docs/codebase/PIPELINE.md 2>/dev/null
ls docs/PROJECT_DETAILS.md docs/ARCHITECTURE.md docs/PIPELINE.md 2>/dev/null   # legacy location
```

If any exist in `docs/codebase/`, inform the user they will be **updated**, not replaced — existing content is preserved and refined per the Update Merge Strategy above. If any are found directly in `docs/` (legacy location), **suggest migrating them to `docs/codebase/` first** (see Shared Guardrails → Migrating Legacy Context Files) and proceed from there once confirmed.

## Step 2: Bootstrap Analysis (Claude Code only)

Run `/init` to get an initial codebase perspective. Use output **only as supporting context** for subsequent steps — **do not save the generated CLAUDE.md**. If `/init` writes a CLAUDE.md, discard or revert it.

Skip if `/init` is unavailable (other AI coding tools, non-interactive mode) — the manual exploration in Step 3 is sufficient.

## Step 3: Explore the Codebase

Use Glob and Read to gather context. Adapt searches to the actual language, framework, and tooling the project uses.

**Do not over-read.** 10–15 files for small/medium projects. 25–30 for monorepos, focusing on one representative module per layer. Prioritize breadth (get the shape of the project) over depth.

| Area | What to look for |
|------|-----------------|
| **Dependency manifests** | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `Gemfile`, `requirements.txt` — extract exact pinned versions for all key libraries; these feed the Key Libraries table in Step 4 |
| **Infrastructure** | `Dockerfile`, `docker-compose.yml`, `Makefile`, `justfile` |
| **Local dev tooling** | Seed scripts, mock servers, dev-only config, fixture data, local service stubs |
| **Environment** | `.env.example`, `.env.sample`, `README.md` for env docs |
| **Monorepo config** | `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json` |
| **Project structure** | Top-level directory tree (one level deep), main source and test directories |
| **Entry points** | Main files, bootstrap, application config |
| **Existing docs** | Any pre-existing architecture or project documentation |
| **External integrations** | API client dirs, SDK configs, webhook handlers/endpoints, service wrappers, gateway adapters, ERP connectors, payment provider modules |
| **Architecture layers** | API routes, services, data access, background jobs |
| **Database** | Schema/migration dirs, ORM config, connection pool config, read replica setup |
| **Observability** | Logging config, tracing setup (OpenTelemetry, Datadog APM), metrics collection, structured logging conventions |
| **State management** | Session config, cache config, state store setup (Redis, Memcached, in-memory) |
| **Feature flag system** | Feature flag provider config (LaunchDarkly, Unleash, env-based, DB-based) |
| **API specs** | OpenAPI, GraphQL schemas, protobuf definitions |
| **CI/CD** | `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml`, `azure-pipelines.yml`, `.buildkite/` |
| **Deployment** | `deploy/`, `k8s/`, `helm/`, `terraform/`, `cdk/`, `pulumi/`, `serverless.yml`, `fly.toml`, `vercel.json`, `netlify.toml` |
| **Release management** | `.releaserc`, `release.config.js`, `changesets/`, `.changeset/` |
| **Data pipelines** | `dags/`, `pipelines/`, Airflow, dbt, Spark configs |
| **Monitoring** | Datadog monitors, PagerDuty integrations, alerting configs tied to deploys |

## Step 4: Write PROJECT_DETAILS.md

> **Delegate to `docs-writer`** for the `.md` file write to ensure consistent formatting.

Create or update `docs/codebase/PROJECT_DETAILS.md` (or user-specified path). Include only sections with evidence:

| Section | Content |
|---------|---------|
| **Overview** | 1–2 sentence description of what the project does and who it's for |
| **Tech Stack** | Category / Technology table (language, framework, database, cache, queue, infrastructure). Include minimum runtime/language version constraints (e.g. Node >= 18, Python >= 3.11) — agents must respect these to avoid using unsupported features |
| **Key Libraries** | Library / Version / Purpose / Modern Usage table — extract the exact pinned version from the dependency manifest; for each library, use Context7 (`mcp__context7__*`) or a web search to identify the idiomatic modern APIs and patterns agents should prefer for that version (e.g. "React Query v5 → use `useQuery` not `connect()`", "SQLAlchemy 2.x → use `select()` not `Query`"). Flag any library pinned to a significantly outdated minor or major version. |
| **Project Structure** | Top-level directory tree with brief annotations |
| **Commands** | Task / Command table (setup, build, test, lint, deploy, migrate, seed) |
| **Local Development Setup** | Services to run (docker compose profile, local DB), seed/fixture data, how to mock or stub external services, ports and URLs for local services |
| **Naming Conventions** | Files, classes, database tables, routes, branches |
| **Environment Configuration** | Key env vars from `.env.example` or similar — `VAR_NAME` + description |
| **External Integrations** | For each: name, type (ERP, payment gateway, CRM, email/SMS, auth provider, cloud service, third-party API), purpose, data flow direction (inbound/outbound/both), protocol (REST, SOAP, webhooks, SDK), and auth method used. Include webhook endpoints (both consumed and exposed) |
| **Jobs / Crons** | Job / Frequency / Purpose table |
| **Feature Flags** | Flag name + description and current state |
| **Known Limitations / Tech Debt** | Brief list of items |
| **Monorepo Package Map** | If monorepo: Package name / Path / Responsibility table showing each package and its role in the system |
| **Documentation Pattern** | How docs are organized (Swagger/OpenAPI, JSDoc/PHPDoc, guides, ADRs, etc.) |

## Step 5: Write ARCHITECTURE.md

> **Delegate to `docs-writer`** for the `.md` file write.

Create or update `docs/codebase/ARCHITECTURE.md`. Focus on "how is the system structured" — not "how does X work internally". No implementation details (no method signatures, no SQL queries, no code snippets). Include only sections with evidence:

| Section | Content |
|---------|---------|
| **Overview** | 2–3 sentences: what the system does, primary architectural style (monolith, microservices, event-driven) |
| **Layers** | Layer / Responsibility / Key Files or Dirs table |
| **Dependency Rules** | Who can import whom, who can't (e.g. "services never import controllers") |
| **Request / Data Flow** | ASCII diagram or numbered list showing how a typical request flows through the system |
| **Communication Patterns** | How services/modules communicate: REST, events, queues, gRPC |
| **Key Components** | Component / Role table |
| **Data Model** | Key entities and their relationships — conceptual map, not full schema |
| **Database Access Patterns** | Access pattern (repository, active record, raw queries, query builder), connection pooling strategy, read replica usage, migrations framework |
| **External Dependencies** | Service / How Used / Protocol table. Split into infrastructure (databases, caches, queues) and business integrations (ERPs, payment gateways, CRMs, third-party APIs). For business integrations: include data flow direction and integration pattern (sync API call, async webhook, event-driven, batch file exchange) |
| **State Management** | How application state is managed: stateless (JWT), server sessions, distributed cache, event sourcing. Where state lives, how it's shared across instances |
| **Error Handling Strategy** | Where errors are caught, where they propagate, error format |
| **Auth Strategy** | Middleware, guards, where the logic lives |
| **Observability** | Logging framework and conventions (structured/unstructured, log levels), tracing (OpenTelemetry, vendor APM), metrics collection, correlation IDs. How agents should instrument new code |
| **API Versioning** | How API versions are managed (URL path `/v1/`, headers, query params, no versioning), deprecation policy, version coexistence strategy |
| **Feature Flag System** | Provider (LaunchDarkly, Unleash, env-based, DB-based), how flags are evaluated at runtime, where flag definitions live, how agents should gate new features |
| **Background Jobs** | Job types and their triggers |
| **Testing Strategy** | Test types, frameworks, patterns (e.g. "Jest + Supertest for integration, no mocking of DB") |
| **Notable Patterns** | Repository pattern, service wrappers, decorator usage, etc. |

## Step 6: Write PIPELINE.md

> **Delegate to `docs-writer`** for the `.md` file write.

**If no CI/CD or pipeline configuration exists, skip this file entirely** and note its absence in the Step 7 report.

Create or update `docs/codebase/PIPELINE.md`. Focus on "how does code get from commit to production" — not internal implementation. No secrets, tokens, or sensitive values — only describe how secrets are managed. Include only sections with evidence:

| Section | Content |
|---------|---------|
| **Overview** | 1–2 sentences: CI/CD platform, pipeline philosophy (trunk-based, GitFlow, monorepo-aware) |
| **CI/CD Platform** | Platform / Config location / Runner type table |
| **Pipeline Stages** | ASCII diagram of pipeline flow + Stage / Purpose / Trigger table |
| **Trigger Rules** | Event / Pipeline / Conditions table (push, PR, tag, schedule, manual) |
| **Environment Matrix** | ASCII promotion flow + Environment / Purpose / Promotion method table |
| **Quality Gates** | Required checks, coverage thresholds, approvals before merge/deploy |
| **Build Artifacts** | Artifact / Format / Storage table |
| **Deployment Strategy** | Strategy type (blue/green, rolling, canary), tooling, rollback procedure |
| **Secrets Management** | How secrets are injected (vault, CI env vars, sealed secrets) — where references live, never values |
| **Infrastructure as Code** | Tool / Scope table (e.g. Terraform → AWS infrastructure) |
| **Monitoring & Alerting** | Deploy notifications, failure alerts, post-deploy health checks |
| **Data Pipelines** | Pipeline / Type / Schedule / Purpose table (ETL, streaming, batch) |
| **Release Management** | Versioning scheme (semver, calver, commit-based), changelog generation (manual, automated via changesets/conventional commits), how tags are cut, release notes process |
| **Notable Patterns** | Matrix builds, reusable workflow templates, etc. |

## Step 7: Report

```
✓ docs/codebase/PROJECT_DETAILS.md — [created | updated]
✓ docs/codebase/ARCHITECTURE.md — [created | updated]
✓ docs/codebase/PIPELINE.md — [created | updated | skipped (no pipeline config found)]

These files are automatically loaded by agents at the start of each session
via the directive in AGENTS.global.md.
```

If any file could not be written, report the error and reason.

# Mode B — Incremental

Brings documentation in sync with the **current state of the workspace** — inline API docs, root context files, and the context files in `docs/codebase/`. Updates only what changed in the git diff, and detects new packages to scaffold (handing off to Package mode internally). Use this mode for "update docs", "document my changes", "sync documentation", and similar.

Per the **Holistic Updates** guardrail, an "update" is never scoped to a single file: after determining what changed, open **every** file in `docs/codebase/` and update each one whose purpose is touched by the change.

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

1. **Read project context first.** Load `docs/codebase/PROJECT_DETAILS.md` and `docs/codebase/ARCHITECTURE.md` if available (fall back to `docs/` per the read-fallback guardrail). Understand how this project is structured, what its module boundaries look like, and what patterns existing packages follow.
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

**Always ask for user confirmation before scaffolding.** Package detection can produce false positives — the user must confirm before any scaffolding happens.

For each candidate new package:

1. Present findings and ask for confirmation:
   > "I detected what looks like a new package: `<path>`. Should I generate a `CLAUDE.md` for it?"
2. If the user confirms, **switch to Package mode internally** for the package path: run the Package mode steps below, which write the package's `CLAUDE.md` directly via `docs-writer`. This is an in-skill mode switch — no cross-skill handoff.
3. If the user declines, skip and continue to Step 4.

If multiple candidates are detected, present them all at once so the user can confirm or decline each one in a single response. A confirmed new package is a **structural change** — per the Re-evaluate on Structural Change guardrail, suggest a Full-mode re-evaluation of all context files afterward.

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

## Step 6: Cross-Reference Context Files in `docs/codebase/`

List **all** files in `docs/codebase/` and evaluate each against the change — not only the ones obviously related to the diff (per the **Holistic Updates** guardrail):

```bash
find docs/codebase/ -maxdepth 1 -name '*.md' -type f 2>/dev/null
```

Typical files: `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, `PIPELINE.md`. For each:
1. Read the file to understand its scope and purpose.
2. Compare against the code changes from Step 1.
3. Mark as impacted if changes fall within its scope.

Other base `docs/` files (e.g. `TECH_DEBTS.md`) and `docs/` subfolders are owned by other skills — do not modify them here (see the `docs/` Traversal Guardrail).

## Step 7: Update All Impacted .md Files via docs-writer

For each impacted `.md` file identified in Steps 5 and 6 (plus any new-package `CLAUDE.md` from Step 3):

> **Delegate to `docs-writer`**: invoke the docs-writer skill with the target file path and a summary of what changed. docs-writer handles style, formatting, link verification, and consistency.

Provide docs-writer with:
- The file to update
- A concise description of what changed in the codebase
- Any specific sections that need to be added, removed, or revised

## Step 8: Verify and Report

After all updates, check that:

- [ ] All modified source files with public symbols have updated inline documentation
- [ ] New packages have a `CLAUDE.md` generated (via Package mode, written through docs-writer)
- [ ] Root-level context files are still accurate
- [ ] **Every** file in `docs/codebase/` was opened and evaluated; impacted ones were updated
- [ ] All `.md` edits were delegated to docs-writer

Then report:

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

If any file could not be updated (e.g. ambiguous change, insufficient context), flag it and explain what information is needed.

## Incremental Mode Examples

### Example 1: Standard documentation update

User: "update docs"

1. `git diff --name-only HEAD` → `src/api/auth.go`, `src/api/auth_test.go`, `docs/codebase/ARCHITECTURE.md`
2. No new directories detected → skip package detection
3. Update inline docs in `src/api/auth.go` (new exported function `ValidateToken` undocumented)
4. Root files: `README.md` — not impacted. `CLAUDE.md` — not impacted.
5. Holistic sweep of `docs/codebase/`: `ARCHITECTURE.md` already in the diff → impacted. `PROJECT_DETAILS.md`, `PIPELINE.md` — opened and evaluated, not impacted.
6. Delegate `docs/codebase/ARCHITECTURE.md` update to docs-writer
7. Report: 1 source file updated, 1 context doc updated

### Example 2: New package detected — user confirms

User: "document my changes"

1. `git diff HEAD --name-only --diff-filter=A` → new files under `app/code/Vendor/Shipping/`
2. Project is Magento 2 (from `docs/codebase/PROJECT_DETAILS.md`). New directory has `registration.php` + `etc/module.xml` → matches existing module pattern in `app/code/Vendor/`
3. Ask: "I detected what looks like a new Magento module: `app/code/Vendor/Shipping/`. Should I generate a CLAUDE.md for it?"
4. User: "yes" → switch to Package mode internally for that path → write `Shipping/CLAUDE.md` via docs-writer
5. Update inline docs in modified source files
6. Holistic sweep of `docs/codebase/`: `ARCHITECTURE.md` — impacted (new module in the system); others opened and evaluated
7. Delegate `docs/codebase/ARCHITECTURE.md` update to docs-writer
8. A new package is a structural change → suggest a Full-mode re-evaluation of all context files
9. Report: 1 package scaffolded, inline docs updated, 1 context doc updated

### Example 3: New directory — user declines

User: "sync documentation"

1. `git diff HEAD --name-only --diff-filter=A` → new files under `internal/notifications/`
2. Project is a Go monolith. `internal/notifications/` is newly created with `.go` files.
3. Ask: "I found a new directory `internal/notifications/` with Go files. Should it get its own CLAUDE.md?"
4. User: "no, it's just a helper package" → skip scaffolding
5. Continue with inline docs, root files, and the `docs/codebase/` holistic sweep as usual

# Mode C — Package

Triggered when invoked with a specific package/module path (e.g. "evaluate architecture for `packages/auth`"), or **internally by Incremental mode** when a new package is detected and confirmed.

Produces a **single `CLAUDE.md`** inside the package directory instead of the full `docs/codebase/` file set. Analysis is scoped exclusively to the package but goes deeper than project-level — internal structure, public API surface, dependency graph, integration points.

## Scope Constraints

- Analyze ONLY files within the given package directory.
- Go deeper than project-level: map internal structure, enumerate public API surface, trace dependency graph, document integration boundaries.
- Do NOT create `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, or `PIPELINE.md` — package mode produces only the package's `CLAUDE.md`.
- Same quality standards as project-level files (factual, scannable, no code snippets unless strictly necessary, ASCII diagrams encouraged).

## PM Step 1: Validate Package Path

Confirm the path exists and looks like a package for this project's stack. Load `docs/codebase/PROJECT_DETAILS.md` and `docs/codebase/ARCHITECTURE.md` if available (fall back to `docs/` per the read-fallback guardrail) for context on module conventions.

What constitutes a valid package depends on the tech stack — a Go package is a directory with `.go` files under an existing `go.mod`, a Magento module has `registration.php` + `etc/module.xml`, a Django app has `models.py`/`views.py`, etc. Reason from the project's actual structure and conventions rather than a fixed checklist.

If the path does not appear to be a meaningful package boundary, inform the caller and stop.

## PM Step 2: Explore the Package

- Read manifest/entry-point files for metadata (name, version, dependencies).
- List directory tree (2–3 levels deep).
- Read entry points, main source files, key modules (cap at 15–20 files).
- Identify public API surface (exported symbols, interfaces, types).
- Identify internal patterns (layers, abstractions, data flow within the package).

**Do not over-read.** 15–20 files is usually enough. For very large packages, focus on entry points, public interfaces, and one representative file per internal layer.

## PM Step 3: Analyze Integration Points

- How does this package relate to the parent project?
- What other project packages import this one? (`grep` for import/require statements referencing this package path.)
- What does this package import from the rest of the project?
- Identify boundary interfaces — the contracts between this package and its consumers.

## PM Step 4: Write `<package-path>/CLAUDE.md`

> **Delegate to `docs-writer`** for the `.md` file write.

**Line budget:** Up to 500 lines. Use the depth the package warrants — a small utility may need 50 lines; a complex domain module may need 400+. Same Update Merge Strategy as project-level files. Include only sections with evidence:

| Section | Content |
|---------|---------|
| **Purpose** | What this package does, why it exists, what problem it solves within the larger project |
| **Architecture** | Internal structure, layers, patterns used. ASCII diagram if multi-layered |
| **Key Components** | Component / Role table |
| **Public API** | Exported interfaces, functions, types, contracts — the package's boundary |
| **Internal Design** | Non-obvious implementation details for maintainers: algorithms, state management, concurrency, caching |
| **Data Model** | Key entities, schemas, data structures internal to the package. Entity relationships if applicable |
| **Dependencies (Internal)** | Other project packages this depends on and why |
| **Dependencies (External)** | Third-party libraries and their purpose within this package |
| **Integration Points** | How it connects to the rest of the project, imports, events produced/consumed |
| **Error Handling** | How errors are produced, propagated, expected handling by callers |
| **Constraints** | Rules, invariants, performance considerations, thread safety, ordering guarantees |
| **Conventions** | Naming, file organization, patterns specific to this package — deviations from project-wide conventions |
| **Testing Strategy** | How tested: unit, integration, fixtures, mocks. Key scenarios and edge cases |

## PM Step 5: Report

```
Package architecture evaluated:
  ✓ <package-path>/CLAUDE.md — [created | updated]
    Sections: [list of sections included]
    Lines: [count]
```

If the package could not be fully evaluated (e.g. insufficient source files, ambiguous structure), report what was generated and flag gaps. A newly scaffolded package is a structural change — suggest a Full-mode re-evaluation of the `docs/codebase/` context files.

## Keeping Docs Up to Date

Re-run this skill when:

- Major new dependencies are added → **Full mode**
- The project structure significantly changes → **Full mode** (re-evaluate all context files as a set)
- A new architectural layer or pattern is introduced → **Full mode**
- CI/CD pipelines, deployment strategies, or environment configurations change → **Full mode**
- You've made code changes and want docs to reflect them → **Incremental mode** (syncs only what changed, including inline API docs and root context files, and runs the holistic `docs/codebase/` sweep)
- A new package/module is added → **Package mode** (directly, or via Incremental mode's detection), then suggest a Full-mode re-evaluation
- Onboarding a new developer or agent to the project → **Full mode**

These files should reflect the **current state of the codebase**, not aspirational design.
