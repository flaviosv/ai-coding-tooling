---
name: update-external-skill
description: >
  Update externally installed skills by reinstalling them from their vendor registry and re-applying any extended skill symlinks. Use when the user says "update external skills", "update all skills", "update skill X", "reinstall skill X", "upgrade skills", "refresh skills", or "check for skill updates". Detects vendor automatically from references/vendors.md. Does NOT update local project-sourced or personal symlinked skills — those are symlinks and always current. Do NOT trigger for "install skill" (use skill-global-installation) or "setup global agent" (use global-agent-setup).
---

# update-external-skill

Reinstalls externally sourced skills from their vendor registry and repairs any extended skill symlinks that were overwritten during the reinstall.

## Instructions

### Step 0: Resolve the target agent

If the user did not specify which agent to update skills for, ask:

> Which agent's skills should be updated? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer before proceeding. Store it as `<agent>`.

Load the agent reference file from `skills/global-agent-setup/references/<agent>.md`. It contains `<skills-dir>` (the global skills directory) and `<npx-agent-id>`. If no reference file exists, ask the user for both values directly.

### Step 1: Load the vendor registry

Read `skills/update-external-skill/references/vendors.md`. It defines how to detect skills from each vendor and the command template used to reinstall them. You will use this in Step 2 and Step 3.

### Step 2: Identify external skills

Scan `<skills-dir>` for subdirectories. For each entry, determine whether it is a symlink or a real directory:

```bash
# Strip trailing slash before testing — trailing slash causes -L to follow the link
path="<skills-dir>/<entry>"
[ -L "${path%/}" ] && echo "SYMLINK" || echo "REAL"
```

- **SYMLINK** → local project or personal skill; always current. Skip silently.
- **REAL directory** → externally installed; candidate for update.

For each real directory candidate, apply vendor detection rules from `references/vendors.md` (e.g. presence of `.skill-meta.json`). If a candidate matches no known vendor, warn:

> Warning: `<skill-name>` is a real directory with no recognized vendor marker. Skipping.

### Step 3: Resolve scope

- **Specific skill named by the user** → verify it is a real directory; error if it is a symlink or does not exist. Process only that skill.
- **No specific skill named** → process all candidates identified in Step 2.

### Step 4: Update each skill

Process skills **sequentially** (not in parallel) so errors are easy to trace.

For each skill:

1. Read the `contentHash` from `<skills-dir>/<skill>/.skill-meta.json` if it exists (before state). Store as `<hash-before>`.
2. Run the vendor's reinstall command from `references/vendors.md`, substituting `<skill-name>` and `<npx-agent-id>`:
   ```bash
   # Example for Tech Leads Club:
   npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
   ```
3. If the command fails, report the error and continue to the next skill. Do not attempt Step 4.4 for failed skills.
4. Read the new `contentHash` from `.skill-meta.json` (after state). Store as `<hash-after>`.
5. Compare:
   - `<hash-before>` ≠ `<hash-after>` → mark as **updated**
   - `<hash-before>` = `<hash-after>` → mark as **already current**
   - `.skill-meta.json` absent before or after → mark as **updated** (cannot confirm; assume changed)

### Step 5: Re-apply extended skill symlinks

For every skill that was processed in Step 4 (regardless of whether its content changed), check whether an `extended/<skill-name>/` directory exists at the project root. If yes:

1. **Repair `SKILL.extended.md`:**
   ```bash
   rm -f "<skills-dir>/<skill>/SKILL.extended.md"
   ln -s "$(pwd)/extended/<skill>/SKILL.md" "<skills-dir>/<skill>/SKILL.extended.md"
   ```

2. **Repair the `reference` or `reference.extended` symlink** — collision-aware:
   - If `extended/<skill>/reference/` exists in this project AND `<skills-dir>/<skill>/references/` already exists (installed by vendor): remove any stale `reference.extended` symlink and recreate as `reference.extended`:
     ```bash
     rm -f "<skills-dir>/<skill>/reference.extended"
     ln -s "$(pwd)/extended/<skill>/reference" "<skills-dir>/<skill>/reference.extended"
     ```
   - If `extended/<skill>/reference/` exists AND no `references/` collision: remove any stale `reference` symlink and recreate as `reference`:
     ```bash
     rm -f "<skills-dir>/<skill>/reference"
     ln -s "$(pwd)/extended/<skill>/reference" "<skills-dir>/<skill>/reference"
     ```
   - If `extended/<skill>/reference/` does not exist: skip the reference symlink step.

3. Log each symlink that was re-applied.

If `extended/` does not exist at the project root, skip Step 5 silently for all skills.

### Step 6: Report

Summarize:

- **Updated** (content hash changed): list skill names
- **Already current** (no change): list skill names
- **Failed** (reinstall command errored): list skill names with error
- **Extended symlinks re-applied**: list symlink paths that were recreated
- **Skipped** (unknown vendor): list skill names with reason

## Examples

### Example 1: Update all external skills for claude-code

User says: "Update all external skills"

Actions:
1. Agent is `claude-code` → load `skills/global-agent-setup/references/claude-code.md` → skills dir is `~/.claude/skills/`, npx id is `claude-code`
2. Load `references/vendors.md`
3. Scan `~/.claude/skills/` → find real dirs (e.g. `skill-architect`, `coding-guidelines`, `best-practices`, …); skip symlinks
4. Match each real dir to a vendor via `.skill-meta.json` presence → all are Tech Leads Club
5. For each: snapshot hash → `npx @tech-leads-club/agent-skills install --skill <name> --agent claude-code --global` → compare hash
6. For `skill-architect`: `extended/skill-architect/` exists → re-apply `SKILL.extended.md`
7. For `coding-guidelines`: `extended/coding-guidelines/` exists → re-apply `SKILL.extended.md` and `reference/`
8. Report summary

### Example 2: Update a single skill

User says: "Update skill-architect"

Actions:
1. Confirm `~/.claude/skills/skill-architect` is a real directory (not symlink)
2. Snapshot hash → run npx reinstall → compare hash
3. Re-apply `SKILL.extended.md` from `extended/skill-architect/`
4. Report

### Example 3: User tries to update a local project skill

User says: "Update tech-reference-add"

Actions:
1. `~/.claude/skills/tech-reference-add` is a symlink → error:
   > `tech-reference-add` is a local project symlink. It is always current — no update needed.

### Example 4: Unknown vendor

A real directory is found with no `.skill-meta.json` and no matching vendor pattern in `references/vendors.md`.

Result: Warn "unknown vendor, skipping" and continue.

## Troubleshooting

### Error: npx command not found
Cause: Node.js / npx is not installed.
Solution: Install Node.js and re-run.

### Error: skill reinstall fails
Cause: Network error, registry unavailability, or invalid skill name.
Solution: Report which skill failed and its error. Continue with remaining skills. User can retry manually using the vendor's install command.

### Error: symlink already exists after rm -f
Cause: Filesystem permission issue or concurrent write.
Solution: Report the path. User should inspect with `ls -la <path>` and remove manually if needed.

### Extended symlinks not re-applied
Cause: No `extended/` directory at the project root — this skill may not be running from inside the `ai-coding-tooling` project.
Solution: Run from the `ai-coding-tooling` project root, or create the extended symlinks manually.
