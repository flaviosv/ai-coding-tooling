# Brownfield Mapping — ai-coding-tooling Augmentation

Read this **after** the parent `references/brownfield-mapping.md`. It augments the parent's
codebase-mapping flow; it does not replace it. The parent produces 7 `.specs/codebase/`
files from its own templates — apply these additions on top of those templates, and add the
new modes/files described here.

All paths are `.specs/codebase/` (parent convention). Everything below that names a
`docs/codebase/` path in its source lineage has been repointed to `.specs/codebase/`.

## Output: 8 Files

Parent generates 7 (`STACK`, `ARCHITECTURE`, `CONVENTIONS`, `STRUCTURE`, `TESTING`,
`INTEGRATIONS`, `CONCERNS`). This overlay adds **`PIPELINE.md`** (8th, CI/CD). Project
**vision/goals** go to `.specs/project/PROJECT.md` (parent `project-init`), not `STACK.md`.

## Three Modes

| Mode | Intent | Triggers |
|------|--------|----------|
| **Full** (parent + this overlay) | Bootstrap / full refresh of codebase docs | "map codebase", "analyze existing code", "evaluate architecture", "onboard project", "create/update project docs" |
| **Incremental** (this overlay, Mode B) | Sync docs to recent workspace changes | "update docs", "document my changes", "sync documentation", "document recent changes", "keep docs in sync" |
| **Package** (this overlay, Mode C) | Scoped `CLAUDE.md` for one package | "evaluate package", "package architecture" |

> Activation note: the Incremental/Package trigger phrases are routed to this skill by the
> session-level directive in `AGENTS.global.md`. When invoked that way, run the matching mode
> below. Full mode = the parent mapping flow plus the per-file augmentations and `PIPELINE.md`.

---

## Per-File Augmentations (Full mode)

For each parent file, add the sections below **to** the parent's template — the overlay augments,
never replaces. Each file is documented the same way the parent documents its files: a **Document
(overlay additions)** block (the file-structure example, showing only what this overlay adds)
followed by **Instructions**. Heading markers: **`<!-- AUG -->`** = extends an existing parent
section (shown as a `[+ …]` delta); **`<!-- NEW -->`** = a section the parent template lacks (shown
in full). Every added section is **conditional** — include only with codebase evidence — and the
parent's per-file token budgets still apply.

### STACK.md

**Document (overlay additions):**

```markdown
## Core   <!-- AUG -->

- Minimum versions: [runtime/language constraints, e.g. Node >= 18, Python >= 3.11]

## Key Libraries   <!-- NEW -->

| Library | Version  | Purpose | Modern Usage           |
| ------- | -------- | ------- | ---------------------- |
| [name]  | [pinned] | [role]  | [idiomatic modern API] |

## Commands   <!-- NEW -->

| Task                                        | Command   |
| ------------------------------------------- | --------- |
| [setup/build/test/lint/deploy/migrate/seed] | [command] |

## Local Development Setup   <!-- NEW -->

[Services to run (docker compose profile, local DB), seed/fixture data, how to mock/stub external services, ports and URLs]

## Environment Configuration   <!-- NEW -->

| Variable   | Description |
| ---------- | ----------- |
| [VAR_NAME] | [purpose]   |
```

**Instructions:**

- **Core (AUG):** minimum runtime/language version constraints — agents must respect these.
- **Key Libraries:** extract exact pinned versions from the manifest; for each, use Context7 (`mcp__context7__*`) or web search to identify the idiomatic modern APIs for that version (e.g. "React Query v5 → `useQuery`", "SQLAlchemy 2.x → `select()`"); flag significantly outdated pins.
- **Commands:** test/gate commands also feed `TESTING.md` Gate Check Commands.
- **Environment Configuration:** variable **names only, never values.**

### ARCHITECTURE.md

**Document (overlay additions):**

```markdown
## Overview / Pattern   <!-- AUG -->

[+ primary architectural style: monolith / microservices / event-driven]

## Layers   <!-- AUG -->

| Layer   | Responsibility | Key Files or Dirs |
| ------- | -------------- | ----------------- |
| [layer] | [role]         | [paths]           |

## Dependency Rules   <!-- NEW -->

[Who can import whom, who can't — e.g. "services never import controllers"]

## Communication Patterns   <!-- NEW -->

[How services/modules communicate: REST, events, queues, gRPC]

## Data Model   <!-- NEW -->

[Key entities and relationships — conceptual map, not full schema]

## Database Access Patterns   <!-- NEW -->

[Access pattern (repository, active record, query builder, raw), connection pooling, read replicas, migrations framework]

## State Management   <!-- NEW -->

[Stateless (JWT) / server sessions / distributed cache / event sourcing; where state lives, how it's shared across instances]

## Error Handling Strategy   <!-- NEW -->

[System-level: where errors are caught, where they propagate, error format]

## Auth Strategy   <!-- NEW -->

[Middleware, guards, where the logic lives]

## Observability   <!-- NEW -->

[Logging framework/conventions (structured, levels), tracing (OpenTelemetry/APM), metrics, correlation IDs; how agents should instrument new code]

## API Versioning   <!-- NEW -->

[URL path /v1/ / headers / query / none; deprecation policy; version coexistence]

## Feature Flag System   <!-- NEW -->

[Provider (LaunchDarkly, Unleash, env-based, DB-based), runtime evaluation, where definitions live, how agents gate new features]

## Notable Patterns   <!-- AUG -->

[+ repository pattern, service wrappers, decorators, etc.]
```

**Instructions:**

- **Error Handling Strategy:** code-level conventions go in `CONVENTIONS.md`, not here.
- **Auth Strategy:** the auth *library* name stays in `STACK.md`.
- **External Dependencies:** keep **infrastructure** deps (DBs, caches, queues) here; route **business integrations** (ERPs, payment, CRM, third-party APIs) to `INTEGRATIONS.md` with data-flow direction and integration pattern.
- `Testing Strategy` and `Background Jobs` are single-sourced in `TESTING.md` and `INTEGRATIONS.md` respectively.

### CONVENTIONS.md

**Document (overlay additions):**

```markdown
## Naming Conventions   <!-- AUG -->

[+ rows for database tables, routes, and branches (parent covers files/functions/variables/constants)]

## Error Handling   <!-- AUG -->

[Code-level pattern — how errors are raised/wrapped in code]

## Documentation Pattern   <!-- NEW -->

[How docs are organized: Swagger/OpenAPI, JSDoc/PHPDoc, guides]
```

**Instructions:**

- **Error Handling (AUG):** system-level propagation goes in `ARCHITECTURE.md`, not here.

### STRUCTURE.md

**Document (overlay additions):**

```markdown
## Directory Tree   <!-- AUG -->

[Parent covers this — no overlay delta]

## Monorepo Package Map   <!-- NEW -->

| Package   | Path   | Responsibility |
| --------- | ------ | -------------- |
| [package] | [path] | [role]         |
```

**Instructions:**

- **Monorepo Package Map:** include only if the project is a monorepo.

### TESTING.md

**Document (overlay additions):**

```markdown
## Testing Patterns   <!-- AUG -->

[+ test types/frameworks/patterns, e.g. "Jest + Supertest for integration, no DB mocking"]
```

**Instructions:**

- Parent already covers the coverage matrix, parallelism, and gate-check commands — keep those.

### INTEGRATIONS.md

**Document (overlay additions):**

```markdown
## [Service Category] / API Integrations   <!-- AUG -->

[Per integration: type (ERP, payment, CRM, email/SMS, auth, cloud, third-party API), purpose, data-flow direction (inbound/outbound/both), protocol (REST/SOAP/webhooks/SDK), auth method]

## Webhooks   <!-- AUG -->

[Endpoints both consumed and exposed]

## Background Jobs   <!-- AUG -->

| Job   | Frequency   | Purpose |
| ----- | ----------- | ------- |
| [job] | [frequency] | [role]  |
```

**Instructions:**

- **Background Jobs:** single source of truth for jobs/crons.

### CONCERNS.md

**Document (overlay additions):**

```markdown
## Tech Debt   <!-- AUG -->

[Known limitations / tech debt observed in code]
```

**Instructions:**

- **Coexists with `docs/TECH_DEBTS.md`** — reference a tracked `TD-XX` rather than restating it (see `SKILL.extended.md`).

---

## PIPELINE.md (8th file — Full mode)

**Purpose:** Document how code gets from commit to production. `.specs/codebase/PIPELINE.md`.

**Size limit:** 3,000 tokens (~1,800 words)

**Extract from:**

- CI config: `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml`, `azure-pipelines.yml`, `.buildkite/`
- Deploy/infra: `deploy/`, `k8s/`, `helm/`, `terraform/`, `cdk/`, `pulumi/`, `serverless.yml`, `fly.toml`, `vercel.json`, `netlify.toml`
- Release: `.releaserc`, `release.config.js`, `.changeset/`
- Data pipelines: `dags/`, `pipelines/` (Airflow, dbt, Spark)

**Document:**

```markdown
# CI/CD Pipeline

## Overview

[CI/CD platform + pipeline philosophy — trunk-based / GitFlow / monorepo-aware, 1–2 sentences]

## CI/CD Platform

| Platform | Config Location | Runner Type          |
| -------- | --------------- | -------------------- |
| [name]   | [path]          | [hosted/self-hosted] |

## Pipeline Stages

[Pipeline flow diagram — Mermaid via `mermaid-studio`, ASCII fallback]

| Stage   | Purpose        | Trigger        |
| ------- | -------------- | -------------- |
| [stage] | [what it does] | [when it runs] |

## Trigger Rules

| Event                         | Pipeline   | Conditions            |
| ----------------------------- | ---------- | --------------------- |
| [push/PR/tag/schedule/manual] | [pipeline] | [branch/path filters] |

## Environment Matrix

[Promotion flow — Mermaid via `mermaid-studio`, ASCII fallback — e.g. dev → staging → prod]

| Environment | Purpose | Promotion Method       |
| ----------- | ------- | ---------------------- |
| [env]       | [use]   | [auto/manual/approval] |

## Quality Gates

[Required checks, coverage thresholds, approvals before merge/deploy]

## Build Artifacts

| Artifact | Format | Storage           |
| -------- | ------ | ----------------- |
| [name]   | [type] | [registry/bucket] |

## Deployment Strategy

[Strategy (blue/green, rolling, canary), tooling, rollback procedure]

## Secrets Management

[How secrets are injected — vault / CI env vars / sealed secrets. Names and mechanisms only, never values.]

## Infrastructure as Code

| Tool   | Scope                |
| ------ | -------------------- |
| [tool] | [what it provisions] |

## Monitoring & Alerting

[Deploy notifications, failure alerts, post-deploy health checks]

## Data Pipelines

| Pipeline | Type                  | Schedule | Purpose   |
| -------- | --------------------- | -------- | --------- |
| [name]   | [ETL/streaming/batch] | [cron]   | [purpose] |

## Release Management

[Versioning scheme (semver/calver/commit-based), changelog generation, how tags are cut, release-notes process]

## Notable Patterns

[Matrix builds, reusable workflow templates, etc.]
```

**Instructions:**

- **If no CI/CD or pipeline configuration exists, skip this file entirely** and note its absence in the report.
- Focus on "how code gets from commit to production" — not internal application implementation.
- No secrets/tokens/values — only describe how secrets are managed.
- Include only sections with evidence; omit sections with no findings.
- CI/CD specifics live in this file only; other `.specs/codebase/` files may reference but not duplicate them.

---

## Reconcile Manually-Added Docs (Full + Incremental Sync)

The canonical set is 8 files, but the **folder is the source of truth** — never regenerate or sync
only the fixed list while ignoring what's actually on disk. In **Full mode** (after generating/
refreshing the 8) and in **Incremental sync** (Mode B's holistic sweep, B6), glob the whole
`.specs/codebase/` tree and reconcile anything extra:

```bash
find .specs/codebase/ -name '*.md' -type f 2>/dev/null
```

For each `.md` **not** in the canonical 8 (e.g. a hand-added `SECURITY.md`, or nested docs under
`.specs/codebase/adr/`), do **not** silently overwrite or drop it. Investigate it against the current
code; if it's impacted or stale, flag it and offer to refresh it — "Found `SECURITY.md` outside the
standard set — refresh it too?". Hand-authored docs are preserved unless the user opts in. **Package
mode** applies the same rule to its target package dir (see PM2).

---

## Mode B — Incremental Sync

Brings docs in sync with the **current state of the workspace** — inline API docs, root context
files, and the `.specs/codebase/` set. Updates only what changed in the git diff and detects new
packages (handing off to Package mode internally). Triggers: "update docs", "document my
changes", "sync documentation", "document recent changes", "keep docs in sync".

**Holistic Updates:** an "update" is never scoped to one file. After determining what changed,
open **every** file in `.specs/codebase/` and update each whose purpose is touched by the change.

**If the codebase docs are absent from `.specs/codebase/`:** if they exist under legacy
`docs/codebase/` (or `docs/`), suggest migrating to `.specs/codebase/` first; if they exist
nowhere, suggest Full mode first — there's no baseline to sync against.

### B1 — Identify modified files
```bash
git diff --name-only HEAD                      # staged + unstaged vs HEAD
git ls-files --others --exclude-standard        # untracked new files
```
Group into source files (may carry inline API docs) and documentation files. If nothing changed, inform the user and stop.

### B2 — Detect new packages
```bash
git diff HEAD --name-only --diff-filter=A
git ls-files --others --exclude-standard
```
Extract unique parent dirs from new files; a dir is "newly created" if ALL its files are new.
Decide whether a new dir is a package using project context — read `.specs/codebase/STACK.md`
and `ARCHITECTURE.md` (fall back to `docs/codebase/` then `docs/`), compare against sibling
packages, and apply stack-aware reasoning (Go: dir of `.go` under a `go.mod`; Django: app dir
with `models.py`/`views.py`; Magento: `registration.php` + `etc/module.xml`; Node monorepo: dir
under `packages/`/`apps/` with its own `package.json`; PSR-4 namespaces). When uncertain, ask:
"I found new directories: `<list>`. Are any new packages that should get their own `CLAUDE.md`?"

### B3 — Scaffold new package context
**Always confirm before scaffolding** (detection has false positives). For each candidate, ask
"I detected what looks like a new package: `<path>`. Generate a `CLAUDE.md` for it?" If yes,
**switch to Package mode internally** for that path. If multiple candidates, present all at once.
A confirmed new package is a structural change → afterward, suggest a Full-mode re-evaluation.

### B4 — Update inline API documentation
For each modified source file: read it, check public/exported symbols for missing/outdated docs,
update inline docs directly. Only touch symbols that changed or are undocumented public exports;
preserve the file's existing doc style; do **not** refactor or modify code, only comments/annotations.

### B5 — Review root context files
Check if present and impacted: `README.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, other root
`.md`. Read each, decide if any section is affected, mark impacted/not. If `CLAUDE.md`/`GEMINI.md`
are symlinks to `AGENTS.md`, update only `AGENTS.md`.

### B6 — Holistic sweep of `.specs/codebase/`
```bash
find .specs/codebase/ -name '*.md' -type f 2>/dev/null
```
Read **every** file — the whole tree, not just the top level, so nested and manually-added docs are
covered — compare against the change, mark impacted ones. Files beyond the canonical 8 are handled
per **Reconcile Manually-Added Docs** above: investigate them as input, don't ignore them, and
flag/offer before refreshing rather than silently rewriting. Do **not** modify
`docs/TECH_DEBTS.md`, `.specs/project/*`, `.specs/features/*`, or other out-of-scope areas.

### B7 — Apply updates via docs-writer
For each impacted `.md` (plus any new-package `CLAUDE.md` from B3), delegate the write to the
`docs-writer` skill with the target path, a summary of what changed, and the sections to revise.

### B8 — Verify and report
Confirm: modified source files have updated inline docs; new packages have a `CLAUDE.md`; root
files reviewed; every `.specs/codebase/` file opened and impacted ones updated; all `.md` writes
delegated to docs-writer. Report created/updated/unchanged files and flag anything ambiguous.

---

## Mode C — Package

Triggered with a specific package path ("evaluate package", "package architecture") or
**internally by Mode B** when a new package is confirmed. Produces a **single `CLAUDE.md` inside
the package directory** — not the `.specs/codebase/` set — scoped to the package but deeper than
project level (internal structure, public API surface, dependency graph, integration points).

**Scope:** analyze only files within the package dir; do **not** create
`STACK/ARCHITECTURE/...` files. Same quality bar (factual, scannable, no code snippets unless
necessary, diagrams encouraged — Mermaid via `mermaid-studio`, ASCII fallback).

### PM1 — Validate package path
Confirm the path exists and looks like a package for the stack (load `.specs/codebase/STACK.md`
and `ARCHITECTURE.md` for module conventions, fall back to `docs/codebase/` then `docs/`). Reason
from actual structure. If not a meaningful package boundary, inform the caller and stop.

### PM2 — Explore the package
Read manifest/entry-point metadata; list the dir tree (2–3 levels); read entry points, main
sources, key modules (cap 15–20 files); identify the public API surface and internal patterns.
**The package dir is the source of truth here:** glob it for any manually-added docs
(`find <package-path> -name '*.md' -type f` — READMEs, NOTES, ADRs, an existing `CLAUDE.md`) and
investigate them as input. Preserve hand-authored docs — never overwrite or delete them; fold their
content into the merge (PM4) and flag, don't clobber.

### PM3 — Analyze integration points
How the package relates to the parent project; which other packages import it (`grep` for imports
of this path); what it imports from the project; the boundary interfaces with consumers.

### PM4 — Write `<package-path>/CLAUDE.md` (via docs-writer)
Up to 500 lines; depth the package warrants. Same Update Merge Strategy. Sections (conditional):
Purpose, Architecture, Key Components, Public API, Internal Design, Data Model, Dependencies
(Internal), Dependencies (External), Integration Points, Error Handling, Constraints, Conventions,
Testing Strategy.

### PM5 — Report
Report the created/updated `CLAUDE.md`, its sections, and line count. A new package is a
structural change → suggest a Full-mode re-evaluation of `.specs/codebase/`.

---

## Guardrails (all modes)

- **The folder is the source of truth.** Every mode treats the actual contents of its target
  directory as authoritative — `.specs/codebase/` for Full and Incremental sync, the package dir for
  Package mode. Sweep the real directory and **preserve and consider every `.md` present**, including
  files added by hand beyond the canonical 8 and any nested under subfolders. Never regenerate or
  sync only the fixed list while ignoring what's on disk.
- **Default write location is `.specs/codebase/`.** Create it if missing. (Package mode writes a
  `CLAUDE.md` inside the target package dir instead.)
- **Reading existing context for input:** check `.specs/codebase/<file>` first, then
  `docs/codebase/<file>`, then legacy `docs/<file>`. The skill only *writes* to `.specs/codebase/`
  (or the package dir); the fallback applies to reads. If old structure is found, suggest migrating
  to `.specs/codebase/`.
- **Token/line budgets** per the parent templates (and ~3k for `PIPELINE.md`); summarize
  aggressively — tables over paragraphs, bullets over tables, omission over filler. Follow
  [Token Efficiency Rules](../../templates/token-efficiency-rules.md).
- **No code samples** unless strictly necessary — prose, tables, bullets; code blocks only for
  directory trees, diagrams, and exact runnable commands.
- **CI/CD belongs in `PIPELINE.md` only.** Other files may reference it but not contain specifics.
- **Factual only** — document what exists; never invent or speculate; omit sections without evidence.
- **Never write secret values** anywhere — reference secrets by name and how they're managed.
- **Re-evaluate on structural change** — new layer, moved/renamed top-level dirs, new package →
  suggest regenerating the whole `.specs/codebase/` set via Full mode.
- **Delegate every `.md` write to the `docs-writer` skill** — no exceptions.
- **Diagrams:** author every diagram (data flows, layer relationships, component interactions,
  pipeline stages) in **Mermaid** and render it via the `mermaid-studio` skill. Only fall back to
  inline ASCII when `mermaid-studio` is unavailable.
