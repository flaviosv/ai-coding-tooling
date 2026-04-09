---
name: extension-frontmatter
description: YAML frontmatter template for extended/ skills with variable placeholders.
type: template
---

## Extension Frontmatter Template

Use this frontmatter when creating a new `extended/<skill-name>/SKILL.md`:

```yaml
---
name: <skill-name>-extended
extends: <skill-name>
description: >
  Extension for the <skill-name> skill. This file MUST be read together with the parent
  <skill-name> SKILL.md. The parent skill defines [what the parent governs]. This extension adds [what this adds].
metadata:
  version: "1.0.0"
  parent_skill: <skill-name>
  source: "ai-coding-tooling (extended/)"
---
```

**Field guidance:**

- `name`: always `<skill-name>-extended` — suffixed with `-extended`
- `extends`: the exact name of the parent skill (matches its frontmatter `name` field)
- `description`: must state that both files must be read together, what the parent governs, and what this extension adds
- `metadata.version`: start at `"1.0.0"`, increment on meaningful changes
- `metadata.parent_skill`: the parent skill name (same as `extends`)
- `metadata.source`: always `"ai-coding-tooling (extended/)"` for extensions in this repo
