---
name: docs-writer-extended
extends: docs-writer
description: >
  Token-efficiency extension for the docs-writer skill. This file MUST be read
  together with the parent docs-writer SKILL.md. Adds output rules to keep
  AI-agent-facing .md files lean.
metadata:
  version: "1.0.0"
  parent_skill: docs-writer
  source: "ai-coding-tooling (extended/)"
---

# docs-writer — Token Efficiency Extension

> This file extends the **docs-writer** skill. The parent SKILL.md governs core documentation behavior. This extension adds output efficiency rules.

## Output Rules

When generating or editing any `.md` file intended for AI agent consumption, follow [Token Efficiency Rules](../../templates/token-efficiency-rules.md).

Apply these rules to all generated content: reference files, SKILL.md files, docs/ files, and any other agent-facing documentation.
