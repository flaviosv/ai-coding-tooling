---
name: architecture-evaluate
description: >
  Creates or updates the three mandatory project context files: PROJECT_DETAILS.md, ARCHITECTURE.md,
  and PIPELINE.md in docs/. These files are auto-loaded by agents at session start to provide project
  context. Also supports package mode for evaluating individual packages/modules, generating a scoped
  CLAUDE.md inside the package directory. Use when the user says "evaluate architecture", "update
  architecture docs", "refresh project context", "onboard project", "create project docs", "update
  project docs", "evaluate package", or "package architecture".
metadata:
  version: "2.0.0"
  triggers:
    - "evaluate architecture"
    - "initial architecture"
    - "update architecture docs"
    - "refresh project context"
    - "setup project docs"
    - "run architecture-evaluate"
    - "update project docs"
    - "create project docs"
    - "onboard project"
    - "evaluate package"
    - "evaluate architecture for package"
    - "package architecture"
---

# Architecture Evaluate

Creates or updates the three project context files (`docs/PROJECT_DETAILS.md`, `docs/ARCHITECTURE.md`, `docs/PIPELINE.md`) that agents load at session start. Package mode produces a scoped `CLAUDE.md` inside a specific package directory.

## Guardrails

- **500-line budget** per output file — these are agent context files, not exhaustive documentation. Summarize aggressively. Prefer table rows over paragraphs, bullets over tables, omission over filler.
- **No code samples** unless strictly necessary. Use prose, tables, bullets. Code blocks only for directory trees, ASCII diagrams, and exact runnable commands. Do not include code snippets, method signatures, SQL queries, or implementation examples.
- **CI/CD belongs in PIPELINE.md only.** PROJECT_DETAILS.md and ARCHITECTURE.md may reference PIPELINE.md but must not contain pipeline specifics.
- **ASCII diagrams encouraged** for data flows, layer relationships, component interactions, pipeline stages. Keep them simple (box-and-arrow style) and focused on the conceptual level.
- **Factual only** — document what exists in the codebase. Never invent or speculate. Omit any section with no evidence.
- **Conditional sections** — every section in every output file is conditional. Only include it if the codebase provides evidence for it.

### Update Merge Strategy

When updating existing files:

- Read the existing file first. Work section by section.
- Update sections where codebase evidence changed (new dependencies, renamed dirs, etc.).
- Preserve sections the user manually added that are not part of the standard template — those represent intentional customization.
- Never delete a section just because you cannot find evidence for it in this pass — the user may have added it from knowledge outside the codebase.
- If a section's content is now inaccurate, replace the content but keep the heading.

## Step 1: Confirm File Location

Default: `docs/` at project root. Create if it doesn't exist. If the user specifies a different location, use that instead.

Check for existing files:

```bash
ls docs/PROJECT_DETAILS.md docs/ARCHITECTURE.md docs/PIPELINE.md 2>/dev/null
```

If any exist, inform the user they will be **updated**, not replaced — existing content will be preserved and refined per the merge strategy above.

## Step 2: Bootstrap Analysis (Claude Code only)

Run `/init` to get an initial codebase perspective. Use output **only as supporting context** for subsequent steps — **do not save the generated CLAUDE.md**. If `/init` writes a CLAUDE.md, discard or revert it.

Skip if `/init` is unavailable (other AI coding tools, non-interactive mode) — the manual exploration in Step 3 is sufficient.

## Step 3: Explore the Codebase

Use Glob and Read to gather context. Adapt searches to the actual language, framework, and tooling the project uses.

**Do not over-read.** 10–15 files for small/medium projects. 25–30 for monorepos, focusing on one representative module per layer. Prioritize breadth (get the shape of the project) over depth.

| Area | What to look for |
|------|-----------------|
| **Dependency manifests** | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `Gemfile`, `requirements.txt` |
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

Create or update `docs/PROJECT_DETAILS.md` (or user-specified path). Include only sections with evidence:

| Section | Content |
|---------|---------|
| **Overview** | 1–2 sentence description of what the project does and who it's for |
| **Tech Stack** | Category / Technology table (language, framework, database, cache, queue, infrastructure). Include minimum runtime/language version constraints (e.g. Node >= 18, Python >= 3.11) — agents must respect these to avoid using unsupported features |
| **Key Libraries** | Library / Purpose table |
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

Create or update `docs/ARCHITECTURE.md`. Focus on "how is the system structured" — not "how does X work internally". No implementation details (no method signatures, no SQL queries, no code snippets). Include only sections with evidence:

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

Create or update `docs/PIPELINE.md`. Focus on "how does code get from commit to production" — not internal implementation. No secrets, tokens, or sensitive values — only describe how secrets are managed. Include only sections with evidence:

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
✓ docs/PROJECT_DETAILS.md — [created | updated]
✓ docs/ARCHITECTURE.md — [created | updated]
✓ docs/PIPELINE.md — [created | updated | skipped (no pipeline config found)]

These files are automatically loaded by agents at the start of each session
via the directive in AGENTS.global.md.
```

If any file could not be written, report the error and reason.

---

## Package Mode

Triggered when invoked with a specific package/module path (e.g. "evaluate architecture for `packages/auth`") or called by **documentation-upsert** when a new package is detected.

Produces a **single `CLAUDE.md`** inside the package directory instead of the full `docs/` file set. Analysis is scoped exclusively to the package but goes deeper than project-level — internal structure, public API surface, dependency graph, integration points.

### Scope Constraints

- Analyze ONLY files within the given package directory.
- Go deeper than project-level: map internal structure, enumerate public API surface, trace dependency graph, document integration boundaries.
- Do NOT create `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, or `PIPELINE.md` — package mode produces only `CLAUDE.md`.
- Same quality standards as project-level files (factual, scannable, no code snippets unless strictly necessary, ASCII diagrams encouraged).

### PM Step 1: Validate Package Path

Confirm the path exists and looks like a package for this project's stack. Load `docs/PROJECT_DETAILS.md` and `docs/ARCHITECTURE.md` if available for context on module conventions.

What constitutes a valid package depends on the tech stack — a Go package is a directory with `.go` files under an existing `go.mod`, a Magento module has `registration.php` + `etc/module.xml`, a Django app has `models.py`/`views.py`, etc. Reason from the project's actual structure and conventions rather than a fixed checklist.

If the path does not appear to be a meaningful package boundary, inform the caller and stop.

### PM Step 2: Explore the Package

- Read manifest/entry-point files for metadata (name, version, dependencies).
- List directory tree (2–3 levels deep).
- Read entry points, main source files, key modules (cap at 15–20 files).
- Identify public API surface (exported symbols, interfaces, types).
- Identify internal patterns (layers, abstractions, data flow within the package).

**Do not over-read.** 15–20 files is usually enough. For very large packages, focus on entry points, public interfaces, and one representative file per internal layer.

### PM Step 3: Analyze Integration Points

- How does this package relate to the parent project?
- What other project packages import this one? (`grep` for import/require statements referencing this package path.)
- What does this package import from the rest of the project?
- Identify boundary interfaces — the contracts between this package and its consumers.

### PM Step 4: Write `<package-path>/CLAUDE.md`

> **Delegate to `docs-writer`** for the `.md` file write.

**Line budget:** Up to 500 lines. Use the depth the package warrants — a small utility may need 50 lines; a complex domain module may need 400+. Same update merge strategy as project-level files. Include only sections with evidence:

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

### PM Step 5: Report

```
Package architecture evaluated:
  ✓ <package-path>/CLAUDE.md — [created | updated]
    Sections: [list of sections included]
    Lines: [count]
```

If the package could not be fully evaluated (e.g. insufficient source files, ambiguous structure), report what was generated and flag gaps.

---

## Keeping Docs Up to Date

Re-run this skill when:

- Major new dependencies are added
- The project structure significantly changes
- A new architectural layer or pattern is introduced
- CI/CD pipelines, deployment strategies, or environment configurations change
- A new package/module is added (use package mode for the new package)
- Onboarding a new developer or agent to the project

These files should reflect the **current state of the codebase**, not aspirational design.
