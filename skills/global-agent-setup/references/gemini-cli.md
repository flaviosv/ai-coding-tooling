# Gemini CLI — Agent Setup Reference

Agent identifier for npx: `gemini`

## Global Config File

| Path | Notes |
|------|-------|
| `~/.gemini/GEMINI.md` | Symlink target for `AGENTS.global.md` |

The `~/.gemini/` directory may not exist on first run — create it before symlinking:

```bash
mkdir -p ~/.gemini
```

## Skills Directory

```
~/.gemini/skills/
```

Create it before installing skills:

```bash
mkdir -p ~/.gemini/skills
```

Each skill is a subdirectory inside this folder. Project-sourced skills are symlinked; Tech Leads Club skills are copied via npx.

## Extended Skills

- `SKILL.extended.md` is symlinked into `~/.gemini/skills/<skill-name>/SKILL.extended.md`
- If the extended folder has a `reference/` directory and the parent skill already has a `references/` folder (e.g. from npx install), symlink it as `reference.extended` to avoid collision:
  ```bash
  ln -s "$(pwd)/extended/<skill-name>/reference" ~/.gemini/skills/<skill-name>/reference.extended
  ```
- If no collision, symlink as `reference`:
  ```bash
  ln -s "$(pwd)/extended/<skill-name>/reference" ~/.gemini/skills/<skill-name>/reference
  ```

## npx Install Command

```bash
npx @tech-leads-club/agent-skills install --skill <skill-name> --agent gemini --global
```

## Native Skills (skip installation)

None — Gemini CLI has no built-in skills that overlap with this project's skill list.
