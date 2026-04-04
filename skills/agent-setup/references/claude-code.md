# Claude Code — Agent Setup Reference

Agent identifier for npx: `claude-code`

## Global Config File

| Path | Notes |
|------|-------|
| `~/.claude/CLAUDE.md` | Symlink target for `AGENTS.global.md` |

## Skills Directory

```
~/.claude/skills/
```

Each skill is a subdirectory inside this folder. Project-sourced skills are symlinked; Tech Leads Club skills are copied via npx.

## Extended Skills

- `SKILL.extended.md` and `reference/` are symlinked directly into `~/.claude/skills/<skill-name>/`
- If the parent skill already has a `references/` directory (e.g. from npx install), name the incoming symlink `reference.extended` to avoid collision.

## npx Install Command

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent claude-code --global
```

## Native Skills (skip installation)

- `keybindings-help` — built into Claude Code, no file needed