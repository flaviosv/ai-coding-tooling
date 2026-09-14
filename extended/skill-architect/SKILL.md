---
name: skill-architect-extended
extends: skill-architect
description: >
  Extension for the skill-architect skill. This file MUST be read together with the parent
  skill-architect SKILL.md. Adds two capabilities: (1) guardrail design guidance injected into
  the existing workflow phases, and (2) the extended/ pattern for modifying globally installed
  skills without touching the source.
metadata:
  version: "1.2.0"
  parent_skill: skill-architect
  source: "ai-coding-tooling (extended/)"
---

# skill-architect — Extension

> This file extends the **skill-architect** skill. The parent SKILL.md governs the full
> DISCOVERY → ARCHITECTURE → CRAFT → VALIDATE → DELIVER workflow. This extension injects
> guardrail design into those phases and adds the `extended/` pattern for global skill modifications.

## Extension 1: Guardrail Design

### Inject into Phase 1 (Discovery) — after 1.2 Define Use Cases, before 1.3 Identify the Category

**1.2a — Guardrail Discovery**

Ask the user one focused question about risk profile:

> "Does this skill take any actions that are hard to reverse or visible outside this session —
> for example: writing or deleting files, running git operations, calling external APIs, sending
> messages, or touching credentials?"

Based on the answer, categorize the skill as:

- **Low risk** — read-only, output is suggestions or text, no side effects
- **Medium risk** — writes files or makes local changes, but reversible
- **High risk** — irreversible actions, external side effects, or touches credentials

Record the risk category, then → start from the 2.2a menu rows whose When to propose condition matches.

### Inject into Phase 2 (Architecture) — after 2.2 Plan the Folder Structure, before 2.3 Design the Description

**2.2a — Design the Guardrail Set**

Based on the risk category from Discovery, propose the appropriate guardrails to the user from
the menu below. Present only the ones relevant to the skill's risk profile — do not dump the
full list for a low-risk skill. Ask the user to confirm or adjust before moving on.

**Guardrail menu:**

| Guardrail | When to propose | What it looks like in the skill |
|-----------|----------------|----------------------------------|
| **Scope guardrails** | Always | Explicit "Do NOT" statements at the top of the skill — e.g. "Do not modify files outside `src/`", "Do not run without user confirmation" |
| **Precondition checks** | Medium + High risk | Conditions that must be true before the skill executes — e.g. tests passing, a required file existing, the user having confirmed intent. Define what the skill does if a precondition fails (stop, warn, ask). |
| **Destructive action gates** | Any irreversible operation | The skill must pause and show a clear summary of what will be changed/deleted and ask for explicit confirmation before proceeding. No silent destructive actions. |
| **Escalation rules** | When ambiguity is possible | Define the threshold at which the agent stops and asks rather than guessing — e.g. "If the target file is ambiguous, ask before writing", "If more than 3 files would be modified, confirm the list first" |
| **Idempotency checks** | Skills that create resources | Check whether the resource (file, section, task, entry) already exists before creating it. Define behavior on collision: skip, merge, overwrite with confirmation, or error. |
| **Secret/credential protection** | Any skill that reads config, env vars, or auth files | Explicit rule: never include credential values in output, never log them, never commit them. If a secret is encountered during execution, reference it by name only. |
| **Output validation** | Skills that generate files or structured output | Minimum quality bar before delivery: required sections present, no placeholder text remaining, output parses correctly if it's a structured format (YAML, JSON, Markdown frontmatter). |

After the user confirms the guardrail set, record each selected guardrail with:
- Its trigger condition (when does it activate?)
- Its behavior (what exactly does the skill do when triggered?)

This becomes the source material for the `## Guardrails` section in Phase 3.

### Inject into Phase 3 (Craft) — add to 3.2 Write the Instructions

**Guardrails section template**

Every skill with a Medium or High risk profile MUST include a `## Guardrails` section in its
`SKILL.md`. Place it near the top, before the workflow steps, so gates are read before any action. Use this format:

```markdown
## Guardrails

### Scope
- [Do NOT statement]
- [Do NOT statement]

### Before Starting
- [Precondition check with failure behavior]

### Before [Destructive Action Name]
Pause. Show the user:
- What will be changed: [list]
- What cannot be undone: [list]
Ask for explicit confirmation before proceeding.

### When to Stop and Ask
- [Ambiguity condition] → ask before proceeding
- [Risk threshold condition] → confirm the scope first

### On Collision
If [resource] already exists: [skip / merge / overwrite with confirmation / error].

### Credentials and Secrets
Never include credential values in output. Reference by name only (e.g. `$API_KEY`, not its value).
```

Omit sections that don't apply.

### Inject into Phase 4 (Validate) — add to 4.3 Instruction Quality Review

**Guardrail testing**

For each guardrail, simulate its failure path (precondition fails, gate declined, escalation triggered, secret encountered, collision) and confirm the skill stops or asks cleanly.

## Extension 3: Token Efficiency

### Inject into Phase 2 (Architecture) — after 2.2 Plan the Folder Structure (following 2.2a), when the skill includes reference files

**2.2b — Reference File Design**

If the skill will include technology-specific reference files:
- Name them `<technology>-<skill-name>.md`, where `<technology>` is the kebab-case slug for the language or framework (e.g. `php`, `go-gin`, `ruby-on-rails`) and `<skill-name>` is the reference folder the skill scans (e.g. `coding-guidelines` in `extended/tlc-spec-driven/references/coding-guidelines/php-coding-guidelines.md`).
- **Exception — scoped variants.** A skill whose references split by scope declares its own naming in its `SKILL.md` and uses `<name>.<scope>.md` instead (e.g. `code-review`: `php.code.md`, `review-checklist.tests.md`). Follow the skill's declaration over the default pattern.
- Generic baseline files (non-tech-specific) are exempt from the `<technology>` prefix (e.g. `code-review`'s `review-checklist.code.md`).

**Keep links inside the skill** — a skill links only files within its own directory (its `references/`, `scripts/`, or `../SKILL.md` from a reference file). It never links, loads, or defers its instructions to anything outside that directory — not `CLAUDE.md`, `CLAUDE.global.md`, the repo's `references/`, `docs/`, or another skill's files — and naming an outside file as the source of a rule counts as depending on it: state the rule inline instead. Files the skill works *on* as its subject (reading or writing a target project's `CLAUDE.md` or `docs/codebase/`, reviewing a PR) are not dependencies.

### Inject into Phase 3 (Craft) — add to 3.2 Write the Instructions

**Output rules for reference files** (any file under `references/`):

- No `## Resources` or `## References` section — agents do not browse links
- One `---` only — immediately after the scope line (first 1–2 sentence paragraph); none elsewhere
- "Bad" examples: keep signature + problematic line(s) only; remove surrounding scaffolding
- Max 1 consecutive blank line; no blank lines inside code blocks
- Never write filler phrases: "It is important to note", "In order to", "As a general rule"
- Preserve WHY context, disambiguation, and edge-case prose — this is the most valuable content

**Output rules for SKILL.md files:**

- No `---` between sections — only the frontmatter closing `---` is kept
- Do not restate the frontmatter `description` in the skill body
- Step introductions lead with the action, not with context ("Check whether…" not "Before checking…")
- No filler phrases in any directive

### Inject into Phase 4 (Validate) — add to 4.3 Instruction Quality Review

**Token efficiency check**

Before delivering any generated file, re-check it against the Phase 3.2 output rules above (reference files and SKILL.md).
