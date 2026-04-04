---
name: skill-installation
description: >
  Install a skill into the agent's global skills directory and update the Global Skills list in the agent's global config file. Use when the user says "install this skill globally", "add this skill to global skills", "install skill", "skill-global-installation", or when a new skill folder is being placed under the agent's skills directory. After installation, always update the global config's Global Skills list. Do NOT trigger for agent setup or unrelated configuration tasks.
metadata:
  version: "3.0.0"
  triggers:
    - "install this skill globally"
    - "add this skill to global skills"
    - "install skill"
    - "skill-global-installation"
---

# Skill Installation

Install a skill into the agent's global skills directory using the appropriate method based on its source, then update the Global Skills list in the agent's global config file.

## Guardrails

### Scope

- Only write to `<skills-dir>` (the agent's global skills directory) and `<config-path>` (the agent's global config file).
- Never touch project source files, other config files, or any path outside these two locations.

### Self-installation restriction

Never install `skill-installation` itself via symlink. This skill must always be installed via `npx` or copied manually. If the user asks to install `skill-installation` as a local symlink, refuse and explain this restriction.

### On collision: target path exists

If `<skills-dir>/<skill-name>` already exists (file, folder, or broken symlink), stop and report. Never overwrite or remove automatically. The user must resolve the collision manually.

### On collision: duplicate config entry

If the skill name already exists in the `# Global Skills` section of `<config-path>`, update the existing entry in place. Never add a duplicate.

## Step 0: Resolve the target agent

If the user did not specify which agent to install for, ask:

> Which agent are you installing for? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer before proceeding. Store it as `<agent>`.

**Load agent-specific reference:** Check if a file exists at `skills/agent-setup/references/<agent>.md`. If it exists, read it now — it contains `<config-path>` (the global config file path), `<skills-dir>` (the global skills directory), `<npx-agent-id>` (the npx agent identifier), and any agent-specific caveats. Use that information for all subsequent steps.

If no reference file exists for the agent, ask the user for:
- The global config file path (e.g. `~/.someagent/SOMEAGENT.md`)
- The global skills directory path (e.g. `~/.someagent/skills/`)
- The npx `--agent` identifier (e.g. `someagent`)

## Step 1: Identify the skill source

Read the `# Global Skills` section in `<config-path>` (or the project's `AGENTS.md` if available) and find the entry for the skill being installed. Check its `Source:` field:

- `Source: Tech Leads Club` → install via npx (Step 2a)
- `Source: This project (...)` or any local project path → install via symlink (Step 2b)
- `Source: Native <agent> skill` → no installation needed; inform the user the skill is built-in
- Source unknown or not listed → ask the user before proceeding

## Step 2a: Install from Tech Leads Club (npx)

Run the following command, substituting the skill name and agent identifier:

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
```

If the command fails, report the error output and stop. Do not fall back to a manual copy.

## Step 2b: Install from local project (symlink)

**Do not use this step for `skill-installation`** — see the self-installation restriction guardrail.

Determine the absolute path to the skill folder in the local project. Then create a symlink:

```bash
ln -s "<absolute-path-to-project>/skills/<skill-name>" <skills-dir>/<skill-name>
```

Confirm the symlink was created successfully before proceeding.

## Step 3: Read the skill frontmatter

Read `<skills-dir>/<skill-name>/SKILL.md` and extract:
- `name` field (kebab-case identifier)
- `description` field (what the skill does and when it triggers)

## Step 4: Update the global config

Read `<config-path>` and add a new entry under the `# Global Skills` section using this format:

```
- **<name>** (`skills/<name>/SKILL.md`): <description> Source: <source>
```

Append the new entry at the end of the existing list. If the skill name already exists in the list, update it in place (see duplicate config entry guardrail).

If no `# Global Skills` section exists, create the section header and add the entry beneath it.

## Examples

### Example 1: Installing a Tech Leads Club skill for Claude Code

User says: "Install skill-architect globally"

Actions:
1. Agent not specified → ask → user says `claude-code`
2. Load `skills/agent-setup/references/claude-code.md` → config is `~/.claude/CLAUDE.md`, skills dir is `~/.claude/skills/`, npx id is `claude-code`
3. Source is Tech Leads Club → use npx
4. Run: `npx @tech-leads-club/agent-skills install --skill skill-architect --agent claude-code --global`
5. Read installed `SKILL.md` frontmatter
6. Append to `# Global Skills` in `~/.claude/CLAUDE.md`

### Example 2: Installing a local project skill for Gemini CLI

User says: "Install my-custom-skill globally for gemini-cli" (skill lives in `~/Projects/my-project/skills/my-custom-skill`)

Actions:
1. Agent is `gemini-cli` → load `skills/agent-setup/references/gemini-cli.md` → config is `~/.gemini/GEMINI.md`, skills dir is `~/.gemini/skills/`, npx id is `gemini`
2. Source is local → use symlink
3. Run: `ln -s ~/Projects/my-project/skills/my-custom-skill ~/.gemini/skills/my-custom-skill`
4. Read symlinked `SKILL.md` frontmatter
5. Append to `# Global Skills` in `~/.gemini/GEMINI.md`

### Example 3: Attempting to symlink skill-installation

User says: "Install skill-installation from my local project"

Actions:
1. Skill name is `skill-installation` → self-installation restriction applies
2. Refuse: "skill-installation cannot be installed via symlink. Use `npx @tech-leads-club/agent-skills install --skill skill-installation --agent <npx-agent-id> --global` instead."

### Example 4: Skill already in list

If `name` from frontmatter matches an existing entry in `# Global Skills`, update the description in place rather than adding a duplicate.

## Troubleshooting

### No `# Global Skills` section in the config file
Create the section header and add the entry beneath it.

### SKILL.md is missing from the skill folder
Halt and inform the user — a valid skill folder must contain a SKILL.md file.

### Target path already exists for symlink
Inspect with `ls -la <skills-dir>/<skill-name>`. Report to the user and stop — do not remove or overwrite automatically.

### npx command not found
Cause: Node.js / npx is not installed.
Solution: Install Node.js and re-run.