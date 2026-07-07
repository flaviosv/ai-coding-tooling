---
name: mermaid-studio-extended
extends: mermaid-studio
description: >
  Extension for the mermaid-studio skill. This file MUST be read together with the parent
  mermaid-studio SKILL.md. The parent governs Mermaid diagram creation, validation, and
  rendering. This extension adds a required substitute renderer for multi-row C4 diagrams.
metadata:
  version: "1.0.0"
  parent_skill: mermaid-studio
  source: "ai-coding-tooling (extended/)"
---

# mermaid-studio — C4 Renderer Extension

> This file extends the **mermaid-studio** skill. The parent SKILL.md governs diagram
> creation, validation, and rendering. This extension overrides which script renders C4
> diagrams in one specific case.

## Use render-c4-fixed.mjs Instead of the Parent's render.mjs

For any C4 diagram whose `UpdateLayoutConfig` sets `c4ShapeInRow` or `c4BoundaryInRow`
above 1, render it with `scripts/render-c4-fixed.mjs` (sibling to this file), not the
parent's `scripts/render.mjs` — the parent's mmdc-based renderer collapses these diagrams
to one shape per row regardless of `--width`.

This skill is installed as a symlink at `~/.claude/skills/mermaid-studio/SKILL.extended.md`.
Resolve it to find this file's real directory, then run the sibling script from there:

```bash
real_dir="$(dirname "$(readlink -f ~/.claude/skills/mermaid-studio/SKILL.extended.md)")"
node "$real_dir/scripts/render-c4-fixed.mjs" \
  --input diagram.mmd --output diagram.png \
  --screen-width 3000 --scale 3
```

`--screen-width` (default 3000) must exceed the diagram's total row width; `--scale`
(default 3) is the device-scale-factor for PNG sharpness, matching the parent's `-s 3`.

The script reuses the parent skill's own puppeteer + mermaid install
(`~/.claude/skills/mermaid-studio/.deps`) — run the parent's `scripts/setup.sh` first if
`.deps` doesn't exist yet.

All other diagram types, and C4 diagrams without `c4ShapeInRow`/`c4BoundaryInRow` above 1,
still use the parent's `scripts/render.mjs` as normal.
