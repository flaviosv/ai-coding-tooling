---
name: coding-guidelines-extended
extends: coding-guidelines
description: >
  Tech-specific coding style extension for the coding-guidelines skill. This file MUST be read
  together with the parent coding-guidelines SKILL.md. The parent skill defines behavioral
  guidelines; this extension adds stack-specific naming, structure, and idiom rules loaded from
  reference files.
metadata:
  version: "1.0.0"
  parent_skill: coding-guidelines
  source: "ai-coding-tooling (extended/)"
---

# coding-guidelines — Tech-Specific Extension

> This file extends the **coding-guidelines** skill from Tech Leads Club. The parent SKILL.md
> governs behavioral guidelines. This extension adds language and framework-specific style rules.

## How to Use This Extension

Load this file alongside the parent `SKILL.md`. Both must be active simultaneously.

## Reference Files

Load and apply [Reference Loading Constraint](../../templates/reference-loading-constraint.md).

Detect the project's tech stack from `docs/PROJECT_DETAILS.md`. Then check both reference locations and load ONLY matching files:

1. **Parent skill's `reference/` directory** — contains language and framework-specific review checklists (e.g. `golang-code-review.md`, `python-django-code-review.md`). Load ONLY files whose tech prefix matches the detected stack. Skip non-matching files.

2. **This extension's `reference/` directory** — contains language and framework-specific coding style guides (e.g. `go-coding-guidelines.md`, `php-adobe-commerce-coding-guidelines.md`). Load ONLY files whose tech prefix matches the detected stack. Skip non-matching files.

Reference files in both directories follow the naming convention `<language>-<framework>-*.md` or `<language>-*.md`. Load ONLY files that match the detected stack — if the project uses Python + Django, load `python-*` and `django-*` files from both locations. Skip all other tech-specific files.

If no matching reference file exists for the detected stack in either location, STOP immediately and apply [Unsupported Tech Stack Alert](../../templates/unsupported-tech-stack-alert.md).

## Web Design Guidelines

If the code being written or modified contains **HTML or CSS** (including template files, JSX/TSX with className, inline styles, or `.css`/`.scss`/`.less` files), also invoke the `web-design-guidelines` skill alongside this one. Apply its rules to any UI markup or styling changes.

## SOLID Principles

Always load `reference/solid-guidelines.md` from this extension's reference directory when writing or reviewing OOP-style code. Apply its rules proactively — treat SOLID violations as design defects, not style suggestions.

Key checkpoints before completing any implementation task:

1. **SRP**: Can you describe each new class/module in one sentence without "and"?
2. **OCP**: Will adding the next variant require editing stable existing code?
3. **LSP**: If subclassing, does the subclass honor the parent's full contract?
4. **ISP**: Does the caller depend only on methods it actually uses?
5. **DIP**: Is every volatile dependency (DB, HTTP, file system) injected rather than instantiated?
