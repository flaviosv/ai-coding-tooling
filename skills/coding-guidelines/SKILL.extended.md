# coding-guidelines — Project Extension

This file extends the global `coding-guidelines` skill with project-specific rules.
It is automatically loaded alongside the base skill when present.

---

## SOLID Principles

Always load `reference/solid-guidelines.md` when writing or reviewing OOP-style code.
Apply its rules proactively — treat SOLID violations as design defects, not style suggestions.

Key checkpoints before completing any implementation task:

1. **SRP**: Can you describe each new class/module in one sentence without "and"?
2. **OCP**: Will adding the next variant require editing stable existing code?
3. **LSP**: If subclassing, does the subclass honor the parent's full contract?
4. **ISP**: Does the caller depend only on methods it actually uses?
5. **DIP**: Is every volatile dependency (DB, HTTP, file system) injected rather than instantiated?
