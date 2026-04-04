---
name: code
description: >
  Apply coding guidelines when writing, modifying, or refactoring code. Thin delegator
  that invokes the coding-guidelines skill (with its tech-specific extensions). Use when
  the user says "code", "apply coding guidelines", "follow coding guidelines", or
  "coding standards". Do NOT use for code review — use code-review for that.
metadata:
  version: "1.0.0"
  triggers:
    - "apply coding guidelines"
    - "code"
    - "coding standards"
    - "follow coding guidelines"
  alias_for: coding-guidelines
---

# Code

Delegates to **coding-guidelines**. Provides a short `/code` command pairing with `/code-review`, mirroring the `/tests` + `/tests-code-review` pattern.

## Behavior

Immediately invoke the `coding-guidelines` skill using the Skill tool. Pass through any user context or arguments unchanged.

The `coding-guidelines` skill (and its extended version if present) handles all logic: behavioral guidelines, tech-specific style guides, SOLID principles, and stack detection.

Do NOT add logic here — this is a passthrough.