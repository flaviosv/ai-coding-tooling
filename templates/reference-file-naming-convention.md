---
name: reference-file-naming-convention
description: Naming convention for tech-specific reference files using <tech-prefix>-<purpose>.md pattern.
type: template
---

## File Naming Convention

All tech-specific reference files follow the pattern: **`<technology>-<skill-name>.md`**

- `<technology>` is the kebab-case slug for the language or framework (e.g. `fastapi`, `go-gin`, `ruby-on-rails`)
- `<skill-name>` is the exact name of the skill directory (e.g. `code-review`, `tests`, `tests-code-review`)
- Examples: `fastapi-code-review.md`, `go-gin-tests.md`, `ruby-on-rails-tests-code-review.md`

Generic baseline files (non-tech-specific) are exempt from this pattern and keep their existing names (e.g. `review-checklist.md`, `testing-patterns.md`).
