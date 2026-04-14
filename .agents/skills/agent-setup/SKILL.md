---
name: agent-setup
description: >
  Sets up global agent configuration by symlinking AGENTS.global.md to the agent's global config file and installing all global skills from the Tech Leads Club registry. Use when the user says "setup global agent", "setup agent", "install global skills", "run agent-setup", "run global-agent-setup", "initialize agent global config", or "setup my agent globally". Asks which agent to target if not specified. Do NOT trigger for general skill installation, project setup, or unrelated configuration tasks.
metadata:
  version: "2.0.0"
  triggers:
    - "setup global agent"
    - "setup agent"
    - "install global skills"
    - "run agent-setup"
    - "run global-agent-setup"
    - "initialize agent global config"
    - "setup my agent globally"
---

# Agent Setup

## Guardrails

### Scope

This is a local setup tool for the `ai-coding-tooling` project. It is **not available via npx or any package registry**. It must be run manually by opening this project in your agent and invoking it directly (e.g. "run agent-setup"). Do not attempt to install it as a global skill.

Only modify the agent's global config path, skills directory, and extended/personal skill links. Never modify project source files.

### Config file exists

If the global config file already exists at `<config-path>`, **stop immediately**. Never overwrite existing configuration. Report the error and instruct the user to remove it manually before re-running.

### Never auto-delete

Never remove existing symlinks, files, or directories without user confirmation. If a collision is found, report it and stop — or skip and log as "already present". Do not delete or overwrite automatically.

### Sequential processing

Process skills sequentially (not in parallel) so errors are isolated and traceable. If any individual install fails, report the error and continue with remaining skills.

## Step 0: Resolve the target agent

If the user did not specify which agent to set up, ask:

> Which agent are you setting up for? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer before proceeding. Store it as `<agent>`.

**Load agent-specific reference:** Check if a file exists at `.agents/skills/agent-setup/references/<agent>.md`. If it exists, read it now — it contains the config file path, skills directory, npx agent identifier, native skills to skip, and any agent-specific caveats. Use that information for all subsequent steps.

If no reference file exists for the agent, ask the user for:
- The global config file path (e.g. `~/.someagent/SOMEAGENT.md`)
- The global skills directory path (e.g. `~/.someagent/skills/`)
- The npx `--agent` identifier (e.g. `someagent`)

## Step 1: Check if the global config file already exists

Run the following check using Bash (substitute the actual resolved path):

```bash
test -e <config-path> && echo "EXISTS" || echo "NOT_FOUND"
```

If the output is `EXISTS`, **stop immediately** and report an error to the user:

> Error: `<config-path>` already exists. Remove it manually before running this setup to avoid overwriting your existing configuration.

Do NOT proceed with any further steps if the file exists.

## Step 2: Ensure required directories exist, then create the symlink

Some agents require their config directory and/or skills directory to be created first. Check the agent reference file — if it specifies a `mkdir` step, run it before symlinking.

```bash
ln -s "$(pwd)/AGENTS.global.md" <config-path>
```

This must be run from the root of the project (where `AGENTS.global.md` lives). Confirm the symlink was created successfully before proceeding.

If the symlink creation fails, report the error and stop.

## Step 3: Install global skills

Read `AGENTS.md` at the project root using the **Read tool** (not grep or bash) to ensure no lines are truncated. Extract every skill entry from the `# Global Skills` section. Process each skill sequentially (not in parallel) so errors are easy to trace.

For each skill entry, check its `Source:` field and act accordingly:

- **`Source: Tech Leads Club`** (or a techlead.club link) → install via npx using the agent identifier from the reference file:
  - If the entry also has `Install: local` → install into the project-local skills directory (omit `--global`):
    ```bash
    npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id>
    ```
  - Otherwise → install globally:
    ```bash
    npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
    ```
- **`Source: Native <agent> skill`** (or listed as native in the agent reference) → skip installation entirely; the skill is built into the agent. Log it as "skipped (native)".
- **`Source: This project (...)`** → install via symlink from the project's `skills/` folder into the agent's skills directory:
  ```bash
  ln -s "$(pwd)/skills/<skill-name>" <skills-dir>/<skill-name>
  ```
  Skip if a symlink or folder already exists at that path (log as "skipped (already present)").
- **Source unknown or missing** → skip and warn the user.

If any individual install fails, report which skill failed and its error output, then continue with the remaining skills. Summarize all successes, skips, and failures at the end.

## Step 4: Install extended skills

After all global skills are installed, check for an `extended/` directory at the project root. If it exists, process each subdirectory inside it. Each subdirectory represents an extended version of an existing skill — its name matches the parent skill's name.

For each `extended/<skill-name>/` directory:

1. Verify the parent skill is already installed at `<skills-dir>/<skill-name>/`. If not, look up the skill by name in the `# Global Skills` list already read in Step 3, determine its `Source:`, and install it using the same strategy as Step 3 before proceeding. If the parent cannot be found in the list, warn and skip.
2. Symlink the `SKILL.md` from the extended folder into the installed skill directory as `SKILL.extended.md`:
   ```bash
   ln -s "$(pwd)/extended/<skill-name>/SKILL.md" <skills-dir>/<skill-name>/SKILL.extended.md
   ```
3. If the extended folder contains a `reference/` directory, check whether `<skills-dir>/<skill-name>/reference` already exists (e.g. installed by npx). If it does, symlink as `reference.extended`; otherwise symlink as `reference`:
   ```bash
   # no collision:
   ln -s "$(pwd)/extended/<skill-name>/reference" <skills-dir>/<skill-name>/reference
   # collision with existing reference/:
   ln -s "$(pwd)/extended/<skill-name>/reference" <skills-dir>/<skill-name>/reference.extended
   ```
4. Skip any symlink target that already exists (log as "skipped (already present)").

Refer to the agent reference file for any agent-specific notes on extended skill installation.

If any individual symlink fails, report it and continue with the remaining extensions.

## Step 5: Install personal skills

After extended skills are installed, check for a `personal/` directory at the project root. If it exists, scan it for subdirectories — each one is a personal (local-only) skill.

For each `personal/<skill-name>/` directory:

1. Check that `personal/<skill-name>/SKILL.md` exists. If not, skip and warn.
2. Symlink the folder into the agent's skills directory:
   ```bash
   ln -s "$(pwd)/personal/<skill-name>" <skills-dir>/<skill-name>
   ```
3. Skip if a symlink or folder already exists at that path (log as "skipped (already present)").

Label each installed personal skill as `Personal (local-only)` in the summary. These skills are gitignored and never listed in `AGENTS.md` — they are discovered dynamically at install time.

If `personal/` does not exist, skip this step silently.

## Step 6: Confirm completion

Report to the user:

- The agent targeted
- The full symlink path (e.g. `<config-path> -> /path/to/project/AGENTS.global.md`)
- Which skills were installed successfully
- Which extended skill files were symlinked
- Which personal skills were installed (labeled `Personal (local-only)`)
- Any failures encountered

## Examples

### Example 1: Known agent specified upfront

User says: "Run agent-setup for claude-code"

Actions:
1. Agent is `claude-code` → load `.agents/skills/agent-setup/references/claude-code.md`
2. Config path is `~/.claude/CLAUDE.md`, skills dir is `~/.claude/skills/`, npx id is `claude-code`
3. Check `~/.claude/CLAUDE.md` → not found
4. Create symlink from `$(pwd)/AGENTS.global.md` → `~/.claude/CLAUDE.md`
5. Read `# Global Skills` from `AGENTS.md`, install each per source
6. Process `extended/` directory — symlink `SKILL.extended.md` and `reference/` per agent reference rules
7. Report summary

### Example 2: Known agent — Gemini CLI

User says: "Run agent-setup for gemini-cli"

Actions:
1. Agent is `gemini-cli` → load `.agents/skills/agent-setup/references/gemini-cli.md`
2. Config path is `~/.gemini/GEMINI.md`, skills dir is `~/.gemini/skills/`, npx id is `gemini`
3. Reference specifies `mkdir -p ~/.gemini && mkdir -p ~/.gemini/skills` before symlinking
4. Check `~/.gemini/GEMINI.md` → not found
5. Run `mkdir -p ~/.gemini && mkdir -p ~/.gemini/skills`
6. Create symlink, install skills, process extended skills
7. Report summary

### Example 3: Unknown agent

User says: "Run agent-setup for cursor"

Actions:
1. Agent is `cursor` → no reference file found
2. Ask user: config file path, skills directory, and npx `--agent` identifier
3. Proceed with symlink and skill installation using provided values

### Example 4: Config file already exists

User says: "Setup agent for claude-code"

Actions:
1. Load `references/claude-code.md`, config path is `~/.claude/CLAUDE.md`
2. Check → EXISTS

Result: Stop with error telling the user to remove the file manually first. Do not install any skills.

## Troubleshooting

### Error: config file already exists

Cause: A previous setup was run or the user already has a global config file.
Solution: Remove it manually (e.g. `rm <config-path>`) and re-run. Do not delete it automatically — it may contain important config.

### Error: ln: file exists (symlink target collision)

Cause: A broken or existing symlink is already at that path.
Solution: Inspect with `ls -la <config-path>`, then remove manually if appropriate.

### Error: npx command not found

Cause: Node.js / npx is not installed.
Solution: Install Node.js and re-run.

### Error: skill install fails for one or more skills

Cause: Network issue, registry unavailability, or invalid skill name.
Solution: Note which skills failed, continue with the rest, and report at the end. The user can retry individual installs manually using the same `npx @tech-leads-club/agent-skills install` command.
