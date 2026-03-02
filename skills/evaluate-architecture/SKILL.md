---
name: evaluate-architecture
description: >
  Creates or updates the two mandatory project context files: PROJECT_DETAILS.md and ARCHITECTURE.md. These files are auto-loaded by agents at the start of every session to provide project context. Use when setting up a new project, onboarding a project, or when the user says "update architecture docs", "refresh project context", "run evaluate-architecture", or "update project docs".
metadata:
  version: "1.0.0"
  triggers:
    - "initial architecture"
    - "update architecture docs"
    - "refresh project context"
    - "setup project docs"
    - "run evaluate-architecture"
    - "update project docs"
    - "create project docs"
---

# evaluate-architecture

Creates or updates the two mandatory project context files that agents load at the start of every session. These files give the agent just enough context to work effectively without bloating the context window.

## Output Files

| File | Purpose |
|------|---------|
| `PROJECT_DETAILS.md` | Tech stack, project description, key libraries, environment config |
| `ARCHITECTURE.md` | Concise architectural overview — layers, data flow, key components |

Default location: `.agents/` at the project root (e.g. `.agents/PROJECT_DETAILS.md`).

> If the user specifies a different location (e.g. `docs/`), use that instead.

---

## Instructions

### Step 0: Confirm file location

If the user did not specify where to put the files, default to `.agents/`. If `.agents/` does not exist, create it.

Check whether each file already exists:
```bash
ls .agents/PROJECT_DETAILS.md .agents/ARCHITECTURE.md 2>/dev/null
```

If any files exist, inform the user:
> Found existing files: [list]. These will be **updated**, not replaced from scratch — existing content will be preserved and refined.

### Step 1: Explore the codebase

Use Glob and Read to gather context. Investigate in this order:

**Tech stack detection:**
- Look for `package.json`, `pyproject.toml`, `requirements.txt`, `Gemfile`, `go.mod`, `Cargo.toml`, `composer.json`
- Look for `Dockerfile`, `docker-compose.yml` for infrastructure
- Look for `.env.example`, `.env.sample`, or `README.md` for environment config
- Look for CI config: `.github/workflows/`, `.gitlab-ci.yml`, `Makefile`

**Project structure:**
- Read the top-level directory tree (one level deep)
- Identify main source directories (e.g. `src/`, `app/`, `lib/`, `packages/`)
- Identify test directories

**Architecture:**
- Look for existing architecture documentation
- Read entry point files (e.g. `main.py`, `index.ts`, `app.py`, `server.ts`)
- Identify layers: API, services, data access, background jobs, etc.
- Identify external integrations: databases, queues, third-party APIs

**Do not over-read.** 10–15 files is usually enough to produce accurate documentation. Prioritize breadth (get the shape of the project) over depth.

---

> **Formatting:** When writing or updating any of the output files, use the **docs-writer** skill to ensure consistent formatting, style, and link integrity across all documentation.

### Step 2: Write PROJECT_DETAILS.md

Create or update `.agents/PROJECT_DETAILS.md` (or the user-specified path).

The file must include:

```markdown
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
| CI/CD | ... |

## Key Libraries
| Library | Purpose |
|---------|---------|
| ... | ... |

## Project Structure
```
<top-level directory tree with brief annotations>
```

## Environment Configuration
Key environment variables (from .env.example or similar):
- `VAR_NAME` — description

## External Integrations
- [Integration name]: [what it's used for]
```

**Principles:**
- Keep it factual and scannable
- No prose paragraphs — use tables and bullet lists
- Only include what was actually found in the codebase; do not invent

---

### Step 3: Write ARCHITECTURE.md

Create or update `.agents/ARCHITECTURE.md`.

The file must include:

```markdown
# Architecture

## Overview
[2–3 sentences: what the system does, its primary architectural style (e.g. monolith, microservices, event-driven)]

## Layers
| Layer | Responsibility | Key Files/Dirs |
|-------|---------------|----------------|
| ... | ... | ... |

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

## Key Components
| Component | Role |
|-----------|------|
| ... | ... |

## External Dependencies
| Service | How Used |
|---------|---------|
| PostgreSQL | Primary data store |
| Redis | Session cache + job queue |
| S3 | File storage |

## Background Jobs
[If applicable: list job types and their triggers]

## Notable Patterns
- [Pattern 1, e.g. "Repository pattern for all DB access"]
- [Pattern 2, e.g. "All external calls wrapped in service classes"]
```

**Principles:**
- Aim for ~50–100 lines total — enough to orient an agent, not a full system design doc
- No implementation details (no method signatures, no SQL queries)
- Focus on "how is the system structured" not "how does X work internally"
- Keep diagrams simple (ASCII only)

---

### Step 4: Confirm completion

After writing all files, report:

```
✓ .agents/PROJECT_DETAILS.md — [created | updated]
✓ .agents/ARCHITECTURE.md — [created | updated]

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
- Onboarding a new developer or agent to the project

These files should reflect the **current state of the codebase**, not aspirational design.
