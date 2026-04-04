---
name: skill-update
description: >
  Update externally installed skills by reinstalling them from their vendor registry
  and re-applying any extended skill symlinks. Supports updating a single skill, a set
  of skills, or all external skills. Use when the user says "update skills", "update
  all skills", "update skill X", "update skill X and Y", "reinstall skill", "upgrade
  skills", "refresh skills", or "check for skill updates". Detects vendor automatically
  from references/vendors.md. Does NOT update local project-sourced or personal symlinked
  skills — those are symlinks and always current. Do NOT trigger for "install skill"
  (use skill-install) or "setup global agent" (use agent-setup).
metadata:
  version: "2.0.0"
  triggers:
    - "update skills"
    - "update all skills"
    - "update skill X"
    - "update skill X and Y"
    - "reinstall skill"
    - "upgrade skills"
    - "refresh skills"
    - "check for skill updates"
---

# Skill Update

Reinstalls externally sourced skills from their vendor registry and repairs any extended skill symlinks that were overwritten during the reinstall.

## Guardrails

### Scope Resolution

- **One or more skills named in prompt** → process only those skills. Validate each is a real directory; error if symlink or missing.
- **No skills named** → process all external skill candidates.

### What NOT to Update

- Symlinked skills (local project or personal) — always current by definition.
- Skills with no recognized vendor marker — warn and skip.

## Step 1: Resolve the Target Agent

If the user did not specify which agent to update skills for, ask:

> Which agent's skills should be updated? (e.g. `claude-code`, `gemini-cli`, `cursor`, `windsurf`)

Wait for the answer before proceeding. Store it as `<agent>`.

Load the agent reference file from `skills/agent-setup/references/<agent>.md`. It contains `<skills-dir>` (the global skills directory) and `<npx-agent-id>`. If no reference file exists, ask the user for both values directly.

## Step 2: Load the Vendor Registry

Read `skills/skill-update/references/vendors.md`. It defines how to detect skills from each vendor and the command template used to reinstall them.

## Step 3: Identify External Skills

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

## Step 4: Resolve Scope

Parse the user's request for skill names:

- **One or more skills named** → validate each exists in `<skills-dir>` as a real directory. Error for any that are symlinks or missing. Process only the validated set.
- **No skills named** → process all candidates identified in Step 3.

## Step 5: Update Each Skill

Process skills **sequentially** (not in parallel) so errors are easy to trace.

For each skill:

1. Read the `contentHash` from `<skills-dir>/<skill>/.skill-meta.json` if it exists (before state). Store as `<hash-before>`.
2. Run the vendor's reinstall command from `references/vendors.md`, substituting `<skill-name>` and `<npx-agent-id>`:
   ```bash
   # Example for Tech Leads Club:
   npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
   ```
3. If the command fails, report the error and continue to the next skill.
4. Read the new `contentHash` from `.skill-meta.json` (after state). Store as `<hash-after>`.
5. Compare:
   - `<hash-before>` ≠ `<hash-after>` → mark as **updated**
   - `<hash-before>` = `<hash-after>` → mark as **already current**
   - `.skill-meta.json` absent before or after → mark as **updated** (cannot confirm; assume changed)

## Step 6: Re-apply Extended Skill Symlinks

For every skill processed in Step 5 (regardless of whether its content changed), check whether an `extended/<skill-name>/` directory exists at the project root. If yes:

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

If `extended/` does not exist at the project root, skip Step 6 silently for all skills.

## Step 7: Report

| Category | Details |
|----------|---------|
| **Updated** (content hash changed) | list skill names |
| **Already current** (no change) | list skill names |
| **Failed** (reinstall command errored) | list skill names with error |
| **Extended symlinks re-applied** | list symlink paths recreated |
| **Skipped** (unknown vendor) | list skill names with reason |

## Examples

### Example 1: Update all external skills

User: "update all skills"

1. Agent is `claude-code` → load `skills/agent-setup/references/claude-code.md` → skills dir is `~/.claude/skills/`, npx id is `claude-code`
2. Load `references/vendors.md`
3. Scan `~/.claude/skills/` → find real dirs (e.g. `skill-architect`, `coding-guidelines`, `best-practices`, …); skip symlinks
4. Match each real dir to a vendor via `.skill-meta.json` presence → all are Tech Leads Club
5. For each: snapshot hash → reinstall → compare hash
6. Re-apply extended symlinks for `skill-architect`, `coding-guidelines`
7. Report summary

### Example 2: Update a single skill

User: "update skill-architect"

1. Confirm `~/.claude/skills/skill-architect` is a real directory (not symlink)
2. Snapshot hash → run npx reinstall → compare hash
3. Re-apply `SKILL.extended.md` from `extended/skill-architect/`
4. Report

### Example 3: Update a set of skills

User: "update skill-architect, coding-guidelines, and best-practices"

1. Validate all three exist as real directories in `~/.claude/skills/`
2. Process sequentially: snapshot hash → reinstall → compare hash for each
3. Re-apply extended symlinks for `skill-architect` and `coding-guidelines`
4. Report all three in summary

### Example 4: User tries to update a local project skill

User: "update tech-reference-add"

1. `~/.claude/skills/tech-reference-add` is a symlink → error:
   > `tech-reference-add` is a local project symlink. It is always current — no update needed.

### Example 5: Unknown vendor

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
