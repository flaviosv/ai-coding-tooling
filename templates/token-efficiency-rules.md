---
name: token-efficiency-rules
description: Rules for generating token-efficient .md content for AI agent consumption. Apply when creating reference files, SKILL.md files, or any agent-facing documentation.
type: template
---

## Token Efficiency Rules

Apply these rules when generating or editing any `.md` file intended for AI agent consumption (reference files, SKILL.md files, docs/ files, and any other agent-facing documentation).

### Remove

- `## Resources` / `## References` URL sections — agents do not browse links; remove them entirely
- `---` horizontal rules between sections — keep only the single `---` after the frontmatter scope line
- Consecutive blank lines — reduce to a single blank line between elements
- Filler phrases: "It is important to note", "In order to", "As a general rule", "Note that", "Please note"
- Obvious boilerplate imports in code examples (e.g. `import os`, `import sys` when they are not the focus)

### Trim (keep structure, shorten content)

- `// Good` / `// Bad` markers — keep the markers, trim explanatory text after ` — ` when the heading already conveys the intent
- "Bad" code examples — keep only the signature and the problematic line(s); remove the surrounding scaffolding
- Version sections with ≤1 code block and <5 prose lines — collapse into the parent section with an inline version annotation (e.g. `# PHP 8.3+`)

### Preserve

- **WHY context** — explanatory prose that explains reasoning, trade-offs, or edge cases. This is the most valuable content for agents.
- **Disambiguation** — any text that prevents an agent from making a wrong choice between two similar patterns
- **Edge cases** — boundary conditions, error scenarios, non-obvious gotchas
- **Examples that demonstrate the pattern** — not every example, but the canonical one per rule
