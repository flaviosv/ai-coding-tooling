---
name: mermaid-studio-extended
extends: mermaid-studio
description: >
  Extension for the mermaid-studio skill. This file MUST be read together with the parent
  mermaid-studio SKILL.md. The parent governs Mermaid diagram creation, validation, and
  rendering. This extension adds a required substitute renderer for multi-row C4 diagrams,
  and a mandatory black-text override for any node/box that renders with a white or
  near-white background.
metadata:
  version: "1.1.0"
  parent_skill: mermaid-studio
  source: "ai-coding-tooling (extended/)"
---

# mermaid-studio — Renderer & Styling Extension

> This file extends the **mermaid-studio** skill. The parent SKILL.md governs diagram
> creation, validation, and rendering. This extension overrides which script renders C4
> diagrams in one specific case, and hardens the parent's default styling against
> white-on-white text.

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

## Force Black Text on White/Light Node Fills

> This extension overrides the parent's Rule 1 init directive: its template sets `mainBkg`
> (the default node background) to a near-white color (`#f8fafc`) but never sets
> `nodeTextColor`, so any node using that default background silently inherits
> `primaryTextColor` — which the same template sets to white. The result is white/near-white
> text on a white/near-white box: illegible. This is exactly what happened in a rendered
> `docs/codebase/ARCHITECTURE.md` diagram — every default-class box came out with the label
> nearly invisible against its own fill.

### Rule: Every White/Light Box Fill Must Declare Black Text Explicitly

Whenever a node, C4 element, or styled shape resolves to a white or near-white background —
via `mainBkg`, an unset `primaryColor`/`secondaryColor`/`tertiaryColor`, an explicit `fill:`
in `style`/`classDef`, or a C4 `UpdateElementStyle` with no `$bgColor` override — its text
color MUST be declared explicitly as black (`#000000`). Never leave it to inherit
`primaryTextColor` or any other theme-default text color; those are tuned for the *colored*
(non-white) nodes and will collide with a white/light fill.

**Corrected init directive** — add `nodeTextColor` to the parent's Rule 1 template whenever
`mainBkg` (or any node's resolved background) is white/near-white:

```
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#4f46e5', 'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#3730a3', 'lineColor': '#94a3b8',
  'secondaryColor': '#10b981', 'tertiaryColor': '#f59e0b',
  'background': '#ffffff', 'mainBkg': '#f8fafc',
  'nodeBorder': '#cbd5e1', 'clusterBkg': '#f1f5f9',
  'clusterBorder': '#e2e8f0', 'titleColor': '#1e293b',
  'edgeLabelBackground': '#ffffff', 'textColor': '#334155',
  'nodeTextColor': '#000000'
}}}%%
```

**Explicit `style`/`classDef` fills** — pair every white/light `fill:` with `color:#000000`
in the same declaration:

```
style A fill:#ffffff,stroke:#cbd5e1,color:#000000
classDef default fill:#f8fafc,stroke:#e2e8f0,color:#000000
```

**C4 `UpdateElementStyle`** — pair every light/unset `$bgColor` with black `$fontColor`:

```
UpdateElementStyle(elementAlias, $bgColor="#f8fafc", $fontColor="#000000", $borderColor="#cbd5e1")
```

Apply this check before every render, not only after a bug is spotted: if any node in the
diagram ends up white/near-white, its black text-color declaration must be present in that
same init/style/classDef/UpdateElementStyle line — never assumed inherited.
