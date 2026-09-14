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

## Extension 2: The `extended/` Pattern for Global Skills

Inject the following into the parent skill's **Important Boundaries** section.

### Modifying a Globally Installed Skill

When a user asks to modify, update, or extend a skill that is globally installed (i.e. lives in
`~/.claude/skills/` and is sourced from Tech Leads Club or another external registry), **never
edit the global file directly**. Instead, use the `extended/` pattern:

**When to use this pattern:**
- User wants to add behavior to an existing global skill
- User wants to override specific instructions in a global skill
- User wants to add tech-specific references to a global skill

**How it works:**

1. Create `extended/<skill-name>/SKILL.md` in the project repository.
2. Use `extends: <skill-name>` in the frontmatter — this signals the relationship to the parent.
3. The extension file is loaded **alongside** the parent SKILL.md, not instead of it. Write it additively: only add or clarify, don't repeat what the parent already says.
4. Run `fs-harness override <skill-name>` to scaffold and link the overlay into `~/.claude/skills/<skill-name>/SKILL.extended.md` (only needed the first time a new `extended/<skill-name>/` directory is created). If its exact syntax or flags are unclear, run `fs-harness help` and read the `override` entry — the CLI's own source of truth, so it can't drift out of sync with the tool the way a linked doc file could.
5. Update `AGENTS.md` to annotate the parent skill entry with `— **Extended**: if \`extended/<skill-name>/SKILL.md\` exists, load it alongside the parent skill.`

**Frontmatter template for an extension:**

```yaml
---
name: <skill-name>-extended
extends: <skill-name>
description: >
  Extension for the <skill-name> skill. This file MUST be read together with the parent
  <skill-name> SKILL.md. The parent skill defines [what]. This extension adds [what].
metadata:
  version: "1.0.0"
  parent_skill: <skill-name>
  source: "ai-coding-tooling (extended/)"
---
```

**Writing rules for extension files:**
- State clearly at the top which phases or sections of the parent are being extended.
- Use "Inject into Phase X" or "Add to section Y" headings so the agent knows exactly where the new instructions apply in the parent's workflow.
- Do not re-state parent instructions — reference them by name and add only the delta.
- Keep the extension under 200 lines where possible. If it grows larger, move content to `reference/` files under `extended/<skill-name>/reference/`.

## Extension 3: Token Efficiency

### Inject into Phase 2 (Architecture) — after 2.2 Plan the Folder Structure (following 2.2a), when the skill includes reference files

**2.2b — Reference File Design**

If the skill will include technology-specific reference files:
- Name them `<technology>-<skill-name>.md`, where `<technology>` is the kebab-case slug for the language or framework (e.g. `fastapi`, `go-gin`, `ruby-on-rails`) and `<skill-name>` is the exact skill directory name (e.g. `tests`, `coding-guidelines`) — e.g. `go-gin-tests.md`, `django-coding-guidelines.md`.
- **Exception — scoped variants.** A skill whose references split by scope declares its own naming in its `SKILL.md` and uses `<technology>.<variant>.md` instead (e.g. `code-review`: `fastapi.code.md`, `fastapi-performance.code.md`, `fastapi.tests.md`). Follow the skill's declaration over the default pattern.
- Generic baseline files (non-tech-specific) are exempt from this pattern and keep their existing names (e.g. `review-checklist.md`, `testing-patterns.md`).

**Keep links inside the skill** — a skill links only files within its own directory (its `references/`, `scripts/`, or `../SKILL.md` from a reference file). Never link or load anything outside the skill — not `CLAUDE.md`, `CLAUDE.global.md`, the repo's `references/`, `docs/`, or another skill's files.

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
