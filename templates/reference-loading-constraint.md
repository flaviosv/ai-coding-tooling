---
name: reference-loading-constraint
description: Constraint for loading only stack-relevant reference files based on docs/PROJECT_DETAILS.md tech stack detection.
type: template
---

> **CONSTRAINT: Load ONLY stack-relevant references.**
> Detect the tech stack from `docs/PROJECT_DETAILS.md`. Reference files use the naming convention
> `<tech-prefix>-<purpose>.md`. A file is **tech-specific** if its name starts with a known prefix
> (e.g., `python-`, `django-`, `golang-`, `gin-`). A file is **generic** if it has no tech prefix
> (e.g., `review-checklist.md`, `solid-principles.md`). Load ONLY:
> - Generic files (always)
> - Tech-specific files whose prefix matches the detected stack
>
> **Skip all non-matching tech-specific files.** If the project uses Python + Django, do NOT load
> `golang-code-review.md`, `php-code-review.md`, etc. If `docs/PROJECT_DETAILS.md` is missing or
> has no Tech Stack section, do NOT load any tech-specific references — load only generic files.
