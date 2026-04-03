---
name: evaluate-architecture
description: >
  Creates or updates the three mandatory project context files: PROJECT_DETAILS.md, ARCHITECTURE.md, and PIPELINE.md. These files are auto-loaded by agents at the start of every session to provide project context. Also supports package mode for evaluating individual packages/modules within a project, generating a scoped CLAUDE.md inside the package directory. Use when setting up a new project, onboarding a project, or when the user says "update architecture docs", "refresh project context", "run evaluate-architecture", "update project docs", "onboard project", "evaluate architecture", "evaluate package", or "package architecture".
metadata:
  version: "1.2.0"
  triggers:
    - "initial architecture"
    - "update architecture docs"
    - "refresh project context"
    - "setup project docs"
    - "run evaluate-architecture"
    - "update project docs"
    - "create project docs"
    - "onboard project"
    - "evaluate architecture"
    - "evaluate package"
    - "evaluate architecture for package"
    - "package architecture"
---

# evaluate-architecture

Creates or updates the three mandatory project context files that agents load at the start of every session. These files give the agent just enough context to work effectively without bloating the context window.

## Output Files

PROJECT_DETAILS.md:
- Overview of the project
- Tech stack with versions
- Key libraries
- Setup, build, and test commands (the agent needs to know how to run the project)
- Naming conventions (files, classes, tables, routes, branches)
- Jobs/crons with frequency and purpose of each
- Active feature flags or toggles
- External integrations (third-party APIs, webhooks, SDKs) with the purpose of each
- Known limitations or relevant tech debt
- Documentation pattern

ARCHITECTURE.md:
- Architecture pattern
- Layer responsabilities
- Directory map with the semantic responsibility of each folder (not a full tree, but what each level means)
- Main data flow — request enters where, passes through which layers, exits where
- Dependency rules between layers (who can import whom, who can't)
- Communication patterns between services/modules (REST, events, queues, gRPC)
- Error handling strategy (where errors are caught, where they propagate, error format)
- Auth strategy (middleware, guards, where the logic lives)
- Key components and their roles
- Data model (key entities and their relationships — not full schema, just the conceptual map)
- External dependencies
- Testing strategy / patterns
- Notable patterns

PIPELINE.md:
- CI/CD platform and tooling
- Pipeline stages and their purpose (lint, build, test, deploy, etc.)
- Environment matrix (dev, staging, production) and promotion flow between them
- Trigger rules (on push, on PR, on tag, scheduled, manual)
- Quality gates (required checks, coverage thresholds, approvals before merge/deploy)
- Build artifacts (what is produced, where it is stored)
- Deployment strategy (blue/green, rolling, canary, direct)
- Secrets management (how secrets are injected — vault, environment, CI variables — not the secrets themselves)
- Rollback strategy (how to revert a bad deploy)
- Infrastructure-as-code overview (Terraform, CDK, Pulumi, Helm — what manages what)
- Monitoring and alerting tied to pipeline events (deploy notifications, failure alerts)
- Data pipelines (ETL, streaming, batch processing — if present)

**Line budget:** Each output file must not exceed 500 lines — these are agent context files, not exhaustive documentation. If a section would push the file over budget, summarize more aggressively. Prefer a table row over a paragraph, a bullet over a table, and omission over filler.

**No code samples** in the output files unless strictly necessary. These files describe architecture and project context — use prose, tables, and bullet lists. Code blocks are only justified for directory tree structures, ASCII diagrams, and exact commands the agent must run. Do not include code snippets, method signatures, SQL queries, or implementation examples.

**CI/CD and deployment information belongs exclusively in PIPELINE.md.** Do not duplicate pipeline, deployment, or release workflow details in PROJECT_DETAILS.md or ARCHITECTURE.md. Those files may reference PIPELINE.md but must not contain pipeline specifics.

**ASCII diagrams are strongly encouraged** whenever they clarify structure — data flows, layer relationships, component interactions, entity relationships, pipeline stage flows. Keep them simple (box-and-arrow style) and focused on the conceptual level.

Default location: `docs/` at the project root (e.g. `docs/PROJECT_DETAILS.md`).

> If the user specifies a different location (e.g. `docs/`), use that instead.

---

## Package Mode

Triggered when invoked with a specific package/module path (e.g. "evaluate architecture for `packages/auth`") or called by the **documentation-upsert** skill when a new package is detected.

In package mode, the skill produces a **single `CLAUDE.md`** inside the package directory instead of the full `docs/` file set. The analysis is scoped exclusively to the package but goes deeper than project-level evaluation — internal structure, public API surface, dependency graph, and integration points with the parent project.

### When to use

- Called by **documentation-upsert** when a new package is detected in the git diff.
- Called directly by the user: "evaluate architecture for `<path>`", "evaluate package `<path>`", "package architecture `<path>`".

### Scope constraints

- Analyze ONLY files within the given package directory.
- Go deeper than project-level: map internal structure, enumerate public API surface, trace dependency graph, document integration boundaries.
- Do NOT create `PROJECT_DETAILS.md`, `ARCHITECTURE.md`, or `PIPELINE.md` — package mode produces only `CLAUDE.md`.
- Apply the same quality standards and principles as project-level files (factual, scannable, no code snippets unless strictly necessary, ASCII diagrams encouraged).

### Output: `<package-path>/CLAUDE.md`

**Line budget:** Up to 500 lines — same as project-level context files. Use the depth that the package warrants. A small utility package may need 50 lines; a complex domain module may need 400+.

The CLAUDE.md must include the sections below. Every section is conditional — only include it if the package provides evidence for it:

````markdown
# <Package Name>

## Purpose
[What this package does, why it exists, and what problem it solves within the larger project]

## Architecture
[Internal structure, layers, patterns used within the package]
[ASCII diagram encouraged if the package has multiple internal layers or components]

## Key Components
| Component | Role |
|-----------|------|
| ... | ... |

## Public API
[Exported interfaces, functions, types, and their contracts]
[This is the package's boundary — what consumers depend on]

## Internal Design
[Implementation details that matter for maintainers: algorithms, state management, concurrency patterns, caching strategies]
[Only include what would be non-obvious to someone reading the code for the first time]

## Data Model
[Key entities, schemas, or data structures internal to the package]
[Entity relationships if applicable]

## Dependencies
### Internal
[Other project packages this depends on and why]

### External
[Third-party libraries and their purpose within this package]

## Integration Points
[How this package connects to the rest of the project]
[What imports this package, what events/messages it produces or consumes]

## Error Handling
[How errors are produced, propagated, and expected to be handled by callers]

## Constraints
[Rules, invariants, things to watch out for]
[Performance considerations, thread safety, ordering guarantees]

## Conventions
[Naming, file organization, patterns specific to this package]
[Anything that deviates from project-wide conventions]

## Testing Strategy
[How this package is tested: unit, integration, fixtures, mocks]
[Key test scenarios and edge cases]
````

### Package Mode Steps

#### PM Step 1: Validate package path

Confirm the path exists and looks like a package in the context of this project. Load `docs/PROJECT_DETAILS.md` and `docs/ARCHITECTURE.md` if available to understand the project's module conventions.

What constitutes a valid package depends on the tech stack — a Go package is a directory with `.go` files under an existing `go.mod`, a Magento module has `registration.php` + `etc/module.xml`, a Django app has `models.py`/`views.py`, etc. Reason from the project's actual structure and conventions rather than a fixed checklist.

If the path does not appear to be a meaningful package boundary, inform the caller and stop.

#### PM Step 2: Explore the package

- Read any manifest or entry-point files for metadata (name, version, dependencies).
- List the directory tree (2–3 levels deep).
- Read entry points, main source files, and key modules (cap at 15–20 files).
- Identify public API surface (exported symbols, interfaces, types).
- Identify internal patterns (layers, abstractions, data flow within the package).

**Do not over-read.** 15–20 files is usually enough. For very large packages, focus on entry points, public interfaces, and one representative file per internal layer.

#### PM Step 3: Analyze integration points

- How does this package relate to the parent project?
- What other project packages import this one? (`grep` for import/require statements referencing this package path.)
- What does this package import from the rest of the project?
- Identify boundary interfaces — the contracts between this package and its consumers.

#### PM Step 4: Write `<package-path>/CLAUDE.md`

Create or update the CLAUDE.md using the template above. Apply the same principles as project-level files:
- Factual and scannable — tables and bullets over prose.
- No code blocks except ASCII diagrams and exact commands.
- Conditional sections — omit any section with no evidence.
- ASCII diagrams encouraged for internal architecture and data flow.

> **Delegate to `docs-writer`** for the `.md` file write to ensure consistent formatting.

**Update merge strategy** (same as project-level): if a CLAUDE.md already exists, read it first, preserve manually-added sections, update sections where evidence changed, never delete unverified sections.

#### PM Step 5: Report

```
Package architecture evaluated:
  ✓ <package-path>/CLAUDE.md — [created | updated]
    Sections: [list of sections included]
    Lines: [count]
```

If the package could not be fully evaluated (e.g. insufficient source files, ambiguous structure), report what was generated and flag gaps.

---

## Instructions

### Step 0: Confirm file location

If the user did not specify where to put the files, default to `docs/`. If `docs/` does not exist, create it.

Check whether each file already exists:
```bash
ls docs/PROJECT_DETAILS.md docs/ARCHITECTURE.md docs/PIPELINE.md 2>/dev/null
```

If any files exist, inform the user:
> Found existing files: [list]. These will be **updated**, not replaced from scratch — existing content will be preserved and refined.

**Update merge strategy:** When updating existing files:
- Read the existing file first. Work section by section.
- Update sections where the codebase evidence has changed (new dependencies, renamed directories, etc.).
- Preserve sections the user manually added that are not part of the standard template — these represent intentional customization.
- Never delete a section just because you cannot find evidence for it in this pass — the user may have added it from knowledge outside the codebase.
- If a section's content is now inaccurate, replace the content but keep the heading.

### Step 1: Bootstrap analysis (Claude Code only)

If you are running in **Claude Code**, run the `/init` command to get Claude's initial perspective on the project. This performs a holistic analysis of the codebase — purpose, tech stack, structure, and conventions.

- Use the output **only as supporting context** for writing the output files in subsequent steps.
- **Do not save the generated CLAUDE.md.** If `/init` writes a CLAUDE.md, discard or revert it — the analysis is consumed internally by this skill, not persisted.
- If `/init` is unavailable (other AI coding tools, non-interactive mode), skip this step entirely — the manual exploration in Step 2 is sufficient.

### Step 2: Explore the codebase

Use Glob and Read to gather context. The examples below are common patterns — adapt your search to whatever language, framework, or tooling the project actually uses.

**Tech stack detection:**
- Look for dependency/package manifests (e.g. `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `Gemfile`, `requirements.txt`)
- Look for containerization and infrastructure config (e.g. `Dockerfile`, `docker-compose.yml`)
- Look for environment config (e.g. `.env.example`, `.env.sample`, or `README.md`)
- Look for build/task runner files (e.g. `Makefile`, `justfile`) — these often contain the most accurate build/test commands
- Look for workspace/monorepo config (e.g. `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`)

**Project structure:**
- Read the top-level directory tree (one level deep)
- Identify main source directories and test directories
- Look for any additional config, scripts, or tooling directories relevant to the stack

**Architecture:**
- Look for existing architecture documentation
- Read application entry points and bootstrap files
- Identify layers: API, services, data access, background jobs, etc.
- Identify external integrations: databases, queues, third-party APIs
- Look for database schema/migration directories and ORM config
- Look for API specification files (e.g. OpenAPI, GraphQL schemas, protobuf definitions)

**Pipelines:**
- Look for CI/CD configuration files (e.g. `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml`, `azure-pipelines.yml`, `.buildkite/`)
- Look for deployment configuration (e.g. `deploy/`, `k8s/`, `helm/`, `terraform/`, `cdk/`, `pulumi/`, `serverless.yml`, `fly.toml`, `render.yaml`, `vercel.json`, `netlify.toml`)
- Look for release or version management config (e.g. `.releaserc`, `release.config.js`, `changesets/`, `.changeset/`)
- Look for data pipeline definitions (e.g. `dags/`, `pipelines/`, Airflow, dbt, Spark configs)
- Look for monitoring/alerting config tied to deploys (e.g. Datadog monitors, PagerDuty integrations, Slack webhook configs)

**Do not over-read.** 10–15 files is usually enough for small/medium projects. For monorepos or large codebases, explore up to 25–30 files, focusing on one representative module per layer. Prioritize breadth (get the shape of the project) over depth.

---

> **Formatting:** When writing or updating any of the output files, use the **docs-writer** skill to ensure consistent formatting, style, and link integrity across all documentation.

### Step 3: Write PROJECT_DETAILS.md

Create or update `docs/PROJECT_DETAILS.md` (or the user-specified path).

The file must include the sections below. Every section is conditional — only include it if the codebase provides evidence for it:

````markdown
# Project Details

## Overview
[1–2 sentence description of what the project does and who it's for]

## Tech Stack
| Category | Technology |
|----------|-----------|
| Language | ... |
| Framework | ... |
| Database | ... |
| Cache | ... |
| Queue | ... |
| Infrastructure | ... |

## Key Libraries
| Library | Purpose |
|---------|---------|
| ... | ... |

## Project Structure
```
<top-level directory tree with brief annotations>
```

## Commands
| Task | Command |
|------|---------|
| Setup | ... |
| Build | ... |
| Test | ... |

## Naming Conventions
- Files: [convention, e.g. kebab-case]
- Classes: [convention]
- Database tables: [convention]
- Routes: [convention]
- Branches: [convention]

## Environment Configuration
Key environment variables (from .env.example or similar):
- `VAR_NAME` — description

## External Integrations
- [Integration name]: [what it's used for]

## Jobs / Crons
| Job | Frequency | Purpose |
|-----|-----------|---------|
| ... | ... | ... |

## Feature Flags
- `FLAG_NAME` — description and current state

## Known Limitations / Tech Debt
- [Item]: [brief description]

## Documentation Pattern
- [How docs are organized: Swagger/OpenAPI, inline code docs (JSDoc, PHPDoc, etc.), guides, ADRs, etc.]
````

**Principles:**
- Must not exceed 500 lines
- Keep it factual and scannable — no prose paragraphs, use tables and bullet lists
- No code blocks except for directory trees and runnable commands
- Only include what was actually found in the codebase; do not invent
- Omit any section for which there is no evidence in the codebase

---

### Step 4: Write ARCHITECTURE.md

Create or update `docs/ARCHITECTURE.md`.

The file must include the sections below. Every section is conditional — only include it if the codebase provides evidence for it:

````markdown
# Architecture

## Overview
[2–3 sentences: what the system does, its primary architectural style (e.g. monolith, microservices, event-driven)]

## Layers
| Layer | Responsibility | Key Files/Dirs |
|-------|---------------|----------------|
| ... | ... | ... |

## Dependency Rules
- [who can import whom, who can't, e.g. "services never import controllers"]

## Request / Data Flow
[ASCII diagram or numbered list showing how a typical request flows through the system]

Example:
```
HTTP Request
  → API Layer (routes/)
  → Service Layer (services/)
  → Repository Layer (repositories/)
  → Database
```

## Communication Patterns
- [How services/modules communicate: REST, events, queues, gRPC, etc.]

## Key Components
| Component | Role |
|-----------|------|
| ... | ... |

## Data Model
Key entities and their relationships (conceptual map, not full schema):
- [Entity A] → has many → [Entity B]
- [Entity C] → belongs to → [Entity A]

## External Dependencies
| Service | How Used |
|---------|---------|
| PostgreSQL | Primary data store |
| Redis | Session cache + job queue |
| S3 | File storage |

## Error Handling Strategy
- [Where errors are caught, where they propagate, error format]

## Auth Strategy
- [Middleware, guards, where the logic lives]

## Background Jobs
[List job types and their triggers]

## Testing Strategy
- [Test types used, frameworks, patterns, e.g. "Jest + Supertest for integration, no mocking of DB"]

## Notable Patterns
- [Pattern 1, e.g. "Repository pattern for all DB access"]
- [Pattern 2, e.g. "All external calls wrapped in service classes"]
````

**Principles:**
- Must not exceed 500 lines — enough to orient an agent, not a full system design doc
- No implementation details (no method signatures, no SQL queries, no code snippets)
- No code blocks except for ASCII diagrams and directory trees
- Focus on "how is the system structured" not "how does X work internally"
- ASCII diagrams are strongly encouraged — they make data flows, layer relationships, and component interactions much easier to grasp at a glance. Keep them simple and focused
- Omit any section for which there is no evidence in the codebase

---

### Step 5: Write PIPELINE.md

Create or update `docs/PIPELINE.md` (or the user-specified path).

The file must include the sections below. Every section is conditional — only include it if the codebase provides evidence for it:

````markdown
# Pipeline

## Overview
[1–2 sentences: CI/CD platform used, overall pipeline philosophy (e.g. trunk-based, GitFlow, monorepo-aware)]

## CI/CD Platform
| Attribute | Value |
|-----------|-------|
| Platform | [e.g. GitHub Actions, GitLab CI, Jenkins, CircleCI] |
| Config location | [e.g. `.github/workflows/`] |
| Runner type | [e.g. GitHub-hosted, self-hosted, hybrid] |

## Pipeline Stages
[ASCII diagram showing the pipeline flow, e.g.]
```
Push / PR
  → Lint & Format Check
  → Build
  → Unit Tests
  → Integration Tests
  → Security Scan
  → Deploy (staging)
  → E2E Tests
  → Deploy (production)
```

| Stage | Purpose | Trigger |
|-------|---------|---------|
| ... | ... | ... |

## Trigger Rules
| Event | Pipeline | Conditions |
|-------|----------|------------|
| Push to main | Full pipeline | Always |
| Pull request | CI checks | Always |
| Tag push | Release pipeline | `v*` pattern |
| Schedule | Nightly tests | Cron |
| Manual | Deploy to prod | Workflow dispatch |

## Environment Matrix
```
feature branch → dev → staging → production
```

| Environment | Purpose | Promotion method |
|-------------|---------|-----------------|
| dev | ... | ... |
| staging | ... | ... |
| production | ... | ... |

## Quality Gates
- [Required checks before merge/deploy]
- [Coverage thresholds]
- [Required approvals]
- [Automated security scans]

## Build Artifacts
| Artifact | Format | Storage |
|----------|--------|---------|
| ... | ... | ... |

## Deployment Strategy
- Strategy: [blue/green, rolling, canary, direct, etc.]
- Tooling: [what orchestrates deploys — Argo, Flux, scripts, platform-native]
- Rollback: [how to revert a bad deploy]

## Secrets Management
- [How secrets are injected — vault, CI environment variables, sealed secrets, etc.]
- [Where secret references live — not the secrets themselves]

## Infrastructure as Code
| Tool | Scope |
|------|-------|
| [e.g. Terraform] | [e.g. AWS infrastructure] |
| [e.g. Helm] | [e.g. Kubernetes deployments] |

## Monitoring & Alerting
- [Deploy notifications — where they go (Slack, email, etc.)]
- [Failure alerts — who gets paged, via what]
- [Post-deploy health checks]

## Data Pipelines
| Pipeline | Type | Schedule | Purpose |
|----------|------|----------|---------|
| ... | [ETL / streaming / batch] | ... | ... |

## Notable Patterns
- [Pattern 1, e.g. "Matrix builds for multiple Node versions"]
- [Pattern 2, e.g. "Reusable workflow templates in `.github/workflows/shared/`"]
````

**Principles:**
- Must not exceed 500 lines — enough to orient an agent, not a full ops runbook
- No secrets, tokens, or sensitive values — only describe how secrets are managed, never include them
- No code blocks except for ASCII diagrams and exact commands
- Focus on "how does code get from commit to production" not internal implementation
- ASCII diagrams are strongly encouraged for pipeline flows and environment promotion paths
- Omit any section for which there is no evidence in the codebase
- If the project has no CI/CD or pipeline configuration at all, **skip this file entirely** and note its absence in the completion report

---

### Step 6: Confirm completion

After writing all files, report:

```
✓ docs/PROJECT_DETAILS.md — [created | updated]
✓ docs/ARCHITECTURE.md — [created | updated]
✓ docs/PIPELINE.md — [created | updated | skipped (no pipeline config found)]

These files are automatically loaded by agents at the start of each session
via the directive in AGENTS.global.md.
```

If any file could not be written, report the error and reason.

---

## Keeping Docs Up to Date

Run this skill again whenever:
- Major new dependencies are added
- The project structure significantly changes
- A new architectural layer or pattern is introduced
- CI/CD pipelines, deployment strategies, or environment configurations change
- A new package/module is added to the project (use package mode for the new package)
- Onboarding a new developer or agent to the project

These files should reflect the **current state of the codebase**, not aspirational design.
