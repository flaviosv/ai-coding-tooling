---
name: skill-alias
description: >
  Create a slash-command alias for an existing skill by generating a thin
  delegator skill. The original skill remains unchanged. Use when the user
  says "alias skill", "create shortcut for skill", "skill alias",
  or "change slash command for skill". Do NOT use for skill deletion or
  modification.
metadata:
  author: flaviostudart
  version: "1.0.0"
  triggers:
    - "alias skill"
    - "change slash command"
    - "create shortcut for skill"
    - "skill alias"
---

# Skill Alias

Creates a slash-command alias for an existing skill by generating a thin delegator that immediately invokes the original. The original skill remains unchanged and fully functional.

## Guardrails

### Scope
- Do NOT modify or delete the original skill.
- Do NOT create aliases for skills that do not exist.
- Only create new skills in the `skills/` directory of the current project.
- If the original skill has a Skill Override entry (in AGENTS.global.md or CLAUDE.md), the alias does NOT need one — delegation triggers the override automatically.

### Before Starting
- Original skill must exist (project `skills/` or agent's global skills dir).
- New name must not conflict with an existing skill directory.

### On Collision
If `skills/<new-name>/` already exists → stop and inform the user. Do NOT overwrite.

## Steps

### 1. Gather Input

If not provided in the invocation prompt, ask the user for:
1. **Original skill name** — the existing skill to alias (e.g., `coding-guidelines`)
2. **New name** — the desired slash command (kebab-case, e.g., `code`)

### 2. Validate

1. Verify original skill exists:
   - Check `skills/<original>/SKILL.md` (project-local)
   - Check agent's global skills directory for `<original>/SKILL.md`
   - If not found in either → stop, list available skills
2. Verify no collision:
   - `skills/<new-name>/` must not exist
   - If collision → stop, inform user
3. Read original skill's `SKILL.md` frontmatter to extract:
   - `description` (to understand what it does)
   - `metadata.triggers` (for context)

### 3. Create Delegator Skill

Create `skills/<new-name>/SKILL.md` with this structure:

```
---
name: <new-name>
description: >
  <Rewritten one-line description based on original skill's purpose>.
  Thin delegator that invokes the <original-name> skill. Use when the user
  says "<new-name>", <2-3 relevant trigger phrases>. Do NOT use for
  <negative triggers if applicable>.
metadata:
  version: "1.0.0"
  triggers:
    - "<new-name>"
    - <2-3 relevant triggers derived from the original>
  alias_for: <original-name>
---

# <New Name Title Case>

Delegates to **<original-name>**. Provides a short `/<new-name>` command
<optional: mention the naming pattern it establishes, e.g., pairing with code-review>.

## Behavior

Immediately invoke the `<original-name>` skill using the Skill tool.
Pass through any user context or arguments unchanged.

The `<original-name>` skill (and its extended version if present) handles all logic.

Do NOT add logic here — this is a passthrough.
```

### 4. Update Config Files

Add the new skill to each config file, maintaining **alphabetical order**:

#### 4a. `CLAUDE.md` → `# Available Skills` section

Insert bullet (alphabetically):
```
- **<new-name>** (`skills/<new-name>/SKILL.md`): <description from frontmatter>. Source: This project (`ai-coding-tooling`).
```

#### 4b. `AGENTS.md` → `# Available Skills` section

Same entry as 4a (files are identical).

#### 4c. `README.md` → "Source: This Project" skills table

Insert row (alphabetically):
```
| **<new-name>** | <Short description>. Delegator to `<original-name>`. |
```

#### 4d. `README.md` → "Skill Aliases" table

If the `### Skill Aliases` section does not exist in README.md, create it immediately after the "Source: This Project" skills table (before any other source tables). Add a row for the new alias:

```markdown
### Skill Aliases

Aliases are thin delegators that provide shorter slash commands for existing skills. The original skill remains unchanged.

| Alias | Original Skill | Description |
|---|---|---|
| **<new-name>** | `<original-name>` | Short command for `/<original-name>` |
```

If the section already exists, insert the new row alphabetically into the existing table.

#### 4e. `AGENTS.global.md` → `# Global Skills` section

Ask the user: "Should `<new-name>` be available as a global skill?"
- If yes → add entry (alphabetically)
- If no → skip

### 5. Verify & Next Steps

1. Confirm `skills/<new-name>/SKILL.md` exists and frontmatter is valid
2. Confirm config files have the new entry in correct alphabetical position
3. Inform user of next steps:
   - Run `make link` to create local symlinks
   - Run `/skill-manager` to install globally on current agent
   - Run `/agent-setup` to reinstall all global skills (if setting up fresh)

## Examples

### Example 1: Alias coding-guidelines → code

**User says:** "alias coding-guidelines to code"

**Actions:**
1. Validate `coding-guidelines` exists at `~/.claude/skills/coding-guidelines/` → found
2. Validate `skills/code/` doesn't exist → clear
3. Read `coding-guidelines` SKILL.md → extract description and triggers
4. Create `skills/code/SKILL.md` as delegator with `alias_for: coding-guidelines`
5. Update CLAUDE.md, AGENTS.md, README.md skills table (alphabetical)
6. Add row to README.md "Skill Aliases" table (create section if missing)
7. Ask about AGENTS.global.md → user says yes → add entry
8. Inform: "Created `/code` → delegates to `coding-guidelines`. Run `make link` to activate."

### Example 2: Missing original skill

**User says:** "alias foo-bar to fb"

**Actions:**
1. Check `skills/foo-bar/SKILL.md` → not found
2. Check `~/.claude/skills/foo-bar/SKILL.md` → not found
3. Stop: "Skill `foo-bar` not found in project or global skills."

### Example 3: Name collision

**User says:** "alias tests to code-review"

**Actions:**
1. Validate `tests` exists → yes
2. Check `skills/code-review/` → already exists
3. Stop: "Skill `code-review` already exists. Choose a different name."

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| Original skill not found | Misspelled name or skill not installed | List available skills for the user to pick from |
| New name already exists | Collision with existing skill | Ask user for a different name |
| Config file format changed | CLAUDE.md/AGENTS.md structure differs from expected | Read the file first, find the `# Available Skills` section, match existing entry format |
