---
name: global-agent-setup
description: >
  Sets up global agent configuration by symlinking AGENTS.global.md to the agent's global config file and installing all global skills from the Tech Leads Club registry. Use when the user says "setup global agent", "install global skills", "run global-agent-setup", "initialize agent global config", or "setup my agent globally". Asks which agent to target if not specified. Do NOT trigger for general skill installation, project setup, or unrelated configuration tasks.
---

# global-agent-setup

Sets up the global agent configuration by symlinking this project's `AGENTS.global.md` to the agent's global config file and installing all global skills from the Tech Leads Club registry.

## Important: Manual Use Only

This is a local setup tool for the `ai-coding-tooling` project. It is **not available via npx or any package registry**. It must be run manually by opening this project in your agent and invoking it directly (e.g. "run global-agent-setup"). Do not attempt to install it as a global skill.

## Instructions

### Step 0: Resolve the target agent

If the user did not specify which agent to set up (e.g. did not say "for claude-code" or "for cursor"), ask:

> Which agent are you setting up for? (e.g. `claude-code`, `cursor`, `windsurf`)

Wait for the answer before proceeding. Store it as `<agent>` for use in all subsequent steps.

The global config file path depends on the agent:
- `claude-code` → `~/.claude/CLAUDE.md`
- Other agents → ask the user for the config file path if unknown.

### Step 1: Check if the global config file already exists

Run the following check using Bash (substitute the actual resolved path):

```bash
test -e <config-path> && echo "EXISTS" || echo "NOT_FOUND"
```

If the output is `EXISTS`, **stop immediately** and report an error to the user:

> Error: `<config-path>` already exists. Remove it manually before running this setup to avoid overwriting your existing configuration.

Do NOT proceed with any further steps if the file exists.

### Step 2: Create the symlink

Run:

```bash
ln -s "$(pwd)/AGENTS.global.md" <config-path>
```

This must be run from the root of the project (where `AGENTS.global.md` lives). Confirm the symlink was created successfully before proceeding.

If the symlink creation fails, report the error and stop.

### Step 3: Install global skills

Read `AGENTS.global.md` at the project root using the **Read tool** (not grep or bash) to ensure no lines are truncated. Extract every skill entry from the `# Global Skills` section. Process each skill sequentially (not in parallel) so errors are easy to trace.

For each skill entry, check its `Source:` field and act accordingly:

- **`Source: Tech Leads Club`** (or a techlead.club link) → install via npx:
  ```bash
  npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <agent> --global
  ```
- **`Source: Native Claude Code skill`** → skip installation entirely; the skill is built into the agent. Log it as "skipped (native)".
- **`Source: This project (...)`** → install via symlink from the project's `skills/` folder:
  ```bash
  ln -s "$(pwd)/skills/<skill-name>" ~/.claude/skills/<skill-name>
  ```
  Skip if a symlink or folder already exists at that path (log as "skipped (already present)").
- **Source unknown or missing** → skip and warn the user.

If any individual install fails, report which skill failed and its error output, then continue with the remaining skills. Summarize all successes, skips, and failures at the end.

### Step 4: Install extended skills

After all global skills are installed, check for an `extended/` directory at the project root. If it exists, process each subdirectory inside it. Each subdirectory represents an extended version of an existing skill — its name matches the parent skill's name.

For each `extended/<skill-name>/` directory:

1. Verify the parent skill is already installed at `~/.claude/skills/<skill-name>/`. If not, look up the skill by name in the `# Global Skills` list already read in Step 3, determine its `Source:`, and install it using the same strategy as Step 3 before proceeding. If the parent cannot be found in the list, warn and skip.
2. Symlink the `SKILL.md` from the extended folder into the installed skill directory as `SKILL.extended.md`:
   ```bash
   ln -s "$(pwd)/extended/<skill-name>/SKILL.md" ~/.claude/skills/<skill-name>/SKILL.extended.md
   ```
3. If the extended folder contains a `reference/` directory, symlink it into the installed skill directory:
   ```bash
   ln -s "$(pwd)/extended/<skill-name>/reference" ~/.claude/skills/<skill-name>/reference
   ```
4. Skip any symlink target that already exists (log as "skipped (already present)").

If any individual symlink fails, report it and continue with the remaining extensions.

### Step 5: Confirm completion

Report to the user:

- The agent targeted (e.g. `claude-code`)
- The full symlink path (e.g. `~/.claude/CLAUDE.md -> /path/to/project/AGENTS.global.md`)
- Which skills were installed successfully
- Which extended skill files were symlinked
- Any failures encountered

## Examples

### Example 1: Agent specified upfront

User says: "Run global-agent-setup for claude-code"

Actions:
1. Agent is `claude-code`, config path is `~/.claude/CLAUDE.md`
2. Check `~/.claude/CLAUDE.md` → not found
3. Create symlink from `$(pwd)/AGENTS.global.md` → `~/.claude/CLAUDE.md`
4. Read `# Global Skills` section from `AGENTS.global.md`, identify each skill's `Source:` field, and apply the appropriate install strategy for each
5. Process `extended/` directory — symlink `SKILL.md` as `SKILL.extended.md` and `reference/` into each parent skill's installed directory
6. Report summary of installs, symlinks, and skips

Result: CLAUDE.md symlinked, skills installed per their declared source.

### Example 2: Agent not specified

User says: "Run the global-agent-setup"

Actions:
1. Ask: "Which agent are you setting up for? (e.g. `claude-code`, `cursor`, `windsurf`)"
2. User responds: "cursor"
3. Ask: "What is the global config file path for cursor?"
4. User responds: "~/.cursor/config.md"
5. Proceed with symlink and skill installation using `--agent cursor`

Result: Config file symlinked, all skills installed for cursor.

### Example 3: Config file already exists

User says: "Setup global agent for claude-code"

Actions:
1. Agent is `claude-code`, config path is `~/.claude/CLAUDE.md`
2. Check `~/.claude/CLAUDE.md` → EXISTS

Result: Stop with error telling the user to remove the file manually first. Do not install any skills.

## Troubleshooting

### Error: config file already exists

Cause: A previous setup was run or the user already has a global config file.
Solution: Remove it manually (e.g. `rm ~/.claude/CLAUDE.md`) and re-run. Do not delete it automatically — it may contain important config.

### Error: ln: file exists (symlink target collision)

Cause: A broken or existing symlink is already at that path.
Solution: Inspect with `ls -la <config-path>`, then remove manually if appropriate.

### Error: npx command not found

Cause: Node.js / npx is not installed.
Solution: Install Node.js and re-run.

### Error: skill install fails for one or more skills

Cause: Network issue, registry unavailability, or invalid skill name.
Solution: Note which skills failed, continue with the rest, and report at the end. The user can retry individual installs manually using the same `npx @tech-leads-club/agent-skills install` command.
