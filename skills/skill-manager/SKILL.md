---
name: skill-manager
description: >
  Install or update skills in an agent's global skills directory. Handles both
  fresh installation (from Tech Leads Club via npx or from a local project via
  symlink) and updating externally installed skills by reinstalling from their
  vendor registry and re-applying extended skill symlinks. Use when the user says
  "install skill", "install this skill globally", "add this skill to global skills",
  "skill-global-installation", "update skills", "update all skills", "update skill X",
  "reinstall skill", "upgrade skills", "refresh skills", or "check for skill updates".
  If intent (install vs update) is not explicit, ask the user before proceeding.
  Do NOT trigger for "setup global agent" (use agent-setup).
metadata:
  version: "1.0.0"
  triggers:
    - "install skill"
    - "install this skill globally"
    - "add this skill to global skills"
    - "skill-global-installation"
    - "update skills"
    - "update all skills"
    - "update skill X"
    - "reinstall skill"
    - "upgrade skills"
    - "refresh skills"
    - "check for skill updates"
---

# Skill Manager

Install new skills into an agent's global skills directory, or update externally installed skills from their vendor registry.

## Step 0: Determine Operation Mode

Detect intent from the user's request:

- **Install signals:** "install", "add … to global skills", "skill-global-installation" → proceed as **Install** (Step I-1 onward).
- **Update signals:** "update", "upgrade", "reinstall", "refresh", "check for skill updates" → proceed as **Update** (Step U-1 onward).
- **Ambiguous** (no clear signal): ask before proceeding:

  > Do you want to **install** a new skill or **update** an existing one?

  Wait for the answer before continuing.

---

## INSTALL PATH

### Step I-1: Resolve the Target Agent

If the user did not specify which agent to install for, ask:

> Which agent are you installing for? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer. Store as `<agent>`.

**Load agent reference:** Check for `skills/agent-setup/references/<agent>.md`. If it exists, read it — it contains `<config-path>`, `<skills-dir>`, `<npx-agent-id>`, and caveats. If no reference exists, ask the user for all three values.

### Step I-2: Guardrails

- Only write to `<skills-dir>` and `<config-path>`. Never touch project source files or other paths.
- If `<skills-dir>/<skill-name>` already exists (file, folder, or broken symlink): stop and report. Never overwrite automatically.
- If the skill name already exists in `# Global Skills` in `<config-path>`: update in place, never duplicate.

### Step I-3: Identify the Skill Source

Read the `# Global Skills` section in `<config-path>` (or the project's `AGENTS.md` if available) and find the `Source:` field for the skill:

- `Source: Tech Leads Club` → install via npx (Step I-4a)
- `Source: This project (...)` or any local project path → install via symlink (Step I-4b)
- `Source: Native <agent> skill` → no installation needed; inform the user the skill is built-in
- Unknown or unlisted → ask the user before proceeding

### Step I-4a: Install from Tech Leads Club (npx)

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
```

If the command fails, report the error and stop. Do not fall back to manual copy.

### Step I-4b: Install from Local Project (symlink)

```bash
ln -s "<absolute-path-to-project>/skills/<skill-name>" <skills-dir>/<skill-name>
```

Confirm the symlink was created before proceeding.

### Step I-5: Update the Global Config

Read `<skills-dir>/<skill-name>/SKILL.md` and extract `name` and `description`. Then add/update in `<config-path>` under `# Global Skills`:

```
- **<name>** (`skills/<name>/SKILL.md`): <description> Source: <source>
```

Append at the end of the list. Update in place if the skill name already exists. If no `# Global Skills` section exists, create the header and add the entry.

---

## UPDATE PATH

### Step U-1: Resolve the Target Agent

If the user did not specify which agent, ask:

> Which agent's skills should be updated? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer. Load `skills/agent-setup/references/<agent>.md` for `<skills-dir>` and `<npx-agent-id>`. If no reference exists, ask the user for both.

### Step U-2: Load the Vendor Registry

Read `skills/skill-manager/references/vendors.md`. It defines detection patterns and reinstall commands per vendor.

### Step U-3: Identify External Skills

Scan `<skills-dir>` for subdirectories. For each entry, check symlink vs real directory:

```bash
path="<skills-dir>/<entry>"
[ -L "${path%/}" ] && echo "SYMLINK" || echo "REAL"
```

- **SYMLINK** → local project or personal skill; always current. Skip silently.
- **REAL directory** → externally installed; candidate for update.

Apply vendor detection rules from `references/vendors.md`. If a candidate matches no known vendor, warn and skip:

> Warning: `<skill-name>` is a real directory with no recognized vendor marker. Skipping.

### Step U-4: Resolve Scope

- **Skills named in prompt** → validate each exists as a real directory. Error for symlinks or missing. Process only the validated set.
- **No skills named** → process all candidates from Step U-3.

### Step U-5: Update Each Skill

Process **sequentially** (not parallel) so errors are easy to trace.

For each skill:

1. Read `contentHash` from `<skills-dir>/<skill>/.skill-meta.json` if it exists. Store as `<hash-before>`.
2. Run the vendor's reinstall command from `references/vendors.md`:
   ```bash
   npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
   ```
3. If the command fails, report the error and continue to the next skill.
4. Read new `contentHash`. Store as `<hash-after>`.
5. Compare:
   - `<hash-before>` ≠ `<hash-after>` → **updated**
   - `<hash-before>` = `<hash-after>` → **already current**
   - `.skill-meta.json` absent before or after → **updated** (cannot confirm; assume changed)

### Step U-6: Re-apply Extended Skill Symlinks

For every processed skill, check if `extended/<skill-name>/` exists at the project root. If yes:

1. **Repair `SKILL.extended.md`:**
   ```bash
   rm -f "<skills-dir>/<skill>/SKILL.extended.md"
   ln -s "$(pwd)/extended/<skill>/SKILL.md" "<skills-dir>/<skill>/SKILL.extended.md"
   ```

2. **Repair `reference` / `reference.extended` symlink** — collision-aware:
   - If `extended/<skill>/reference/` exists AND `<skills-dir>/<skill>/references/` already exists: recreate as `reference.extended`:
     ```bash
     rm -f "<skills-dir>/<skill>/reference.extended"
     ln -s "$(pwd)/extended/<skill>/reference" "<skills-dir>/<skill>/reference.extended"
     ```
   - If `extended/<skill>/reference/` exists AND no `references/` collision: recreate as `reference`:
     ```bash
     rm -f "<skills-dir>/<skill>/reference"
     ln -s "$(pwd)/extended/<skill>/reference" "<skills-dir>/<skill>/reference"
     ```
   - If `extended/<skill>/reference/` does not exist: skip.

3. Log each symlink re-applied.

If no `extended/` directory at project root, skip Step U-6 silently for all skills.

### Step U-7: Report

| Category | Details |
|----------|---------|
| **Updated** (hash changed) | list skill names |
| **Already current** (no change) | list skill names |
| **Failed** (reinstall errored) | list skill names with error |
| **Extended symlinks re-applied** | list symlink paths |
| **Skipped** (unknown vendor or symlink) | list skill names with reason |

---

## Examples

### Install: Tech Leads Club skill for Claude Code

User: "Install skill-architect globally"

1. Install signal detected.
2. Agent not specified → ask → `claude-code`
3. Load `skills/agent-setup/references/claude-code.md`
4. Source is Tech Leads Club → npx install
5. Run: `npx @tech-leads-club/agent-skills install --skill skill-architect --agent claude-code --global`
6. Read installed `SKILL.md` frontmatter → update `# Global Skills` in `~/.claude/CLAUDE.md`

### Install: Local project skill for Gemini CLI

User: "Install my-custom-skill globally for gemini-cli"

1. Install signal detected.
2. Agent is `gemini-cli` → load reference
3. Source is local → symlink: `ln -s ~/Projects/my-project/skills/my-custom-skill ~/.gemini/skills/my-custom-skill`
4. Update `# Global Skills` in `~/.gemini/GEMINI.md`

### Update: All external skills

User: "update all skills"

1. Update signal detected.
2. Agent not specified → ask → `claude-code`
3. Scan `~/.claude/skills/` → find real dirs, skip symlinks
4. Match each to vendor via `.skill-meta.json` → all Tech Leads Club
5. Reinstall each sequentially; compare hashes
6. Re-apply extended symlinks
7. Report summary

### Update: Single skill

User: "update skill-architect"

1. Update signal detected.
2. Validate `~/.claude/skills/skill-architect` is a real directory
3. Snapshot hash → reinstall → compare
4. Re-apply `SKILL.extended.md` if `extended/skill-architect/` exists
5. Report

### Ambiguous: No clear intent

User: "/skill-manager"

1. No install or update signal → ask:
   > Do you want to **install** a new skill or **update** an existing one?
2. Wait for answer, then follow the appropriate path above.

---

## Troubleshooting

### npx command not found
Install Node.js and re-run.

### Skill reinstall fails
Report which skill failed with its error. Continue remaining skills. User can retry with the vendor's install command.

### Target path already exists (install)
Inspect with `ls -la <skills-dir>/<skill-name>`. Report and stop — never remove or overwrite automatically.

### No `# Global Skills` section in config
Create the section header and add the entry beneath it.

### SKILL.md missing from skill folder
Halt — a valid skill folder must contain a SKILL.md file.

### Symlink re-apply fails after rm -f
Report the path. User should inspect with `ls -la <path>` and remove manually.

### Extended symlinks not re-applied
No `extended/` directory at project root. Run from the `ai-coding-tooling` project root, or create symlinks manually.
