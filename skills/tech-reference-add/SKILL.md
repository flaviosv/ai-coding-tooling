---
name: tech-reference-add
description: >
  Capture project-specific, opinionated insights about a technology into skill reference files. Skills
  load these files at invocation time if they exist. Use when the user says "save this insight",
  "add this to the [tech] reference", "remember this [tech] pattern", "capture this convention",
  or "log this for [tech]". Do NOT use to generate generic best practices from public documentation.
metadata:
  version: "3.0.0"
  triggers:
    - "save this insight"
    - "add this to the [tech] reference"
    - "remember this [tech] pattern"
    - "capture this convention"
    - "log this for [tech]"
---

# Tech Reference Add

Append a project-specific insight about a technology into skill reference files. Skills scan for `{tech}-{skill}.md` files in their `references/` directories at invocation time and load them if present — same file structure and naming convention as always. What changes is only the source of content: session observations, not generated best practices.

## Guardrails

### Scope
- Do NOT write outside `skills/` or `extended/` directories.
- Do NOT include sensitive information — no credentials, tokens, keys, or connection strings. Use placeholder names only (e.g. `$API_KEY`).

### Public Knowledge Check
After extracting the insight, evaluate whether it's general public knowledge available in official documentation. If it is, do NOT reject — instead warn the user:

> "This may already be covered by my training data without needing a reference file. Want to save it anyway?"

Wait for the answer. If yes, continue. If no, stop.

### Before Writing
Show the formatted insight and target file list. Get explicit confirmation before writing.

### On Duplication
Before appending, scan the target file for semantically equivalent rules. If found, show both and ask: **replace / merge / keep both / skip**.

## Step 1: Extract the Insight

Parse from the user's message:
- **Tech** — e.g. `Django`, `Go`. Ask if ambiguous.
- **Insight** — the rule, pattern, or convention. If too vague to write a precise rule, ask for clarification.
- **Code snippet** — if the insight references specific syntax and no example was provided, ask whether one would help. Omit if purely conceptual.

Ask clarifying questions before proceeding if any of the above is unclear.

## Step 2: Public Knowledge Check

Evaluate whether the insight is general public knowledge. If yes:

> "This may already be covered by my training data without needing a reference file. Want to save it anyway?"

If no, continue directly to Step 3.

## Step 3: Discover Reference-Enabled Skills

Scan `skills/` and `extended/` for directories containing a `references/` or `reference/` folder. For each, read its `SKILL.md` description to understand the workflow it supports.

## Step 4: Infer Relevant Skills

For each reference-enabled skill, reason semantically: **"Does this insight affect the workflow this skill performs?"**

Reasoning examples:
- Naming convention → `coding-guidelines`, `code-review`; not `performance-review`
- Query optimization → `performance-review`, `code-review`; likely `coding-guidelines`
- Test fixture pattern → `tests`, `tests-code-review`; not `coding-guidelines`
- Security input handling → `security-best-practices`, `code-review`; not `tests`

Do not hardcode skill relationships — infer from each skill's SKILL.md description. When an insight is cross-cutting, include all skills where it would surface. If a skill's relevance is uncertain, include it in the proposal marked with `(?)` and let the user decide.

## Step 5: Propose and Confirm

Present:

| Skill | Target File | Action | Rationale |
|-------|-------------|--------|-----------|
| code-review | `skills/code-review/references/django-code-review.md` | Append | Affects review correctness |
| coding-guidelines | `extended/coding-guidelines/reference/django-coding-guidelines.md` | Create + append | Style convention |
| performance-review | `skills/performance-review/references/django-performance-review.md` | Append (?) | May surface during perf review — confirm |

Ask: **"Confirm saving to these files? Remove any you don't want or adjust the list."**

Do not write until the user confirms.

## Step 6: Write

For each confirmed target file:

**If the file does not exist**, create it with this header:

```markdown
# {Tech} — {skill-name} insights

Project-specific patterns and conventions.

---
```

**Append the insight** as the next numbered item:

```
{N}. {Rule} — {brief why, if non-obvious}
```

If a code snippet applies, add it immediately after the rule line:

```{lang}
// Good
{minimal example — signature + key line(s) only}

// Bad
{minimal example — signature + problematic line(s) only}
```

Use `// Good` / `// Bad` markers only when contrast aids understanding. Omit the code block if the rule is purely conceptual.

## Step 7: Report

```
## tech-reference-add: insight saved

Tech: {tech}
Insight: {rule}

Written to
- skills/code-review/references/django-code-review.md (appended, item 3)
- extended/coding-guidelines/reference/django-coding-guidelines.md (created)

Skipped
- performance-review: removed by user
```
