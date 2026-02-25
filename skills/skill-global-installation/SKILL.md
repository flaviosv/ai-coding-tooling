---
name: skill-global-installation
description: Guides the installation of a new skill into the global Claude Code skills directory (~/.claude/skills/) and keeps the Global Skills list in ~/.claude/CLAUDE.md up to date. Use when the user says "install this skill globally", "add this skill to global skills", "install skill", or when a new skill folder is being placed under ~/.claude/skills/. After installation, always update the CLAUDE.md Global Skills list. Source: This project (ai-coding-tooling).
metadata:
  version: '2.0.0'
---

# Skill Global Installation

When a skill is installed globally, install it using the appropriate method based on its source, then update the Global Skills list in `~/.claude/CLAUDE.md`.

## Restriction

**Never install `skill-global-installation` itself using a symlink.** This skill must always be installed via `npx` or copied manually. If the user asks to install `skill-global-installation` as a local symlink, refuse and explain this restriction.

## Instructions

### Step 1: Identify the skill source

Read the `# Global Skills` section in `~/.claude/CLAUDE.md` (or the project's `AGENTS.md` if available) and find the entry for the skill being installed. Check its `Source:` field:

- `Source: Tech Leads Club` → install via npx (Step 2a)
- `Source: This project (...)` or any local project path → install via symlink (Step 2b)
- `Source: Native Claude Code skill` → no installation needed; inform the user the skill is built-in
- Source unknown or not listed → ask the user before proceeding

### Step 2a: Install from Tech Leads Club (npx)

Run the following command, substituting the skill name and agent:

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <agent> --global
```

For Claude Code, `--agent` is `claude-code`. If the agent is not known, ask the user.

If the command fails, report the error output and stop. Do not fall back to a manual copy.

### Step 2b: Install from local project (symlink)

**Do not use this step for `skill-global-installation`** — see Restriction above.

Determine the absolute path to the skill folder in the local project. Then create a symlink:

```bash
ln -s "<absolute-path-to-project>/skills/<skill-name>" ~/.claude/skills/<skill-name>
```

Confirm the symlink was created successfully before proceeding.

If the target path `~/.claude/skills/<skill-name>` already exists (file, folder, or broken symlink), report it and stop — do not overwrite automatically.

### Step 3: Read the skill frontmatter

Read `~/.claude/skills/<skill-name>/SKILL.md` and extract:
- `name` field (kebab-case identifier)
- `description` field (what the skill does and when it triggers)

### Step 4: Update CLAUDE.md

Read `~/.claude/CLAUDE.md` and add a new entry under the `# Global Skills` section using this format:

```
- **<name>** (`skills/<name>/SKILL.md`): <description> Source: <source>
```

Append the new entry at the end of the existing list. Do not duplicate entries — if the skill name already exists in the list, update it in place.

## Examples

### Example 1: Installing a Tech Leads Club skill

User says: "Install skill-architect globally"

AGENTS.md entry has `Source: Tech Leads Club`.

Actions:
1. Source is Tech Leads Club → use npx
2. Run: `npx @tech-leads-club/agent-skills install --skill skill-architect --agent claude-code --global`
3. Read installed `SKILL.md` frontmatter
4. Append to `# Global Skills` in `~/.claude/CLAUDE.md`

### Example 2: Installing a local project skill

User says: "Install my-custom-skill globally" (skill lives in `~/Projects/my-project/skills/my-custom-skill`)

AGENTS.md entry has `Source: This project (my-project)`.

Actions:
1. Source is local → use symlink
2. Run: `ln -s ~/Projects/my-project/skills/my-custom-skill ~/.claude/skills/my-custom-skill`
3. Read symlinked `SKILL.md` frontmatter
4. Append to `# Global Skills` in `~/.claude/CLAUDE.md`

### Example 3: Attempting to symlink skill-global-installation

User says: "Install skill-global-installation from my local project"

Actions:
1. Skill name is `skill-global-installation` → restriction applies
2. Refuse: "skill-global-installation cannot be installed via symlink. Use `npx @tech-leads-club/agent-skills install --skill skill-global-installation --agent claude-code --global` instead."

### Example 4: Skill already in list

If `name` from frontmatter matches an existing entry in `# Global Skills`, update the description in place rather than adding a duplicate.

## Troubleshooting

### No `# Global Skills` section in CLAUDE.md
Create the section header and add the entry beneath it.

### SKILL.md is missing from the skill folder
Halt and inform the user — a valid skill folder must contain a SKILL.md file.

### Duplicate entry detected
Update the existing entry in place rather than adding a new one.

### Target path already exists for symlink
Inspect with `ls -la ~/.claude/skills/<skill-name>`. Report to the user and stop — do not remove or overwrite automatically.

### npx command not found
Cause: Node.js / npx is not installed.
Solution: Install Node.js and re-run.
