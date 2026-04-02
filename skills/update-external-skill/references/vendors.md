# Vendor Registry

This file maps external skill vendors to their detection patterns and reinstall commands. The `update-external-skill` skill reads this file to identify who installed a given skill and how to update it.

---

## Tech Leads Club

**Detection:** A `.skill-meta.json` file is present inside the skill directory. Example content:

```json
{
  "contentHash": "7d98273930ef3622d6d5339403860722a26e5de91fdcf9d96738618aedd82c10",
  "downloadedAt": 1772127856091
}
```

**Reinstall command:**

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent <npx-agent-id> --global
```

Substitute `<skill-name>` with the skill directory name and `<npx-agent-id>` with the agent identifier from the agent reference file (e.g. `claude-code`, `gemini`, `cursor`).

**Notes:**
- Overwrites the skill directory in-place. Extended symlinks (SKILL.extended.md, reference/) are removed and must be re-applied after each reinstall.
- The `contentHash` in `.skill-meta.json` changes only when the registry publishes a new version. If it is identical before and after reinstall, the skill was already at the latest version.
- Requires Node.js and npx to be installed.

---

## Adding a new vendor

To support a new vendor, add a section below using this structure:

```markdown
## <Vendor Name>

**Detection:** Describe what distinguishes a skill installed by this vendor (e.g. a marker file, a specific directory structure, an entry in a manifest).

**Reinstall command:**

\`\`\`bash
<the shell command to reinstall, using <skill-name> and <npx-agent-id> as placeholders>
\`\`\`

**Notes:** Any caveats — whether it overwrites in-place, whether extended symlinks survive, etc.
```
