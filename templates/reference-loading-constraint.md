---
name: reference-loading-constraint
description: Constraint for loading only stack-relevant reference files based on .specs/codebase/STACK.md tech stack detection.
type: template
---

> **CONSTRAINT: Load ONLY stack-relevant references.**
> Detect the tech stack from `.specs/codebase/STACK.md` (fall back to `docs/codebase/PROJECT_DETAILS.md`, then `docs/PROJECT_DETAILS.md`, for projects not yet migrated to `.specs/`). Reference files use the naming convention
> `<tech-prefix>-<purpose>.md`. A file is **tech-specific** if its name starts with a known prefix
> (e.g., `python-`, `django-`, `golang-`, `gin-`). A file is **generic** if it has no tech prefix
> (e.g., `review-checklist.md`, `solid-principles.md`). Load ONLY:
> - Generic files (always)
> - Tech-specific files whose prefix matches the detected stack
>
> **Skip all non-matching tech-specific files.** If the project uses Python + Django, do NOT load
> `golang-code-review.md`, `php-code-review.md`, etc. If `.specs/codebase/STACK.md` (or the legacy `docs/codebase/PROJECT_DETAILS.md` / `docs/PROJECT_DETAILS.md`) is missing or
> has no tech stack section, do NOT load any tech-specific references — load only generic files.
