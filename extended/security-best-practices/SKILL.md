---
name: security-best-practices-extended
extends: security-best-practices
description: >
  Tech-specific extension for the security-best-practices skill. This file MUST be read together
  with the parent security-best-practices SKILL.md. The parent skill defines the core workflow;
  this extension adds stack-specific security guidance loaded from reference files.
metadata:
  version: "1.0.0"
  parent_skill: security-best-practices
  source: "ai-coding-tooling (extended/)"
---

# security-best-practices — Tech-Specific Extension

> This file extends the **security-best-practices** skill. The parent SKILL.md governs the
> overall workflow (generation mode, passive review, active audit, report format, fixes).
> This extension adds framework-specific security reference files.

## How to Use This Extension

This file is always loaded together with the parent `SKILL.md`. Both must be active simultaneously.

## Reference Files

> **CONSTRAINT: Load ONLY stack-relevant references.**
> Reference files use `<tech-prefix>-<purpose>.md` naming. A file is tech-specific if its name
> starts with a known prefix (e.g., `python-`, `golang-`, `gin-`). Skip all non-matching
> tech-specific files. If `docs/PROJECT_DETAILS.md` is missing or has no Tech Stack section,
> do NOT load any tech-specific references — rely solely on the parent skill's built-in guidance.

Detect the project's tech stack from `docs/PROJECT_DETAILS.md`. Then check both reference
locations and load ONLY matching files:

1. **Parent skill's `references/` directory** — contains language and framework-specific security
   specs (e.g. `golang-general-backend-security.md`, `python-django-web-server-security.md`).
   Load ONLY files whose name matches the detected stack. Skip non-matching. The naming convention is
   `<language>-<framework>-<stack>-security.md` or `<language>-general-<stack>-security.md`.

2. **This extension's `reference/` directory** — contains additional framework-specific security
   guides (e.g. `gin-security-best-practices.md`). Load ONLY files that match the detected stack.
   Skip non-matching.

When the project uses Go with the Gin framework, load BOTH `golang-general-backend-security.md`
(parent skill) AND `gin-security-best-practices.md` (this extension). The Gin file is additive —
it covers Gin-specific patterns that are not captured in the general Go backend spec.

If no matching reference file exists for the detected stack in either location, rely solely on the
parent skill's built-in guidance.
