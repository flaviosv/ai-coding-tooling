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

This file is always loaded together with the parent `SKILL.md`. Both must be active simultaneously.

## Reference Files

Detect the project's tech stack from `.agents/PROJECT_DETAILS.md` (if present) or from the files
being edited. Then check both reference locations and load all matching files:

1. **Parent skill's `reference/` directory** — contains language and framework-specific review
   checklists (e.g. `golang-code-review.md`, `python-django-code-review.md`). Load every
   file whose name matches the detected stack to inform style expectations.

2. **This extension's `reference/` directory** — contains language and framework-specific coding
   style guides (e.g. `go-coding-guidelines.md`, `php-adobe-commerce-coding-guidelines.md`). Load every file
   that matches the detected stack.

Reference files in both directories follow the naming convention `<language>-<framework>-*.md` or
`<language>-*.md`. Load all files that match — if the project uses multiple layers, load every
matching file from both locations.

If no matching reference file exists for the detected stack in either location, STOP immediately before proceeding with any coding task. Output the following alert and wait for the user's response:

---
🚨🔴 **UNSUPPORTED TECH STACK — ACTION REQUIRED** 🔴🚨

> ❌ No tech-specific reference files were found for the detected stack: **[detected stack]**
> Neither the parent skill's `reference/` directory nor this extension's `reference/` directory contains matching guidelines.
>
> **Choose how to proceed:**
> 1. 🛠️ **Add support** — run the `add-tech-reference` skill to generate guidelines for this stack, then retry.
> 2. ⚠️ **Proceed without stack-specific rules** — base behavioral guidelines only will apply. Tech-specific naming, idioms, and patterns will NOT be enforced.
>
> _Reply with **1** or **2** to continue._
---

Do not apply any coding guidelines or make any code changes until the user replies. If they choose option 2, proceed using only the parent skill's behavioral guidelines and note at the top of your response that no stack-specific rules are in effect.

## SOLID Principles

Always load `reference/solid-guidelines.md` from this extension's reference directory when writing or reviewing OOP-style code. Apply its rules proactively — treat SOLID violations as design defects, not style suggestions.

Key checkpoints before completing any implementation task:

1. **SRP**: Can you describe each new class/module in one sentence without "and"?
2. **OCP**: Will adding the next variant require editing stable existing code?
3. **LSP**: If subclassing, does the subclass honor the parent's full contract?
4. **ISP**: Does the caller depend only on methods it actually uses?
5. **DIP**: Is every volatile dependency (DB, HTTP, file system) injected rather than instantiated?
